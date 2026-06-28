from __future__ import annotations
import baostock as bs
import pandas as pd
from datetime import date, datetime, timedelta
from sqlalchemy.dialects.mysql import insert as mysql_insert
from app.utils.database import engine, get_session
from app.models.db_model import Stock, DayKline, WeekKline, MonthKline, YearKline, get_kline_model
from app.config.config import PERIOD_MAP


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


def _rs_to_dataframe(rs) -> pd.DataFrame:
    """手动遍历 baostock 结果集，避免 get_data() 在新版 pandas 中因 DataFrame.append() 被移除而报错"""
    rows: list[list] = []
    fields = rs.fields if isinstance(rs.fields, list) else rs.fields.split(',') if rs.fields else []
    while rs.next():
        rows.append(rs.get_row_data())
    if not rows:
        return pd.DataFrame(columns=fields)
    return pd.DataFrame(rows, columns=fields)


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
        table_key = None
        df = None
        normalized = PERIOD_MAP.get(period.lower(), period)
        start = datetime.strptime(start_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
        end = datetime.strptime(end_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")

        if normalized == "d":
            rs = bs.query_history_k_data_plus(f"{market}.{code}", "date,code,open,high,low,close,volume", start_date=start, end_date=end, frequency=normalized, adjustflag="3")
            if rs is None:
                return False
            print('query_history_k_data_plus respond error_code:' + rs.error_code)
            print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)
            df = _rs_to_dataframe(rs)

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
        elif normalized in ("60", "30"):
            rs = bs.query_history_k_data_plus(f"{market}.{code}", "time,code,open,high,low,close,volume", start_date=start, end_date=end, frequency=normalized, adjustflag="3")
            if rs is None:
                return False
            print('query_history_k_data_plus respond error_code:' + rs.error_code)
            print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)
            df = _rs_to_dataframe(rs)

            timedelta_val = timedelta(hours=1) if normalized == "60" else timedelta(minutes=30)
            period_label = 'hour' if normalized == "60" else 'half'
            df['period'] = period_label
            df['level'] = 5
            df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
            df['market'] = df['market'].str.lower()
            df['end_time'] = df['time'].apply(parse_time_to_minute)
            df["start_time"] = df["end_time"] - timedelta_val
            df['start_time'] = df['start_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
            df['end_time'] = df['end_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
            df = df.drop(columns=['code', 'time'])
            df.rename(columns={'new_code': 'code'}, inplace=True)
            table_key = period_label
        if table_key is None or df is None:
            return False
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


def get_stock_data_daily_bao(code: str, market: str, period: str, start_timestamp: str, end_timestamp: str):
    try:
        lg = bs.login()
        print('login respond error_code:' + lg.error_code)
        print('login respond  error_msg:' + lg.error_msg)
        start = datetime.strptime(start_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
        end = datetime.strptime(end_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
        print(start, end, period)
        rs = bs.query_history_k_data_plus(f"{market}.{code}", "date,code,open,high,low,close,volume", start_date=start, end_date=end, frequency=period, adjustflag="1")
        if rs is None:
            return False
        print('query_history_k_data_plus respond error_code:' + rs.error_code)
        print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)
        df = _rs_to_dataframe(rs)

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
        rs = bs.query_all_stock(day)
        df = _rs_to_dataframe(rs)
        if df.empty:
            print("warning: baostock returned no stock data for", day, ", retrying with previous day")
            prev_day = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            rs = bs.query_all_stock(prev_day)
            df = _rs_to_dataframe(rs)
            if df.empty:
                print("warning: baostock returned no stock data for", prev_day, "either")
                return pd.DataFrame()
            day = prev_day
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
    PERIOD_NORMALIZE = PERIOD_MAP

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
                    if rs is None:
                        stock_results[display_name] = "查询失败"
                        continue
                    df = _rs_to_dataframe(rs)
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
                    df = _rs_to_dataframe(rs)
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
                    df = _rs_to_dataframe(rs)
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
                    df = _rs_to_dataframe(rs)
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
                    df = _rs_to_dataframe(rs)
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


def get_kline_date_range(code: str, market: str, period: str) -> tuple[date | None, date | None]:
    """查询数据库中某只股票某周期K线数据的日期范围

    Returns:
        (最早日期, 最晚日期) 元组，无数据时返回 (None, None)
    """
    normalized = PERIOD_MAP.get(period.lower(), period)
    model_class = get_kline_model(normalized)
    if model_class is None:
        return (None, None)

    with get_session() as session:
        if hasattr(model_class, 'date'):
            min_row = session.query(model_class.date).filter(
                model_class.code == code, model_class.market == market
            ).order_by(model_class.date.asc()).first()
            max_row = session.query(model_class.date).filter(
                model_class.code == code, model_class.market == market
            ).order_by(model_class.date.desc()).first()
        else:
            min_row = session.query(model_class.start_time).filter(
                model_class.code == code, model_class.market == market
            ).order_by(model_class.start_time.asc()).first()
            max_row = session.query(model_class.start_time).filter(
                model_class.code == code, model_class.market == market
            ).order_by(model_class.start_time.desc()).first()

    if min_row is None or max_row is None:
        return (None, None)

    min_val = min_row[0]
    max_val = max_row[0]
    if hasattr(min_val, 'date'):
        min_val = min_val.date()
    if hasattr(max_val, 'date'):
        max_val = max_val.date()
    return (min_val, max_val)


def query_stocks_list() -> list[dict]:
    """查询全部股票列表"""
    with get_session() as session:
        stocks = session.query(Stock).all()
        return [{"name": s.name, "code": s.code, "market": s.market} for s in stocks]


def get_stock_data_database(code: str, market: str, period: str, start_timestamp: str, end_timestamp: str) -> pd.DataFrame | None:
    """从数据库读取K线数据

    Args:
        code: 股票代码
        market: 市场类型 sh/sz
        period: 周期，如 "d", "60", "30", "5", "w", "m", "y"
        start_timestamp: 开始日期/时间 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
        end_timestamp: 结束日期/时间 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS

    Returns:
        DataFrame 或 None（周期不支持时）
    """
    normalized = PERIOD_MAP.get(period.lower(), period)
    model_class = get_kline_model(normalized)
    if model_class is None:
        return None

    with get_session() as session:
        query = session.query(model_class).filter(
            model_class.code == code,
            model_class.market == market,
        )

        # 日期类模型按 date 列筛选，时间类模型按 start_time 列筛选
        if hasattr(model_class, 'date'):
            start_dt = datetime.strptime(start_timestamp[:10], "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_timestamp[:10], "%Y-%m-%d").date()
            query = query.filter(
                model_class.date >= start_dt,
                model_class.date <= end_dt,
            )
        else:
            start_dt = datetime.strptime(start_timestamp[:19], "%Y-%m-%d %H:%M:%S") if len(start_timestamp) > 10 else datetime.strptime(start_timestamp[:10], "%Y-%m-%d")
            end_dt = datetime.strptime(end_timestamp[:19], "%Y-%m-%d %H:%M:%S") if len(end_timestamp) > 10 else datetime.strptime(end_timestamp[:10], "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(
                model_class.start_time >= start_dt,
                model_class.start_time <= end_dt,
            )

        rows = query.order_by(model_class.date if hasattr(model_class, 'date') else model_class.start_time).all()

        if not rows:
            return pd.DataFrame()

        # 必须在 session 内完成 ORM → dict 转换，否则会话关闭后访问属性会报 DetachedInstanceError
        records = []
        for row in rows:
            record = {}
            for col in model_class.__table__.columns:
                record[col.name] = getattr(row, col.name)
            records.append(record)

    return pd.DataFrame(records)


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
