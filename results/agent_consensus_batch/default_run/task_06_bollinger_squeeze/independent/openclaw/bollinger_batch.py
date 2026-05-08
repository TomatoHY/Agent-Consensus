import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime

print("Fetching ChiNext stock list...")
stock_info = ak.stock_info_a_code_name()
gem_stocks = stock_info[stock_info['code'].str.startswith('3')]['code'].tolist()
print(f"Total ChiNext stocks: {len(gem_stocks)}")

# Try to get batch data for ChiNext
print("\nFetching market data...")
try:
    # Get real-time quotes for all A-shares
    spot_df = ak.stock_zh_a_spot_em()
    
    # Filter for ChiNext stocks (code starts with 3)
    gem_spot = spot_df[spot_df['代码'].str.startswith('3')].copy()
    print(f"Found {len(gem_spot)} ChiNext stocks in spot data")
    
    count_squeeze = 0
    total_processed = 0
    
    # For each stock, get historical data and calculate Bollinger
    for idx, row in gem_spot.iterrows():
        stock_code = row['代码']
        
        try:
            # Get historical data
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                    start_date='20240701', end_date='20240830', adjust="qfq")
            
            if df is None or len(df) < 20:
                continue
            
            # Sort and get last 30 days
            df = df.sort_values('日期')
            df_recent = df.tail(30).copy()
            
            if len(df_recent) < 20:
                continue
            
            # Calculate Bollinger Bands
            closes = df_recent['收盘'].values
            
            # 20-day SMA
            sma20 = np.mean(closes[-20:])
            
            # 20-day STD
            std20 = np.std(closes[-20:], ddof=1)
            
            # Upper and Lower bands
            upper = sma20 + 2 * std20
            lower = sma20 - 2 * std20
            
            # Bandwidth
            if sma20 > 0:
                bandwidth = (upper - lower) / sma20
                
                if bandwidth < 0.05:
                    count_squeeze += 1
                
                total_processed += 1
                
                if total_processed % 100 == 0:
                    print(f"Processed {total_processed} stocks, found {count_squeeze} in squeeze")
        
        except Exception as e:
            continue
    
    print(f"\nProcessing complete!")
    print(f"Total stocks processed: {total_processed}")
    print(f"Stocks in Bollinger squeeze: {count_squeeze}")
    
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

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
