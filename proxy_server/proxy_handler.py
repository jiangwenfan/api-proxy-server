import json
import time
import httpx
import logging
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
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
            logger.info(f"实际转发请求: {method}, {url}, {headers}, {body}")
        try:
            async with httpx.AsyncClient() as client:
               
                # 会导致死循环
                # 删除content-length
                headers.pop("content-length", None)
                # 删除host
                headers.pop("host", None)
                # 移除可能会导致问题的headers
                # filtered_headers = {k: v for k, v in headers.items() 
                #                   if k.lower() not in ["host", "content-length"]}
                
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=body,
                    timeout=self.timeout
                )
                if config_manager.debug:
                    logger.info(f"转发成功: {response.status_code}")
                
                # 如果配置了响应延时，则延时
                if response_delay:
                   time.sleep(response_delay)

                # 创建响应
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.headers.get("content-type")
                )
        except Exception as e:
            logger.error(f"转发请求失败: {e}")
            raise HTTPException(status_code=502, detail=f"代理请求失败: {str(e)}")
    
    async def handle_proxy_request(self, request: Request, path: str) -> Response:
        """处理代理请求的主要逻辑"""
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

        # 获取配置中的响应延时，默认不延时是None
        response_delay = url_config.get("response_delay",None)
        
        # 查询参数存在时，拼接查询参数
        remote_url = config_manager.remote_server + endpoint
        if request.query_params:
            remote_url += query_params
        
        # 获取原始请求体
        try:
            request_body = await request.body()
        except Exception:
            request_body = b""
        
        
        if url_config:
            # 如果配置了直接返回的响应数据
            if url_config.get("response_data") is not None:
                logger.info(f"请求返回mock response <--: {method} {endpoint}")
                return JSONResponse(
                    content=url_config["response_data"],
                    status_code=200
                )
            
            # 如果配置了要替换的请求体数据
            if url_config.get("request_body") is not None:
                logger.info(f"请求使用mock request -->: {method} {endpoint}")
                request_body = json.dumps(url_config["request_body"]).encode("utf-8")
        else:
            if method != "OPTIONS":
                logger.info(f"请求转发成功: {method} {endpoint}")
                
        
        # 没有配置或只是普通转发，转发到远程服务器
        if config_manager.debug:
            logger.info(f"请求: {method},转发到远程服务器: {remote_url},headers: {headers},body: {request_body}")
        return await self.forward_request(
            url=remote_url,
            method=method,
            headers=headers,
            body=request_body,
            response_delay=response_delay
        )

# 全局代理处理器实例
proxy_handler = ProxyHandler() 