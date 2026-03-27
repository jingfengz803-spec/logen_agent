"""
短视频创作自动化API服务 - 主入口

提供抖音数据抓取、AI分析、TTS语音合成、视频生成等API
"""

import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

# 添加项目路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.config import settings
from core.logger import logger, get_logger
from core.task_manager import task_manager
from database import Database  # 添加数据库导入

# 导入中间件
from middleware.cors import CorsMiddleware, LoggingMiddleware, TimingMiddleware, ErrorHandlingMiddleware
from middleware.auth import AuthMiddleware
from middleware.error_handler import setup_exception_handlers

# 导入API路由
from api.v1 import douyin, ai, tts, video, storage, users, chain, resources, profiles, topics

# 获取日志器
app_logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    app_logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    app_logger.info(f"📁 工作目录: {settings.BASE_DIR}")
    app_logger.info(f"🔧 调试模式: {settings.DEBUG}")

    # 确保必要的目录存在
    settings.output_dir_path.mkdir(parents=True, exist_ok=True)
    settings.temp_dir_path.mkdir(parents=True, exist_ok=True)
    settings.audio_dir_path.mkdir(parents=True, exist_ok=True)
    Path(settings.LOG_DIR).mkdir(parents=True, exist_ok=True)

    # 初始化数据库（如果配置了 MySQL）
    db_enabled = False
    try:
        from database import init_database
        from models.db import init_tables
        from dao.user_dao import UserDAO
        from dao.douyin_dao import DouyinDAO
        from dao.task_dao import TaskDAO
        from dao.resource_dao import ResourceDAO

        if init_database():
            # 创建所有表
            init_tables()
            DouyinDAO.init_table()  # 抖音表
            TaskDAO.init_table()      # 任务表（已在 models/db.py 定义）
            ResourceDAO.init_table()  # 资源表
            from dao.profile_dao import ProfileDAO
            ProfileDAO.init_tables()  # 档案表
            from dao.topic_dao import TopicDAO
            TopicDAO.init_table()  # 选题表

            # 从数据库加载任务
            task_manager.load_from_db()

            # 确保默认用户存在
            if Database.is_connected():
                from dao.user_dao import UserDAO
                UserDAO.ensure_default_users()
                _migrate_orphan_data()

            db_enabled = True
            app_logger.info("✅ MySQL 数据库已启用")
        else:
            app_logger.info("⚠️ MySQL 未配置，使用 JSON 文件存储")
    except ImportError as e:
        app_logger.info(f"⚠️ 数据库模块未安装: {e}，使用降级模式")
    except Exception as e:
        app_logger.warning(f"⚠️ 数据库初始化失败: {e}，使用降级模式")

    # 如果启用了数据库，同步现有 JSON 数据
    if db_enabled:
        try:
            from dao.task_dao import TaskDAO
            from dao.user_dao import UserDAO  # 添加 UserDAO 导入
            import json

            # 同步 tasks.json 到数据库
            tasks_file = settings.temp_dir_path / "tasks.json"
            if tasks_file.exists():
                with open(tasks_file, "r", encoding="utf-8") as f:
                    tasks_data = json.load(f)

                # 构建用户映射（从数据库获取）
                user_map = {}
                for task_data in tasks_data.values():
                    user_id = task_data.get("user_id")
                    if user_id:
                        # 获取数据库 ID
                        user = UserDAO.get_by_user_id(user_id)
                        if user:
                            user_map[user_id] = user.id

                TaskDAO.sync_from_json(str(tasks_file), user_map)
                app_logger.info(f"✅ 同步了 {len(tasks_data)} 个任务到数据库")
        except Exception as e:
            app_logger.warning(f"同步任务数据失败: {e}")

    yield

    # 关闭时
    app_logger.info("👋 服务关闭中...")
    # 清理旧任务
    task_manager.cleanup_old_tasks()


