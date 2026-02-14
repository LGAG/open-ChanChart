import redis
import pymysql
from dbutils.pooled_db import PooledDB
from typing import Optional, Dict, Any
from app.config.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, MYSQL_DATABASE, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_URL, MYSQL_USER

class SingletonMeta(type):
    _instances: Dict[type, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class RedisClient(metaclass=SingletonMeta):
    def __init__(self):
        self.pool = redis.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=0,
            decode_responses=True,
            socket_timeout=5,
            max_connections=10
        )
        self.client = redis.Redis(connection_pool=self.pool)

    def get_client(self) -> redis.Redis:
        return self.client

    def close(self):
        if self.pool:
            self.pool.disconnect()

class MysqlClient(metaclass=SingletonMeta):
    """MySQL单例客户端（适配Docker连接）"""
    def __init__(self):
        # 初始化MySQL连接池（DBUtils实现，自动管理连接）
        self.pool = PooledDB(
            creator=pymysql,
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            charset="utf8mb4",
            maxconnections=20,
            mincached=2,
            maxcached=5,
            ping=0,
            autocommit=True
        )

    def get_connection(self):
        return self.pool.connection()

    def close(self):
        if self.pool:
            self.pool.close()

def test_redis():
    redis1 = RedisClient()
    redis2 = RedisClient()
    print(f"Redis实例是否相同: {redis1 is redis2}")  # 输出：True

    # 操作Redis
    client = redis1.get_client()
    try:
        client.set("name", "python-docker-redis", ex=3600)
        name = client.get("name")
        print(f"Redis获取值: {name}")  # 输出：python-docker-redis
    except redis.RedisError as e:
        print(f"Redis操作失败: {e}")

def test_mysql():
    mysql1 = MysqlClient()
    mysql2 = MysqlClient()
    print(f"MySQL实例是否相同: {mysql1 is mysql2}")  # 输出：True

    try:
        with mysql1.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(50) NOT NULL,
                        age INT
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
                cursor.execute("INSERT INTO user (name, age) VALUES (%s, %s)", ("张三", 25))
                cursor.execute("SELECT * FROM user WHERE name = %s", ("张三",))
                result = cursor.fetchone()
                print(f"MySQL查询结果: {result}")  # 输出：(1, '张三', 25)
    except pymysql.MySQLError as e:
        print(f"MySQL操作失败: {e}")

if __name__ == "__main__":
    try:
        test_redis()
        test_mysql()
    finally:
        RedisClient().close()
        MysqlClient().close()