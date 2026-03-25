# 用户数据隔离 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Database 层实现自动用户过滤，所有 API 端点强制认证，实现严格的数据隔离。

**Architecture:** 认证中间件拦截所有请求，验证 X-API-Key 后将 user_db_id 和 role 写入 Database 上下文。Database 的 fetch_one/fetch_all 方法自动追加 `AND user_id = ?` 条件（管理员跳过）。旧数据迁移到系统用户。

**Tech Stack:** FastAPI, PyMySQL, Python 3.10+

**Spec:** `docs/superpowers/specs/2026-03-25-user-data-isolation-design.md`

---

### Task 1: Database 层 — 添加用户上下文管理

**Files:**
- Modify: `python_services/database.py`

- [ ] **Step 1: 在 Database 类中添加用户上下文属性和方法**

在 `database.py` 的 `Database` 类中：

1. 添加类属性 `_current_user_id`、`_current_user_role`
2. 添加 `set_current_user()`、`clear_current_user()`、`is_admin()`、`get_current_user_id()` 方法
3. 添加 `_ISOLATED_TABLES` 集合，标记需要隔离的表名
4. 修改 `fetch_one()` 和 `fetch_all()`，添加 `skip_user_filter` 参数，当当前用户非 admin 且查询的表在隔离列表中时，自动追加 `AND user_id = %s`

```python
class Database:
    """数据库连接管理类"""

    _pool = None
    _current_user_id = None
    _current_user_role = None

    # 需要用户隔离的表（user_id 字段必须存在）
    _ISOLATED_TABLES = {
        "tasks",
        "generated_resources",
        "douyin_fetch_tasks",
        "douyin_videos",
        "operation_logs",
    }

    @classmethod
    def set_current_user(cls, user_db_id: int, role: str):
        cls._current_user_id = user_db_id
        cls._current_user_role = role

    @classmethod
    def clear_current_user(cls):
        cls._current_user_id = None
        cls._current_user_role = None

    @classmethod
    def is_admin(cls) -> bool:
        return cls._current_user_role == "admin"

    @classmethod
    def get_current_user_id(cls) -> Optional[int]:
        return cls._current_user_id

    @classmethod
    def _extract_table_name(cls, sql: str) -> Optional[str]:
        """从 SQL 中提取主表名"""
        import re
        sql_upper = sql.strip().upper()
        # 处理 FROM 和 JOIN
        match = re.search(r'\bFROM\s+`?(\w+)`?', sql_upper)
        if match:
            return match.group(1).lower()
        return None

    @classmethod
    def _apply_user_filter(cls, sql: str, params: tuple) -> tuple:
        """自动追加用户过滤条件"""
        if cls.is_admin() or cls._current_user_id is None:
            return sql, params

        table = cls._extract_table_name(sql)
        if table not in cls._ISOLATED_TABLES:
            return sql, params

        sql_upper = sql.strip().upper()
        params = params or ()

        if "WHERE" in sql_upper:
            modified_sql = sql.rstrip().rstrip(";") + f" AND user_id = %s"
        else:
            modified_sql = sql.rstrip().rstrip(";") + f" WHERE user_id = %s"

        return modified_sql, params + (cls._current_user_id,)
```

然后修改 `fetch_one` 和 `fetch_all`：

```python
    @classmethod
    def fetch_one(cls, sql: str, params: Optional[tuple] = None, *, skip_user_filter: bool = False) -> Optional[Dict]:
        if not skip_user_filter:
            sql, params = cls._apply_user_filter(sql, params)
        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchone()

    @classmethod
    def fetch_all(cls, sql: str, params: Optional[tuple] = None, *, skip_user_filter: bool = False) -> list:
        if not skip_user_filter:
            sql, params = cls._apply_user_filter(sql, params)
        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchall()
```

- [ ] **Step 2: 验证 Database 修改无误**

