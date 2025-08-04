# api-proxy-server
api代理服务,mock指定接口，其他接口转发

使用
```bash
# 1. 创建config.json文件

# 2. 复制compose.yml文件,并且执行命令启动
docker compose up -d
```

内容复用:
- "common"字段中写内容
- 在需要替换的地方`"{{xxx}}"`
  

路径通配功能：
```
/api/u/[id]/sdsd/
表示匹配:
/api/u/123/sdsd/
/api/u/hhhh/sdsd/

/api/u/[id]/
表示匹配:
/api/u/123/
/api/u/xxxx/

[id]表示这里可以是任意字符
```

mock_server功能:
- 当没有找到匹配的路径时,转发到真实后端
- 当匹配到时:
  - response_data字段不存在时，转发到mock_server; 
  - response_data是null时,忽略mock,转发真实server;
  - response_data是具体object时，返回该object数据
注意：当api的mock请求是stream时会转换为普通请求
```json
// 这里分别是要转发的mock server 和 请求该server要携带的请求头
"mock_server": "http://ip地址:8001",
"mock_server_headers": {
    "token1":"token1",
}

// 高级配置,如果存在/api/前缀，转发时是否需要移除
"remove_mock_prefix": false,
```