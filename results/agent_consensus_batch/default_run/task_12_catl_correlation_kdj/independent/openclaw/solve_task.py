#!/usr/bin/env python3
"""
Task: Find ChiNext stocks highly correlated with CATL (300750) that show KDJ golden cross
Stage 1: Calculate 30-day return correlation with CATL
Stage 2: Check KDJ golden cross in last 5 days for high-correlation stocks
"""

import os
import sys

# Disable proxy at environment level
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]
os.environ['NO_PROXY'] = '*'

# Patch urllib before any imports
import urllib.request
urllib.request.getproxies = lambda: {}

# Import requests and patch it
import requests
from requests.adapters import HTTPAdapter

# Create a custom adapter that forces no proxy
class NoProxyHTTPAdapter(HTTPAdapter):
    def send(self, request, **kwargs):
        kwargs['proxies'] = {}
        return super().send(request, **kwargs)

# Monkey-patch requests.Session to use our adapter
original_init = requests.Session.__init__
def patched_init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    self.mount('http://', NoProxyHTTPAdapter())
    self.mount('https://', NoProxyHTTPAdapter())
requests.Session.__init__ = patched_init

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import pearsonr
import time

# Configuration
TARGET_STOCK = "300750"  # CATL
END_DATE = "2024-04-15"
LOOKBACK_DAYS = 30
CORR_THRESHOLD = 0.8
TOP_N = 10
KDJ_LOOKBACK = 5
KDJ_PERIOD = 9
KDJ_D_PERIOD = 3

RESULT_DIR = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_12_catl_correlation_kdj/independent/openclaw"

def get_trading_days(end_date, days=60):
    """Get trading days before end_date"""
    end = pd.to_datetime(end_date)
    start = end - timedelta(days=days*2)  # Buffer for weekends/holidays
    
    # Get trading calendar from any stock
    for attempt in range(3):
        try:
            df = ak.stock_zh_a_hist(symbol=TARGET_STOCK, period="daily", 
                                    start_date=start.strftime("%Y%m%d"),
                                    end_date=end.strftime("%Y%m%d"),
                                    adjust="qfq")
            return df['日期'].tolist()
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2)
    raise Exception("Failed to get trading days")

def get_stock_data(symbol, start_date, end_date, max_retries=2):
    """Get stock daily data with retry"""
    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                    start_date=start_date.replace("-", ""),
                                    end_date=end_date.replace("-", ""),
                                    adjust="qfq")
            if df is None or len(df) == 0:
                return None
            df['日期'] = pd.to_datetime(df['日期'])
            return df[['日期', '收盘']].rename(columns={'收盘': 'close'})
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            continue
    return None

def calculate_returns(prices):
    """Calculate daily returns"""
    return prices.pct_change().dropna()