Run: `cd D:/pythonProject && python -c "from python_services.database import Database; print('OK')"`
Expected: OK (no import errors)

- [ ] **Step 3: Commit**

```bash
git add python_services/database.py
git commit -m "feat: add user context and auto-filtering to Database layer"
```

---

### Task 2: 认证中间件

**Files:**
- Create: `python_services/middleware/auth.py`

- [ ] **Step 1: 创建认证中间件**

```python
"""
全局认证中间件
所有请求必须携带 X-API-Key，白名单路径除外
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

from core.logger import get_logger
from database import Database

logger = get_logger("middleware:auth")

# 白名单路径（不需要认证）
WHITELIST_PATHS = {
    "/health",
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/users/register",
    "/api/v1/users/login",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """全局 API Key 认证中间件"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 白名单跳过
        if path in WHITELIST_PATHS:
            return await call_next(request)

        # OPTIONS 预检请求跳过（CORS）
        if request.method == "OPTIONS":
            return await call_next(request)

        # 提取 API Key
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "缺少 API Key，请在请求头中添加 X-API-Key"}
            )

        # 验证 API Key
        try:
            from core.security import SimpleAuth
            user = SimpleAuth.verify_api_key(api_key)

            # 获取数据库 ID
            user_db_id = None
            user_id_str = user.get("user_id")
            if user_id_str:
                from dao.user_dao import UserDAO
                u = UserDAO.get_by_user_id(user_id_str)
                if u:
                    user_db_id = u.id

            # 写入 Database 上下文
            Database.set_current_user(user_db_id, user.get("role", "user"))

        except Exception as e:
            logger.warning(f"认证失败: {e}")
            return JSONResponse(
                status_code=401,
                content={"detail": "无效的 API Key"}
            )

        try:
            response = await call_next(request)
            return response
        finally:
            Database.clear_current_user()
```

- [ ] **Step 2: 验证导入无误**

Run: `cd D:/pythonProject && python -c "from python_services.middleware.auth import AuthMiddleware; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add python_services/middleware/auth.py
git commit -m "feat: add global auth middleware"
```

---

### Task 3: 注册中间件 + 旧数据迁移

**Files:**
- Modify: `python_services/main.py`

- [ ] **Step 1: 在 main.py 中注册认证中间件**

在 `create_app()` 函数中，在 `app.add_middleware(LoggingMiddleware)` 之前添加认证中间件：

```python
# 导入认证中间件
from middleware.auth import AuthMiddleware

# 在 create_app() 中，LoggingMiddleware 之前添加：
app.add_middleware(AuthMiddleware)
```

具体位置：在 `_setup_routes(app)` 调用之前，`ErrorHandlingMiddleware` 之后。

- [ ] **Step 2: 在 lifespan 中添加系统用户创建和旧数据迁移**

在 `lifespan` 函数中，`db_enabled = True` 分支内、`UserDAO.ensure_default_users()` 之后添加：

```python
            # 创建系统用户并迁移旧数据
            _migrate_orphan_data()
```

在 `main.py` 底部添加迁移函数：

```python
def _migrate_orphan_data():
    """创建系统用户并迁移无归属的旧数据"""
    from database import db, Database
    from dao.user_dao import UserDAO

    # 1. 创建系统用户
    system_user = UserDAO.get_by_user_id("user_system")
    if not system_user:
        sql = """
            INSERT INTO users (user_id, username, role, status)
            VALUES ('user_system', 'system', 'admin', 1)
        """
        try:
            db.execute(sql)
            app_logger.info("✅ 创建系统用户完成")
            system_user = UserDAO.get_by_user_id("user_system")
        except Exception as e:
            app_logger.warning(f"创建系统用户失败: {e}")
            return

    if not system_user:
        return

    system_db_id = system_user.id

    # 2. 迁移旧数据
    tables = [
        "tasks",
        "generated_resources",
        "douyin_fetch_tasks",
        "douyin_videos",
    ]

    for table in tables:
        try:
            # 检查是否有需要迁移的数据
            check_sql = f"SELECT COUNT(*) as cnt FROM {table} WHERE user_id IS NULL"
            row = db.fetch_one(check_sql, skip_user_filter=True)
            if row and row["cnt"] > 0:
                migrate_sql = f"UPDATE {table} SET user_id = %s WHERE user_id IS NULL"
                affected = db.execute(migrate_sql, (system_db_id,))
                app_logger.info(f"✅ 迁移 {table}: {affected} 条数据归属到系统用户")
        except Exception as e:
            # 某些表可能没有 user_id 字段，忽略
            app_logger.debug(f"迁移 {table} 跳过: {e}")
```

