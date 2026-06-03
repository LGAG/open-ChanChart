"""股票数据API接口"""
from fastapi import APIRouter, Query, Body
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.service.stock import get_stock_data_daily_bao, query_stock, get_stock_data_bao
from app.models.stock_model import StockListResponse

router = APIRouter(prefix="/api/stock", tags=["stock"])


LIST_STOCKS = [

]


@router.post("/list", response_model=StockListResponse)
async def list_stocks(params: Optional[Dict[str, Any]] = Body(default=None)):
    """
    获取股票列表
    """
    if params is None:
        params = {}
    
    global LIST_STOCKS
    LIST_STOCKS = query_stock("SELECT * FROM stock", params)

    return StockListResponse(
        code=200,
        message="Success",
        data=LIST_STOCKS
    )

@router.get("/search", response_model=dict)
async def search_stocks(
    keyword: str = Query(..., description="股票名称或代码"),
    market: Optional[str] = Query(None, description="市场类型 sh/sz")
):
    """
    搜索股票
    """
    results = []
    global LIST_STOCKS
    if len(LIST_STOCKS) == 0:
        LIST_STOCKS = query_stock("SELECT * FROM stock")
    
    for stock in LIST_STOCKS:
        # 匹配关键词
        if keyword.lower() in stock["code"].lower() or keyword in stock["name"]:
            # 如果指定了市场，则过滤
            if market is None or stock["market"] == market:
                results.append(stock)
                if len(results) >= 5:
                    break
    
    return {
        "code": 200,
        "message": "Success",
        "data": results
    }


@router.get("/kline", response_model=dict)
async def get_kline_data(
    code: str = Query(..., description="股票代码"),
    market: str = Query(default="sh", description="市场类型"),
    period: str = Query(default="daily", description="周期 D/30F/5F"),
    start_date: str = Query(default="2025-01-01", description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(default="2026-02-26", description="结束日期 YYYY-MM-DD")
):
    """
    获取股票K线数据
    """
    print(f"code:{code}, market:{market}, period:{period}, start_date:{start_date}, end_date:{end_date}")
    df = get_stock_data_bao(code=code, market=market, period=period, start_timestamp=start_date, end_timestamp=end_date)
    if df is False:
        print("获取数据失败，返回False")
    else:
        print(df.info())

    # 只保留需要的列并转换
    if period == "hour" or period == '60' or period == '60F' or period == '30F' or period == '5F':
        df['date'] = df['end_time']
    klines = df[
            ['date', 'open', 'high', 'low', 'close', 'volume', 'period', 'level', 'code']
        ].to_dict('records')
    
    return {
        "code": 200,
        "message": "Success",
        "data": {
            "code": code,
            "market": market,
            "period": period,
            "klines": klines
        }
    }
