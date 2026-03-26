# Voices User Data Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user data isolation to the `voices` table so each user only sees their own voices, while admins can see all.

**Architecture:** Add `"voices"` to the existing `_ISOLATED_TABLES` auto-filter mechanism in `Database`. Switch `list_voices` and `get_voice` API endpoints from Dashscope direct calls to local DB queries via `VoiceDAO`. Add an admin endpoint for viewing all voices. Save voice records to DB on creation.

**Tech Stack:** Python, FastAPI, MySQL, existing Database auto-filter mechanism

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `python_services/database.py` | Modify | Add `"voices"` to `_ISOLATED_TABLES` |
| `python_services/dao/voice_dao.py` | Modify | Remove manual user_id from `list_by_user` → `list_voices`; add `skip_user_filter=True` to `list_all` |
| `python_services/api/v1/tts.py` | Modify | Switch list/get endpoints to use VoiceDAO; add admin endpoint; save to DB on creation |

---

### Task 1: Add voices to _ISOLATED_TABLES

**Files:**
- Modify: `python_services/database.py:25-33`

- [ ] **Step 1: Add "voices" to the isolated tables set**

In `python_services/database.py`, line 25-33, change `_ISOLATED_TABLES` to include `"voices"`:

```python
    _ISOLATED_TABLES = {
        "tasks",
        "generated_resources",
        "douyin_fetch_tasks",
        "douyin_videos",
        "operation_logs",
        "profiles",
        "user_industries",
        "voices",
    }
```

- [ ] **Step 2: Commit**

```bash
git add python_services/database.py
git commit -m "feat: add voices to _ISOLATED_TABLES for user data isolation"
```

---

### Task 2: Simplify VoiceDAO to use auto-filter

**Files:**
- Modify: `python_services/dao/voice_dao.py`

- [ ] **Step 1: Rename `list_by_user` to `list_voices` and remove manual user_id filtering**

Replace the `list_by_user` method (lines 63-76) with `list_voices` that relies on Database auto-filter:

```python
    @staticmethod
    def list_voices(status: str = None) -> list:
        """获取当前用户的音色列表（自动按 user_id 过滤）"""
        if status:
            sql = "SELECT * FROM voices WHERE status = %s ORDER BY created_at DESC"
            rows = db.fetch_all(sql, (status,))
        else:
            sql = "SELECT * FROM voices ORDER BY created_at DESC"
            rows = db.fetch_all(sql)
        return rows
```

Note: No `user_db_id` param needed — `db.fetch_all` will auto-append `WHERE user_id = ?`.

- [ ] **Step 2: Add `skip_user_filter=True` to `list_all`**

In `list_all` method (lines 78-100), add `skip_user_filter=True` to both `db.fetch_all` calls:

```python
    @staticmethod
    def list_all(status: str = None, limit: int = 100) -> List[dict]:
        """获取所有音色（管理员用，跳过用户过滤）"""
        if status:
            sql = """
                SELECT v.*, u.username
                FROM voices v
                LEFT JOIN users u ON v.user_id = u.id
                WHERE v.status = %s
                ORDER BY v.created_at DESC
                LIMIT %s
            """
            rows = db.fetch_all(sql, (status, limit), skip_user_filter=True)
        else:
            sql = """
                SELECT v.*, u.username
                FROM voices v
                LEFT JOIN users u ON v.user_id = u.id
                ORDER BY v.created_at DESC
                LIMIT %s
            """
            rows = db.fetch_all(sql, (limit,), skip_user_filter=True)
        return rows
```

- [ ] **Step 3: Commit**

```bash
git add python_services/dao/voice_dao.py
git commit -m "refactor: simplify VoiceDAO to use Database auto-filter"
```

---

### Task 3: Switch API endpoints to use VoiceDAO and save on creation

**Files:**
- Modify: `python_services/api/v1/tts.py`

- [ ] **Step 1: Add VoiceDAO import and `require_admin` dependency**

At the top of `python_services/api/v1/tts.py`, add the import:

```python
from dao.voice_dao import VoiceDAO
from api.deps import get_request_id, require_admin
```

Note: `require_admin` is already available in `api.deps`. Update the existing `from api.deps import get_request_id` line.

- [ ] **Step 2: Rewrite `list_voices` endpoint to use VoiceDAO**

Replace the `list_voices` function (lines 162-204) with:

