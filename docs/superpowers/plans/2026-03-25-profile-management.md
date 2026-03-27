# Profile Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add profile management so users can create profiles with industry, links, and analysis fields, then feed profiles to LLM for multi-version copy generation.

**Architecture:** Two new database tables (`profiles`, `user_industries`) with auto-isolation via existing `Database._ISOLATED_TABLES`. New DAO layer (`profile_dao.py`) for data access. New API router (`profiles.py`) for CRUD + industry management. New endpoint in `chain.py` for LLM copy generation from profiles.

**Tech Stack:** FastAPI, PyMySQL, Pydantic, OpenAI-compatible LLM API (via existing `analyze_and_generate` module)

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `python_services/dao/profile_dao.py` | Data access for profiles + user_industries tables |
| Create | `python_services/api/v1/profiles.py` | API routes for profile CRUD + industry management |
| Modify | `python_services/database.py:25-31` | Add `profiles` and `user_industries` to `_ISOLATED_TABLES` |
| Modify | `python_services/main.py:31,58-66,238-273` | Import + register profiles router, init profiles tables |
| Modify | `python_services/api/v1/chain.py:1-25,680` | Add `generate-from-profile` endpoint |

---

### Task 1: Add tables to Database isolation

**Files:**
- Modify: `python_services/database.py:25-31`

- [ ] **Step 1: Add `profiles` and `user_industries` to `_ISOLATED_TABLES`**

In `python_services/database.py`, update the `_ISOLATED_TABLES` set (line 25-31):

```python
    _ISOLATED_TABLES = {
        "tasks",
        "generated_resources",
        "douyin_fetch_tasks",
        "douyin_videos",
        "operation_logs",
        "profiles",
        "user_industries",
    }
```

- [ ] **Step 2: Commit**

```bash
git add python_services/database.py
git commit -m "feat: add profiles and user_industries to isolated tables"
```

---

### Task 2: Create ProfileDAO

**Files:**
- Create: `python_services/dao/profile_dao.py`

- [ ] **Step 1: Create `dao/profile_dao.py` with table init + CRUD + industry management**

