import akshare as ak
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import time
from app.utils.middleware import Mysql_client, MysqlClient
from sqlalchemy import text, MetaData, Table
from sqlalchemy.dialects.mysql import insert as mysql_insert

def parse_time_to_minute(time_str: str) -> pd.Timestamp:
    if pd.isna(time_str) or time_str == "":
        return pd.NaT  # 处理空值
    
    try:
        parse_str = time_str[:14]
        dt = datetime.strptime(parse_str, "%Y%m%d%H%M%S")
        dt_minute = dt.replace(microsecond=0)
        return pd.Timestamp(dt_minute)
    except (ValueError, TypeError):
        return pd.NaT

def get_stock_data_daily_sina(code: str, market: str, period: str, start_timestamp: str = None, end_timestamp: str = None):
    try:
        df = ak.stock_zh_a_daily(symbol=code, adjust="qfq", start_date=start_timestamp, end_date=end_timestamp)
        df.to_sql(
            name="daily",
            con=Mysql_client.get_engine(),
            if_exists="append",
            index=False,
            chunksize=1000
        )
        return True
    except Exception as e:
        print(e)
        return False

def get_stock_data_bao(code: str, market: str, period: str, start_timestamp: str = None, end_timestamp: str = None):
    try:
        lg = bs.login()
        print('login respond error_code:'+lg.error_code)
        print('login respond  error_msg:'+lg.error_msg)
        if period == "daily" or period == "day" or period == "d":
            period = "d"
            start = datetime.strptime(start_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
            end = datetime.strptime(end_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
            rs = bs.query_history_k_data_plus(f"{market}.{code}", "date,code,open,high,low,close,volume", start_date=start, end_date=end, frequency=period, adjustflag="3")
            print('query_history_k_data_plus respond error_code:'+rs.error_code)
            print('query_history_k_data_plus respond  error_msg:'+rs.error_msg)
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
            period = 'day'
        elif period == "60F":
            period = "60"
            start = datetime.strptime(start_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
            end = datetime.strptime(end_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
            rs = bs.query_history_k_data_plus(f"{market}.{code}", "time,code,open,high,low,close,volume", start_date=start, end_date=end, frequency=period, adjustflag="3")
            print('query_history_k_data_plus respond error_code:'+rs.error_code)
            print('query_history_k_data_plus respond  error_msg:'+rs.error_msg)
            df = rs.get_data()
            
            df['period'] = 'hour'
            df['level'] = 5
            df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
            df['market'] = df['market'].str.lower()
            df['end_time'] = df['time'].apply(parse_time_to_minute)
            df["start_time"] = df["end_time"] - timedelta(hours=1)
            df['start_time'] = df['start_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
            df['end_time'] = df['end_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
            df = df.drop(columns=['code','time'])
            df.rename(columns={'new_code': 'code'}, inplace=True)
            period = 'hour'
        elif period == "30F":
            period = "30"
            start = datetime.strptime(start_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
            end = datetime.strptime(end_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
            rs = bs.query_history_k_data_plus(f"{market}.{code}", "time,code,open,high,low,close,volume", start_date=start, end_date=end, frequency=period, adjustflag="3")
            print('query_history_k_data_plus respond error_code:'+rs.error_code)
            print('query_history_k_data_plus respond  error_msg:'+rs.error_msg)
            df = rs.get_data()
            
            df['period'] = 'hour'
            df['level'] = 5
            df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
            df['market'] = df['market'].str.lower()
            df['end_time'] = df['time'].apply(parse_time_to_minute)
            df["start_time"] = df["end_time"] - timedelta(hours=1)
            df['start_time'] = df['start_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
            df['end_time'] = df['end_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
            df = df.drop(columns=['code','time'])
            df.rename(columns={'new_code': 'code'}, inplace=True)
            period = 'half'
            
        data = df.to_dict('records')
        engine = Mysql_client.get_engine()
        metadata = MetaData()
        stock_index_table = Table(
            period,
            metadata,
            autoload_with=engine
        )
        data = df.to_dict('records')
        insert_stmt = mysql_insert(stock_index_table).values(data)
        update_stmt = {col: insert_stmt.inserted[col] for col in df.columns}
        upsert_stmt = insert_stmt.on_duplicate_key_update(**update_stmt)
        with engine.connect() as conn:
            conn.execute(upsert_stmt)
            conn.commit()
        return df
    except Exception as e:
        print("error: ",e)
        return False
    finally:
        bs.logout()


def get_stock_data_daily_bao(code: str, market: str, period: str, start_timestamp: str = None, end_timestamp: str = None):
    try:
        lg = bs.login()
        print('login respond error_code:'+lg.error_code)
        print('login respond  error_msg:'+lg.error_msg)
        start = datetime.strptime(start_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
        end = datetime.strptime(end_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
        print(start, end, period)
        rs = bs.query_history_k_data_plus(f"{market}.{code}", "date,code,open,high,low,close,volume", start_date=start, end_date=end, frequency=period, adjustflag="1")
        print('query_history_k_data_plus respond error_code:'+rs.error_code)
        print('query_history_k_data_plus respond  error_msg:'+rs.error_msg)
        df = rs.get_data()
        
        df['period'] = 'day'
        df['level'] = 6
        df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
        df['market'] = df['market'].str.lower()
        df = df.drop(columns=['code'])
        df.rename(columns={'new_code': 'code'}, inplace=True)

        data = df.to_dict('records')
        engine = Mysql_client.get_engine()
        metadata = MetaData()
        stock_index_table = Table(
            'day',
            metadata,
            autoload_with=engine
        )
        data = df.to_dict('records')
        insert_stmt = mysql_insert(stock_index_table).values(data)
        update_stmt = {col: insert_stmt.inserted[col] for col in df.columns}
        upsert_stmt = insert_stmt.on_duplicate_key_update(**update_stmt)
        with engine.connect() as conn:
            conn.execute(upsert_stmt)
            conn.commit()
        return df
    except Exception as e:
        print("error: ",e)
        return False
    finally:
        bs.logout()
    
def update_all_stock(day="2026-02-27"):
    try:
        lg = bs.login()
        print('login respond error_code:'+lg.error_code)
        print('login respond  error_msg:'+lg.error_msg)
        res = bs.query_all_stock(day).get_data()
        df = res.copy()
        df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
        df['market'] = df['market'].str.lower()
        df = df.drop(columns=['code','tradeStatus'])
        df.rename(columns={'new_code': 'code', "code_name":"name"}, inplace=True)
        data = df.to_dict('records')
        engine = Mysql_client.get_engine()
        metadata = MetaData()
        stock_index_table = Table(
            'stock',
            metadata,
            autoload_with=engine
        )
        data = df.to_dict('records')
        insert_stmt = mysql_insert(stock_index_table).values(data)
        update_stmt = {col: insert_stmt.inserted[col] for col in df.columns}
        upsert_stmt = insert_stmt.on_duplicate_key_update(**update_stmt)
        with engine.connect() as conn:
            conn.execute(upsert_stmt)
            conn.commit()
        return df
    except Exception as e:
        print("error: ",e)
        return False
    finally:
        bs.logout()

def query_stock(sql, params=None):
    """
    从数据库查询数据并返回列表
    :param sql: 查询SQL语句（字符串）
    :param params: SQL参数（字典，用于防SQL注入），如 {"code": "600000"}
    :param return_dict: 是否返回字典列表（True：字典列表，False：元组列表）
    :return: list - 查询结果列表；None - 查询失败
    """
    try:
        engine = Mysql_client.get_engine()
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            
            row_mappings = result.mappings().all()
            data_list = [dict(row) for row in row_mappings]
        
        print(f"✅ 查询成功，共返回 {len(data_list)} 条数据")
        return data_list
    
    except Exception as e:
        print(f"❌ 查询异常：{str(e)}")
        return None