import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from data_process import BaseProcessor
from app.models.stock_model import KlineData
from typing import List
from app.utils.redis import get_cache, set_cache

PERIOD_MAP = {
    "D": "daily",       # 日线
    "30F": "30min",     # 30分钟线
    "5F": "5min"        # 5分钟线
}

MARKET_CODE_MAP = {
    "sh": "6",  # 沪市A股前缀
    "sz": "0"   # 深市A股前缀（创业板300、科创板688需兼容，这里做基础适配）
}


class AkshareProcessor(BaseProcessor):
    
    def _get_cache_key(self, code, market, period, start, end):
        return f"{code}_{market}_{period}_{start}_{end}"
    
    def _format_date(self, date_str: str, is_minute: bool = False) -> str:
        if is_minute:
            # 分钟线格式：2026-02-13 14:30:00 → 2026-02-13 14:30
            return pd.to_datetime(date_str).strftime("%Y-%m-%d %H:%M")
        else:
            # 日线格式：20260213 → 2026-02-13
            return pd.to_datetime(date_str).strftime("%Y-%m-%d")
    
    def _validate_kline_data(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        
        # 剔除价格异常值（0值、负数）
        df = df[(df['open'] > 0) & (df['high'] > 0) & (df['low'] > 0) & (df['close'] > 0)]
        # 确保high >= low
        df['high'] = df.apply(lambda x: max(x['high'], x['low'], x['open'], x['close']), axis=1)
        df['low'] = df.apply(lambda x: min(x['high'], x['low'], x['open'], x['close']), axis=1)
        # 补全成交量,空值填0
        df['volume'] = df['volume'].fillna(0).astype(int)
        return df
    
    def get_bar_data(self, code, market, period, start_date = None, end_date = None) -> List[KlineData]:
        """
        获取股票K线数据（基于Akshare，优先读缓存）
        """
        # 处理日期：转换为Akshare要求的8位格式（无横杠）
        start = start_date.replace("-", "") if start_date else self.default_start_date
        end = end_date.replace("-", "") if end_date else self.default_end_date

        cache_key = self._get_cache_key(code, market, period, start, end)
        cache_data = get_cache(cache_key)
        if cache_data:
            return cache_data

        try:
            # 拼接Akshare需要的完整股票代码（例：沪市600000 → 600000，深市000001 → 000001）
            ak_code = f"{MARKET_CODE_MAP[market]}{code}" if len(code) == 5 else code  # 兼容5位/6位代码
            
            if period == "D":
                # 日线
                df = ak.stock_zh_a_hist(
                    symbol=ak_code,
                    period="daily",
                    start_date=start,
                    end_date=end,
                    adjust="hfq"  # 后复权（可选：qfq前复权/None不复权）
                )
                df.rename(columns={
                    '日期': 'date',
                    '股票代码': 'code',
                    '开盘': 'open',
                    '最高': 'high',
                    '最低': 'low',
                    '收盘': 'close',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '涨跌幅': 'change',
                    '振幅': 'amplitude',
                    '换手率': 'turnover'
                }, inplace=True)
                # 格式化日线日期
                df['date'] = df['date'].apply(lambda x: self._format_date(x))
            
            else:
                # 分钟线
                df = ak.stock_zh_a_minute(
                    symbol=ak_code,
                    period=PERIOD_MAP[period],
                    adjust="qfq"
                )
                # 过滤时间范围（Akshare分钟线默认返回最近数据，需手动过滤）
                df['date'] = pd.to_datetime(df['day'])
                start_dt = pd.to_datetime(start)
                end_dt = pd.to_datetime(end) + timedelta(days=1)  # 包含结束日
                df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
                
                df.rename(columns={
                    '开盘价': 'open',
                    '最高价': 'high',
                    '最低价': 'low',
                    '收盘价': 'close',
                    '成交量': 'volume'
                }, inplace=True)
                df['date'] = df['day'].apply(lambda x: self._format_date(x, is_minute=True))
                # 保留核心字段
                df = df[['date', 'open', 'high', 'low', 'close', 'volume']]

            # 4. 数据校验 & 格式转换
            df = self._validate_kline_data(df)
            if df.empty:
                return []

            # 5. 转换为标准化格式（适配原有KlineData模型）
            kline_list = []
            for _, row in df.iterrows():
                kline = KlineData(
                    date=row['date'],
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=int(row['volume'])
                )
                kline_list.append(kline.model_dump())

            # 6. 写入缓存
            set_cache(cache_key, kline_list)

            return kline_list

        except Exception as e:
            print(f"获取K线数据失败：{e}")
            return []