- [ ] **Step 3: Commit**

```bash
git add python_services/main.py
git commit -m "feat: register auth middleware and add orphan data migration"
```

---

### Task 4: 简化 deps.py

**Files:**
- Modify: `python_services/api/deps.py`

- [ ] **Step 1: 简化 get_current_user 为从 Database 上下文读取**

将 `get_current_user` 改为从 `Database` 上下文获取当前用户信息，不再需要每次从 API Key 查询：

```python
"""
依赖注入模块
提供API路由使用的依赖函数
"""

from typing import Optional
from fastapi import Header, HTTPException, status, Request

from core.logger import get_logger

logger = get_logger("deps")


async def get_request_id(
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID")
) -> Optional[str]:
    """获取请求ID"""
    return x_request_id or "req_unknown"


async def get_current_user() -> Optional[dict]:
    """
    获取当前用户（从 Database 上下文）

    认证中间件已验证，这里只读取上下文
    """
    from database import Database
    from dao.user_dao import UserDAO

    user_db_id = Database.get_current_user_id()
    if not user_db_id:
        return None

    # 通过缓存或查询获取用户信息
    user = UserDAO.get_by_id(user_db_id, skip_user_filter=True)
    if not user:
        return None

    return {
        "user_id": user.user_id,
        "api_key": user.api_key,
        "name": user.username,
        "role": user.role,
    }


async def require_admin() -> dict:
    """要求管理员权限"""
    user = await get_current_user()
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
```

- [ ] **Step 2: Commit**

```bash
git add python_services/api/deps.py
git commit -m "refactor: simplify deps.py to read from Database context"
```

---

### Task 5: 简化 task_manager.py

**Files:**
- Modify: `python_services/core/task_manager.py`

- [ ] **Step 1: 简化 create_task，自动从 Database 获取 user_db_id**

修改 `create_task` 方法：移除 `user_id` 参数，从 Database 上下文自动获取。

```python
    def create_task(self, task_type: str, params: Optional[Dict[str, Any]] = None) -> str:
        """创建新任务（自动关联当前用户）"""
        from database import Database

        task_id = str(uuid.uuid4())
        user_db_id = Database.get_current_user_id()

        task = Task(
            task_id=task_id,
            task_type=task_type,
            user_id=str(user_db_id) if user_db_id else None
        )

        self.tasks[task_id] = task
        self.tasks_by_type[task_type][task_id] = task
        self._save_task_to_db(task, params)

        logger.info(f"创建任务: {task_type} - {task_id} (用户: {user_db_id})")
        return task_id
```

- [ ] **Step 2: 简化 _save_task_to_db，直接从 Database 获取 user_db_id**

```python
    def _save_task_to_db(self, task: Task, params: Optional[Dict[str, Any]] = None) -> None:
        """保存任务到数据库"""
        try:
            from database import db, Database
            if not db.is_connected():
                return

            import json
            user_db_id = Database.get_current_user_id()

            sql = """
                INSERT INTO tasks (task_id, user_id, task_type, status, progress, input_params)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE status = VALUES(status)
            """
            db.execute(sql, (
                task.task_id,
                user_db_id,
                task.task_type,
                task.status.value,
                task.progress,
                json.dumps(params, ensure_ascii=False) if params else None
            ))
        except Exception as e:
            logger.warning(f"保存任务到数据库失败: {e}")
```

