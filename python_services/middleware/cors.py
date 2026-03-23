"""
CORS中间件配置
"""

from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.logger import get_logger

logger = get_logger("middleware:cors")


class CorsMiddleware:
    """CORS中间件配置类"""

    @staticmethod
    def setup_cors(app):
        """
        配置CORS中间件

        Args:
            app: FastAPI应用实例
        """
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        )


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next):
        """处理请求并记录日志"""
        # 生成请求ID
        request_id = request.headers.get("X-Request-ID", "unknown")

        # 记录请求信息
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"[{request_id}]"
        )

        # 处理请求
        response = await call_next(request)

        # 记录响应状态
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"[{request_id}] - Status: {response.status_code}"
        )

        # 添加请求ID到响应头
        response.headers["X-Request-ID"] = request_id

        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """请求计时中间件"""

    async def dispatch(self, request: Request, call_next):
        """处理请求并记录耗时"""
        import time

        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # 记录慢请求
        if process_time > 1.0:
            logger.warning(
                f"Slow Request: {request.method} {request.url.path} "
                f"took {process_time:.2f}s"
            )

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """错误处理中间件"""

    async def dispatch(self, request: Request, call_next):
        """处理请求并捕获异常"""
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(f"Unhandled error: {e}")

            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=500,
                content={
                    "code": 500,
                    "message": "Internal Server Error",
                    "detail": str(e) if settings.DEBUG else "An error occurred"
                }
            )
