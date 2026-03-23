"""FastAPI主应用程序"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import stock, chan
import os
from dotenv import load_dotenv
from app.utils.middleware import RedisClient, MysqlClient

# 加载环境变量
load_dotenv()

app = FastAPI(
    title="ChanChart API",
    description="缠论股票图表可视化系统 API",
    version="1.0.0"
)

# 配置CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(stock.router)
app.include_router(chan.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to ChanChart API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

def init():
    RedisClient()
    MysqlClient()

if __name__ == "__main__":
    init()
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
