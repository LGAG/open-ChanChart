import json
from app.utils.middleware import RedisClient, MysqlClient
from app.config.config import REDIS_EXPIRE

def get_cache(cache_key):
    try:
        client = RedisClient.get_client()
        data = client.get(cache_key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"Redis读取缓存失败：{e}")
        return None

def set_cache(cache_key, kline_list):
    try:
        client = RedisClient.get_client()
        client.setex(cache_key, time=REDIS_EXPIRE, value=json.dumps(kline_list, ensure_ascii=False))
    except Exception as e:
        print(f"Redis写入缓存失败：{e}")