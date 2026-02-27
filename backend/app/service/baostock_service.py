import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from app.service.data_process import BaseProcessor
from app.models.stock_model import KlineData
from typing import List

PERIOD_MAP = {
    "D": "d",
    "30F": "30",
    "5F": "5"
}

DEFAULT_LOOKBACK_DAYS = 50


class BaostockProcessor(BaseProcessor):

    def get_bar_data(self, code, market, period, start_date=None, end_date=None) -> List[KlineData]:
        """
        获取股票K线数据（基于Baostock）
        """
        if not start_date or not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=DEFAULT_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
        else:
            # Ensure YYYY-MM-DD format using robust datetime parsing
            try:
                start_date = pd.to_datetime(start_date).strftime("%Y-%m-%d")
                end_date = pd.to_datetime(end_date).strftime("%Y-%m-%d")
            except Exception:
                raise ValueError(f"Invalid date format: start_date={start_date}, end_date={end_date}")

        bs_code = f"{market}.{code}"
        freq = PERIOD_MAP.get(period, "d")

        lg = bs.login()
        if lg.error_code != '0':
            raise RuntimeError(f"Baostock login failed: {lg.error_msg}")
        try:
            if period == "D":
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    "date,open,high,low,close,volume",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="2"
                )
            else:
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    "date,time,open,high,low,close,volume",
                    start_date=start_date,
                    end_date=end_date,
                    frequency=freq,
                    adjustflag="2"
                )

            if rs.error_code != '0':
                raise RuntimeError(f"Baostock query failed: {rs.error_msg}")

            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                return []

            df = pd.DataFrame(data_list, columns=rs.fields)
            df = df[(df['open'] != '') & (df['close'] != '')].copy()

            for col in ['open', 'high', 'low', 'close']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype(int)
            df = df.dropna(subset=['open', 'high', 'low', 'close'])
            df = df[(df['open'] > 0) & (df['close'] > 0)]

            kline_list = []
            for _, row in df.iterrows():
                kline = KlineData(
                    date=str(row['date']),
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=int(row['volume']),
                    code=str(code),
                )
                kline_list.append(kline.model_dump())

            return kline_list

        finally:
            bs.logout()
