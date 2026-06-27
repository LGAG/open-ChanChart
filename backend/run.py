"""后端启动脚本"""
import os
import sys
from datetime import datetime

# 添加app目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from dotenv import load_dotenv

load_dotenv()

from app.utils.database import engine
from app.models.db_model import Base
from app.service.stock import update_all_stock


def init_tables():
    """使用 ORM 模型自动创建所有表"""
    try:
        Base.metadata.create_all(engine)
        print("✅ 所有表初始化完成！")
        return True
    except Exception as e:
        print(f"❌ 初始化表失败：{str(e)}")
        return False


if __name__ == "__main__":
    import uvicorn

    init_tables()
    update_all_stock()

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8001"))

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True
    )
