#!/usr/bin/env python3
"""
测试数据获取
"""

import sys
import subprocess

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "akshare", "pandas"], check=False)

import pandas as pd
import akshare as ak
from datetime import datetime

def get_chinext_stocks():
    """获取创业板股票列表"""
    df = ak.stock_info_a_code_name()
    return df[df['code'].str.startswith('300')]['code'].tolist()

def get_kline(code, period=120):
    """获取K线数据"""
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        df = df.tail(period).reset_index(drop=True)
        print(f"\n{code} 原始列名: {df.columns.tolist()}")
        print(f"{code} 数据行数: {len(df)}")
        print(f"{code} 前3行:\n{df.head(3)}")
        return df
    except Exception as e:
        print(f"Error fetching {code}: {e}")
        return None

# 测试前3只股票
stocks = get_chinext_stocks()
print(f"创业板股票总数: {len(stocks)}")
print(f"前5只: {stocks[:5]}")

for code in stocks[:3]:
    df = get_kline(code, period=120)
    if df is not None:
        print(f"\n{code} 成功获取数据")
        break
