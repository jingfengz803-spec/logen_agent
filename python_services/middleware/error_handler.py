"""
异常处理器
统一处理API异常
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.logger import get_logger

logger = get_logger("error_handler")


def setup_exception_handlers(app: FastAPI):
    """配置异常处理器"""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理HTTP异常"""
        request_id = request.headers.get("X-Request-ID", "unknown")

        logger.warning(
            f"HTTP Exception: {exc.status_code} - {exc.detail} "
            f"[{request_id}]"
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": str(exc.detail),
                "request_id": request_id
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request,
        exc: StarletteHTTPException
    ):
        """处理Starlette HTTP异常"""
        request_id = request.headers.get("X-Request-ID", "unknown")

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": exc.detail,
                "request_id": request_id
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
    ):
        """处理请求验证异常"""
        request_id = request.headers.get("X-Request-ID", "unknown")

        logger.warning(
            f"Validation Error: {exc.errors()} "
            f"[{request_id}]"
        )

        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": "请求参数验证失败",
                "errors": exc.errors(),
                "request_id": request_id
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理未捕获的异常"""
        request_id = request.headers.get("X-Request-ID", "unknown")

        logger.exception(
            f"Unhandled Exception: {exc} "
            f"[{request_id}]"
        )

        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误",
                "request_id": request_id
            }
        )
