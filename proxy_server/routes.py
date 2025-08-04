from fastapi import FastAPI, Request
from .proxy_handler import proxy_handler


def setup_routes(app: FastAPI):
    """设置应用程序的所有路由"""

    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    )
    async def proxy_handler_route(request: Request, path: str):
        """代理处理器路由 - 处理所有其他请求"""
        # print("###path111###", path)
        return await proxy_handler.handle_proxy_request(request, path)