- [ ] **Step 3: 简化 get_task，移除手动 user_id 参数**

```python
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务（Database 层自动过滤）"""
        return self.tasks.get(task_id)
```

- [ ] **Step 4: Commit**

```bash
git add python_services/core/task_manager.py
git commit -m "refactor: simplify task_manager to use Database context"
```

---

### Task 6: 简化 chain.py

**Files:**
- Modify: `python_services/api/v1/chain.py`

- [ ] **Step 1: 移除所有端点中的手动用户获取逻辑**

每个端点函数中删除以下重复代码块：

```python
# 删除这段（每个端点都有）
user_db_id = None
if current_user:
    user_id_str = current_user.get("user_id")
    from dao.user_dao import UserDAO
    user = UserDAO.get_by_user_id(user_id_str)
    if user:
        user_db_id = user.id
```

同时删除 `current_user: dict = Depends(get_current_user)` 参数。

将所有 `task_manager.create_task(..., user_id=user_db_id)` 改为 `task_manager.create_task(...)`。
将所有 `task_manager.create_task(..., user_id=user_id_str)` 改为 `task_manager.create_task(...)`。
将所有 `TaskDAO.get_task(task_id, user_db_id)` 改为 `TaskDAO.get_task(task_id)`。

需要修改的端点：
1. `analyze_from_fetch_task` (line ~94)
2. `generate_script_from_analysis` (line ~247)
3. `tts_from_script` (line ~353)
4. `tts_from_analysis` (line ~471)
5. `video_from_tts` (line ~612)

- [ ] **Step 2: Commit**

```bash
git add python_services/api/v1/chain.py
git commit -m "refactor: remove manual user handling from chain endpoints"
```

---

### Task 7: 简化 douyin.py

**Files:**
- Modify: `python_services/api/v1/douyin.py`

- [ ] **Step 1: 移除手动用户逻辑**

在 `fetch_user_videos` 端点中：
- 删除手动获取 `user_db_id` 的代码
- 将 `task_manager.create_task(..., user_id=user_id_str)` 改为 `task_manager.create_task(...)`
- 将 `DouyinDAO.create_fetch_task(user_db_id=user_db_id, ...)` 中的 `user_db_id` 改为从 `Database.get_current_user_id()` 获取

注意：`douyin.py` 的 fetch 流程中，后台任务 `run_fetch` 会在异步上下文中保存视频。需要确保 `run_fetch` 内部也能访问到用户上下文。由于中间件使用 `finally: Database.clear_current_user()`，异步任务执行时上下文可能已被清除。**解决方案**：在创建异步任务前，将 `user_db_id` 捕获到局部变量中，在异步任务内使用 `db.execute()` (execute 不受自动过滤影响) 传入 `user_db_id`。

具体改动：
```python
# 在端点中捕获 user_db_id
from database import Database
user_db_id = Database.get_current_user_id()

# 在异步任务中使用 db.execute (不受自动过滤) 而不是依赖上下文
async def run_fetch():
    # 使用捕获的 user_db_id
    ...
```

同样修改 `fetch_topic_videos` 端点。

- [ ] **Step 2: Commit**

```bash
git add python_services/api/v1/douyin.py
git commit -m "refactor: simplify douyin.py user handling"
```

---

### Task 8: 简化 tts.py

**Files:**
- Modify: `python_services/api/v1/tts.py`

- [ ] **Step 1: 移除手动用户逻辑**

检查 tts.py 中所有使用 `current_user` 或 `user_db_id` 的地方：
- 移除 `current_user: dict = Depends(get_current_user)` 参数
- `task_manager.create_task(...)` 不再传 `user_id`
- 后台异步任务中保存资源时，从 `Database.get_current_user_id()` 获取（或在创建前捕获）

