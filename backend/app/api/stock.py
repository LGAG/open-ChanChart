"""股票数据API接口"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta
import akshare as ak
import random
from app.service.akshare_service import stock_processor
from app.service.stock import get_stock_data_daily_bao, query_stock

router = APIRouter(prefix="/api/stock", tags=["stock"])


# 模拟股票数据库
MOCK_STOCKS = [
    {"code": "000001", "name": "平安银行", "market": "sz"},
    {"code": "000002", "name": "万科A", "market": "sz"},
    {"code": "600000", "name": "浦发银行", "market": "sh"},
    {"code": "600036", "name": "招商银行", "market": "sh"},
    {"code": "600519", "name": "贵州茅台", "market": "sh"},
    {"code": "000858", "name": "五粮液", "market": "sz"},
    {"code": "300927", "name": "江天化学", "market": "sz"},
    {"code": "601211", "name": "国泰海通", "market": "sh"},
]


@router.get("/list", response_model=list)
async def list_stocks(params: dict = Query(default={})):
    """
    获取股票列表
    """
    return {
        "code": 200,
        "message": "Success",
        "data": query_stock(params)
    }

@router.get("/search", response_model=dict)
async def search_stocks(
    keyword: str = Query(..., description="股票名称或代码"),
    market: Optional[str] = Query(None, description="市场类型 sh/sz")
):
    """
    搜索股票
    """
    results = []
    
    for stock in MOCK_STOCKS:
        # 匹配关键词
        if keyword.lower() in stock["code"].lower() or keyword in stock["name"]:
            # 如果指定了市场，则过滤
            if market is None or stock["market"] == market:
                results.append(stock)
    
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
    start_date: Optional[str] = Query(default="20250101", description="开始日期 YYYYMMDD"),
    end_date: Optional[str] = Query(default="20260226", description="结束日期 YYYYMMDD")
):
    """
    获取股票K线数据
    """
    print(f"code:{code}, market:{market}, period:{period}, start_date:{start_date}, end_date:{end_date}")
    df = get_stock_data_daily_bao(code=code, market=market, period=period, start_timestamp=start_date, end_timestamp=end_date)
    print(df.info())

    # 只保留需要的列并转换
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
