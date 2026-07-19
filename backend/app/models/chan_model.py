from pydantic import BaseModel, Field
from typing import List

DAY = "day"

class ClassicChanKline(BaseModel):
    """缠论k线数据模型"""
    index: int = Field(..., description="缠论K线索引")
    start: int = Field(..., description="开始k线索引")
    end: int = Field(..., description="结束k线索引")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")

class Fractal(BaseModel):
    """分型数据模型"""
    index: int = Field(..., description="缠论K线索引")
    k_index: int = Field(..., description="K线索引")
    date: str = Field(..., description="日期")
    type: str = Field(..., description="分型类型 top/bottom")
    is_sure: bool = Field(default=True, description="是否确认分型(True=确定/False=虚拟)")


class Pen(BaseModel):
    """笔数据模型"""
    start_index: int = Field(..., description="起始缠论K线索引")
    end_index: int = Field(..., description="结束缠论K线索引")
    start_date: str = Field(..., description="起始日期")
    end_date: str = Field(..., description="结束日期")
    direction: str = Field(..., description="方向 up/down")
    is_sure: bool = Field(default=True, description="是否确认笔(True=确定笔/False=虚拟笔)")


class Segment(BaseModel):
    """线段数据模型"""
    start_index: int = Field(..., description="起始笔索引")
    end_index: int = Field(..., description="结束笔索引")
    top: float = Field(..., description="线段高点")
    bottom: float = Field(..., description="线段低点")
    direction: str = Field(..., description="方向 up/down")


class ZhongShu(BaseModel):
    """中枢数据模型"""
    start_index: int = Field(..., description="起始索引")
    end_index: int = Field(..., description="结束索引")
    high: float = Field(..., description="中枢上沿")
    low: float = Field(..., description="中枢下沿")
    level: int = Field(..., description="中枢级别")


class ChanData(BaseModel):
    """缠论数据响应模型"""
    fractals: List[Fractal] = Field(default_factory=list, description="分型列表")
    pens: List[Pen] = Field(default_factory=list, description="笔列表")
    segments: List[Segment] = Field(default_factory=list, description="段列表")
    zhongshus: List[ZhongShu] = Field(default_factory=list, description="中枢列表")
