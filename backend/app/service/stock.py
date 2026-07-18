from __future__ import annotations
import pandas as pd
from datetime import date, datetime, timedelta
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy import case
from app.utils.database import engine, get_session
from app.models.db_model import Stock, DayKline, WeekKline, MonthKline, YearKline, get_kline_model, KLINE_MODEL_MAP
from app.config.config import PERIOD_MAP
from app.models.period import SUPPORTED_PERIODS, resolve_period

# 时间类周期（按 start_time/end_time 存储），其余为日期类（按 date 存储）。
_TIME_PERIOD_TABLE_KEYS = {"hour", "half", "five_min"}
# 时间类周期每根 K 线的时长，用于由 end_time 反推 start_time。
_TIME_TABLE_KEY_DURATION = {
    "hour": timedelta(hours=1),
    "half": timedelta(minutes=30),
    "five_min": timedelta(minutes=5),
}


def validate_stock(code: str, market: str, name: str | None = None) -> bool:
    """验证股票是否存在于数据库中（仅按 code + market 判定）

    name 已弱化为展示字段：主键改为 (code, market) 后，同 code+market 不再有多个
    name，故 name 不再参与存在性校验。同时修复前端持有改名前旧 name 时误判
    "股票未找到" 的潜在 bug。

    Args:
        code: 股票代码
        market: 市场类型 sh/sz
        name: 股票名称（可选，保留以兼容 API/前端入参，不再参与校验）

    Returns:
        True 如果 (code, market) 存在，否则 False
    """
    with get_session() as session:
        query = session.query(Stock).filter(Stock.code == code, Stock.market == market)
        return session.query(query.exists()).scalar() is True


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
        import baostock as bs  # 延迟导入：baostock 首次导入耗时数秒，避免拖慢模块加载与首搜
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
        import baostock as bs  # 延迟导入：baostock 首次导入耗时数秒，避免拖慢模块加载与首搜
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
        import baostock as bs  # 延迟导入：baostock 首次导入耗时数秒，避免拖慢模块加载与首搜
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