def calculate_kdj(df, n=9, m1=3, m2=3):
    """
    Calculate KDJ indicator
    K = SMA(RSV, m1)
    D = SMA(K, m2)
    J = 3*K - 2*D
    """
    df = df.copy()
    
    # Calculate RSV (Raw Stochastic Value)
    low_min = df['低'].rolling(window=n, min_periods=n).min()
    high_max = df['高'].rolling(window=n, min_periods=n).max()
    
    df['RSV'] = 100 * (df['收盘'] - low_min) / (high_max - low_min)
    df['RSV'].fillna(50, inplace=True)  # Initial value
    
    # Calculate K, D, J
    df['K'] = df['RSV'].ewm(com=m1-1, adjust=False).mean()
    df['D'] = df['K'].ewm(com=m2-1, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']
    
    return df

def detect_golden_cross(df, lookback=5):
    """
    Detect KDJ golden cross (K crosses above D) in last N days
    Returns: (has_cross, cross_date)
    """
    if len(df) < 2:
        return False, None
    
    # Get last N days
    recent = df.tail(lookback + 1)
    
    for i in range(1, len(recent)):
        prev_k = recent.iloc[i-1]['K']
        prev_d = recent.iloc[i-1]['D']
        curr_k = recent.iloc[i]['K']
        curr_d = recent.iloc[i]['D']
        
        # Golden cross: K was below D, now above D
        if prev_k <= prev_d and curr_k > curr_d:
            return True, recent.iloc[i]['日期'].strftime('%Y-%m-%d')
    
    return False, None

print("=" * 60)
print("Stage 1: Calculate correlation with CATL (300750)")
print("=" * 60)

# Get CATL data
trading_days = get_trading_days(END_DATE, days=60)
if len(trading_days) < LOOKBACK_DAYS:
    print(f"Error: Not enough trading days")
    sys.exit(1)

# Get last 30 trading days
target_days = trading_days[-LOOKBACK_DAYS:]
start_date = target_days[0]

print(f"Date range: {start_date} to {END_DATE}")
print(f"Trading days: {len(target_days)}")

# Get CATL returns
catl_df = get_stock_data(TARGET_STOCK, start_date, END_DATE)
if catl_df is None:
    print("Error: Cannot get CATL data")
    sys.exit(1)

catl_returns = calculate_returns(catl_df.set_index('日期')['close'])
print(f"CATL returns: {len(catl_returns)} days")

# Get ChiNext stock list
print("\nFetching ChiNext stock list...")
for attempt in range(3):
    try:
        stock_list = ak.stock_zh_a_spot_em()
        break
    except Exception as e:
        print(f"Attempt {attempt+1} to get stock list failed: {e}")
        time.sleep(2)
        if attempt == 2:
            raise

chinext_stocks = stock_list[stock_list['代码'].str.startswith('3')]['代码'].tolist()
chinext_stocks = [s for s in chinext_stocks if s != TARGET_STOCK]
print(f"Total ChiNext stocks: {len(chinext_stocks)}")

# Calculate correlations
print("\nCalculating correlations...")
correlations = []

for i, symbol in enumerate(chinext_stocks):
    if (i + 1) % 100 == 0:
        print(f"Progress: {i+1}/{len(chinext_stocks)}")
    
    df = get_stock_data(symbol, start_date, END_DATE)
    if df is None or len(df) < LOOKBACK_DAYS:
        continue
    
    returns = calculate_returns(df.set_index('日期')['close'])
    
    # Align dates
    common_dates = catl_returns.index.intersection(returns.index)
    if len(common_dates) < LOOKBACK_DAYS * 0.8:  # At least 80% data
        continue
    
    catl_aligned = catl_returns.loc[common_dates]
    stock_aligned = returns.loc[common_dates]
    
    # Calculate Pearson correlation
    if len(catl_aligned) >= 10:  # Minimum data points
        corr, pval = pearsonr(catl_aligned, stock_aligned)
        if not np.isnan(corr):
            correlations.append({
                'symbol': symbol,
                'correlation': corr,
                'data_points': len(common_dates)
            })

# Sort by correlation
correlations_df = pd.DataFrame(correlations)
correlations_df = correlations_df.sort_values('correlation', ascending=False)

print(f"\nTotal stocks with valid correlation: {len(correlations_df)}")
print(f"\nTop 10 correlations:")
print(correlations_df.head(10))

# Filter by threshold and get top N
high_corr = correlations_df[correlations_df['correlation'] > CORR_THRESHOLD].head(TOP_N)
print(f"\nStocks with correlation > {CORR_THRESHOLD}: {len(high_corr)}")

if len(high_corr) == 0:
    print("\nNo stocks found with correlation > 0.8")
    with open(f'{RESULT_DIR}/corr_kdj_result.txt', 'w') as f:
        f.write("# 无符合条件的股票（相关系数>0.8且近5日出现KDJ金叉）\n")
    sys.exit(0)

print("\n" + "=" * 60)
print("Stage 2: Check KDJ golden cross for high-correlation stocks")
print("=" * 60)

# For KDJ calculation, need more historical data
kdj_start_date = trading_days[-60] if len(trading_days) >= 60 else trading_days[0]

results = []

for idx, row in high_corr.iterrows():
    symbol = row['symbol']
    corr = row['correlation']
    
    print(f"\nChecking {symbol} (corr={corr:.4f})...")
    
    # Get full data for KDJ calculation
    for attempt in range(2):
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                    start_date=kdj_start_date.replace("-", ""),
                                    end_date=END_DATE.replace("-", ""),
                                    adjust="qfq")
            break
        except Exception as e:
            if attempt == 0:
                time.sleep(1)
            else:
                print(f"  Error fetching data: {e}")
                df = None
    
    if df is None or len(df) < KDJ_PERIOD + KDJ_LOOKBACK:
        print(f"  Insufficient data")
        continue
    
    df['日期'] = pd.to_datetime(df['日期'])
    
    # Calculate KDJ
    df = calculate_kdj(df, n=KDJ_PERIOD, m1=KDJ_D_PERIOD, m2=KDJ_D_PERIOD)
    
    # Detect golden cross in last 5 days
    has_cross, cross_date = detect_golden_cross(df, lookback=KDJ_LOOKBACK)
    
    if has_cross:
        print(f"  ✓ Golden cross found on {cross_date}")
        results.append({
            'symbol': symbol,
            'correlation': corr,
            'cross_date': cross_date
        })
    else:
        print(f"  ✗ No golden cross in last {KDJ_LOOKBACK} days")

print("\n" + "=" * 60)
print("Final Results")
print("=" * 60)

if len(results) == 0:
    print("No stocks meet both criteria (correlation > 0.8 AND KDJ golden cross)")
    with open(f'{RESULT_DIR}/corr_kdj_result.txt', 'w') as f:
        f.write("# 无符合条件的股票（相关系数>0.8且近5日出现KDJ金叉）\n")
else:
    print(f"\nFound {len(results)} stocks meeting both criteria:")
    
    # Write results
    with open(f'{RESULT_DIR}/corr_kdj_result.txt', 'w') as f:
        f.write("股票代码,相关系数,KDJ金叉日期\n")
        for r in results:
            line = f"{r['symbol']},{r['correlation']:.4f},{r['cross_date']}\n"
            f.write(line)
            print(line.strip())
    
    print(f"\nResults written to: corr_kdj_result.txt")

print("\nTask completed!")
