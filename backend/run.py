"""后端启动脚本"""
import os
import sys
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
# 添加app目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
from app.utils.middleware import MysqlClient, Mysql_client
from app.service.stock import update_all_stock
from app.api.stock import list_stocks

def _check_and_create_table(conn, table_name, create_sql):
    """
    通用函数：检查单张表是否存在，不存在则创建
    :param conn: 数据库连接对象
    :param table_name: 表名
    :param create_sql: 创建该表的SQL语句
    :return: bool - 创建/检查是否成功
    """
    try:
        # 1. 检查表格是否存在
        check_sql = text("""
            SELECT COUNT(*) 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = :table_name
        """)
        table_exists = conn.execute(check_sql, {"table_name": table_name}).scalar() > 0
        
        if table_exists:
            print(f"✅ {table_name}表已存在，无需创建")
            return True
        
        # 2. 执行建表SQL
        conn.execute(text(create_sql))
        conn.commit()
        print(f"✅ {table_name}表创建成功")
        return True
    
    except Exception as e:
        print(f"❌ {table_name}表处理失败：{str(e)}")
        # 失败时回滚事务，避免影响其他表
        conn.rollback()
        return False

def init_tables():
    """
    初始化所有需要的表（支持批量扩展）
    可在 TABLE_CONFIG 中新增表名和对应的建表SQL
    """
    # 配置所有需要初始化的表：键=表名，值=建表SQL
    TABLE_CONFIG = {
        "hour": """
            CREATE TABLE `hour` (
              `period` VARCHAR(20) NOT NULL COMMENT '周期',
              `level` INT NOT NULL COMMENT '级别',
              `start_time` DATETIME NOT NULL COMMENT '开始时间',
              `end_time` DATETIME NOT NULL COMMENT '结束时间',
              `code` VARCHAR(20) NOT NULL COMMENT '股票代码',
              `market` VARCHAR(20) NOT NULL COMMENT '交易所',
              `open` DECIMAL(10,2) NOT NULL COMMENT '开盘价',
              `high` DECIMAL(10,2) NOT NULL COMMENT '最高价',
              `low` DECIMAL(10,2) NOT NULL COMMENT '最低价',
              `close` DECIMAL(10,2) NOT NULL COMMENT '收盘价',
              `volume` DECIMAL(16,2) DEFAULT NULL COMMENT '成交量',
              PRIMARY KEY (`code`, `start_time`, `market`),
              KEY `idx_date_code_period_level` (`start_time`, `code`, `period`, `level`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='小时线数据表';
        """,
        "day": """
            CREATE TABLE `day` (
              `period` VARCHAR(20) NOT NULL COMMENT '周期',
              `level` INT NOT NULL COMMENT '级别',
              `date` DATE NOT NULL COMMENT '日期',
              `code` VARCHAR(20) NOT NULL COMMENT '股票代码',
              `market` VARCHAR(20) NOT NULL COMMENT '交易所',
              `open` DECIMAL(10,2) NOT NULL COMMENT '开盘价',
              `high` DECIMAL(10,2) NOT NULL COMMENT '最高价',
              `low` DECIMAL(10,2) NOT NULL COMMENT '最低价',
              `close` DECIMAL(10,2) NOT NULL COMMENT '收盘价',
              `volume` DECIMAL(16,2) DEFAULT NULL COMMENT '成交量',
              `amount` DECIMAL(18,2) DEFAULT NULL COMMENT '成交额',
              `amplitude` DECIMAL(8,2) DEFAULT NULL COMMENT '振幅',
              `change` DECIMAL(8,2) DEFAULT NULL COMMENT '涨跌幅',
              `turnover` DECIMAL(8,4) DEFAULT NULL COMMENT '换手率',
              PRIMARY KEY (`code`, `date`, `market`),
              KEY `idx_date_code_period_level` (`date`, `code`, `period`, `level`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='日线数据表';
        """,
        "week": """
            CREATE TABLE `week` (
              `period` VARCHAR(20) NOT NULL COMMENT '周期',
              `level` INT NOT NULL COMMENT '级别',
              `date` DATE NOT NULL COMMENT '日期',
              `code` VARCHAR(20) NOT NULL COMMENT '股票代码',
              `market` VARCHAR(20) NOT NULL COMMENT '交易所',
              `open` DECIMAL(10,2) NOT NULL COMMENT '开盘价',
              `high` DECIMAL(10,2) NOT NULL COMMENT '最高价',
              `low` DECIMAL(10,2) NOT NULL COMMENT '最低价',
              `close` DECIMAL(10,2) NOT NULL COMMENT '收盘价',
              `volume` DECIMAL(16,2) DEFAULT NULL COMMENT '成交量',
              `amount` DECIMAL(18,2) DEFAULT NULL COMMENT '成交额',
              PRIMARY KEY (`code`, `date`, `market`),
              KEY `idx_date_code` (`date`, `code`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='周线数据表';
        """,
        "month": """
            CREATE TABLE `month` (
              `period` VARCHAR(20) NOT NULL COMMENT '周期',
              `level` INT NOT NULL COMMENT '级别',
              `date` DATE NOT NULL COMMENT '日期',
              `code` VARCHAR(20) NOT NULL COMMENT '股票代码',
              `market` VARCHAR(20) NOT NULL COMMENT '交易所',
              `open` DECIMAL(10,2) NOT NULL COMMENT '开盘价',
              `high` DECIMAL(10,2) NOT NULL COMMENT '最高价',
              `low` DECIMAL(10,2) NOT NULL COMMENT '最低价',
              `close` DECIMAL(10,2) NOT NULL COMMENT '收盘价',
              `volume` DECIMAL(16,2) DEFAULT NULL COMMENT '成交量',
              `amount` DECIMAL(18,2) DEFAULT NULL COMMENT '成交额',
              PRIMARY KEY (`code`, `date`, `market`),
              KEY `idx_date_code` (`date`, `code`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='月线数据表';
        """,
        "year": """
            CREATE TABLE `year` (
              `period` VARCHAR(20) NOT NULL COMMENT '周期',
              `level` INT NOT NULL COMMENT '级别',
              `date` DATE NOT NULL COMMENT '日期',
              `code` VARCHAR(20) NOT NULL COMMENT '股票代码',
              `market` VARCHAR(20) NOT NULL COMMENT '交易所',
              `open` DECIMAL(10,2) NOT NULL COMMENT '开盘价',
              `high` DECIMAL(10,2) NOT NULL COMMENT '最高价',
              `low` DECIMAL(10,2) NOT NULL COMMENT '最低价',
              `close` DECIMAL(10,2) NOT NULL COMMENT '收盘价',
              `volume` DECIMAL(16,2) DEFAULT NULL COMMENT '成交量',
              `amount` DECIMAL(18,2) DEFAULT NULL COMMENT '成交额',
              PRIMARY KEY (`code`, `date`, `market`),
              KEY `idx_date_code` (`date`, `code`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='年线数据表';
        """,
        "stock": """
            CREATE TABLE `stock` (
              `name` VARCHAR(50) NOT NULL COMMENT '股票名称',
              `code` VARCHAR(20) NOT NULL COMMENT '股票代码',
              `market` VARCHAR(20) NOT NULL COMMENT '交易所',
              PRIMARY KEY (`code`, `name`, `market`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票数据表';
        """
    }

    try:
        engine = Mysql_client.get_engine()
        with engine.connect() as conn:
            # 批量处理所有表
            results = {}
            for table_name, create_sql in TABLE_CONFIG.items():
                results[table_name] = _check_and_create_table(conn, table_name, create_sql)
            
            # 检查是否所有表都处理成功
            all_success = all(results.values())
            if all_success:
                print("\n🎉 所有表初始化完成！")
            else:
                failed_tables = [tbl for tbl, success in results.items() if not success]
                print(f"\n❌ 部分表初始化失败：{failed_tables}")
            
            return all_success
    
    except SQLAlchemyError as e:
        print(f"❌ 数据库连接失败：{str(e)}")
        return False
    except Exception as e:
        print(f"❌ 初始化表失败：{str(e)}")
        return False

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
                  `market` VARCHAR(20) NOT NULL COMMENT '交易所',
                  `open` DECIMAL(10,2) NOT NULL COMMENT '开盘价',
                  `high` DECIMAL(10,2) NOT NULL COMMENT '最高价',
                  `low` DECIMAL(10,2) NOT NULL COMMENT '最低价',
                  `close` DECIMAL(10,2) NOT NULL COMMENT '收盘价',
                  `volume` DECIMAL(16,2) DEFAULT NULL COMMENT '成交量',
                  `amount` DECIMAL(18,2) DEFAULT NULL COMMENT '成交额',
                  `amplitude` DECIMAL(8,2) DEFAULT NULL COMMENT '振幅',
                  `change` DECIMAL(8,2) DEFAULT NULL COMMENT '涨跌幅',
                  `turnover` DECIMAL(8,4) DEFAULT NULL COMMENT '换手率',
                   PRIMARY KEY (`code`, `date`, `market`),
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
    init_tables()
    res = update_all_stock()
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True
    )