def update_kline_data(code: str | None = None, market: str = "sh", periods: list[str] | None = None, start_date: str | None = None, end_date: str | None = None, name: str | None = None) -> dict:
    """批量更新K线数据到数据库

    Args:
        code: 股票代码，为 None 时更新全量股票
        market: 市场类型 sh/sz
        periods: 周期列表，如 ["day", "60F", "30F", "5F"]，为 None 时更新所有周期
        start_date: 开始日期 YYYY-MM-DD，为 None 时从默认日期开始
        end_date: 结束日期 YYYY-MM-DD，为 None 时到今天
        name: 股票名称（可选，展示字段，保留以兼容 API/前端入参，不再参与行匹配）

    Returns:
        更新结果统计
    """
    # 周期定义来自 app.models.period 的单一真相源：value 即前后端约定的 period 字符串。
    if periods is None:
        period_defs = list(SUPPORTED_PERIODS)
    else:
        period_defs = []
        for p in periods:
            pd_def = resolve_period(p)
            if pd_def is None:
                # 无法识别的周期跳过，避免向下传非法值
                continue
            period_defs.append(pd_def)

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    # 获取股票列表
    if code is not None:
        # 仅按 (code, market) 定位；name 已弱化为展示字段，不再参与行匹配。
        # 仍做一次存在性校验，避免对不存在的股票无谓拉取 baostock。
        with get_session() as session:
            row = session.query(Stock.code, Stock.market).filter(
                Stock.code == code, Stock.market == market
            ).first()
            if row is None:
                return {f"{market}.{code}": {"错误": f"未找到股票 {code}"}}
            stocks = [{"code": row.code, "market": row.market}]
    else:
        with get_session() as session:
            rows = session.query(Stock.code, Stock.market).all()
            stocks = [{"code": r.code, "market": r.market} for r in rows]

    results: dict[str, dict[str, str]] = {}

    for stock in stocks:
        stock_key = f"{stock['market']}.{stock['code']}"
        stock_results: dict[str, str] = {}

        for pd_def in period_defs:
            display_name = pd_def.label
            try:
                import baostock as bs  # 延迟导入：baostock 首次导入耗时数秒，避免拖慢模块加载与首搜
                lg = bs.login()
                baostock_symbol = f"{stock['market']}.{stock['code']}"

                if pd_def.table_key in _TIME_PERIOD_TABLE_KEYS:
                    # 时间类周期（hour/half/five_min）：按 time 列取数，存 start_time/end_time
                    rs = bs.query_history_k_data_plus(
                        baostock_symbol,
                        "time,code,open,high,low,close,volume",
                        start_date=start_date, end_date=end_date,
                        frequency=pd_def.baostock_freq, adjustflag="3"
                    )
                    df = _rs_to_dataframe(rs)
                    if df.empty:
                        stock_results[display_name] = "无数据"
                        continue
                    timedelta_val = _TIME_TABLE_KEY_DURATION[pd_def.table_key]
                    df['period'] = pd_def.table_key
                    df['level'] = pd_def.level
                    df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
                    df['market'] = df['market'].str.lower()
                    df['end_time'] = df['time'].apply(parse_time_to_minute)
                    df['start_time'] = df['end_time'] - timedelta_val
                    df['start_time'] = df['start_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
                    df['end_time'] = df['end_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
                    df = df.drop(columns=['code', 'time'])
                    df.rename(columns={'new_code': 'code'}, inplace=True)

                    model_class = KLINE_MODEL_MAP.get(pd_def.table_key)
                    if model_class:
                        _upsert_dataframe(df, model_class)

                else:
                    # 日期类周期（day/week/month/year）：按 date 列取数
                    rs = bs.query_history_k_data_plus(
                        baostock_symbol,
                        "date,code,open,high,low,close,volume",
                        start_date=start_date, end_date=end_date,
                        frequency=pd_def.baostock_freq, adjustflag="3"
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
                    df['period'] = pd_def.table_key
                    df['level'] = pd_def.level
                    df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
                    df['market'] = df['market'].str.lower()
                    df = df.drop(columns=['code'])
                    df.rename(columns={'new_code': 'code'}, inplace=True)

                    model_class = KLINE_MODEL_MAP.get(pd_def.table_key)
                    if model_class:
                        _upsert_dataframe(df, model_class)

                stock_results[display_name] = f"成功({len(df)}条)"

            except Exception as e:
                stock_results[display_name] = f"失败: {e}"
            finally:
                bs.logout()

        results[stock_key] = stock_results

    return results


def get_kline_date_range(code: str, market: str, period: str, name: str | None = None) -> tuple[date | None, date | None]:
    """查询数据库中某只股票某周期K线数据的日期范围

    Args:
        code: 股票代码
        market: 市场类型 sh/sz
        period: 周期
        name: 股票名称（可选），传入时用于区分同代码不同名称的股票

    Returns:
        (最早日期, 最晚日期) 元组，无数据时返回 (None, None)
    """
    # 如果提供了 name，先校验股票是否存在
    if name is not None:
        if not validate_stock(code, market, name):
            print(f"股票 {code}({name}) 在 {market} 市场中未找到")
            return (None, None)
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


def get_stock_data_database(code: str, market: str, period: str, start_timestamp: str, end_timestamp: str, name: str | None = None) -> pd.DataFrame | None:
    """从数据库读取K线数据

    Args:
        code: 股票代码
        market: 市场类型 sh/sz
        period: 周期，如 "d", "60", "30", "5", "w", "m", "y"
        start_timestamp: 开始日期/时间 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
        end_timestamp: 结束日期/时间 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
        name: 股票名称（可选），传入时用于区分同代码不同名称的股票

    Returns:
        DataFrame 或 None（周期不支持时）
    """
    # 如果提供了 name，先校验股票是否存在
    if name is not None:
        if not validate_stock(code, market, name):
            print(f"股票 {code}({name}) 在 {market} 市场中未找到")
            return None
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
    """搜索股票（按代码或名称模糊匹配，代码前缀优先排序）

    排序优先级：代码前缀匹配 > 代码包含 > 名称包含，使最相关结果排在前面。
    关键词去空格后长度 < 2 时直接返回空，避免单字符模糊匹配命中过多噪声。
    """
    kw = (keyword or "").strip()
    if len(kw) < 2:
        return []
    with get_session() as session:
        query = session.query(Stock)
        if market:
            query = query.filter(Stock.market == market)
        query = query.filter(
            (Stock.code.contains(kw)) | (Stock.name.contains(kw))
        )
        # CASE 排序：代码前缀(0) < 代码包含(1) < 仅名称包含(2)
        order_expr = case(
            (Stock.code.like(f"{kw}%"), 0),
            (Stock.code.contains(kw), 1),
            else_=2,
        )
        stocks = query.order_by(order_expr, Stock.code).limit(limit).all()
        return [{"name": s.name, "code": s.code, "market": s.market} for s in stocks]
