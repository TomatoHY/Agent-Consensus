import akshare as ak
import pandas as pd
import numpy as np
import time

print("Testing data access...")

# Get ChiNext stock list
stock_info = ak.stock_info_a_code_name()
gem_stocks = stock_info[stock_info['code'].str.startswith('3')]['code'].tolist()
total_gem = len(gem_stocks)
print(f"Total ChiNext stocks: {total_gem}")

# Test a few stocks to see what's working
test_stocks = gem_stocks[:10]
print(f"\nTesting first 10 stocks...")

for stock_code in test_stocks:
    try:
        print(f"\nTrying {stock_code}...")
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date='20240701', end_date='20240830', adjust="qfq")
        
        if df is not None and len(df) > 0:
            print(f"  Success! Got {len(df)} rows")
            print(f"  Date range: {df['日期'].min()} to {df['日期'].max()}")
            print(f"  Columns: {df.columns.tolist()}")
            
            # Try calculating Bollinger
            if len(df) >= 20:
                df = df.sort_values('日期')
                closes = df['收盘'].values[-20:]
                sma20 = np.mean(closes)
                std20 = np.std(closes, ddof=1)
                upper = sma20 + 2 * std20
                lower = sma20 - 2 * std20
                bandwidth = (upper - lower) / sma20 if sma20 > 0 else 0
                print(f"  Bollinger bandwidth: {bandwidth:.4f} ({'SQUEEZE' if bandwidth < 0.05 else 'normal'})")
        else:
            print(f"  Failed: No data returned")
        
        time.sleep(0.2)
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "="*50)
print("If most stocks failed, there may be a data access issue.")
print("Checking alternative approach...")

# Try using stock_zh_a_daily instead
print("\nTrying alternative API: stock_zh_a_daily...")
try:
    test_code = gem_stocks[0]
    print(f"Testing with {test_code}...")
    df = ak.stock_zh_a_daily(symbol=f"sz{test_code}", start_date="20240701", end_date="20240830", adjust="qfq")
    if df is not None and len(df) > 0:
        print(f"Success with stock_zh_a_daily! Got {len(df)} rows")
    else:
        print("Failed with stock_zh_a_daily")
except Exception as e:
    print(f"Error with stock_zh_a_daily: {e}")
