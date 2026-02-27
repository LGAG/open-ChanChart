"""后端启动脚本"""
import os
import sys
from backend.app.utils.middleware import MysqlClient, Mysql_client

# 添加app目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    
    load_dotenv()

    if Mysql_client is None:
        Mysql_clinet = MysqlClient()
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True
    )
