from __future__ import annotations
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.dialects.mysql import insert as mysql_insert
from app.utils.database import engine, get_session
from app.models.db_model import Stock, DayKline, WeekKline, MonthKline, YearKline, get_kline_model


def parse_time_to_minute(time_str: str) -> pd.Timestamp:
    if pd.isna(time_str) or time_str == "":
        return pd.NaT  # type: ignore[return-value]

    try:
        parse_str = time_str[:14]
        dt = datetime.strptime(parse_str, "%Y%m%d%H%M%S")
        dt_minute = dt.replace(microsecond=0)
        return pd.Timestamp(dt_minute)
    except (ValueError, TypeError):
        return pd.NaT  # type: ignore[return-value]


def _upsert_dataframe(df: pd.DataFrame, model_class) -> None:
    """将 DataFrame 数据 upsert 到对应的 ORM 表中"""
    data = df.to_dict('records')
    table = model_class.__table__
    insert_stmt = mysql_insert(table).values(data)
    update_stmt = {col: insert_stmt.inserted[col] for col in df.columns}
    upsert_stmt = insert_stmt.on_duplicate_key_update(**update_stmt)
    with engine.connect() as conn:
        conn.execute(upsert_stmt)
        conn.commit()


def get_stock_data_bao(code: str, market: str, period: str, start_timestamp: str, end_timestamp: str):
    try:
        lg = bs.login()
        print('login respond error_code:' + lg.error_code)
        print('login respond  error_msg:' + lg.error_msg)
        if period == "daily" or period == "day" or period == "d":
            period = "d"
            start = datetime.strptime(start_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
            end = datetime.strptime(end_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
            rs = bs.query_history_k_data_plus(f"{market}.{code}", "date,code,open,high,low,close,volume", start_date=start, end_date=end, frequency=period, adjustflag="3")
            print('query_history_k_data_plus respond error_code:' + rs.error_code)
            print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)
            df = rs.get_data()

            df['volume'] = df['volume'].astype(str).replace({
                '': '0',
                'nan': '0',
                'None': '0'
            })
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0)
            df['period'] = 'day'
            df['level'] = 6
            df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
            df['market'] = df['market'].str.lower()
            df = df.drop(columns=['code'])
            df.rename(columns={'new_code': 'code'}, inplace=True)
            table_key = 'day'
        elif period == "60F":
            period = "60"
            start = datetime.strptime(start_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
            end = datetime.strptime(end_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
            rs = bs.query_history_k_data_plus(f"{market}.{code}", "time,code,open,high,low,close,volume", start_date=start, end_date=end, frequency=period, adjustflag="3")
            print('query_history_k_data_plus respond error_code:' + rs.error_code)
            print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)
            df = rs.get_data()

            df['period'] = 'hour'
            df['level'] = 5
            df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
            df['market'] = df['market'].str.lower()
            df['end_time'] = df['time'].apply(parse_time_to_minute)
            df["start_time"] = df["end_time"] - timedelta(hours=1)
            df['start_time'] = df['start_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
            df['end_time'] = df['end_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
            df = df.drop(columns=['code', 'time'])
            df.rename(columns={'new_code': 'code'}, inplace=True)
            table_key = 'hour'
        elif period == "30F":
            period = "30"
            start = datetime.strptime(start_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
            end = datetime.strptime(end_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
            rs = bs.query_history_k_data_plus(f"{market}.{code}", "time,code,open,high,low,close,volume", start_date=start, end_date=end, frequency=period, adjustflag="3")
            print('query_history_k_data_plus respond error_code:' + rs.error_code)
            print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)
            df = rs.get_data()

            df['period'] = 'hour'
            df['level'] = 5
            df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
            df['market'] = df['market'].str.lower()
            df['end_time'] = df['time'].apply(parse_time_to_minute)
            df["start_time"] = df["end_time"] - timedelta(minutes=30)
            df['start_time'] = df['start_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
            df['end_time'] = df['end_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
            df = df.drop(columns=['code', 'time'])
            df.rename(columns={'new_code': 'code'}, inplace=True)
            table_key = 'half'

        model_class = get_kline_model(table_key)
        if model_class is None:
            raise ValueError(f"不支持的周期: {table_key}")

        _upsert_dataframe(df, model_class)
        return df
    except Exception as e:
        print("error: ", e)
        return False
    finally:
        bs.logout()


def get_stock_data_daily_bao(code: str, market: str, period: str, start_timestamp: str = None, end_timestamp: str = None):
    try:
        lg = bs.login()
        print('login respond error_code:' + lg.error_code)
        print('login respond  error_msg:' + lg.error_msg)
        start = datetime.strptime(start_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
        end = datetime.strptime(end_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
        print(start, end, period)
        rs = bs.query_history_k_data_plus(f"{market}.{code}", "date,code,open,high,low,close,volume", start_date=start, end_date=end, frequency=period, adjustflag="1")
        print('query_history_k_data_plus respond error_code:' + rs.error_code)
        print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)
        df = rs.get_data()

        df['period'] = 'day'
        df['level'] = 6
        df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
        df['market'] = df['market'].str.lower()
        df = df.drop(columns=['code'])
        df.rename(columns={'new_code': 'code'}, inplace=True)

        _upsert_dataframe(df, DayKline)
        return df
    except Exception as e:
        print("error: ", e)
        return False
    finally:
        bs.logout()


def update_all_stock(day: str | None = None):
    """从 baostock 更新全量股票列表到数据库"""
    if day is None:
        day = datetime.now().strftime("%Y-%m-%d")
    try:
        lg = bs.login()
        print('login respond error_code:' + lg.error_code)
        print('login respond  error_msg:' + lg.error_msg)
        res = bs.query_all_stock(day).get_data()
        df = res.copy()
        df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
        df['market'] = df['market'].str.lower()
        df = df.drop(columns=['code', 'tradeStatus'])
        df.rename(columns={'new_code': 'code', "code_name": "name"}, inplace=True)

        _upsert_dataframe(df, Stock)
        return df
    except Exception as e:
        print("error: ", e)
        return False
    finally:
        bs.logout()


def update_kline_data(code: str | None = None, market: str = "sh", periods: list[str] | None = None, start_date: str | None = None, end_date: str | None = None) -> dict:
    """批量更新K线数据到数据库

    Args:
        code: 股票代码，为 None 时更新全量股票
        market: 市场类型 sh/sz
        periods: 周期列表，如 ["day", "60F", "30F", "5F"]，为 None 时更新所有周期
        start_date: 开始日期 YYYY-MM-DD，为 None 时从默认日期开始
        end_date: 结束日期 YYYY-MM-DD，为 None 时到今天

    Returns:
        更新结果统计
    """
    ALL_PERIODS = ["d", "60", "30", "5", "w", "m", "y"]
    PERIOD_DISPLAY = {"d": "日K", "60": "60分K", "30": "30分K", "5": "5分K", "w": "周K", "m": "月K", "y": "年K"}
    # 前端/API 传入的周期值 → baostock 周期值
    PERIOD_NORMALIZE = {
        "day": "d", "daily": "d", "d": "d",
        "60f": "60", "60": "60", "hour": "60",
        "30f": "30", "30": "30", "half": "30",
        "5f": "5", "5": "5", "five_min": "5",
        "week": "w", "w": "w",
        "month": "m", "m": "m",
        "year": "y", "y": "y",
    }

    if periods is None:
        periods = ALL_PERIODS
    else:
        periods = [PERIOD_NORMALIZE.get(p.lower(), p) for p in periods]

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    # 获取股票列表
    if code is not None:
        stocks = [{"code": code, "market": market}]
    else:
        with get_session() as session:
            rows = session.query(Stock.code, Stock.market).all()
            stocks = [{"code": r.code, "market": r.market} for r in rows]

    results: dict[str, dict[str, str]] = {}

    for stock in stocks:
        stock_key = f"{stock['market']}.{stock['code']}"
        stock_results: dict[str, str] = {}

        for period in periods:
            try:
                lg = bs.login()
                display_name = PERIOD_DISPLAY.get(period, period)

                if period == "d":
                    rs = bs.query_history_k_data_plus(
                        f"{stock['market']}.{stock['code']}",
                        "date,code,open,high,low,close,volume",
                        start_date=start_date, end_date=end_date,
                        frequency="d", adjustflag="3"
                    )
                    df = rs.get_data()
                    if df.empty:
                        stock_results[display_name] = "无数据"
                        continue
                    df['volume'] = df['volume'].astype(str).replace({'': '0', 'nan': '0', 'None': '0'})
                    df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0)
                    df['period'] = 'day'
                    df['level'] = 6
                    df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
                    df['market'] = df['market'].str.lower()
                    df = df.drop(columns=['code'])
                    df.rename(columns={'new_code': 'code'}, inplace=True)
                    _upsert_dataframe(df, DayKline)

                elif period in ("60", "30", "5"):
                    freq_map = {"60": "60", "30": "30", "5": "5"}
                    rs = bs.query_history_k_data_plus(
                        f"{stock['market']}.{stock['code']}",
                        "time,code,open,high,low,close,volume",
                        start_date=start_date, end_date=end_date,
                        frequency=freq_map[period], adjustflag="3"
                    )
                    df = rs.get_data()
                    if df.empty:
                        stock_results[display_name] = "无数据"
                        continue
                    period_label = 'hour' if period == '60' else 'half' if period == '30' else 'five_min'
                    level = 5 if period in ('60', '30') else 4
                    timedelta_val = timedelta(hours=1) if period == '60' else timedelta(minutes=30) if period == '30' else timedelta(minutes=5)

                    df['period'] = period_label
                    df['level'] = level
                    df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
                    df['market'] = df['market'].str.lower()
                    df['end_time'] = df['time'].apply(parse_time_to_minute)
                    df['start_time'] = df['end_time'] - timedelta_val
                    df['start_time'] = df['start_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
                    df['end_time'] = df['end_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
                    df = df.drop(columns=['code', 'time'])
                    df.rename(columns={'new_code': 'code'}, inplace=True)

                    model_class = get_kline_model(period_label)
                    if model_class:
                        _upsert_dataframe(df, model_class)

                elif period == "w":
                    rs = bs.query_history_k_data_plus(
                        f"{stock['market']}.{stock['code']}",
                        "date,code,open,high,low,close,volume",
                        start_date=start_date, end_date=end_date,
                        frequency="w", adjustflag="3"
                    )
                    df = rs.get_data()
                    if df.empty:
                        stock_results[display_name] = "无数据"
                        continue
                    df['volume'] = df['volume'].astype(str).replace({'': '0', 'nan': '0', 'None': '0'})
                    df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0)
                    df['period'] = 'week'
                    df['level'] = 7
                    df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
                    df['market'] = df['market'].str.lower()
                    df = df.drop(columns=['code'])
                    df.rename(columns={'new_code': 'code'}, inplace=True)
                    _upsert_dataframe(df, WeekKline)

                elif period == "m":
                    rs = bs.query_history_k_data_plus(
                        f"{stock['market']}.{stock['code']}",
                        "date,code,open,high,low,close,volume",
                        start_date=start_date, end_date=end_date,
                        frequency="m", adjustflag="3"
                    )
                    df = rs.get_data()
                    if df.empty:
                        stock_results[display_name] = "无数据"
                        continue
                    df['volume'] = df['volume'].astype(str).replace({'': '0', 'nan': '0', 'None': '0'})
                    df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0)
                    df['period'] = 'month'
                    df['level'] = 8
                    df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
                    df['market'] = df['market'].str.lower()
                    df = df.drop(columns=['code'])
                    df.rename(columns={'new_code': 'code'}, inplace=True)
                    _upsert_dataframe(df, MonthKline)

                elif period == "y":
                    rs = bs.query_history_k_data_plus(
                        f"{stock['market']}.{stock['code']}",
                        "date,code,open,high,low,close,volume",
                        start_date=start_date, end_date=end_date,
                        frequency="y", adjustflag="3"
                    )
                    df = rs.get_data()
                    if df.empty:
                        stock_results[display_name] = "无数据"
                        continue
                    df['volume'] = df['volume'].astype(str).replace({'': '0', 'nan': '0', 'None': '0'})
                    df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0)
                    df['period'] = 'year'
                    df['level'] = 9
                    df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
                    df['market'] = df['market'].str.lower()
                    df = df.drop(columns=['code'])
                    df.rename(columns={'new_code': 'code'}, inplace=True)
                    _upsert_dataframe(df, YearKline)

                stock_results[display_name] = f"成功({len(df)}条)"

            except Exception as e:
                display_name = PERIOD_DISPLAY.get(period, period)
                stock_results[display_name] = f"失败: {e}"
            finally:
                bs.logout()

        results[stock_key] = stock_results

    return results


def query_stocks() -> list[dict]:
    """查询全部股票列表"""
    with get_session() as session:
        stocks = session.query(Stock).all()
        return [{"name": s.name, "code": s.code, "market": s.market} for s in stocks]


def search_stocks(keyword: str, market: str | None = None, limit: int = 5) -> list[dict]:
    """搜索股票（按代码或名称模糊匹配）"""
    with get_session() as session:
        query = session.query(Stock)
        if market:
            query = query.filter(Stock.market == market)
        query = query.filter(
            (Stock.code.contains(keyword)) | (Stock.name.contains(keyword))
        )
        stocks = query.limit(limit).all()
        return [{"name": s.name, "code": s.code, "market": s.market} for s in stocks]