注意：和 douyin.py 一样，异步后台任务中需要提前捕获 `user_db_id`。

- [ ] **Step 2: Commit**

```bash
git add python_services/api/v1/tts.py
git commit -m "refactor: simplify tts.py user handling"
```

---

### Task 9: 简化 video.py + ai.py + storage.py

**Files:**
- Modify: `python_services/api/v1/video.py`
- Modify: `python_services/api/v1/ai.py`
- Modify: `python_services/api/v1/storage.py`

- [ ] **Step 1: video.py — 移除手动用户逻辑**

移除 `current_user` 依赖，`task_manager.create_task(...)` 不再传 `user_id`。后台任务中提前捕获 `user_db_id`。

- [ ] **Step 2: ai.py — 移除手动用户逻辑**

同上模式。

- [ ] **Step 3: storage.py — 移除手动用户逻辑**

同上模式。注意 storage.py 的上传端点之前没有认证（没有 `current_user`），现在由全局中间件自动保护。

- [ ] **Step 4: Commit**

```bash
git add python_services/api/v1/video.py python_services/api/v1/ai.py python_services/api/v1/storage.py
git commit -m "refactor: simplify video/ai/storage endpoints"
```

---

### Task 10: 简化 resources.py + users.py

**Files:**
- Modify: `python_services/api/v1/resources.py`
- Modify: `python_services/api/v1/users.py`

- [ ] **Step 1: resources.py — 移除手动用户逻辑**

移除所有 `current_user` 依赖和手动 `user_db_id` 获取。`get_user_resources` 端点中 `ResourceDAO.get_user_resources(user_db_id=...)` 改为从 `Database.get_current_user_id()` 获取。

`get_task_resources` 端点中移除手动过滤 `resources = [r for r in resources if r.get("user_id") == user_db_id]`，因为 Database 层已自动过滤。

管理员接口（`get_all_resources`、`update_resource_status`）使用 `require_admin` 依赖。

- [ ] **Step 2: users.py — 保留 register/login 无认证，其他接口用 require_admin**

`register` 和 `login` 在白名单中，不需要改动。
`create_user` 和 `list_users` 改用 `require_admin` 依赖（从 deps.py 导入）。

- [ ] **Step 3: Commit**

```bash
git add python_services/api/v1/resources.py python_services/api/v1/users.py
git commit -m "refactor: simplify resources/users endpoints"
```

---

### Task 11: DAO 层 — 移除手动 user_id 过滤参数

**Files:**
- Modify: `python_services/dao/task_dao.py`
- Modify: `python_services/dao/resource_dao.py`
- Modify: `python_services/dao/douyin_dao.py`
- Modify: `python_services/dao/user_dao.py` (添加 skip_user_filter)

- [ ] **Step 1: task_dao.py — 移除手动 user_id 参数**

- `get_task(task_id, user_db_id=None)` → `get_task(task_id)`，移除内部 `if user_db_id` 分支，Database 自动处理
- `get_user_tasks(user_db_id, ...)` → `get_user_tasks(task_type=None, ...)`，移除 `user_db_id` 参数，Database 自动过滤
- `get_task_stats(user_db_id=None)` → `get_task_stats()`，Database 自动过滤
- `get_recent_tasks(limit)` — 这是管理员接口，添加 `skip_user_filter=True`（因为 JOIN 了 users 表，自动过滤可能不适用）

- [ ] **Step 2: resource_dao.py — 移除手动 user_id 参数**

- `get_user_resources(user_db_id, ...)` → `get_user_resources(resource_type=None, ...)`，从 `Database.get_current_user_id()` 获取
- `count_user_resources(user_db_id, ...)` → `count_user_resources(resource_type=None)`，同上
- `get_all_resources()` — 管理员接口，添加 `skip_user_filter=True`
- `get_resource_stats()` — 管理员接口，添加 `skip_user_filter=True`
- `get_resources_by_task(task_id)` — 添加 `skip_user_filter=True`（通过 task_id 关联即可）