```python
"""
档案数据访问层
管理用户档案和自定义行业
"""

from typing import Optional, List, Dict
from database import db
from core.logger import get_logger

logger = get_logger("dao:profile")

# 系统预设行业
SYSTEM_INDUSTRIES = [
    "美食", "科技", "美妆", "穿搭", "母婴", "教育",
    "健身", "旅行", "汽车", "房产", "家居", "宠物",
    "医疗", "金融", "法律", "娱乐", "电商", "其他"
]


class ProfileDAO:
    """档案数据访问对象"""

    @staticmethod
    def init_tables():
        """初始化档案表和用户行业表"""
        profiles_sql = """
        CREATE TABLE IF NOT EXISTS profiles (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            profile_id VARCHAR(64) UNIQUE NOT NULL,
            user_id BIGINT NOT NULL,
            name VARCHAR(100) NOT NULL COMMENT '档案名称',
            industry VARCHAR(200) NOT NULL COMMENT '所需行业',
            video_url VARCHAR(500) COMMENT '视频链接',
            homepage_url VARCHAR(500) COMMENT '主页链接',
            target_audience TEXT NOT NULL COMMENT '目标用户群体',
            customer_pain_points TEXT NOT NULL COMMENT '客户痛点',
            solution TEXT NOT NULL COMMENT '解决方案',
            persona_background TEXT NOT NULL COMMENT '人设背景',
            status VARCHAR(20) DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_user_status (user_id, status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户档案表'
        """
        industries_sql = """
        CREATE TABLE IF NOT EXISTS user_industries (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            user_id BIGINT NOT NULL,
            name VARCHAR(100) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_industry (user_id, name),
            INDEX idx_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户自定义行业'
        """
        try:
            db.execute(profiles_sql)
            db.execute(industries_sql)
            logger.info("✅ 档案表初始化完成")
        except Exception as e:
            logger.warning(f"档案表初始化失败（可能已存在）: {e}")

    # ── 档案 CRUD ──────────────────────────────────────

    @staticmethod
    def create_profile(
        user_db_id: int,
        profile_id: str,
        name: str,
        industry: str,
        target_audience: str,
        customer_pain_points: str,
        solution: str,
        persona_background: str,
        video_url: Optional[str] = None,
        homepage_url: Optional[str] = None,
    ) -> int:
        """创建档案"""
        sql = """
            INSERT INTO profiles
            (profile_id, user_id, name, industry, video_url, homepage_url,
             target_audience, customer_pain_points, solution, persona_background)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return db.insert_return_id(sql, (
            profile_id, user_db_id, name, industry, video_url, homepage_url,
            target_audience, customer_pain_points, solution, persona_background
        ))

    @staticmethod
    def get_profile(profile_id: str) -> Optional[Dict]:
        """根据 profile_id 获取档案（自动按 user_id 过滤）"""
        sql = "SELECT * FROM profiles WHERE profile_id = %s AND status = 'active'"
        return db.fetch_one(sql, (profile_id,))

    @staticmethod
    def list_profiles(limit: int = 50, offset: int = 0) -> List[Dict]:
        """获取当前用户的档案列表（自动按 user_id 过滤）"""
        sql = """
            SELECT * FROM profiles
            WHERE status = 'active'
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        return db.fetch_all(sql, (limit, offset))

    @staticmethod
    def update_profile(
        profile_id: str,
        name: Optional[str] = None,
        industry: Optional[str] = None,
        video_url: Optional[str] = None,
        homepage_url: Optional[str] = None,
        target_audience: Optional[str] = None,
        customer_pain_points: Optional[str] = None,
        solution: Optional[str] = None,
        persona_background: Optional[str] = None,
    ) -> bool:
        """更新档案"""
        fields = []
        params = []
        for field, value in [
            ("name", name), ("industry", industry),
            ("video_url", video_url), ("homepage_url", homepage_url),
            ("target_audience", target_audience),
            ("customer_pain_points", customer_pain_points),
            ("solution", solution), ("persona_background", persona_background),
        ]:
            if value is not None:
                fields.append(f"{field} = %s")
                params.append(value)

        if not fields:
            return False

        params.append(profile_id)
        sql = f"UPDATE profiles SET {', '.join(fields)} WHERE profile_id = %s AND status = 'active'"
        affected = db.execute(sql, tuple(params))
        return affected > 0

    @staticmethod
    def delete_profile(profile_id: str) -> bool:
        """软删除档案（设置 status = deleted）"""
        sql = "UPDATE profiles SET status = 'deleted' WHERE profile_id = %s AND status = 'active'"
        affected = db.execute(sql, (profile_id,))
        return affected > 0

    # ── 行业管理 ──────────────────────────────────────

    @staticmethod
    def get_custom_industries() -> List[Dict]:
        """获取当前用户的自定义行业列表（自动按 user_id 过滤）"""
        sql = "SELECT * FROM user_industries ORDER BY created_at DESC"
        return db.fetch_all(sql)

    @staticmethod
    def add_custom_industry(user_db_id: int, name: str) -> int:
        """添加自定义行业"""
        sql = "INSERT INTO user_industries (user_id, name) VALUES (%s, %s)"
        return db.insert_return_id(sql, (user_db_id, name))

    @staticmethod
    def delete_custom_industry(industry_id: int) -> bool:
        """删除自定义行业"""
        sql = "DELETE FROM user_industries WHERE id = %s"
        affected = db.execute(sql, (industry_id,))
        return affected > 0
```

- [ ] **Step 2: Commit**

```bash
git add python_services/dao/profile_dao.py
git commit -m "feat: add ProfileDAO with table init, CRUD, and industry management"
```

---

### Task 3: Create profiles API router

**Files:**
- Create: `python_services/api/v1/profiles.py`

- [ ] **Step 1: Create `api/v1/profiles.py` with all endpoints**

