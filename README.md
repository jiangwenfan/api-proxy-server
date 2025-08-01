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