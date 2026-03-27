"""
选题管理API路由
提供AI选题生成和手动输入功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from models.request import CommonRequest
from pydantic import validator
from models.response import BaseResponse, DataResponse
from dao.topic_dao import TopicDAO
from dao.profile_dao import ProfileDAO
from database import Database, db
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


class GenerateScriptRequest(CommonRequest):
    """根据档案+选题生成文案请求"""
    profile_id: str
    topic: str
    style: Optional[str] = None

    @validator("profile_id", pre=True)
    def coerce_profile_id(cls, v):
        return str(v)


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


# ── 根据档案+选题生成文案 ──────────────────────────────────────

@router.post("/generate-script", response_model=DataResponse)
async def generate_script(
    request: GenerateScriptRequest,
    request_id: str = Depends(get_request_id)
):
    """根据档案信息和选题，直接生成短视频文案（无需视频分析）"""
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

        # 调用 LLM 生成文案
        script = await _generate_script_from_profile(profile, request.topic, request.style)

        return DataResponse(
            code=200,
            message="文案生成成功",
            data=script,
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文案生成失败: {e}")
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
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "longgraph"))
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


async def _generate_script_from_profile(profile: dict, topic: str, style: str = None) -> dict:
    """调用 LLM 根据档案+选题生成结构化文案"""
    import sys
    import json
    from pathlib import Path
    from openai import OpenAI

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "longgraph"))
    from config import LLMModel

    config = LLMModel.get_model_config("deepseek")
    client = OpenAI(api_key=config["api_key"](), base_url=config["base_url"])

    style_map = {
        "professional": "专业严谨，数据驱动，适合B端客户",
        "humorous": "幽默风趣，轻松活泼，容易传播",
        "emotional": "情感共鸣，走心故事，引发共情",
        "tutorial": "教学干货，步骤清晰，实用性强",
    }
    style_desc = style_map.get(style, "") if style else ""

    reference_section = ""
    if profile.get("video_url"):
        reference_section += f"\n- 参考视频链接：{profile['video_url']}"
    if profile.get("homepage_url"):
        reference_section += f"\n- 参考主页链接：{profile['homepage_url']}"

    prompt = f"""你是一位专业的短视频文案策划师和口播脚本撰写专家。请根据以下创作者档案和选题，生成一份完整的短视频文案。

【创作者档案】
- 档案名称：{profile.get('name', '')}
- 所属行业：{profile.get('industry', '')}
- 目标用户群体：{profile.get('target_audience', '')}
- 客户痛点：{profile.get('customer_pain_points', '')}
- 解决方案：{profile.get('solution', '')}
- 人设背景：{profile.get('persona_background', '')}
{reference_section}

【选题主题】
{topic}
{f"【文案风格】{style_desc}" if style_desc else ""}

---

请生成两部分内容：

## 第一部分：发布信息
- 视频标题：8-15字，吸睛
- 视频描述：30-50字
- 话题标签：5-8个
- 发布文案：适合直接复制发布

## 第二部分：TTS口播脚本
以{profile.get('persona_background', '')}的人设口吻撰写，口语化表达，像和朋友聊天一样自然。
紧扣{profile.get('industry', '')}行业背景，围绕"{profile.get('customer_pain_points', '')}"这个痛点，提供"{profile.get('solution', '')}"的方案。
短句为主，每句8-15字，多用细节描述、场景还原让内容更生动。
完整口播台词要求300-500字。

请严格按照以下 JSON 格式输出，不要输出任何其他内容：
{{{{
    "title": "视频标题（8-15字）",
    "description": "视频描述（30-50字）",
    "hashtags": ["#标签1", "#标签2", "#标签3"],
    "publish_text": "发布文案（含标签，100字以内）",
    "full_script": "完整口播台词（300-500字，自然口语化）",
    "segments": ["开头钩子句", "痛点共鸣句1", "痛点共鸣句2", "核心内容句1", "核心内容句2", "...", "结尾引导句"]
}}}}

直接返回JSON，不要输出其他内容："""

    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": "你是专业的短视频文案策划师。只输出JSON格式的内容，不要输出任何其他文字或markdown标记。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=4000
    )

    content = response.choices[0].message.content.strip()

    # 清理可能的 markdown 代码块标记
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
    if content.endswith("```"):
        content = content[:-3]

    try:
        script = json.loads(content)
    except json.JSONDecodeError:
        # JSON 解析失败，返回纯文本
        logger.warning(f"文案 JSON 解析失败，返回原始文本")
        script = {
            "title": topic,
            "description": "",
            "hashtags": [],
            "publish_text": content,
            "full_script": content,
            "segments": [content]
        }

    # 计算字数和预估时长
    full_text = script.get("full_script", "")
    script["word_count"] = len(full_text)
    script["estimated_duration"] = max(10, round(len(full_text) / 3.5, 1))  # 约3.5字/秒

    return script
