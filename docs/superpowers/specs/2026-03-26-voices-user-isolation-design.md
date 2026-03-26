# Voices User Data Isolation Design

## Problem

`/tts/voice/list` and `/tts/voice/{voice_id}` endpoints call Dashscope external API directly, bypassing the local `voices` database table. Dashscope API is account-level and cannot filter by user. `VoiceDAO` exists but is never called by the API layer.

All other user-scoped tables (tasks, generated_resources, douyin_fetch_tasks, douyin_videos, operation_logs, profiles, user_industries) are in `_ISOLATED_TABLES` and auto-filtered. `voices` is the only table with `user_id` that is missing.

## Scope

4 files changed:

1. `python_services/database.py` — add `"voices"` to `_ISOLATED_TABLES`
2. `python_services/dao/voice_dao.py` — simplify `list_by_user()` to remove manual user_id filtering; add `skip_user_filter=True` to `list_all()`
3. `python_services/api/v1/tts.py` — `list_voices()` and `get_voice()` query DB instead of Dashscope; new admin endpoint `list_all_voices()`
4. `python_services/services/tts_service.py` — no changes needed (external API calls remain for creation)

## Design

### 1. database.py

Add `"voices"` to `_ISOLATED_TABLES`. This means all SELECT/UPDATE/DELETE on `voices` table automatically gets `WHERE user_id = ?` for non-admin users. Admin users bypass the filter.

### 2. VoiceDAO changes

- `list_by_user(user_db_id, status)` → `list_voices(status)`: remove `user_db_id` param, rely on Database auto-filter
- `list_all(status, limit)`: add `skip_user_filter=True` to both SQL calls, for admin use
- `get_by_voice_id(voice_id)`: no change — auto-filter will ensure users can only see their own voices
- `update_status(voice_id, ...)`: no change — auto-filter protects cross-user updates
- `delete_voice(voice_id)`: no change — auto-filter protects cross-user deletes

### 3. tts.py API changes

- `GET /tts/voice/list` → call `VoiceDAO.list_voices()` instead of `tts_service.list_voices_async()`. Auto-filter ensures user isolation.
- `GET /tts/voice/{voice_id}` → call `VoiceDAO.get_by_voice_id()` instead of `tts_service.get_voice_async()`. Auto-filter ensures user isolation.
- `POST /tts/voice/create-from-file` and `POST /tts/voice/create-from-url` → after creation succeeds, save to DB via `VoiceDAO.create_voice()` and `VoiceDAO.sync_from_dashscope()`.
- New `GET /tts/admin/voices` → calls `VoiceDAO.list_all()`, protected by `require_admin()`.

### 4. Admin access

Admin users see all voices via the admin endpoint or because `Database.is_admin()` bypasses auto-filter. Regular users only see their own voices.

## Out of scope

- Dashscope account-level changes (single account, cannot be split)
- TTS creation flow changes (still calls Dashscope API)
- Frontend changes