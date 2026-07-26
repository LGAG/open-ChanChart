import os
import yaml

def _load_yaml_config():
    path = os.path.join(os.path.dirname(__file__), "config.yaml")
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
MYSQL_PASSWORD = _mysql_cfg.get("password", "root")
MYSQL_DATABASE = _mysql_cfg.get("database", "chan")

_period_map_cfg = _cfg.get("period_map", {}) if isinstance(_cfg, dict) else {}
PERIOD_MAP: dict[str, str] = {str(k): str(v) for k, v in _period_map_cfg.items()}

# baostock 限流配置：全量更新时控制请求速率，避免被封IP
_baostock_cfg = _cfg.get("baostock", {}) if isinstance(_cfg, dict) else {}
BAOSTOCK_QPS_INTERVAL: float = float(_baostock_cfg.get("qps_interval", 0.3))
BAOSTOCK_MAX_RETRIES: int = int(_baostock_cfg.get("max_retries", 3))
BAOSTOCK_RETRY_BASE_DELAY: float = float(_baostock_cfg.get("retry_base_delay", 1.0))

# 缠论算法配置：中枢识别算法选择（见 config.yaml 的 chan 段）
_chan_cfg = _cfg.get("chan", {}) if isinstance(_cfg, dict) else {}
ZHONGSHU_ALGO: str = str(_chan_cfg.get("zhongshu_algo", "seg_pen"))
# T1背驰阈值：最后离开笔力度/前同向离开笔力度 < 此值才判背驰（见 buy_sell_points.md §3.1）
DIVERGENCE_RATIO: float = float(_chan_cfg.get("divergence_ratio", 0.8))