def _migrate_orphan_data():
    """创建系统用户并迁移无归属的旧数据"""
    from database import db, Database
    from dao.user_dao import UserDAO

    # 1. 创建系统用户
    system_user = UserDAO.get_by_user_id("user_system")
    if not system_user:
        sql = """
            INSERT INTO users (user_id, username, api_key, role, status)
            VALUES ('user_system', 'system', 'sys-no-login', 'admin', 1)
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
    tables = ["tasks", "generated_resources", "douyin_fetch_tasks", "douyin_videos"]
    for table in tables:
        try:
            check_sql = f"SELECT COUNT(*) as cnt FROM {table} WHERE user_id IS NULL"
            row = db.fetch_one(check_sql, skip_user_filter=True)
            if row and row["cnt"] > 0:
                migrate_sql = f"UPDATE {table} SET user_id = %s WHERE user_id IS NULL"
                affected = db.execute(migrate_sql, (system_db_id,), skip_user_filter=True)
                app_logger.info(f"✅ 迁移 {table}: {affected} 条数据归属到系统用户")
        except Exception as e:
            app_logger.debug(f"迁移 {table} 跳过: {e}")


def create_app() -> FastAPI:
    """创建FastAPI应用"""

    app = FastAPI(
        title=settings.APP_NAME,
        description="短视频创作自动化API服务，提供抖音数据抓取、AI分析、TTS语音合成、视频生成等功能",
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # 自定义 OpenAPI schema，添加 API Key 认证
    # 保存原始的 openapi 方法避免递归
    original_openapi = app.openapi

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = original_openapi()
        # 添加安全方案
        openapi_schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API 认证密钥，通过 /api/v1/users/create 创建用户获取"
            }
        }
        app.openapi_schema = openapi_schema
        return openapi_schema

    app.openapi = custom_openapi

    # 配置CORS
    CorsMiddleware.setup_cors(app)

    # 添加自定义中间件
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(AuthMiddleware)

    # 配置异常处理
    setup_exception_handlers(app)

    # 注册路由
    _setup_routes(app)

    return app


def _setup_routes(app: FastAPI):
    """配置路由"""

    # 健康检查
    @app.get("/health")
    async def health_check():
        """健康检查接口"""
        return {
            "code": 200,
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION
        }

    # 根路径
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "code": 200,
            "message": f"欢迎使用 {settings.APP_NAME}",
            "version": settings.APP_VERSION,
            "docs": "/docs" if settings.DEBUG else "disabled"
        }

    # API v1 路由
    app.include_router(
        douyin.router,
        prefix=settings.API_PREFIX,
    )
    app.include_router(
        ai.router,
        prefix=settings.API_PREFIX,
    )
    app.include_router(
        tts.router,
        prefix=settings.API_PREFIX,
    )
    app.include_router(
        video.router,
        prefix=settings.API_PREFIX,
    )
    app.include_router(
        storage.router,
        prefix=settings.API_PREFIX,
    )
    # V1: 用户管理路由（不需要鉴权）
    app.include_router(
        users.router,
        prefix=settings.API_PREFIX,
    )
    # 任务串联路由
    app.include_router(
        chain.router,
        prefix=settings.API_PREFIX,
    )
    # 资源管理路由
    app.include_router(
        resources.router,
        prefix=settings.API_PREFIX,
    )
    # 档案管理路由
    app.include_router(
        profiles.router,
        prefix=settings.API_PREFIX,
    )
    # 选题管理路由
    app.include_router(
        topics.router,
        prefix=settings.API_PREFIX,
    )

    app_logger.info("✅ 路由注册完成")


# 创建应用实例
app = create_app()


def run_server(
    host: str = None,
    port: int = None,
    reload: bool = None
):
    """运行服务器

    Args:
        host: 监听地址
        port: 监听端口
        reload: 是否自动重载
    """
    host = host or settings.HOST
    port = port or settings.PORT
    reload = reload if reload is not None else settings.DEBUG

    app_logger.info(f"🌐 服务地址: http://{host}:{port}")
    app_logger.info(f"📚 API文档: http://{host}:{port}/docs")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