```python
"""
档案管理API路由
提供档案CRUD和行业管理功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from models.request import CommonRequest
from models.response import BaseResponse, DataResponse
from dao.profile_dao import ProfileDAO, SYSTEM_INDUSTRIES
from database import Database
from core.logger import get_logger
from api.deps import get_request_id

logger = get_logger("api:profiles")
router = APIRouter(prefix="/profiles", tags=["档案管理"])


# ── 请求模型 ──────────────────────────────────────

class CreateProfileRequest(CommonRequest):
    """创建档案请求"""
    name: str  # 档案名称
    industry: str  # 所需行业
    video_url: Optional[str] = None  # 视频链接
    homepage_url: Optional[str] = None  # 主页链接
    target_audience: str  # 目标用户群体
    customer_pain_points: str  # 客户痛点
    solution: str  # 解决方案
    persona_background: str  # 人设背景


class UpdateProfileRequest(CommonRequest):
    """更新档案请求"""
    name: Optional[str] = None
    industry: Optional[str] = None
    video_url: Optional[str] = None
    homepage_url: Optional[str] = None
    target_audience: Optional[str] = None
    customer_pain_points: Optional[str] = None
    solution: Optional[str] = None
    persona_background: Optional[str] = None


class AddIndustryRequest(CommonRequest):
    """添加自定义行业请求"""
    name: str


# ── 档案 CRUD ──────────────────────────────────────

@router.post("", response_model=DataResponse)
async def create_profile(
    request: CreateProfileRequest,
    request_id: str = Depends(get_request_id)
):
    """创建档案"""
    try:
        user_db_id = Database.get_current_user_id()
        if not user_db_id:
            raise HTTPException(status_code=401, detail="用户未登录")

        import uuid
        profile_id = f"profile_{uuid.uuid4().hex[:12]}"

        pid = ProfileDAO.create_profile(
            user_db_id=user_db_id,
            profile_id=profile_id,
            name=request.name,
            industry=request.industry,
            video_url=request.video_url,
            homepage_url=request.homepage_url,
            target_audience=request.target_audience,
            customer_pain_points=request.customer_pain_points,
            solution=request.solution,
            persona_background=request.persona_background,
        )

        return DataResponse(
            code=201,
            message="档案创建成功",
            data={"profile_id": profile_id, "id": pid},
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建档案失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=DataResponse)
async def list_profiles(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    request_id: str = Depends(get_request_id)
):
    """获取当前用户的档案列表"""
    try:
        profiles = ProfileDAO.list_profiles(limit=limit, offset=offset)

        return DataResponse(
            code=200,
            message="success",
            data={"profiles": profiles, "total": len(profiles)},
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"获取档案列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{profile_id}", response_model=DataResponse)
async def get_profile(
    profile_id: str,
    request_id: str = Depends(get_request_id)
):
    """获取档案详情"""
    try:
        profile = ProfileDAO.get_profile(profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="档案不存在")

        return DataResponse(
            code=200,
            message="success",
            data=profile,
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取档案详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{profile_id}", response_model=BaseResponse)
async def update_profile(
    profile_id: str,
    request: UpdateProfileRequest,
    request_id: str = Depends(get_request_id)
):
    """更新档案"""
    try:
        success = ProfileDAO.update_profile(
            profile_id=profile_id,
            name=request.name,
            industry=request.industry,
            video_url=request.video_url,
            homepage_url=request.homepage_url,
            target_audience=request.target_audience,
            customer_pain_points=request.customer_pain_points,
            solution=request.solution,
            persona_background=request.persona_background,
        )
        if not success:
            raise HTTPException(status_code=404, detail="档案不存在或未修改")

        return BaseResponse(
            code=200,
            message="档案更新成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新档案失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{profile_id}", response_model=BaseResponse)
async def delete_profile(
    profile_id: str,
    request_id: str = Depends(get_request_id)
):
    """删除档案（软删除）"""
    try:
        success = ProfileDAO.delete_profile(profile_id)
        if not success:
            raise HTTPException(status_code=404, detail="档案不存在")

        return BaseResponse(
            code=200,
            message="档案已删除",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除档案失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── 行业管理 ──────────────────────────────────────

@router.get("/industries", response_model=DataResponse)
async def get_industries(
    request_id: str = Depends(get_request_id)
):
    """
    获取行业列表（系统预设 + 用户自定义）

    返回合并后的列表，包含系统预设行业和当前用户的自定义行业
    """
    try:
        custom = ProfileDAO.get_custom_industries()
        custom_names = [item["name"] for item in custom]

        # 合并去重
        all_industries = list(SYSTEM_INDUSTRIES)
        for name in custom_names:
            if name not in all_industries:
                all_industries.append(name)

        return DataResponse(
            code=200,
            message="success",
            data={
                "system": SYSTEM_INDUSTRIES,
                "custom": [{"id": item["id"], "name": item["name"]} for item in custom],
                "all": all_industries
            },
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"获取行业列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/industries", response_model=DataResponse)
async def add_custom_industry(
    request: AddIndustryRequest,
    request_id: str = Depends(get_request_id)
):
    """添加自定义行业"""
    try:
        user_db_id = Database.get_current_user_id()
        if not user_db_id:
            raise HTTPException(status_code=401, detail="用户未登录")

        # 检查是否已存在（系统预设或自定义）
        if request.name in SYSTEM_INDUSTRIES:
            raise HTTPException(status_code=409, detail="该行业已存在于系统预设中")

        custom = ProfileDAO.get_custom_industries()
        if any(item["name"] == request.name for item in custom):
            raise HTTPException(status_code=409, detail="该行业已存在")

        industry_id = ProfileDAO.add_custom_industry(user_db_id, request.name)

        return DataResponse(
            code=201,
            message="自定义行业添加成功",
            data={"id": industry_id, "name": request.name},
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加自定义行业失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/industries/{industry_id}", response_model=BaseResponse)
async def delete_custom_industry(
    industry_id: int,
    request_id: str = Depends(get_request_id)
):
    """删除自定义行业"""
    try:
        success = ProfileDAO.delete_custom_industry(industry_id)
        if not success:
            raise HTTPException(status_code=404, detail="自定义行业不存在")

        return BaseResponse(
            code=200,
            message="自定义行业已删除",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除自定义行业失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: Commit**

```bash
git add python_services/api/v1/profiles.py
git commit -m "feat: add profiles API router with CRUD and industry management"
```

---

### Task 4: Add `generate-from-profile` endpoint to chain.py

**Files:**
- Modify: `python_services/api/v1/chain.py:1-25,680`

- [ ] **Step 1: Add request model and endpoint**

At the top of `chain.py`, after the existing request models (after line 68), add the new request model:

```python
class GenerateFromProfileRequest(CommonRequest):
    """根据档案生成文案请求"""
    profile_id: str  # 档案ID
    generate_type: str = "video_script"  # video_script 或 text_copy
    topic: Optional[str] = None  # 可选的主题补充
    count: int = 3  # 生成版本数量
