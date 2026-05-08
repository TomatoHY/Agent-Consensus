import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Get ChiNext stock list
print("Fetching ChiNext stock list...")
stock_info = ak.stock_info_a_code_name()
gem_stocks = stock_info[stock_info['code'].str.startswith('3')]
print(f"Total ChiNext stocks: {len(gem_stocks)}")

# Target date and date range
end_date = '20240830'
# Need at least 20 days for SMA + some buffer, get 50 days to be safe
start_date = '20240701'

count_squeeze = 0
total_processed = 0
failed_stocks = []

for idx, row in gem_stocks.iterrows():
    stock_code = row['code']
    stock_name = row['name']
    
    try:
        # Get historical data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=start_date, end_date=end_date, adjust="qfq")
        
        if df is None or len(df) < 20:
            failed_stocks.append(stock_code)
            continue
        
        # Sort by date
        df = df.sort_values('日期')
        
        # Get last 30 trading days
        df_recent = df.tail(30).copy()
        
        if len(df_recent) < 20:
            failed_stocks.append(stock_code)
            continue
        
        # Calculate 20-day SMA (middle band)
        df_recent['SMA20'] = df_recent['收盘'].rolling(window=20).mean()
        
        # Calculate 20-day standard deviation
        df_recent['STD20'] = df_recent['收盘'].rolling(window=20).std()
        
        # Calculate upper and lower bands
        df_recent['Upper'] = df_recent['SMA20'] + 2 * df_recent['STD20']
        df_recent['Lower'] = df_recent['SMA20'] - 2 * df_recent['STD20']
        
        # Get the latest day's values
        latest = df_recent.iloc[-1]
        
        if pd.isna(latest['SMA20']) or pd.isna(latest['Upper']) or pd.isna(latest['Lower']):
            failed_stocks.append(stock_code)
            continue
        
        # Calculate bandwidth: (Upper - Lower) / Middle
        bandwidth = (latest['Upper'] - latest['Lower']) / latest['SMA20']
        
        # Check if in squeeze (bandwidth < 5%)
        if bandwidth < 0.05:
            count_squeeze += 1
        
        total_processed += 1
        
        if total_processed % 100 == 0:
            print(f"Processed {total_processed} stocks, found {count_squeeze} in squeeze")
    
    except Exception as e:
        failed_stocks.append(stock_code)
        continue

print(f"\nProcessing complete!")
print(f"Total stocks processed: {total_processed}")
print(f"Stocks in Bollinger squeeze: {count_squeeze}")
print(f"Failed to process: {len(failed_stocks)}")

# Calculate ratio
ratio = (count_squeeze / total_processed * 100) if total_processed > 0 else 0

# Write results
output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_06_bollinger_squeeze/independent/openclaw/bollinger_count.txt'

with open(output_path, 'w', encoding='utf-8') as f:
    f.write(f"符合条件的股票数量: {count_squeeze}\n")
    f.write(f"占创业板比例: {ratio:.2f}%\n")

print(f"\nResults written to bollinger_count.txt")
print(f"符合条件的股票数量: {count_squeeze}")
print(f"占创业板比例: {ratio:.2f}%")
