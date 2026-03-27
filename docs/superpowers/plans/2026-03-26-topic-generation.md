# AI 选题生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 根据用户档案，AI 生成短视频选题标题，支持用户自定义输入

**Architecture:** 新建 topics 表和 TopicDAO，新建 topics API 路由。AI 生成复用现有 OpenAI 兼容接口（DeepSeek）。同一个 profile_id 的 AI 选题只保留最新一条（覆盖），手动输入的选题追加存储。

**Tech Stack:** FastAPI, MySQL (pymysql), OpenAI-compatible API (DeepSeek)

---

### Task 1: 创建 topics 数据表

**Files:**
- Modify: `python_services/dao/topic_dao.py` (create)

- [ ] **Step 1: 创建 TopicDAO，包含建表和 CRUD 方法**

```python
"""
选题数据访问层
"""
from typing import Optional, List, Dict
from database import db
from core.logger import get_logger

logger = get_logger("dao:topic")


class TopicDAO:
    """选题数据访问对象"""

    @staticmethod
    def init_table():
        """初始化选题表"""
        sql = """
        CREATE TABLE IF NOT EXISTS topics (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            user_id BIGINT NOT NULL,
            profile_id VARCHAR(64) NOT NULL,
            title VARCHAR(200) NOT NULL COMMENT '选题标题',
            source VARCHAR(20) NOT NULL DEFAULT 'custom' COMMENT '来源: ai/custom',
            status VARCHAR(20) DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_profile_id (profile_id),
            INDEX idx_user_status (user_id, status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='选题表'
        """
        try:
            db.execute(sql)
            logger.info("✅ 选题表初始化完成")
        except Exception as e:
            logger.warning(f"选题表初始化失败（可能已存在）: {e}")

    @staticmethod
    def _resolve_id(raw_id: str):
        if raw_id.isdigit():
            return "id", int(raw_id)
        return "id", int(raw_id)  # topic 只有数字 id

    @staticmethod
    def create_topic(user_db_id: int, profile_id: str, title: str, source: str = "custom") -> int:
        """创建选题"""
        sql = """
            INSERT INTO topics (user_id, profile_id, title, source)
            VALUES (%s, %s, %s, %s)
        """
        return db.insert_return_id(sql, (user_db_id, profile_id, title, source))

    @staticmethod
    def upsert_ai_topic(user_db_id: int, profile_id: str, title: str) -> int:
        """创建或覆盖 AI 选题（同一 profile_id 只保留一条）"""
        # 先检查是否已存在
        check_sql = "SELECT id FROM topics WHERE profile_id = %s AND source = 'ai' AND status = 'active'"
        existing = db.fetch_one(check_sql, (profile_id,))
        if existing:
            update_sql = "UPDATE topics SET title = %s WHERE id = %s"
            db.execute(update_sql, (title, existing["id"]))
            return existing["id"]
        else:
            return TopicDAO.create_topic(user_db_id, profile_id, title, source="ai")

    @staticmethod
    def list_topics(profile_id: str = None, limit: int = 50, offset: int = 0) -> List[Dict]:
        """获取选题列表"""
        if profile_id:
            sql = """
                SELECT * FROM topics
                WHERE profile_id = %s AND status = 'active'
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            return db.fetch_all(sql, (profile_id, limit, offset))
        else:
            sql = """
                SELECT * FROM topics
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            return db.fetch_all(sql, (limit, offset))

    @staticmethod
    def update_topic(topic_id: int, title: str) -> bool:
        """更新选题标题"""
        sql = "UPDATE topics SET title = %s WHERE id = %s AND status = 'active'"
        affected = db.execute(sql, (title, topic_id))
        return affected > 0

    @staticmethod
    def delete_topic(topic_id: int) -> bool:
        """软删除选题"""
        sql = "UPDATE topics SET status = 'deleted' WHERE id = %s"
        affected = db.execute(sql, (topic_id,))
        return affected > 0
```

- [ ] **Step 2: 在 main.py 中注册 TopicDAO.init_table()**

在 `main.py` 约 line 68 `ProfileDAO.init_tables()` 之后添加：

```python
from dao.topic_dao import TopicDAO
TopicDAO.init_table()
```

同时将 `topics` 添加到 `database.py` 的 `_ISOLATED_TABLES` 集合中。

- [ ] **Step 3: 验证表创建**

重启服务，检查日志中是否出现 `✅ 选题表初始化完成`。

---

### Task 2: 创建选题 API 路由

**Files:**
- Create: `python_services/api/v1/topics.py`
- Modify: `python_services/main.py` (register router)

- [ ] **Step 1: 创建 topics.py 路由文件**

