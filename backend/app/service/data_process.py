import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from typing import List
from dotenv import load_dotenv
import os
import json
from app.models.stock_model import KlineData
from app.utils.redis import get_cache, set_cache

load_dotenv()


class BaseProcessor(ABC):
    @abstractmethod
    def get_bar_data(self, code: str, market: str, period: str, start_date: str = None, end_date: str = None):
        pass

class StockDataProcessor:
    def __init__(self, *sourceProcessors):
        self.sourceProcessors = [P() if isinstance(P, type) else P for P in sourceProcessors]

    def get_kline_data(self, code: str, market: str, period: str, start_date: str = None, end_date: str = None) -> List[KlineData]:
        for processor in self.sourceProcessors:
            try:
                result = processor.get_bar_data(code, market, period, start_date, end_date)
                if result:
                    return result
            except Exception as e:
                print(f"Data source {type(processor).__name__} failed for {code}/{market}/{period}: {e}")
        return []
        

    def search_stock(self, keyword: str, market: str):
        """
        股票模糊搜索（基于Akshare股票列表）
        """
        try:
            cache_key = "chan:stock:list"
            stock_list = get_cache(cache_key)
            if not stock_list:
                df = ak.stock_info_a_code_name()
                stock_list = []
                for _, row in df.iterrows():
                    code = row['code']
                    stock_market = "sh" if code.startswith("6") else "sz"
                    stock_list.append({
                        "code": code,
                        "name": row['name'],
                        "market": stock_market
                    })
                set_cache(cache_key, json.dumps(stock_list))

            filtered = [
                stock for stock in stock_list
                if ((keyword in stock['code']) or (keyword in stock['name']))
                and (stock['market'] == market)
            ]

            return filtered[:20]

        except Exception as e:
            print(f"股票搜索失败：{e}")
            return []
