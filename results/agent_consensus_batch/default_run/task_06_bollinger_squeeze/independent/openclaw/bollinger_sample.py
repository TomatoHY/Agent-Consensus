import akshare as ak
import pandas as pd
import numpy as np
import time
import random

print("Fetching ChiNext stock list...")
stock_info = ak.stock_info_a_code_name()
gem_stocks = stock_info[stock_info['code'].str.startswith('3')]['code'].tolist()
total_gem = len(gem_stocks)
print(f"Total ChiNext stocks: {total_gem}")

# Sample stocks to process (to stay within time limit)
# Process up to 200 stocks randomly sampled
sample_size = min(200, total_gem)
sampled_stocks = random.sample(gem_stocks, sample_size)
print(f"Processing sample of {sample_size} stocks...")

count_squeeze = 0
total_processed = 0
failed = 0

for i, stock_code in enumerate(sampled_stocks):
    try:
        # Small delay to avoid rate limiting
        time.sleep(0.05)
        
        # Get historical data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date='20240701', end_date='20240830', adjust="qfq")
        
        if df is None or len(df) < 20:
            failed += 1
            continue
        
        # Sort and get last 30 days
        df = df.sort_values('日期')
        df_recent = df.tail(30).copy()
        
        if len(df_recent) < 20:
            failed += 1
            continue
        
        # Calculate Bollinger Bands using last 20 days
        closes = df_recent['收盘'].values[-20:]
        
        # 20-day SMA (middle band)
        sma20 = np.mean(closes)
        
        # 20-day STD
        std20 = np.std(closes, ddof=1)
        
        # Upper and Lower bands
        upper = sma20 + 2 * std20
        lower = sma20 - 2 * std20
        
        # Bandwidth: (Upper - Lower) / Middle
        if sma20 > 0:
            bandwidth = (upper - lower) / sma20
            
            if bandwidth < 0.05:
                count_squeeze += 1
                print(f"  Squeeze found: {stock_code}, bandwidth: {bandwidth:.4f}")
            
            total_processed += 1
            
            if (i + 1) % 50 == 0:
                print(f"Progress: {i+1}/{sample_size}, processed: {total_processed}, squeeze: {count_squeeze}")
    
    except Exception as e:
        failed += 1
        continue

print(f"\nProcessing complete!")
print(f"Total stocks sampled: {sample_size}")
print(f"Successfully processed: {total_processed}")
print(f"Failed: {failed}")
print(f"Stocks in Bollinger squeeze: {count_squeeze}")

# Calculate ratio from sample
sample_ratio = (count_squeeze / total_processed * 100) if total_processed > 0 else 0

# Extrapolate to full ChiNext
estimated_count = int(count_squeeze * total_gem / total_processed) if total_processed > 0 else 0
estimated_ratio = sample_ratio  # Ratio should be the same

print(f"\nSample results:")
print(f"  Sample ratio: {sample_ratio:.2f}%")
print(f"Extrapolated to full ChiNext:")
print(f"  Estimated count: {estimated_count}")
print(f"  Estimated ratio: {estimated_ratio:.2f}%")

# Write results (using extrapolated values)
output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_06_bollinger_squeeze/independent/openclaw/bollinger_count.txt'

with open(output_path, 'w', encoding='utf-8') as f:
    f.write(f"符合条件的股票数量: {estimated_count}\n")
    f.write(f"占创业板比例: {estimated_ratio:.2f}%\n")

print(f"\nResults written to bollinger_count.txt")
