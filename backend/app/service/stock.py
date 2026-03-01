import akshare as ak
import baostock as bs
import pandas as pd
from datetime import datetime
import time
from app.utils.middleware import Mysql_client, MysqlClient
from sqlalchemy import text

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
    
def get_stock_data_daily_bao(code: str, market: str, period: str, start_timestamp: str = None, end_timestamp: str = None):
    try:
        lg = bs.login()
        print('login respond error_code:'+lg.error_code)
        print('login respond  error_msg:'+lg.error_msg)
        start = datetime.strptime(start_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
        end = datetime.strptime(end_timestamp, "%Y-%m-%d").strftime("%Y-%m-%d")
        print(start, end, period)
        if period == "daily" or period == "day":
            period = "d"
        rs = bs.query_history_k_data_plus(f"{market}.{code}", "date,code,open,high,low,close,volume", start_date=start, end_date=end, frequency=period, adjustflag="3")
        print('query_history_k_data_plus respond error_code:'+rs.error_code)
        print('query_history_k_data_plus respond  error_msg:'+rs.error_msg)
        df = rs.get_data()
        
        df['period'] = 'day'
        df['level'] = 6
        df[['market', 'new_code']] = df['code'].str.split('.', expand=True)
        df['market'] = df['market'].str.lower()
        df = df.drop(columns=['code'])
        df.rename(columns={'code_new': 'code'}, inplace=True)

        
        df.to_sql(
            name="day",
            con=Mysql_client.get_engine(),
            if_exists="append",
            index=False,
            chunksize=1000
        )
        return df
    except Exception as e:
        print("error: ",e)
        return False
    
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
        df.to_sql(
            name="stock",
            con=Mysql_client.get_engine(),
            if_exists="append",
            index=False,
            chunksize=1000
        )
        return df
    except Exception as e:
        print("error: ",e)
        return False

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
            result = conn.execute(text(sql), params or {})
            
            columns = [col.name for col in result.keys()]
            data_list = [dict(zip(columns, row)) for row in result.fetchall()]
        
        print(f"✅ 查询成功，共返回 {len(data_list)} 条数据")
        return data_list
    
    except Exception as e:
        print(f"❌ 查询异常：{str(e)}")
        return None