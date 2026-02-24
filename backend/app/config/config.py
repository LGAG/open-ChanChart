import os
import yaml

def _load_yaml_config():
    path = os.path.join(os.path.dirname(__file__), "./backend/app/config/config.yaml")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            return {}
    return {}

_cfg = _load_yaml_config()


_redis_cfg = _cfg.get("redis", {}) if isinstance(_cfg, dict) else {}
REDIS_URL = _redis_cfg.get("url", "redis://localhost:6379/0")
REDIS_HOST = _redis_cfg.get("host", "localhost")
REDIS_PORT = _redis_cfg.get("port", 6379)
REDIS_PASSWORD = _redis_cfg.get("password", None)
REDIS_EXPIRE = _redis_cfg.get("expire", 60 * 60 * 24 * 2)

_mysql_cfg = _cfg.get("mysql", {}) if isinstance(_cfg, dict) else {}
MYSQL_URL = _mysql_cfg.get("url", "mysql://root:password@localhost:3306/test")
MYSQL_HOST = _mysql_cfg.get("host", "localhost")
MYSQL_PORT = _mysql_cfg.get("port", 3306)
MYSQL_USER = _mysql_cfg.get("user", "root")
MYSQL_PASSWORD = _mysql_cfg.get("password", "password")
MYSQL_DATABASE = _mysql_cfg.get("database", "test")