```

At the end of `chain.py` (after line 680), add the new endpoint:

```python
@router.post("/generate-from-profile", response_model=TaskResponse)
async def generate_from_profile(
    request: GenerateFromProfileRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    根据档案生成文案（支持短视频脚本和纯文字文案）

    流程：
    1. 从 profiles 表获取档案信息
    2. 组装 prompt 发送给大模型
    3. 返回 3 个版本的文案供用户选择

    请求参数：
    - profile_id: 档案ID
    - generate_type: video_script（短视频脚本）或 text_copy（纯文字文案）
    - topic: 可选的主题补充
    - count: 生成版本数量（默认3）

    返回：任务 task_id，任务完成后 result 中包含多个版本的文案
    """
    try:
        from dao.profile_dao import ProfileDAO

        # 1. 获取档案
        profile = ProfileDAO.get_profile(request.profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"档案不存在: {request.profile_id}")

        logger.info(f"从档案生成文案: profile={request.profile_id}, type={request.generate_type}")

        # 2. 组装 prompt
        type_desc = "短视频脚本（含分镜、台词、时长建议）" if request.generate_type == "video_script" else "纯文字文案（适合社交媒体发布）"

        topic_section = f"\n补充主题：{request.topic}" if request.topic else ""

        reference_section = ""
        if profile.get("video_url"):
            reference_section += f"\n- 参考视频：{profile['video_url']}"
        if profile.get("homepage_url"):
            reference_section += f"\n- 参考主页：{profile['homepage_url']}"

        prompt = f"""你是一个专业的内容策划师，请根据以下档案信息生成{type_desc}：

行业：{profile['industry']}
目标用户群体：{profile['target_audience']}
客户痛点：{profile['customer_pain_points']}
解决方案：{profile['solution']}
人设背景：{profile['persona_background']}
{reference_section}{topic_section}

请生成 {request.count} 个不同风格的版本，每个版本之间用 "---VERSION---" 分隔。
每个版本应包含：标题、正文内容。"""

        # 3. 创建任务
        task_id = task_manager.create_task("chain_generate_from_profile", {
            "profile_id": request.profile_id,
            "generate_type": request.generate_type,
            "count": request.count
        })

        # 4. 调用大模型
        async def run_generation():
            from core.config import settings
            import httpx

            # 获取 LLM 配置
            api_key = settings.get("DASHSCOPE_API_KEY", "")
            base_url = settings.get("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            model = settings.get("LLM_MODEL", "qwen-plus")

            if not api_key:
                raise ValueError("未配置 LLM API Key")

            task_manager.update_progress(task_id, 20, "正在调用大模型...")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "你是一个专业的内容策划师，擅长根据用户档案信息生成高质量的短视频脚本和文案。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.8,
                    }
                )
                response.raise_for_status()
                result = response.json()

            content = result["choices"][0]["message"]["content"]
            task_manager.update_progress(task_id, 80, "文案生成完成，正在解析...")

            # 解析多个版本
            versions = [v.strip() for v in content.split("---VERSION---") if v.strip()]

            # 如果分隔符没生效，按整体返回一个版本
            if len(versions) <= 1:
                versions = [content.strip()]

            result_data = {
                "versions": [
                    {"index": i + 1, "content": v}
                    for i, v in enumerate(versions[:request.count])
                ],
                "profile_id": request.profile_id,
                "generate_type": request.generate_type,
            }

            task_manager.update_progress(task_id, 100, "完成")
            return result_data

        import asyncio
        try:
            asyncio.create_task(task_manager.submit_task(task_id, run_generation))
        except RuntimeError:
            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(task_manager.submit_task(task_id, run_generation))
                finally:
                    new_loop.close()
            background_tasks.add_task(run_in_new_loop)

        task = task_manager.get_task(task_id)
        return TaskResponse(
            code=200,
            message="文案生成任务已创建",
            task_id=task_id,
            status=TaskStatus(task.status.value),
            progress=task.progress,
            created_at=task.created_at,
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从档案生成文案失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: Verify `httpx` is available in requirements**

Check if `httpx` is in `python_services/requirements.txt`. If not, add it:

```bash
grep -q "^httpx" python_services/requirements.txt || echo "httpx>=0.24.0" >> python_services/requirements.txt
```

- [ ] **Step 3: Commit**

```bash
git add python_services/api/v1/chain.py python_services/requirements.txt
git commit -m "feat: add generate-from-profile endpoint for LLM copy generation"
```

---

### Task 5: Register routes and init tables in main.py

**Files:**
- Modify: `python_services/main.py:31,58-66,238-273`

- [ ] **Step 1: Import profiles router**

In `python_services/main.py` line 31, add `profiles` to the import:

```python
from api.v1 import douyin, ai, tts, video, storage, users, chain, resources, profiles
```

- [ ] **Step 2: Init profiles tables in lifespan**

In `main.py` inside the lifespan function, after line 66 (`ResourceDAO.init_table()`), add:

```python
            from dao.profile_dao import ProfileDAO
            ProfileDAO.init_tables()  # 档案表
```

- [ ] **Step 3: Register profiles router**

In `main.py` `_setup_routes` function, after the resources router block (after line 273), add:

```python
    # 档案管理路由
    app.include_router(
        profiles.router,
        prefix=settings.API_PREFIX,
    )
```

- [ ] **Step 4: Commit**

```bash
git add python_services/main.py
git commit -m "feat: register profiles router and init tables on startup"
```

---

### Task 6: Smoke test

- [ ] **Step 1: Start the server and verify**

```bash
cd python_services && python run_server.py
```

Expected log output should include:
- `✅ 档案表初始化完成`
- `✅ 路由注册完成`

- [ ] **Step 2: Test with curl (or API docs)**

1. Open `http://localhost:8000/docs` — verify `/api/v1/profiles` endpoints appear
2. Test `GET /api/v1/profiles/industries` — should return system industries list
3. Test `POST /api/v1/profiles` — create a profile
4. Test `GET /api/v1/profiles` — list profiles
5. Test `POST /api/v1/chain/generate-from-profile` — generate copy from profile
