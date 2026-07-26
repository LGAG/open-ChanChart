"""收藏股票的数据库操作

镜像 service/stock.py 中 query_stocks_list / search_stocks 的 with get_session() +
返回 list[dict] 风格。收藏以 (code, market) 为唯一键，重复收藏时 upsert 刷新 name。
"""
from __future__ import annotations

from sqlalchemy.dialects.mysql import insert as mysql_insert

from app.utils.database import get_session
from app.models.db_model import Favorite


def list_favorites() -> list[dict]:
    """查询全部收藏，按收藏时间升序（先收藏的在前），同时间按代码排序。"""
    with get_session() as session:
        rows = (
            session.query(Favorite)
            .order_by(Favorite.created_at, Favorite.code)
            .all()
        )
        return [{"name": r.name, "code": r.code, "market": r.market} for r in rows]


def add_favorite(code: str, market: str, name: str) -> dict:
    """收藏一只股票（重复收藏时 upsert 刷新 name），返回收藏项。"""
    row = {"code": code, "market": market, "name": name}
    with get_session() as session:
        insert_stmt = mysql_insert(Favorite).values(row)
        # 重复 (code, market) 时仅刷新 name，created_at 保留首次收藏时间
        upsert_stmt = insert_stmt.on_duplicate_key_update(name=insert_stmt.inserted.name)
        session.execute(upsert_stmt)
    return {"name": name, "code": code, "market": market}


def remove_favorite(code: str, market: str) -> bool:
    """取消收藏，返回是否实际删除了记录。"""
    with get_session() as session:
        deleted = (
            session.query(Favorite)
            .filter(Favorite.code == code, Favorite.market == market)
            .delete(synchronize_session=False)
        )
    return deleted > 0
