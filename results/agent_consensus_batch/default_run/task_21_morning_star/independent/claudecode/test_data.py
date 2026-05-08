#!/usr/bin/env python3
"""Find which ChiNext stocks have data available"""

import akshare as ak
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def get_chinext_stocks():
    """Get all ChiNext stock codes"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except:
        return []

def test_stock_data(stock_code):
    """Test if stock has data"""
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                 start_date="20240101", end_date="20240308", adjust="qfq")
        if df is not None and len(df) > 0:
            return True, len(df)
        return False, 0
    except:
        return False, 0

print("Getting ChiNext stocks...")
stocks = get_chinext_stocks()
print(f"Total ChiNext stocks: {len(stocks)}")

print("\nTesting first 50 stocks for data availability...")
valid_stocks = []

for i, code in enumerate(stocks[:50], 1):
    has_data, days = test_stock_data(code)
    if has_data:
        valid_stocks.append((code, days))
        print(f"{i}. {code}: {days} days ✓")
    else:
        print(f"{i}. {code}: No data ✗")

print(f"\nValid stocks with data: {len(valid_stocks)}")
if valid_stocks:
    print("Sample valid stocks:", [s[0] for s in valid_stocks[:10]])
