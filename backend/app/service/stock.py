import akshare as ak
import baostock as bs
import pandas as pd
from datetime import datetime
from app.utils.middleware import Mysql_client, MysqlClient

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
        if period == "daily":
            period = "d"
        rs = bs.query_history_k_data_plus(f"{market}.{code}", "date,code,open,high,low,close,volume", start_date=start, end_date=end, frequency=period, adjustflag="3")
        print('query_history_k_data_plus respond error_code:'+rs.error_code)
        print('query_history_k_data_plus respond  error_msg:'+rs.error_msg)
        df = rs.get_data()
        
        df['period'] = 'daily'
        df['level'] = 6
        
        df.to_sql(
            name="daily",
            con=Mysql_client.get_engine(),
            if_exists="append",
            index=False,
            chunksize=1000
        )
        return df
    except Exception as e:
        print("error: ",e)
        return False