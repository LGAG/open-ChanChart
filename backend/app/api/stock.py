"""股票数据API接口"""
from fastapi import APIRouter, Query, Body
from typing import Optional, Dict, Any, List
from app.service.stock import get_stock_data_bao, query_stocks_list, search_stocks, update_kline_data, update_all_stock, get_stock_data_database
from app.models.stock_model import StockListResponse

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.post("/list", response_model=StockListResponse)
async def list_stocks(params: Optional[Dict[str, Any]] = Body(default=None)):
    """
    获取股票列表
    """
    stocks = query_stocks_list()
    return StockListResponse(
        code=200,
        message="Success",
        data=stocks
    )

@router.get("/search", response_model=dict)
async def search_stocks_api(
    keyword: str = Query(..., description="股票名称或代码"),
    market: Optional[str] = Query(None, description="市场类型 sh/sz")
):
    """
    搜索股票
    """
    results = search_stocks(keyword=keyword, market=market)
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
    优先从数据库读取，数据库无数据时回退到baostock在线拉取
    """
    print(f"code:{code}, market:{market}, period:{period}, start_date:{start_date}, end_date:{end_date}")

    # 优先从数据库读取
    df = get_stock_data_database(code=code, market=market, period=period, start_timestamp=start_date, end_timestamp=end_date)

    if df is not None and not df.empty:
        print(f"从数据库读取到 {len(df)} 条K线数据")
    else:
        # 数据库无数据，从baostock在线拉取
        print("数据库无数据，从baostock在线拉取")
        df = get_stock_data_bao(code=code, market=market, period=period, start_timestamp=start_date, end_timestamp=end_date)
        if df is False or df is None or (hasattr(df, 'empty') and df.empty):
            return {
                "code": 500,
                "message": "获取K线数据失败",
                "data": None
            }

    # 只保留需要的列并转换
    if period == "hour" or period == '60' or period == '60F' or period == '30F' or period == '5F':
        if 'end_time' in df.columns:
            df['date'] = df['end_time'].astype(str)

    # 确保date列存在且为字符串
    if 'date' in df.columns:
        df['date'] = df['date'].astype(str)

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


@router.post("/refresh-list", response_model=dict)
async def refresh_stock_list():
    """
    从baostock刷新股票列表到数据库
    """
    result = update_all_stock()
    if result is False or (hasattr(result, 'empty') and result.empty):
        return {
            "code": 500,
            "message": "刷新股票列表失败，请稍后重试",
            "data": None
        }
    count = len(result) if result is not None else 0
    return {
        "code": 200,
        "message": f"成功刷新 {count} 只股票",
        "data": {"count": count}
    }


@router.post("/update", response_model=dict)
async def update_data(
    code: Optional[str] = Query(None, description="股票代码，不填则更新所有股票"),
    market: str = Query(default="sh", description="市场类型 sh/sz"),
    periods: Optional[str] = Query(None, description="周期列表，逗号分隔，如 day,60F,30F,5F,week,month,year。不填则更新所有周期"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD，不填则默认一年前"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD，不填则默认今天")
):
    """
    批量更新K线数据到数据库

    支持的周期值：day(日K), 60F(1小时), 30F(30分钟), 5F(5分钟), week(周K), month(月K), year(年K)
    """
    period_list = periods.split(",") if periods else None
    results = update_kline_data(
        code=code,
        market=market,
        periods=period_list,
        start_date=start_date,
        end_date=end_date
    )
    return {
        "code": 200,
        "message": "Success",
        "data": results
    }
