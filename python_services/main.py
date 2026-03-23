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

# 导入中间件
from middleware.cors import CorsMiddleware, LoggingMiddleware, TimingMiddleware, ErrorHandlingMiddleware
from middleware.error_handler import setup_exception_handlers

# 导入API路由
from api.v1 import douyin, ai, tts, video, workflow, storage

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
    settings.OUTPUT_DIR.mkdir(exist_ok=True)
    settings.TEMP_DIR.mkdir(exist_ok=True)

    yield

    # 关闭时
    app_logger.info("👋 服务关闭中...")
    # 清理旧任务
    task_manager.cleanup_old_tasks()


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

    # 配置CORS
    CorsMiddleware.setup_cors(app)

    # 添加自定义中间件
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)

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
        workflow.router,
        prefix=settings.API_PREFIX,
    )
    app.include_router(
        storage.router,
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
