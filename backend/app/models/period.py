"""周期定义单一真相源。

所有受支持的 K 线周期在此声明一次，后端的写入路径、读取路径、对前端
暴露的 API 都从 SUPPORTED_PERIODS 派生。新增周期只需在此追加一个
PeriodDef（并在 db_model.KLINE_MODEL_MAP 确认有对应表），无需改其它文件。

注意：此处只列「数据源(baostock)能拉到数据」的周期。baostock 的
query_history_k_data_plus 仅支持 frequency d/w/m/5/15/30/60，不支持年线 y
（年K 暂不从数据源获取，日后可用月线/日线聚合实现）。15F 虽 baostock 支持
但 KLINE_MODEL_MAP 无 15 分钟表，故也未列入。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PeriodDef:
    value: str          # 前端下拉 value，也是前后端约定的 period 字符串（稳定、可读）
    label: str          # 中文显示名
    baostock_freq: str  # baostock frequency 取值（d/w/m/60/30/5）
    table_key: str      # app.models.db_model.KLINE_MODEL_MAP 的键
    level: int          # 写库 level 列的值（缠论级别）


SUPPORTED_PERIODS: list[PeriodDef] = [
    PeriodDef("day", "日K", "d", "day", 6),
    PeriodDef("week", "周K", "w", "week", 7),
    PeriodDef("month", "月K", "m", "month", 8),
    PeriodDef("60F", "60分K", "60", "hour", 5),
    PeriodDef("30F", "30分K", "30", "half", 5),
    PeriodDef("5F", "5分K", "5", "five_min", 4),
]

# 历史别名 → 标准 value，用于兼容旧 period 字符串（大小写不敏感）。
# 注意：15F 暂不列入，因 KLINE_MODEL_MAP 无 15 分钟表；补表后在此追加。
_PERIOD_ALIAS: dict[str, str] = {
    "daily": "day", "d": "day",
    "hour": "60F", "60": "60F",
    "half": "30F", "30": "30F",
    "five_min": "5F", "5": "5F",
    "w": "week", "m": "month", "y": "year",
}


def periods_for_api() -> list[dict[str, str]]:
    """供 /api/chan/periods 返回前端的周期清单。"""
    return [{"value": p.value, "label": p.label} for p in SUPPORTED_PERIODS]


def resolve_period(period: str) -> PeriodDef | None:
    """将任意 period 字符串解析为 PeriodDef，无法识别时返回 None。

    先按标准 value 匹配，再回退到历史别名。大小写不敏感。
    """
    pl = period.lower()
    for p in SUPPORTED_PERIODS:
        if p.value.lower() == pl:
            return p
    mapped = _PERIOD_ALIAS.get(pl)
    if mapped is not None:
        for p in SUPPORTED_PERIODS:
            if p.value == mapped:
                return p
    return None
