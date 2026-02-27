import akshare as ak
from backend.app.utils.middleware import Mysql_client, MysqlClient

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