import json
import time
import httpx
import logging
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, Any, Optional

from .config_manager import config_manager

logger = logging.getLogger(__name__)


class ProxyHandler:
    """代理处理器类"""

    def __init__(self):
        self.timeout = 30.0

    async def forward_request(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        body: Optional[bytes] = None,
        response_delay: Optional[int] = None,
    ) -> Response:
        """转发请求到远程服务器"""
        if config_manager.debug:
            logger.info(
                f"实际转发请求: {method}, {url}, {headers}, {body}, {response_delay=}"
            )
        try:
            async with httpx.AsyncClient() as client:
                # 会导致死循环
                # 删除content-length
                # print(headers, "----")
                if isinstance(headers, dict):
                    headers.pop("content-length", None)
                    # 删除host
                    headers.pop("host", None)
                    # 移除可能会导致问题的headers
                    # filtered_headers = {
                    #     k: v
                    #     for k, v in headers.items()
                    #     if k.lower() not in ["host", "content-length"]
                    # }

                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=body,
                    timeout=self.timeout,
                )
                if config_manager.debug:
                    logger.info(f"转发成功: {response.status_code}")

                # 如果配置了响应延时，则延时
                if response_delay:
                    time.sleep(response_delay)

                # 创建响应
                headers = dict(response.headers)
                # headers.pop("content-length", None)

                # 如果远程响应是chunked，则删除transfer-encoding，改为普通响应
                # 为什么要改？ 因为不能stream转发这个请求，只能转换这个请求
                if "transfer-encoding" in headers:
                    headers.pop("transfer-encoding", None)
                    # 取消压缩，否则计算的值不准确
                    headers.pop("content-encoding", None)
                    # 计算响应体大小
                    headers["content-length"] = str(len(response.content))
                    # res = StreamingResponse(
                    #     content=response.aiter_bytes(),
                    #     status_code=response.status_code,
                    #     headers=headers,
                    #     media_type=response.headers.get("content-type"),
                    # )

                res = Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=headers,
                    media_type=response.headers.get("content-type"),
                )
                # print(response.headers, "--res--")
                return res
        except Exception as e:
            logger.error(f"转发请求失败: {e}")
            raise HTTPException(status_code=502, detail=f"代理请求失败: {str(e)}")

    async def handle_proxy_request(self, request: Request, path: str) -> Response:
        """处理代理请求的主要逻辑"""
        # print("###path", path)
        # 请求方法
        method = request.method
        # 资源路径: /api/reports/
        endpoint = f"/{path}"
        # 查询参数: ?page=1&pagesize=30&owner_space=1
        query_params = f"?{request.query_params}"
        # 请求的headers,从配置中获取access_token并添加到请求头
        headers = dict(request.headers)
        access_token = config_manager.access_token
        # 如果原始请求中没有authorization 且 配置中access_token不为空时
        # 则添加token
        if ("authorization" not in headers) and access_token:
            headers["authorization"] = access_token

        # 查找URL配置 - 传入HTTP方法
        url_config = config_manager.find_url_config(endpoint, method)
        # 默认不配置时,读取为True
        is_enable = url_config and url_config.get("is_enable", True)
        # print(f"is_enable: {is_enable}")
        if is_enable == False:
            # 当是None 或者 True 时， 启用配置；
            # 否则不启用配置,重置为空
            url_config = {}

        # 获取配置中的响应延时，默认不延时是None
        response_delay = url_config and url_config.get("response_delay", None)

        # 查询参数存在时，拼接查询参数
        if request.query_params:
            endpoint += query_params

        # 获取原始请求体
        try:
            request_body = await request.body()
        except Exception:
            request_body = b""

        # print("--url_config--", url_config)
        if url_config is not None:
            # 如果没有配置response_data字段,则转发到mock_server
            if "response_data" not in url_config:
                if config_manager.remove_mock_prefix:
                    endpoint = endpoint.replace("/api", "")
                mock_server_url = config_manager.mock_server + endpoint
                # print(config_manager.mock_server_headers)
                headers.update(config_manager.mock_server_headers)
                # headers.pop("content-length", None)
                # print(f"转发到mock server: {method} {endpoint}")
                return await self.forward_request(
                    url=mock_server_url,
                    method=method,
                    headers=headers,
                    body=request_body,
                    response_delay=response_delay,
                )

            # 如果配置了直接返回的响应数据
            if url_config.get("response_data") is not None:
                logger.info(f"请求返回mock response <--: {method} {endpoint}")
                # 如果配置了响应延时，则延时
                if response_delay:
                    # print(f"start sleep: {response_delay}")
                    time.sleep(response_delay)
                    # print(f"end sleep: {response_delay}")
                return JSONResponse(
                    content=url_config["response_data"], status_code=200
                )

            # 如果配置了要替换的请求体数据
            if url_config.get("request_body") is not None:
                logger.info(f"请求使用mock request -->: {method} {endpoint}")
                request_body = json.dumps(url_config["request_body"]).encode("utf-8")
        else:
            if method != "OPTIONS":
                logger.info(f"请求转发成功: {method} {endpoint}")

        # 没有配置或只是普通转发，转发到远程服务器
        # 1.response_data 是None,
        # 2.没有配置该路径的接口
        remote_url = config_manager.remote_server + endpoint
        if config_manager.debug:
            logger.info(
                f"请求: {method},转发到远程服务器: {remote_url},headers: {headers},body: {request_body}"
            )
        return await self.forward_request(
            url=remote_url,
            method=method,
            headers=headers,
            body=request_body,
            response_delay=response_delay,
        )


# 全局代理处理器实例
proxy_handler = ProxyHandler()
