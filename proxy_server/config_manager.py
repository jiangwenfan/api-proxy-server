import json
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器类"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config_data = json.load(f)
            logger.info(f"配置文件 {self.config_file} 加载成功")
        except FileNotFoundError:
            logger.error(f"配置文件 {self.config_file} 未找到")
            raise HTTPException(status_code=500, detail="配置文件未找到")
        except json.JSONDecodeError:
            logger.error("配置文件格式错误")
            raise HTTPException(status_code=500, detail="配置文件格式错误")
        

    @property
    def remote_server(self) -> str:
        """获取远程服务器地址"""
        return self.config_data.get("remote_server")
    
    @property
    def access_token(self) -> Optional[str]:
        """获取访问令牌"""
        return self.config_data.get("access_token")
    
    @property
    def debug(self) -> bool:
        """获取调试模式"""
        debug_str = self.config_data.get("debug", None)
        # None,false 为 False; true 为 True
        if debug_str is None or debug_str == "false":
            return False
        return True
    
    @property
    def url_configs(self) -> Optional[Dict[str, Any]]:
        """获取URL配置"""
        return self.config_data.get("url_configs", {})
    
    def find_url_config(self, endpoint: str, method: str = "GET") -> Optional[Dict[str, Any]]:
        """查找URL配置
        Args:
            path: URL路径
            method: HTTP方法 (GET, POST, PUT, DELETE等)
        Returns:
            匹配的配置字典或None
        """
        # 查找匹配的路径
        if endpoint in self.url_configs:
            path_config = self.url_configs[endpoint]
            # 查找匹配的HTTP方法
            if method in path_config:
                return path_config[method]
        
        return None
    
    
    


# 全局配置管理器实例
config_manager = ConfigManager() 