- [ ] **Step 3: douyin_dao.py — 移除手动 user_id 参数**

- `get_videos_by_user(user_db_id, ...)` → `get_videos(limit=100, offset=0)`，Database 自动过滤
- `get_video_stats(user_db_id=None)` → `get_video_stats()`，Database 自动过滤
- `get_fetch_tasks(user_db_id=None)` → `get_fetch_tasks()`，Database 自动过滤
- `search_videos(keyword)` — 搜索功能，Database 自动过滤到当前用户的视频
- `get_video_by_aweme_id(aweme_id)` — 按视频ID查找，Database 自动过滤

- [ ] **Step 4: user_dao.py — 查询添加 skip_user_filter**

`user_dao.py` 操作 `users` 表（不在隔离列表中），但为了安全，对 `get_by_api_key`、`get_by_username` 等方法添加 `skip_user_filter=True`。

- [ ] **Step 5: Commit**

```bash
git add python_services/dao/task_dao.py python_services/dao/resource_dao.py python_services/dao/douyin_dao.py python_services/dao/user_dao.py
git commit -m "refactor: remove manual user_id params from DAOs, rely on Database auto-filter"
```

---

### Task 12: 生成管理员 SQL

**Files:**
- None (生成 SQL 给用户手动执行)

- [ ] **Step 1: 生成密码哈希和 API Key**

Run:
```bash
cd D:/pythonProject && python -c "
import os
os.environ['PASSLIB_BUILTIN_BCRYPT'] = '1'
from passlib.context import CryptContext
import secrets

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto', bcrypt__rounds=8)
password = 'admin123'  # 用户可自行修改
hash_val = pwd_context.hash(password)
api_key = f'key-{secrets.token_urlsafe(32)}'

print(f'密码哈希: {hash_val}')
print(f'API Key: {api_key}')
print()
print(f\"\"\"-- 复制以下 SQL 在 MySQL 中执行：
INSERT INTO users (user_id, username, password_hash, api_key, role, status)
VALUES (
    'user_admin_001',
    'admin',
    '{hash_val}',
    '{api_key}',
    'admin',
    1
);\"\"\")
"
```

Expected: 输出可执行的 SQL 语句。

- [ ] **Step 2: 将 SQL 提供给用户**

将生成的 SQL 发给用户，告知其在 MySQL 中执行。

---

### Task 13: 端到端验证

**Files:** None

- [ ] **Step 1: 启动服务器，验证迁移**

Run: `python python_services/run_server.py`

Expected:
- 日志显示 "✅ 创建系统用户完成"（如果首次运行）
- 日志显示迁移数据条数（如果有旧数据）
- 日志显示 "✅ MySQL 数据库已启用"

- [ ] **Step 2: 验证白名单路径可访问（无 API Key）**

```bash
curl http://localhost:8088/health
curl http://localhost:8088/api/v1/users/login -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}'
```

Expected: 200 OK

- [ ] **Step 3: 验证非白名单路径被拦截（无 API Key）**

```bash
curl http://localhost:8088/api/v1/resources/list
```

Expected: 401 "缺少 API Key"

- [ ] **Step 4: 验证普通用户只能看到自己的数据**

使用普通用户 API Key：
```bash
curl http://localhost:8088/api/v1/resources/list -H "X-API-Key: <user_api_key>"
```

Expected: 只返回该用户自己的资源

- [ ] **Step 5: 验证管理员能看到所有数据**

使用管理员 API Key：
```bash
curl http://localhost:8088/api/v1/resources/admin/all -H "X-API-Key: <admin_api_key>"
```

Expected: 返回所有用户的资源

- [ ] **Step 6: Commit (如有修复)**

```bash
git add -A
git commit -m "fix: end-to-end verification fixes"
```