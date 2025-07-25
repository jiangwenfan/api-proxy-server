import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from proxy_server.routes import setup_routes

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    # format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s',
    # datefmt='%Y-%m-%d %H:%M:%S'
)

# 禁用httpx相关的日志输出
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用程序生命周期管理"""
    logger.info("代理服务器启动完成")
    yield
    logger.info("代理服务器关闭")

def create_app() -> FastAPI:
    """创建FastAPI应用程序"""
    app = FastAPI(
        title="代理服务器", 
        description="基于FastAPI的代理服务器",
        lifespan=lifespan
    )
    
    # 设置路由
    setup_routes(app)
    
    return app

# 创建应用程序实例
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 自动重启
        reload_includes=["*.py", "config.json"],  # 只监控Python文件和配置文件
        log_level="info"
    ) 