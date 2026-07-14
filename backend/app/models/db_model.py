"""SQLAlchemy ORM 模型定义"""
from datetime import datetime as dt_datetime
from datetime import date as dt_date
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, Date, DateTime, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ── 股票表 ──

class Stock(Base):
    __tablename__ = "stock"
    __table_args__ = (
        Index("idx_code_name", "code", "name"),
        {"comment": "股票数据表"},
    )

    name: Mapped[str] = mapped_column(String(50), primary_key=True, nullable=False, comment="股票名称")
    code: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="股票代码")
    market: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="交易所")


# ── 日线表（含成交额/振幅/涨跌幅/换手率） ──

class DayKline(Base):
    __tablename__ = "day"
    __table_args__ = (
        Index("idx_date_code_period_level", "date", "code", "period", "level"),
        {"comment": "日线数据表"},
    )

    period: Mapped[str] = mapped_column(String(20), nullable=False, comment="周期")
    level: Mapped[int] = mapped_column(Integer, nullable=False, comment="级别")
    date: Mapped[dt_date] = mapped_column(Date, primary_key=True, nullable=False, comment="日期")
    code: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="股票代码")
    market: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="交易所")
    open: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="开盘价")
    high: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最高价")
    low: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最低价")
    close: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="收盘价")
    volume: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True, comment="成交量")
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True, comment="成交额")
    amplitude: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True, comment="振幅")
    change: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True, comment="涨跌幅")
    turnover: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True, comment="换手率")


# ── 周线/月线/年线（含成交额，主键为 code+date+market） ──

class WeekKline(Base):
    __tablename__ = "week"
    __table_args__ = (
        Index("idx_date_code", "date", "code"),
        {"comment": "周线数据表"},
    )

    period: Mapped[str] = mapped_column(String(20), nullable=False, comment="周期")
    level: Mapped[int] = mapped_column(Integer, nullable=False, comment="级别")
    date: Mapped[dt_date] = mapped_column(Date, primary_key=True, nullable=False, comment="日期")
    code: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="股票代码")
    market: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="交易所")
    open: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="开盘价")
    high: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最高价")
    low: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最低价")
    close: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="收盘价")
    volume: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True, comment="成交量")
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True, comment="成交额")


class MonthKline(Base):
    __tablename__ = "month"
    __table_args__ = (
        Index("idx_date_code", "date", "code"),
        {"comment": "月线数据表"},
    )

    period: Mapped[str] = mapped_column(String(20), nullable=False, comment="周期")
    level: Mapped[int] = mapped_column(Integer, nullable=False, comment="级别")
    date: Mapped[dt_date] = mapped_column(Date, primary_key=True, nullable=False, comment="日期")
    code: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="股票代码")
    market: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="交易所")
    open: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="开盘价")
    high: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最高价")
    low: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最低价")
    close: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="收盘价")
    volume: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True, comment="成交量")
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True, comment="成交额")


class YearKline(Base):
    __tablename__ = "year"
    __table_args__ = (
        Index("idx_date_code", "date", "code"),
        {"comment": "年线数据表"},
    )

    period: Mapped[str] = mapped_column(String(20), nullable=False, comment="周期")
    level: Mapped[int] = mapped_column(Integer, nullable=False, comment="级别")
    date: Mapped[dt_date] = mapped_column(Date, primary_key=True, nullable=False, comment="日期")
    code: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="股票代码")
    market: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="交易所")
    open: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="开盘价")
    high: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最高价")
    low: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最低价")
    close: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="收盘价")
    volume: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True, comment="成交量")
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True, comment="成交额")


# ── 分钟线表（主键为 code+start_time+market） ──

class HourKline(Base):
    __tablename__ = "hour"
    __table_args__ = (
        Index("idx_date_code_period_level", "start_time", "code", "period", "level"),
        {"comment": "小时线数据表"},
    )

    period: Mapped[str] = mapped_column(String(20), nullable=False, comment="周期")
    level: Mapped[int] = mapped_column(Integer, nullable=False, comment="级别")
    start_time: Mapped[dt_datetime] = mapped_column(DateTime, primary_key=True, nullable=False, comment="开始时间")
    end_time: Mapped[dt_datetime] = mapped_column(DateTime, nullable=False, comment="结束时间")
    code: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="股票代码")
    market: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="交易所")
    open: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="开盘价")
    high: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最高价")
    low: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最低价")
    close: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="收盘价")
    volume: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True, comment="成交量")


class HalfKline(Base):
    __tablename__ = "half"
    __table_args__ = (
        Index("idx_date_code_period_level", "start_time", "code", "period", "level"),
        {"comment": "半小时线数据表"},
    )

    period: Mapped[str] = mapped_column(String(20), nullable=False, comment="周期")
    level: Mapped[int] = mapped_column(Integer, nullable=False, comment="级别")
    start_time: Mapped[dt_datetime] = mapped_column(DateTime, primary_key=True, nullable=False, comment="开始时间")
    end_time: Mapped[dt_datetime] = mapped_column(DateTime, nullable=False, comment="结束时间")
    code: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="股票代码")
    market: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="交易所")
    open: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="开盘价")
    high: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最高价")
    low: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最低价")
    close: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="收盘价")
    volume: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True, comment="成交量")


class FiveMinKline(Base):
    __tablename__ = "five_min"
    __table_args__ = (
        Index("idx_date_code_period_level", "start_time", "code", "period", "level"),
        {"comment": "5分钟线数据表"},
    )

    period: Mapped[str] = mapped_column(String(20), nullable=False, comment="周期")
    level: Mapped[int] = mapped_column(Integer, nullable=False, comment="级别")
    start_time: Mapped[dt_datetime] = mapped_column(DateTime, primary_key=True, nullable=False, comment="开始时间")
    end_time: Mapped[dt_datetime] = mapped_column(DateTime, nullable=False, comment="结束时间")
    code: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="股票代码")
    market: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, comment="交易所")
    open: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="开盘价")
    high: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最高价")
    low: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="最低价")
    close: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="收盘价")
    volume: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True, comment="成交量")


# ── 周期 → ORM 模型映射 ──

KLINE_MODEL_MAP: dict[str, type[Base]] = {
    "day": DayKline,
    "week": WeekKline,
    "month": MonthKline,
    "year": YearKline,
    "hour": HourKline,
    "half": HalfKline,
    "five_min": FiveMinKline,
}


def get_kline_model(period: str) -> type[Base] | None:
    """根据周期字符串获取对应的 ORM 模型类

    支持的 period 值：
    - "day", "daily", "d" → DayKline
    - "hour", "60", "60F" → HourKline
    - "half", "30", "30F" → HalfKline
    - "five_min", "5", "5F" → FiveMinKline
    - "week", "w" → WeekKline
    - "month", "m" → MonthKline
    - "year", "y" → YearKline
    """
    normalized = {
        "day": "day", "daily": "day", "d": "day",
        "hour": "hour", "60": "hour", "60f": "hour",
        "half": "half", "30": "half", "30f": "half",
        "five_min": "five_min", "5": "five_min", "5f": "five_min",
        "week": "week", "w": "week",
        "month": "month", "m": "month",
        "year": "year", "y": "year",
    }.get(period.lower())
    if normalized is None:
        return None
    return KLINE_MODEL_MAP.get(normalized)
