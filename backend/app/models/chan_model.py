from pydantic import BaseModel, Field
from typing import List

DAY = "day"

class ClassicChanKline(BaseModel):
    """缠论k线数据模型"""
    index: int = Field(..., description="K线索引")
    start: str = Field(..., description="开始时间")
    end: str = Field(..., description="结束时间")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")

class Fractal(BaseModel):
    """分型数据模型"""
    index: int = Field(..., description="K线索引")
    date: str = Field(..., description="日期")
    type: str = Field(..., description="分型类型 top/bottom")


class Pen(BaseModel):
    """笔数据模型"""
    start_index: int = Field(..., description="起始K线索引")
    end_index: int = Field(..., description="结束K线索引")
    start_date: str = Field(..., description="起始日期")
    end_date: str = Field(..., description="结束日期")
    direction: str = Field(..., description="方向 up/down")


class Segment(BaseModel):
    """线段数据模型"""
    start_index: int = Field(..., description="起始笔索引")
    end_index: int = Field(..., description="结束笔索引")
    pens: List[Pen] = Field(..., description="包含的笔列表")
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
