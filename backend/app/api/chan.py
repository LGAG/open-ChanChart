"""缠论数据API接口"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.models.stock_model import KlineData
from app.core.chan_algorithm import calculate_chan_data
from app.api.stock import get_kline_data

router = APIRouter(prefix="/api/chan", tags=["chan"])


@router.get("/analysis", response_model=dict)
async def get_chan_analysis(
    code: str = Query(..., description="股票代码"),
    market: str = Query(default="sh", description="市场类型"),
    period: str = Query(default="D", description="周期 D/30F/5F"),
    process_include: bool = Query(default=True, description="是否处理包含关系"),
    start_date: str = Query("2025-01-01", description="开始日期 YYYY-MM-DD"),
    end_date: str = Query("2026-02-26", description="结束日期 YYYY-MM-DD")
):
    """
    获取缠论分析数据
    """
    # 1. 获取K线数据
    kline_response = await get_kline_data(
        code=code,
        market=market,
        period=period,
        start_date=start_date,
        end_date=end_date
    )
    
    if kline_response["code"] != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch kline data")
    
    klines_data = kline_response["data"]["klines"]
    
    # 2. 转换为KlineData对象
    klines = [KlineData(**kline) for kline in klines_data]
    
    # 3. 计算缠论数据
    chan_result = calculate_chan_data(klines, process_include=process_include)
    
    return {
        "code": 200,
        "message": "Success",
        "data": {
            "code": code,
            "market": market,
            "period": period,
            "klines": klines,
            "chan": {
                "chan_klines": [f.model_dump() for f in chan_result["chan_klines"]],
                "fractals": [f.model_dump() for f in chan_result["fractals"]],
                "pens": [p.model_dump() for p in chan_result["pens"]],
                "segments": [s.model_dump() for s in chan_result["segments"]],
            }
        }
    }
