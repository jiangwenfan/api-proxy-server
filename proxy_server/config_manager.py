import json
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException
import copy
import re

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器类"""

    def __init__(self, config_file: str = "config.json"):
        self._config_file = config_file
        # 原生文件内容
        self._raw_file_content = self.read_raw_file_content()
        # 先加载原始配置以获取common部分
        self._raw_config_data = self._load_raw_config()
        # 预处理后文件内容
        self.pre_file_content = self.pre_process_config()
        # 预处理后配置
        self.pre_config_data = self.read_config()

    def covert_path_to_regex(self, url_configs: Dict[str, Any]) -> Dict[str, Any]:
        """将路径转换为正则表达式

        将/api/user/[id]/ 转换为正则表达式
        """
        # 处理之后的新配置
        new_config_data = {}

        for url_config_key, url_config_value in url_configs.items():
            if "[id]" in url_config_key:
                # 转换
                # 替换[id]
                new_key = url_config_key.replace("[id]", "([^/]+)")
                # 添加^和$
                new_key = f"^{new_key}$"
                # 添加到新配置
                new_config_data[new_key] = url_config_value
            else:
                # 不转换
                new_config_data[url_config_key] = url_config_value
        return new_config_data

    @property
    def remote_server(self) -> str:
        """获取远程服务器地址"""
        return self.pre_config_data.get("remote_server")

    @property
    def access_token(self) -> Optional[str]:
        """获取访问令牌"""
        return self.pre_config_data.get("access_token")

    @property
    def mock_server(self) -> Optional[str]:
        """获取mock server地址"""
        return self.pre_config_data.get("mock_server")

    @property
    def mock_server_headers(self) -> Optional[Dict[str, Any]]:
        """获取mock server请求头"""
        return self.pre_config_data.get("mock_server_headers", {})

    @property
    def remove_mock_prefix(self) -> bool:
        """获取是否移除mock前缀"""
        return self.pre_config_data.get("remove_mock_prefix", False)

    @property
    def debug(self) -> bool:
        """获取调试模式"""
        debug_str = self.pre_config_data.get("debug", None)
        # None,false 为 False; true 为 True
        if debug_str is None or debug_str == "false":
            return False
        return True

    @property
    def url_configs(self) -> Optional[Dict[str, Any]]:
        """获取URL配置"""
        raw_url_configs = self.pre_config_data.get("url_configs", {})
        url_configs = self.covert_path_to_regex(raw_url_configs)
        # print("url_configs: ", url_configs)
        # with open("url_configs.json", "w", encoding="utf-8") as f:
        #     f.write(json.dumps(url_configs,ensure_ascii=False,indent=4))

        return url_configs

    @property
    def common(self) -> Optional[Dict[str, Any]]:
        """获取公共配置, 用于复用"""
        return self._raw_config_data.get("common", {})

    def read_config(self) -> Dict[str, Any]:
        """从预处理后的内容中解析配置数据"""
        # print("预处理后内容: ", self.pre_file_content)
        # with open("pre_file_content.json", "w", encoding="utf-8") as f:
        #     f.write(self.pre_file_content)

        try:
            logger.info(f"配置内容加载成功")
            return json.loads(self.pre_file_content)
        except Exception as e:
            logger.error(f"解析配置文件失败: {e}")
            raise HTTPException(status_code=500, detail=f"解析配置文件失败: {e}")

    def read_raw_file_content(self) -> str:
        """读取原始文件内容"""
        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"配置文件 {self._config_file} 未找到")
            raise HTTPException(status_code=500, detail="配置文件未找到")

    def _load_raw_config(self) -> Dict[str, Any]:
        """加载原始配置数据（未经预处理）"""
        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取原始配置文件失败: {e}")
            raise HTTPException(status_code=500, detail=f"读取原始配置文件失败: {e}")

    def replace_common_content(
        self, pre_file_content: str, common_key: str, common_value: Any
    ):
        """替换配置中的 "{{xxx}}" 为common中的具体内容"""
        data = json.dumps(common_value, ensure_ascii=False)
        key = '"{{' + common_key + '}}"'
        # print("要写入的内容: ", key)
        # print("要写入的内容: ", data)
        return pre_file_content.replace(key, data)

    def pre_process_config(self) -> str:
        """预处理配置, 将配置中的 "{{xxx}}" 替换为common中的具体内容"""
        # 深拷贝原始文件内容
        pre_file_content = copy.deepcopy(self._raw_file_content)

        # 遍历common中的内容
        for common_key, common_value in self.common.items():
            # print("common_key: ", common_key)
            # print("common_value: ", common_value)
            pre_file_content = self.replace_common_content(
                pre_file_content, common_key, common_value
            )

        return pre_file_content

    def find_url_config(
        self, endpoint: str, method: str = "GET"
    ) -> Optional[Dict[str, Any]]:
        """查找URL配置
        Args:
            path: URL路径
            method: HTTP方法 (GET, POST, PUT, DELETE等)
        Returns:
            匹配的配置字典或None
        """
        # 查找匹配的路径
        # print("匹配数据:", method, endpoint)
        # 1.直接匹配
        if endpoint in self.url_configs:
            path_config = self.url_configs[endpoint]
            # 查找匹配的HTTP方法
            if method in path_config:
                config = path_config[method]
                # self.debug and print("直接匹配成功: ", endpoint, method, config)
                return config

        # 2.正则匹配
        # self.debug and print("开始正则匹配", endpoint, method)
        for url_config_key_pattern, url_config_value in self.url_configs.items():
            if re.match(url_config_key_pattern, endpoint):
                # self.debug and print(
                #     "正则匹配成功: ",
                #     url_config_key_pattern,
                #     endpoint,
                # )
                # self.debug and print(
                #     "匹配数据: ",
                #     json.dumps(url_config_value, ensure_ascii=False, indent=4),
                # )
                # 查找匹配的HTTP方法
                if method in url_config_value:
                    return url_config_value[method]

        # self.debug and print("所有都匹配失败,返回None: ", endpoint, method)
        return None


# 全局配置管理器实例
config_manager = ConfigManager()