```python
@router.get("/voice/list", response_model=VoiceListResponse)
async def list_voices(
    request_id: str = Depends(get_request_id)
):
    """
    获取当前用户的音色列表（自动按用户隔离）
    """
    try:
        voices = VoiceDAO.list_voices()

        voice_infos = []
        for v in voices:
            created_at = ""
            if v.get("gmt_create"):
                created_at = str(v["gmt_create"])
            elif v.get("created_at"):
                created_at = str(v["created_at"])

            voice_infos.append(VoiceInfo(
                voice_id=v.get("voice_id", ""),
                prefix=v.get("prefix", ""),
                model=v.get("target_model") or v.get("model", ""),
                status=v.get("status", "UNKNOWN"),
                created_at=created_at,
                is_available=v.get("status") == "OK"
            ))

        return VoiceListResponse(
            voices=voice_infos,
            request_id=request_id
        )
    except Exception as e:
        logger.error(f"获取音色列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: Rewrite `get_voice` endpoint to use VoiceDAO**

Replace the `get_voice` function (lines 207-247) with:

```python
@router.get("/voice/{voice_id}", response_model=VoiceListResponse)
async def get_voice(
    voice_id: str,
    request_id: str = Depends(get_request_id)
):
    """
    查询单个音色（自动按用户隔离，只能查看自己的音色）
    """
    try:
        voice = VoiceDAO.get_by_voice_id(voice_id)
        if not voice:
            raise HTTPException(status_code=404, detail="音色不存在")

        created_at = ""
        if voice.gmt_create:
            created_at = str(voice.gmt_create)
        elif voice.created_at:
            created_at = str(voice.created_at)

        voice_info = VoiceInfo(
            voice_id=voice.voice_id,
            prefix=voice.prefix,
            model=voice.target_model or voice.model,
            status=voice.status,
            created_at=created_at,
            is_available=voice.status == "OK"
        )

        return VoiceListResponse(
            voices=[voice_info],
            request_id=request_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询音色失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: Save voice to DB after creation in `create_voice_from_file`**

In the `run_create` inner function of `create_voice_from_file` (around line 106-126), after the `result = await tts_service.create_voice_with_preview_async(...)` call, add DB save:

```python
                # 步骤2: 创建音色并生成试听
                result = await tts_service.create_voice_with_preview_async(
                    audio_url=audio_url,
                    prefix=prefix,
                    model=model,
                    preview_text=preview_text,
                    auto_upload_oss=auto_upload_oss
                )

                # 保存音色到数据库
                voice_id = result.get("voice_id")
                if voice_id:
                    user_db_id = Database.get_current_user_id()
                    VoiceDAO.create_voice(
                        user_db_id=user_db_id,
                        voice_id=voice_id,
                        prefix=prefix,
                        model=model,
                        status=result.get("status", "DEPLOYING"),
                        target_model=result.get("model"),
                    )

                task_manager.update_progress(task_id, 100, "完成")
```

- [ ] **Step 5: Save voice to DB after creation in `create_voice_from_url`**

In the `run_create` inner function of `create_voice_from_url` (around line 277-283), add DB save after the async call:

```python
        async def run_create():
            result = await tts_service.create_voice_async(
                audio_url=request.audio_url,
                prefix=request.prefix,
                model=request.model,
                wait_ready=request.wait_ready
            )
            # 保存音色到数据库
            voice_id = result.get("voice_id")
            if voice_id:
                user_db_id = Database.get_current_user_id()
                VoiceDAO.create_voice(
                    user_db_id=user_db_id,
                    voice_id=voice_id,
                    prefix=request.prefix,
                    model=request.model,
                    status=result.get("status", "DEPLOYING"),
                    target_model=result.get("model"),
                )
            return result
```

- [ ] **Step 6: Add admin endpoint for listing all voices**

Add this new endpoint after the existing `get_voice` function:

```python
@router.get("/admin/voices", response_model=VoiceListResponse)
async def list_all_voices(
    status: Optional[str] = None,
    limit: int = 100,
    _admin: dict = Depends(require_admin),
    request_id: str = Depends(get_request_id)
):
    """
    管理员接口：获取所有用户的音色列表
    """
    try:
        voices = VoiceDAO.list_all(status=status, limit=limit)

        voice_infos = []
        for v in voices:
            created_at = ""
            if v.get("gmt_create"):
                created_at = str(v["gmt_create"])
            elif v.get("created_at"):
                created_at = str(v["created_at"])

            voice_infos.append(VoiceInfo(
                voice_id=v.get("voice_id", ""),
                prefix=v.get("prefix", ""),
                model=v.get("target_model") or v.get("model", ""),
                status=v.get("status", "UNKNOWN"),
                created_at=created_at,
                is_available=v.get("status") == "OK"
            ))

        return VoiceListResponse(
            voices=voice_infos,
            request_id=request_id
        )
    except Exception as e:
        logger.error(f"管理员获取音色列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 7: Commit**

```bash
git add python_services/api/v1/tts.py
git commit -m "feat: switch voice endpoints to VoiceDAO with user isolation, add admin endpoint"
```