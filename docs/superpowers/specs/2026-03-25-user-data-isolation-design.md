# 用户数据隔离设计文档

## 概述

为短视频创作自动化 API 系统实现完整的用户数据隔离。所有端点必须认证，普通用户只能访问自己创建的数据，管理员可以访问所有数据。

## 需求总结

| 决策项 | 结论 |
|---|---|
| 认证要求 | 所有端点必须登录（API Key），仅注册/登录/健康检查除外 |
| 隔离模式 | 严格隔离 — 普通用户只看自己的，管理员看全部 |
| 旧数据处理 | 归属到"系统用户"（system, role=admin） |
| 音色权限 | 所有用户可用，仅创建者和管理员可管理 |
| 初始管理员 | 手动 SQL 插入 |
| 技术方案 | 方案 A：中间件自动注入，Database 层统一过滤 |

## 架构设计

### 请求流程

```
所有请求
  → 认证中间件（检查 X-API-Key Header）
    → 白名单路径（/health, /docs, /register, /login）：跳过认证
    → 无 Key / 无效 Key：返回 401
    → 有效 Key：提取 user_db_id 和 role
      → Database.set_current_user(user_db_id, role)
        → 进入业务处理（DAO 查询自动附加 user_id 过滤）
          → 请求结束 → Database.clear_current_user()
```

### 数据隔离规则

**需要隔离的表**：

| 表 | 隔离方式 |
|---|---|
| `tasks` | 普通用户只看自己的 |
| `generated_resources` | 普通用户只看自己的 |
| `douyin_fetch_tasks` | 普通用户只看自己的 |
| `douyin_videos` | 普通用户只看自己的 |
| `operation_logs` | 普通用户只看自己的 |

**不需要隔离的表**：

| 表 | 原因 |
|---|---|
| `users` | 通过专门的管理接口访问 |
| `voices` | 全局共享，创建者 + 管理员可管理 |

## 详细设计

### 1. Database 层改造（database.py）

在 `Database` 类中维护当前用户上下文：

```python
class Database:
    _current_user_id = None  # 当前用户数据库 ID
    _current_user_role = None  # 当前用户角色

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
```

查询方法自动追加过滤：

- `fetch_one(sql, params)` → 管理员：原样执行；普通用户：追加 `AND user_id = ?`
- `fetch_all(sql, params)` → 同上
- `execute(sql, params)` → 不自动过滤（写入操作由 DAO 层控制）
- `insert_return_id(sql, params)` → 不自动过滤

需要跳过过滤的场景通过 `skip_user_filter=True` 参数控制。

### 2. 认证中间件（middleware/auth.py）

新增文件，职责：

1. 从 `X-API-Key` Header 提取并验证用户
2. 将 `user_db_id` 和 `role` 写入 `Database` 上下文
3. 请求结束后清理上下文

**白名单路径**（不需要认证）：

- `/health`
- `/docs`
- `/redoc`
- `/openapi.json`
- `/api/v1/users/register`
- `/api/v1/users/login`

### 3. main.py 改动

1. 注册认证中间件（在 CORS 之后、业务中间件之前）
2. 在 `lifespan` 启动函数中添加迁移逻辑：
   - 创建系统用户（如果不存在）
   - 迁移旧数据（`user_id IS NULL` → 系统用户 ID）

### 4. DAO 层改造

所有 DAO 方法移除手动的 `user_id` 过滤参数，由 Database 层自动处理。

对于需要跳过过滤的特殊场景（如音色查询），使用 `skip_user_filter=True`。

### 5. API 层简化

移除所有端点中手动的 `current_user` 获取和 `user_db_id` 传递逻辑：

```python
# 改造前
@router.post("/chain/analyze")
async def analyze(current_user: dict = Depends(get_current_user)):
    user_db_id = ...
    task_id = task_manager.create_task(..., user_id=user_db_id)

# 改造后
@router.post("/chain/analyze")
async def analyze():
    task_id = task_manager.create_task(...)
    # Database 层自动处理 user_id
```

### 6. deps.py 简化

`get_current_user` 保留，改为从 `Database` 上下文读取（用于需要用户信息的端点，如用户管理）。

### 7. 旧数据迁移

启动时自动执行：

```sql
-- 1. 创建系统用户（由代码自动执行）
INSERT IGNORE INTO users (user_id, username, role, status)
VALUES ('user_system', 'system', 'admin', 1);

-- 2. 迁移旧数据（由代码自动执行）
UPDATE tasks SET user_id = (SELECT id FROM users WHERE user_id = 'user_system') WHERE user_id IS NULL;
UPDATE generated_resources SET user_id = (SELECT id FROM users WHERE user_id = 'user_system') WHERE user_id IS NULL;
UPDATE douyin_fetch_tasks SET user_id = (SELECT id FROM users WHERE user_id = 'user_system') WHERE user_id IS NULL;
UPDATE douyin_videos SET user_id = (SELECT id FROM users WHERE user_id = 'user_system') WHERE user_id IS NULL;
```

## 文件改动清单

### 新增

| 文件 | 说明 |
|---|---|
| `middleware/auth.py` | 全局认证中间件 |

### 修改

| 文件 | 改动 |
|---|---|
| `database.py` | 新增用户上下文管理、自动过滤逻辑 |
| `main.py` | 注册认证中间件、添加迁移逻辑 |
| `api/deps.py` | 简化 get_current_user |
| `api/v1/chain.py` | 移除手动 user_db_id 传递 |
| `api/v1/douyin.py` | 移除手动 user_db_id 传递 |
| `api/v1/tts.py` | 移除手动 user_db_id 传递 |
| `api/v1/video.py` | 移除手动 user_db_id 传递 |
| `api/v1/ai.py` | 移除手动 user_db_id 传递 |
| `api/v1/storage.py` | 移除手动 user_db_id 传递 |
| `api/v1/resources.py` | 移除手动 user_db_id 传递 |
| `api/v1/users.py` | 移除手动 user_db_id 传递 |
| `core/task_manager.py` | 简化，不再手动处理 user_id |
| `dao/task_dao.py` | 移除手动 user_id 过滤参数 |
| `dao/resource_dao.py` | 移除手动 user_id 过滤参数 |
| `dao/douyin_dao.py` | 移除手动 user_id 过滤参数 |

### 不改动

| 文件 | 原因 |
|---|---|
| `dao/user_dao.py` | 用户管理走专门接口 |
| `dao/voice_dao.py` | 音色全局共享 |

## 管理员创建 SQL

```sql
-- 先注册一个普通用户获取 password_hash（通过 /api/v1/users/register）
-- 然后手动将角色改为管理员：

UPDATE users SET role = 'admin' WHERE username = '你的管理员用户名';
```

或者直接插入：

```sql
-- 密码哈希通过 Python 生成：passlib.hash('你的密码')
-- 示例：密码为 admin123，hash 值需要替换为实际生成值
INSERT INTO users (user_id, username, password_hash, api_key, role, status)
VALUES (
    'user_admin_001',
    'admin',
    '$2b$08$替换为实际hash值',
    'key-替换为实际api_key',
    'admin',
    1
);
```
