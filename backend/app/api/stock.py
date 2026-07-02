"""股票数据API接口"""
from fastapi import APIRouter, Query, Body
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.service.stock import get_stock_data_bao, query_stocks_list, search_stocks, update_kline_data, update_all_stock, get_stock_data_database, get_kline_date_range
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
    name: Optional[str] = Query(None, description="股票名称"),
    market: str = Query(default="sh", description="市场类型"),
    period: str = Query(default="daily", description="周期 D/30F/5F"),
    start_date: str = Query(default="2025-01-01", description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(default="2026-02-26", description="结束日期 YYYY-MM-DD")
):
    """
    获取股票K线数据
    优先从数据库读取；如果数据库数据不覆盖请求的日期范围，则先更新数据库再读取。
    """
    print(f"code:{code}, name:{name}, market:{market}, period:{period}, start_date:{start_date}, end_date:{end_date}")

    # 检查数据库中该股票该周期的日期覆盖范围
    db_min, db_max = get_kline_date_range(code, market, period, name=name)
    request_start = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
    request_end = datetime.strptime(end_date[:10], "%Y-%m-%d").date()

    need_update = False
    if db_min is None or db_max is None:
        # 数据库中完全没有该数据
        print(f"数据库中无 {code}({market}) {period} 数据，需要更新")
        need_update = True
    elif db_min > request_start:
        # 数据库最早日期晚于请求起始日期，缺少前期数据
        print(f"数据库数据不完整：最早日期 {db_min} 晚于请求起始日期 {request_start}，需要更新")
        need_update = True
    elif db_max < request_end:
        # 数据库最晚日期早于请求结束日期，缺少近期数据
        print(f"数据库数据不完整：最晚日期 {db_max} 早于请求结束日期 {request_end}，需要更新")
        need_update = True

    if need_update:
        # 从baostock拉取缺失范围的完整数据并写入数据库
        update_start = start_date[:10]
        update_end = end_date[:10]
        # 如果数据库有部分数据，扩大更新范围以覆盖缺口
        if db_min is not None and db_min <= request_start and db_max < request_end:
            # 只缺近期数据，从数据库最晚日期开始更新
            update_start = db_max.strftime("%Y-%m-%d")
        elif db_min is not None and db_min > request_start and db_max >= request_end:
            # 只缺前期数据，更新到数据库最早日期
            update_end = db_min.strftime("%Y-%m-%d")
        print(f"从baostock更新 {code}({market}) {period} 数据：{update_start} ~ {update_end}")
        update_kline_data(code=code, market=market, periods=[period], start_date=update_start, end_date=update_end, name=name)

    # 从数据库读取（更新后的完整数据）
    df = get_stock_data_database(code=code, market=market, period=period, start_timestamp=start_date, end_timestamp=end_date, name=name)

    if df is None or df.empty:
        # 数据库仍无数据，尝试直接从baostock获取（不写库的兜底）
        print("数据库仍无数据，尝试从baostock直接获取")
        df = get_stock_data_bao(code=code, market=market, period=period, start_timestamp=start_date, end_timestamp=end_date)

    if df is False or df is None or (hasattr(df, 'empty') and df.empty):
        return {
            "code": 500,
            "message": "获取K线数据失败",
            "data": None
        }

    print(f"获取到 {len(df)} 条K线数据")

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
    name: Optional[str] = Query(None, description="股票名称"),
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
        end_date=end_date,
        name=name
    )
    return {
        "code": 200,
        "message": "Success",
        "data": results
    }
