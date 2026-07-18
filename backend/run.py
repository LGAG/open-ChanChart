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
from app.service.data_check import check_data_integrity
from app.service.migrations import migrate_stock_primary_key


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

    # stock 表主键迁移 (name,code,market) → (code, market)：幂等、失败不阻断启动。
    # 在 check_data_integrity 之前运行，使改名重复检查在新 schema 上执行（恒为 0）。
    try:
        migrate_stock_primary_key()
    except Exception as e:
        print(f"❌ stock 主键迁移失败（已忽略，继续启动）：{e}")

    # 数据完整性检查：在 init_tables 之后、update_all_stock 之前运行。
    # 即使 update_all_stock 因 baostock 不可用而失败，检查仍会先执行。
    # 整体包裹，任何异常都不得阻断启动。
    try:
        check_data_integrity()
    except Exception as e:
        print(f"❌ 数据完整性检查失败（已忽略，继续启动）：{e}")

    try:
        update_all_stock()
    except Exception as e:
        print(f"❌ 更新股票列表失败（已忽略，继续启动）：{e}")

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8001"))

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True
    )
