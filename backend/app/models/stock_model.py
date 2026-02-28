from pydantic import BaseModel, Field
from typing import Optional


class KlineData(BaseModel):
    """K线数据模型"""
    period: str = Field(..., description="周期")
    level: int = Field(..., description="级别")
    date: str = Field(..., description="日期")
    code: str = Field(..., description="股票代码")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: float = Field(..., description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    amplitude: Optional[float] = Field(None, description="振幅")
    change: Optional[float] = Field(None, description="涨跌幅")
    turnover: Optional[float] = Field(None, description="换手率")


class StockInfo(BaseModel):
    """股票信息模型"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    market: str = Field(..., description="市场类型 sh/sz")


class KlineRequest(BaseModel):
    """K线数据请求模型"""
    code: str = Field(..., description="股票代码")
    market: str = Field(default="sh", description="市场类型")
    period: str = Field(default="D", description="周期 D/30F/5F")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
