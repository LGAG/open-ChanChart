import redis
from app.config.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD


class SingletonMeta(type):
    _instances: dict[type, any] = {}

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
