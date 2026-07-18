"""数据库数据完整性检查（启动期运行，只读，永不阻断启动）

检查项：
1. 股票改名重复：stock 表中同一 (code, market) 对应多个不同 name。
   主键改为 (code, market) 后此为不变量断言——改名现已按 (code, market) 就地
   upsert 覆盖 name，结构上不可能再产生重复，恒报 0；若报告 >0 说明迁移回退或人工篡改。
2. 孤儿 K 线：K 线表中存在 stock 表里完全没有的 (code, market)
3. 同时刻重复行：K 线表中同一 (time, code, market) 出现多行（旧 schema 缺复合主键时可能残留）

异常仅报告到 backend/logs/data_integrity.log 并打印一行控制台摘要，不修改数据、不阻断启动。
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import FromClause
from sqlalchemy.sql.elements import KeyedColumnElement

from app.models.db_model import Stock, KLINE_MODEL_MAP
from app.utils.database import get_session


# 日志文件路径：backend/logs/data_integrity.log（绝对路径，不依赖 CWD）
# __file__ = backend/app/service/data_check.py，三次 dirname 上溯到 backend/
_LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs",
)
_LOG_PATH = os.path.join(_LOG_DIR, "data_integrity.log")


def check_data_integrity() -> dict:
    """执行全部数据完整性检查，返回汇总结果，同时写日志文件并打印一行控制台摘要。

    本函数永不抛异常：任何子检查失败均被捕获并记录为该检查的错误信息，
    不影响其它检查与启动流程。所有查询为只读。

    Returns:
        {"stock_rename_duplicates": list[dict],
         "orphan_kline_pairs": dict[str, list[dict]],
         "duplicate_same_time": dict[str, list[dict]],
         "errors": list[str]}
    """
    results: dict = {
        "stock_rename_duplicates": [],
        "orphan_kline_pairs": {},
        "duplicate_same_time": {},
        "errors": [],
    }

    # 单一 session 串联三个只读检查；每个子检查独立 try/except，互不影响。
    # get_session() 成功退出时 commit()（只读事务，无副作用），异常时 rollback()+raise。
    try:
        with get_session() as session:
            try:
                results["stock_rename_duplicates"] = _check_stock_rename_duplicates(session)
            except Exception as e:
                results["errors"].append(f"stock_rename_duplicates: {e}")

            try:
                results["orphan_kline_pairs"] = _check_orphan_kline(session)
            except Exception as e:
                results["errors"].append(f"orphan_kline: {e}")

            try:
                results["duplicate_same_time"] = _check_duplicate_same_time(session)
            except Exception as e:
                results["errors"].append(f"duplicate_same_time: {e}")
    except Exception as e:
        # get_session 本身出错（连接失败等）
        results["errors"].append(f"session: {e}")

    _write_report(results)
    _print_summary(results)
    return results


def _total_anomalies(results: dict) -> int:
    """统计各类异常条目总数，用于控制台摘要行。"""
    n = len(results.get("stock_rename_duplicates", []))
    for pairs in results.get("orphan_kline_pairs", {}).values():
        n += len(pairs)
    for dups in results.get("duplicate_same_time", {}).values():
        n += len(dups)
    return n


def _check_stock_rename_duplicates(session: Session) -> list[dict]:
    """检查 stock 表中 (code, market) 对应多个不同 name 的情况。

    不变量断言：主键改为 (code, market) 后结构上不可能产生此类重复（改名按
    (code, market) 就地 upsert 覆盖 name），故恒返回空列表。保留此检查作为
    健康态探针：若返回非空说明迁移回退或人工篡改了 stock 表。

    历史成因（已消除）：旧主键含 name，baostock 改名时 update_all_stock 以新
    (name, code, market) upsert，旧 name 行保留导致同 code+market 出现多行不同 name。

    Returns:
        [{"code": str, "market": str, "names": [str, ...]}, ...]
    """
    # 子查询：每个 (code, market) 的不同 name 数量，保留 >1 的对
    sub = (
        session.query(
            Stock.code,
            Stock.market,
            func.count(func.distinct(Stock.name)).label("name_cnt"),
        )
        .group_by(Stock.code, Stock.market)
        .having(func.count(func.distinct(Stock.name)) > 1)
        .subquery()
    )

    dup_pairs = session.query(sub.c.code, sub.c.market).all()

    out: list[dict] = []
    for code, market in dup_pairs:
        names = [
            r[0]
            for r in session.query(Stock.name)
            .filter(Stock.code == code, Stock.market == market)
            .distinct()
            .all()
        ]
        out.append({"code": code, "market": market, "names": names})
    return out


def _check_orphan_kline(session: Session) -> dict[str, list[dict]]:
    """检查各 K 线表中 (code, market) 在 stock 表中完全不存在的孤儿数据。

    Returns:
        {"day": [{"code": str, "market": str}, ...], ...}
        仅包含存在孤儿数据的周期。
    """
    out: dict[str, list[dict]] = {}
    for period, model_class in KLINE_MODEL_MAP.items():
        table = model_class.__table__
        code_col = table.c.code
        market_col = table.c.market
        # 相关子查询：stock 表中存在同 code+market 的记录
        stock_exists = (
            select(Stock.code)
            .where(
                (Stock.code == code_col)
                & (Stock.market == market_col)
            )
            .exists()
        )
        rows = (
            session.query(code_col, market_col)
            .filter(~stock_exists)
            .distinct()
            .all()
        )
        if rows:
            out[period] = [{"code": c, "market": m} for c, m in rows]
    return out


def _get_time_column(table: FromClause) -> tuple[KeyedColumnElement[Any], str]:
    """获取 K 线表的时间列：date 模型返回 (date, "date")，时间模型返回 (start_time, "start_time")。

    通过 __table__.c 按列名访问，避免在 type[Base] 上访问未声明的类属性（mypy [attr-defined]）。
    返回类型 KeyedColumnElement[Any] 为 FromClause.c 访问器的实际返回类型。
    """
    if "date" in table.c:
        return table.c.date, "date"
    return table.c.start_time, "start_time"


def _check_duplicate_same_time(session: Session) -> dict[str, list[dict]]:
    """检查各 K 线表中同一 (time, code, market) 出现多行的情况。

    date 模型（Day/Week/Month/Year）按 date 分组；
    时间模型（Hour/Half/FiveMin）按 start_time 分组。

    防御性检查：Base.metadata.create_all 不修改既有表结构，
    旧 schema 缺复合主键时可能存在真实重复行。

    Returns:
        {"day": [{"date": "YYYY-MM-DD", "code": str, "market": str, "count": int}, ...],
         "hour": [{"start_time": "YYYY-MM-DD HH:MM:SS", "code": str, "market": str, "count": int}, ...]}
        仅包含存在重复的周期。
    """
    out: dict[str, list[dict]] = {}
    for period, model_class in KLINE_MODEL_MAP.items():
        table = model_class.__table__
        time_col, time_key = _get_time_column(table)
        code_col = table.c.code
        market_col = table.c.market

        rows = (
            session.query(
                time_col.label(time_key),
                code_col,
                market_col,
                func.count().label("cnt"),
            )
            .group_by(time_col, code_col, market_col)
            .having(func.count() > 1)
            .all()
        )
        if rows:
            out[period] = [
                {
                    time_key: str(time_val),
                    "code": code,
                    "market": market,
                    "count": int(cnt),
                }
                for time_val, code, market, cnt in rows
            ]
    return out


def _write_report(results: dict) -> None:
    """将完整检查明细追加写入日志文件（带时间戳表头）。目录不存在则创建。

    任何 OSError 均被吞掉：写日志失败不影响启动。
    """
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
    except OSError:
        return

    lines: list[str] = []
    lines.append("=" * 72)
    lines.append(f"数据完整性检查  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 72)

    if results["errors"]:
        lines.append(f"[执行错误] 共 {len(results['errors'])} 项：")
        for e in results["errors"]:
            lines.append(f"  - {e}")
        lines.append("")

    dups = results["stock_rename_duplicates"]
    lines.append(f"[1] 股票改名重复 (code,market) 对：共 {len(dups)} 组")
    if dups:
        for d in dups:
            names = ", ".join(d["names"])
            lines.append(f"    {d['market']}.{d['code']}: names=[{names}]")
    else:
        lines.append("    （无）")
    lines.append("")

    orphans = results["orphan_kline_pairs"]
    orphan_total = sum(len(v) for v in orphans.values())
    lines.append(f"[2] 孤儿 K 线 (code,market) 对：共 {orphan_total} 组，分布在 {len(orphans)} 个周期表")
    if orphans:
        for period, pairs in orphans.items():
            lines.append(f"    {period} ({len(pairs)} 组):")
            for p in pairs:
                lines.append(f"        {p['market']}.{p['code']}")
    else:
        lines.append("    （无）")
    lines.append("")

    sametime = results["duplicate_same_time"]
    sametime_total = sum(len(v) for v in sametime.values())
    lines.append(f"[3] 同时刻重复行 (time,code,market)：共 {sametime_total} 组，分布在 {len(sametime)} 个周期表")
    if sametime:
        for period, groups in sametime.items():
            lines.append(f"    {period} ({len(groups)} 组):")
            for g in groups:
                tk = "date" if "date" in g else "start_time"
                lines.append(f"        {g['market']}.{g['code']} @ {g[tk]}  x{g['count']}")
    else:
        lines.append("    （无）")
    lines.append("")
    lines.append("")

    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except OSError:
        return


def _print_summary(results: dict) -> None:
    """打印一行控制台摘要，风格对齐 run.py 的 emoji 输出。"""
    n = _total_anomalies(results)
    err_n = len(results["errors"])
    if n == 0 and err_n == 0:
        print(f"✅ 数据完整性检查通过（明细见 {_LOG_PATH}）")
    elif err_n == 0:
        print(f"⚠️ 数据完整性检查发现 {n} 项异常（明细见 {_LOG_PATH}）")
    else:
        print(f"❌ 数据完整性检查发现 {n} 项异常 + {err_n} 项执行错误（明细见 {_LOG_PATH}）")
