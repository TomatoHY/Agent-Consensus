import os
import sys

# Force disable proxy before any imports
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

import akshare as ak
import pandas as pd
import numpy as np
import time

# Patch requests to disable proxy
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Create a session that ignores system proxy
session = requests.Session()
session.trust_env = False
session.proxies = {}

# Monkey patch akshare's request module
import akshare.utils.request as ak_request
ak_request.session = session

print("Fetching ChiNext stock list...")
gem_stocks = ak.stock_zh_a_spot_em()
gem_stocks = gem_stocks[gem_stocks['代码'].str.startswith(('300', '301'))]
print(f"Total ChiNext stocks: {len(gem_stocks)}")

end_date = "20240830"
start_date = "20240701"

count_squeeze = 0
total_checked = 0
failed_count = 0

for idx, row in gem_stocks.iterrows():
    stock_code = row['代码']
    
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=start_date, end_date=end_date, adjust="qfq")
        
        if df is None or len(df) < 20:
            failed_count += 1
            continue
            
        df = df.tail(30)
        
        if len(df) < 20:
            failed_count += 1
            continue
            
        total_checked += 1
        
        close_prices = df['收盘'].values
        middle_band = np.mean(close_prices[-20:])
        std_20 = np.std(close_prices[-20:], ddof=1)
        upper_band = middle_band + 2 * std_20
        lower_band = middle_band - 2 * std_20
        bandwidth = (upper_band - lower_band) / middle_band
        
        if bandwidth < 0.05:
            count_squeeze += 1
            
        if total_checked % 100 == 0:
            print(f"Processed {total_checked} stocks, found {count_squeeze} in squeeze")
        
        time.sleep(0.05)
        
    except Exception as e:
        failed_count += 1
        continue

print(f"\nTotal stocks checked: {total_checked}")
print(f"Stocks in Bollinger squeeze: {count_squeeze}")
print(f"Failed: {failed_count}")

ratio = (count_squeeze / total_checked * 100) if total_checked > 0 else 0

with open('bollinger_count.txt', 'w', encoding='utf-8') as f:
    f.write(f"符合条件的股票数量: {count_squeeze}\n")
    f.write(f"占创业板比例: {ratio:.2f}%\n")

print(f"\nResult written to bollinger_count.txt")
print(f"Count: {count_squeeze}, Ratio: {ratio:.2f}%")
