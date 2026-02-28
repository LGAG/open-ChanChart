"""后端启动脚本"""
import os
import sys
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
# 添加app目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
from app.utils.middleware import MysqlClient, Mysql_client

def init_daily_table():
    """
    初始化daily表：检查表是否存在，不存在则创建（字段匹配KlineData模型）
    """
    try:
        # 1. 获取数据库引擎并创建连接
        engine = Mysql_client.get_engine()
        with engine.connect() as conn:
            # 2. 检查daily表是否存在（MySQL语法）
            check_sql = text("""
                SELECT COUNT(*) 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'daily'
            """)
            table_exists = conn.execute(check_sql).scalar() > 0
            
            if table_exists:
                print("✅ daily表已存在，无需创建")
                return True
            
            # 3. 表不存在则创建（字段严格匹配KlineData模型）
            create_sql = text("""
                CREATE TABLE `daily` (
                  `period` VARCHAR(20) NOT NULL COMMENT '周期',
                  `level` INT NOT NULL COMMENT '级别',
                  `date` DATE NOT NULL COMMENT '日期',
                  `code` VARCHAR(20) NOT NULL COMMENT '股票代码',
                  `open` DECIMAL(10,2) NOT NULL COMMENT '开盘价',
                  `high` DECIMAL(10,2) NOT NULL COMMENT '最高价',
                  `low` DECIMAL(10,2) NOT NULL COMMENT '最低价',
                  `close` DECIMAL(10,2) NOT NULL COMMENT '收盘价',
                  `volume` DECIMAL(16,2) DEFAULT NULL COMMENT '成交量',
                  `amount` DECIMAL(18,2) DEFAULT NULL COMMENT '成交额',
                  `amplitude` DECIMAL(8,2) DEFAULT NULL COMMENT '振幅',
                  `change` DECIMAL(8,2) DEFAULT NULL COMMENT '涨跌幅',
                  `turnover` DECIMAL(8,4) DEFAULT NULL COMMENT '换手率',
                  -- 复合索引：提升(date+code+period+level)组合查询效率
                  KEY `idx_date_code_period_level` (`date`, `code`, `period`, `level`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='K线数据表';
            """)
            conn.execute(create_sql)
            conn.commit()  # 提交创建表的事务
            print("✅ daily表创建成功")
            return True
    
    except SQLAlchemyError as e:
        print(f"❌ 初始化daily表失败（数据库错误）：{str(e)}")
        return False
    except Exception as e:
        print(f"❌ 初始化daily表失败：{str(e)}")

if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    
    load_dotenv()

    if Mysql_client is None:
        try:
            Mysql_client = MysqlClient()
            print("init MysqlClient success")
        except Exception as e:
            print(f"Failed to initialize MysqlClient: {e}")
    init_daily_table()
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True
    )
