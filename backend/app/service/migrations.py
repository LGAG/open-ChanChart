"""数据库 schema 迁移（启动期运行，幂等，失败抛异常由 run.py 捕获，绝不阻断启动）

当前迁移项：
1. stock 表主键 (name, code, market) → (code, market)
   成因：旧主键含 name，baostock 改名后 upsert 插入新行而保留旧行，产生同
   (code, market) 多 name 的重复行。改为 (code, market) 后改名就地 upsert 覆盖 name。

幂等性：通过 inspect(engine) 读取真实库主键（非 ORM 模型）判断是否已迁移，
已迁移或新库直接返回；去重为事务性 DELETE，崩溃后重跑为 no-op，再校验+改主键。
"""
from __future__ import annotations

from sqlalchemy import inspect, text

from app.utils.database import engine

# MySQL 咨询锁名：防止多实例同时迁移同一张表
_LOCK_NAME = "chanchart_stock_pk_migration"

# 去重：每组 (code, market) 仅保留 name 最小的一行。
# 旧主键 (name, code, market) 保证组内 name 互不相同，故 s1.name > s2.name 是严格全序，
# 每组恰留一行。保留哪一行无关紧要——迁移后 update_all_stock 的 upsert 会按
# (code, market) 覆盖 name，取 MIN(name) 仅是确定、廉价。
_DEDUPE_SQL = (
    "DELETE s1 FROM stock s1 "
    "JOIN stock s2 "
    "ON s1.code = s2.code AND s1.market = s2.market AND s1.name > s2.name"
)

# 去重后不变量校验：(code, market) 仍重复的组数必须为 0 才能改主键
_COUNT_DUP_SQL = (
    "SELECT COUNT(*) FROM ("
    "SELECT 1 FROM stock GROUP BY code, market HAVING COUNT(*) > 1"
    ") t"
)

# 改主键：单条原子 ALTER。DROP PRIMARY KEY + ADD PRIMARY KEY 之间无中间可见态。
# idx_code_name 由 create_all 不会自动删除，存量库若存在则在此一并清理。
_ALTER_SQL = "ALTER TABLE stock DROP PRIMARY KEY, ADD PRIMARY KEY (code, market)"
_DROP_INDEX_SUFFIX = ", DROP INDEX idx_code_name"


def migrate_stock_primary_key() -> None:
    """stock 表主键 (name, code, market) → (code, market)。幂等；失败抛异常。

    多实例保护：用 MySQL 咨询锁串行化迁移，5s 内拿不到锁则跳过（不阻断启动）。
    """
    insp = inspect(engine)

    # 表不存在（create_all 未成功/未运行）→ 无需迁移
    if "stock" not in insp.get_table_names():
        return

    # 读真实主键列；name 不在则已是 (code, market)（已迁移或新建表）→ 直接返回
    pk_cols: list[str] = list(
        insp.get_pk_constraint("stock").get("constrained_columns") or []
    )
    if "name" not in pk_cols:
        return

    # 多实例保护：拿不到锁则跳过，避免两个 run.py 进程并发改主键
    with engine.connect() as conn:
        got = conn.execute(text("SELECT GET_LOCK(:name, 5)"), {"name": _LOCK_NAME}).scalar()
    if got != 1:
        print("⚠️ stock 主键迁移：另一进程正在迁移，本次跳过")
        return

    try:
        # 1) 去重：每组 (code, market) 仅留 MIN(name)。DELETE 事务性，失败不 commit 即回滚
        with engine.connect() as conn:
            conn.execute(text(_DEDUPE_SQL))
            conn.commit()

        # 2) 校验：(code, market) 已唯一。仍重复则绝不改主键 → 抛异常由 run.py 捕获
        with engine.connect() as conn:
            dup_count: int = int(conn.execute(text(_COUNT_DUP_SQL)).scalar() or 0)
        if dup_count != 0:
            raise RuntimeError(
                f"去重后仍存在 {dup_count} 组重复 (code, market)，中止主键迁移"
            )

        # 3) 改主键（单条原子 ALTER）。条件性附带 DROP idx_code_name
        index_names: set[str] = {
            name for idx in insp.get_indexes("stock")
            if (name := idx.get("name")) is not None
        }
        alter_sql = _ALTER_SQL + (_DROP_INDEX_SUFFIX if "idx_code_name" in index_names else "")
        with engine.connect() as conn:
            conn.execute(text(alter_sql))
            conn.commit()

        print("✅ stock 主键已迁移为 (code, market)")
    finally:
        with engine.connect() as conn:
            conn.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": _LOCK_NAME})
            conn.commit()