```python
"""
选题管理API路由
提供AI选题生成和手动输入功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from models.request import CommonRequest
from models.response import BaseResponse, DataResponse
from dao.topic_dao import TopicDAO
from dao.profile_dao import ProfileDAO
from database import Database
from core.logger import get_logger
from api.deps import get_request_id

logger = get_logger("api:topics")
router = APIRouter(prefix="/topics", tags=["选题管理"])


class GenerateTopicRequest(CommonRequest):
    """AI生成选题请求"""
    profile_id: str


class CreateTopicRequest(CommonRequest):
    """手动输入选题请求"""
    profile_id: str
    title: str


class UpdateTopicRequest(CommonRequest):
    """更新选题请求"""
    title: str


# ── AI 生成选题 ──────────────────────────────────────

@router.post("/generate", response_model=DataResponse)
async def generate_topic(
    request: GenerateTopicRequest,
    request_id: str = Depends(get_request_id)
):
    """AI 根据档案生成选题（覆盖上一次 AI 选题）"""
    try:
        user_db_id = Database.get_current_user_id()
        if not user_db_id:
            raise HTTPException(status_code=401, detail="用户未登录")

        # 获取档案信息
        col, val = ProfileDAO._resolve_id(request.profile_id)
        profile = db.fetch_one(
            f"SELECT * FROM profiles WHERE {col} = %s AND status = 'active'",
            (val,)
        )
        if not profile:
            raise HTTPException(status_code=404, detail="档案不存在")

        # 调用 AI 生成选题
        from database import db as _db
        title = await _generate_topic_title(profile)

        # 覆盖保存
        topic_id = TopicDAO.upsert_ai_topic(
            user_db_id=user_db_id,
            profile_id=profile["profile_id"],
            title=title
        )

        return DataResponse(
            code=201,
            message="选题生成成功",
            data={"id": topic_id, "title": title, "source": "ai"},
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI生成选题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── 手动输入选题 ──────────────────────────────────────

@router.post("", response_model=DataResponse)
async def create_topic(
    request: CreateTopicRequest,
    request_id: str = Depends(get_request_id)
):
    """用户手动输入选题"""
    try:
        user_db_id = Database.get_current_user_id()
        if not user_db_id:
            raise HTTPException(status_code=401, detail="用户未登录")

        # 验证档案存在
        col, val = ProfileDAO._resolve_id(request.profile_id)
        profile = db.fetch_one(
            f"SELECT * FROM profiles WHERE {col} = %s AND status = 'active'",
            (val,)
        )
        if not profile:
            raise HTTPException(status_code=404, detail="档案不存在")

        topic_id = TopicDAO.create_topic(
            user_db_id=user_db_id,
            profile_id=profile["profile_id"],
            title=request.title,
            source="custom"
        )

        return DataResponse(
            code=201,
            message="选题创建成功",
            data={"id": topic_id, "title": request.title, "source": "custom"},
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建选题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── 选题列表 ──────────────────────────────────────

@router.get("", response_model=DataResponse)
async def list_topics(
    profile_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    request_id: str = Depends(get_request_id)
):
    """获取选题列表"""
    try:
        topics = TopicDAO.list_topics(profile_id=profile_id, limit=limit, offset=offset)
        return DataResponse(
            code=200,
            message="success",
            data={"topics": topics, "total": len(topics)},
            request_id=request_id
        )
    except Exception as e:
        logger.error(f"获取选题列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── 更新/删除 ──────────────────────────────────────

@router.put("/{topic_id}", response_model=BaseResponse)
async def update_topic(
    topic_id: int,
    request: UpdateTopicRequest,
    request_id: str = Depends(get_request_id)
):
    """更新选题标题"""
    try:
        success = TopicDAO.update_topic(topic_id, request.title)
        if not success:
            raise HTTPException(status_code=404, detail="选题不存在")
        return BaseResponse(code=200, message="选题更新成功", request_id=request_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新选题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{topic_id}", response_model=BaseResponse)
async def delete_topic(
    topic_id: int,
    request_id: str = Depends(get_request_id)
):
    """删除选题"""
    try:
        success = TopicDAO.delete_topic(topic_id)
        if not success:
            raise HTTPException(status_code=404, detail="选题不存在")
        return BaseResponse(code=200, message="选题已删除", request_id=request_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除选题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── AI 选题生成逻辑 ──────────────────────────────────────

async def _generate_topic_title(profile: dict) -> str:
    """调用 LLM 根据档案生成一个选题标题"""
    import sys
    from pathlib import Path
    from openai import OpenAI

    # 复用 longgraph 的配置
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "longgraph"))
    from config import LLMModel

    config = LLMModel.get_model_config("deepseek")
    client = OpenAI(api_key=config["api_key"](), base_url=config["base_url"])

    prompt = f"""你是一个短视频选题专家。根据以下创作者档案信息，生成一个有吸引力的短视频选题标题。

档案信息：
- 行业: {profile.get('industry', '')}
- 目标用户: {profile.get('target_audience', '')}
- 客户痛点: {profile.get('customer_pain_points', '')}
- 解决方案: {profile.get('solution', '')}
- 人设背景: {profile.get('persona_background', '')}

要求：
1. 只输出一个选题标题，不要任何解释或多余内容
2. 标题要简洁有力，10-25个字
3. 要切中目标用户的痛点
4. 适合短视频传播，有话题性

选题标题："""

    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": "你是专业的短视频选题专家。只输出选题标题，不要任何其他内容。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=100
    )

    title = response.choices[0].message.content.strip()
    # 清理可能的多余引号
    title = title.strip('"\'""''')
    return title
```

注意：topics.py 中有两处用了 `from database import db as _db` 需要在文件顶部统一 import。修正后的 import 部分：

```python
from database import Database, db
```

- [ ] **Step 2: 在 main.py 中注册路由**

在 `main.py` line 31 的 import 行添加 `topics`：
```python
from api.v1 import douyin, ai, tts, video, storage, users, chain, resources, profiles, topics
```

在路由注册部分添加：
```python
app.include_router(topics.router, prefix="/api/v1")
```

- [ ] **Step 3: 将 topics 加入用户隔离表**

在 `database.py` 的 `_ISOLATED_TABLES` 集合中添加 `"topics"`。

- [ ] **Step 4: 重启服务验证**

```bash
# 测试获取选题列表
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/topics

# 测试手动输入选题
curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"profile_id": "<id>", "title": "测试选题"}' \
  http://localhost:8000/api/v1/topics

# 测试 AI 生成选题
curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"profile_id": "<id>"}' \
  http://localhost:8000/api/v1/topics/generate
```

- [ ] **Step 5: Commit**

```bash
git add python_services/dao/topic_dao.py python_services/api/v1/topics.py python_services/main.py python_services/database.py
git commit -m "feat: add AI topic generation based on profiles"
```
