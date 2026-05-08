import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configuration
TARGET_STOCK = "300750"  # CATL
END_DATE = "2024-04-15"
CORRELATION_DAYS = 30
KDJ_CHECK_DAYS = 5
MIN_CORRELATION = 0.8
TOP_N = 10

# KDJ parameters
K_PERIOD = 9
D_PERIOD = 3

def get_trading_days(end_date, days):
    """Get trading days before end_date"""
    end = pd.to_datetime(end_date)
    start = end - timedelta(days=days*2)  # Buffer for non-trading days
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

def calculate_returns(stock_code, start_date, end_date):
    """Calculate daily returns for a stock"""
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=start_date, end_date=end_date, adjust="qfq")
        if df is None or len(df) == 0:
            return None

        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')
        df['return'] = df['收盘'].pct_change()
        return df[['日期', 'return']].dropna()
    except:
        return None

def calculate_kdj(stock_code, start_date, end_date):
    """Calculate KDJ indicator"""
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=start_date, end_date=end_date, adjust="qfq")
        if df is None or len(df) < K_PERIOD:
            return None

        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')

        # Calculate RSV
        low_min = df['最低'].rolling(window=K_PERIOD, min_periods=K_PERIOD).min()
        high_max = df['最高'].rolling(window=K_PERIOD, min_periods=K_PERIOD).max()
        rsv = (df['收盘'] - low_min) / (high_max - low_min) * 100

        # Calculate K and D
        k_values = []
        d_values = []
        k = 50  # Initial K
        d = 50  # Initial D

        for i, rsv_val in enumerate(rsv):
            if pd.isna(rsv_val):
                k_values.append(np.nan)
                d_values.append(np.nan)
            else:
                k = (2/3) * k + (1/3) * rsv_val
                d = (2/3) * d + (1/3) * k
                k_values.append(k)
                d_values.append(d)

        df['K'] = k_values
        df['D'] = d_values
        df['J'] = 3 * df['K'] - 2 * df['D']

        return df[['日期', 'K', 'D', 'J']].dropna()
    except:
        return None

def detect_golden_cross(kdj_df, check_days):
    """Detect KDJ golden cross in last N days"""
    if kdj_df is None or len(kdj_df) < 2:
        return None

    # Get last check_days + 1 for comparison
    recent = kdj_df.tail(check_days + 1).reset_index(drop=True)

    for i in range(1, len(recent)):
        k_prev, d_prev = recent.loc[i-1, 'K'], recent.loc[i-1, 'D']
        k_curr, d_curr = recent.loc[i, 'K'], recent.loc[i, 'D']

        # Golden cross: K crosses above D
        if k_prev <= d_prev and k_curr > d_curr:
            return recent.loc[i, '日期'].strftime("%Y-%m-%d")

    return None

print("=" * 60)
print("Stage 1: Calculating correlation with CATL (300750)")
print("=" * 60)

# Get CATL returns
start_date, end_date = get_trading_days(END_DATE, CORRELATION_DAYS + 10)
print(f"Fetching CATL data from {start_date} to {end_date}...")

catl_returns = calculate_returns(TARGET_STOCK, start_date, end_date)
if catl_returns is None or len(catl_returns) < CORRELATION_DAYS:
    print("Error: Cannot fetch CATL data")
    exit(1)

# Get last 30 trading days
catl_returns = catl_returns.tail(CORRELATION_DAYS)
print(f"CATL returns: {len(catl_returns)} days")

# Get ChiNext stock list (300XXX)
print("\nFetching ChiNext stock list...")
stock_list = ak.stock_zh_a_spot_em()
chinext_stocks = stock_list[stock_list['代码'].str.startswith('300')]['代码'].tolist()
chinext_stocks = [s for s in chinext_stocks if s != TARGET_STOCK]
print(f"Found {len(chinext_stocks)} ChiNext stocks (excluding CATL)")

# Calculate correlations
print("\nCalculating correlations...")
correlations = []

for i, stock_code in enumerate(chinext_stocks):
    if (i + 1) % 50 == 0:
        print(f"Progress: {i+1}/{len(chinext_stocks)}")

    stock_returns = calculate_returns(stock_code, start_date, end_date)
    if stock_returns is None or len(stock_returns) < CORRELATION_DAYS:
        continue

    # Align dates
    merged = pd.merge(catl_returns, stock_returns, on='日期', suffixes=('_catl', '_stock'))
    if len(merged) < CORRELATION_DAYS * 0.8:  # At least 80% overlap
        continue

    # Calculate Pearson correlation
    corr = merged['return_catl'].corr(merged['return_stock'])
    if not pd.isna(corr):
        correlations.append((stock_code, corr))

# Sort by correlation and get top 10 with corr > 0.8
correlations.sort(key=lambda x: x[1], reverse=True)
high_corr_stocks = [(code, corr) for code, corr in correlations if corr > MIN_CORRELATION][:TOP_N]

print(f"\nFound {len(high_corr_stocks)} stocks with correlation > {MIN_CORRELATION}")
for code, corr in high_corr_stocks:
    print(f"  {code}: {corr:.4f}")

if len(high_corr_stocks) == 0:
    print("\nNo stocks meet the correlation threshold > 0.8")
    with open("/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_12_catl_correlation_kdj/independent/claudecode/corr_kdj_result.txt", "w") as f:
        f.write("# 无符合条件的股票（相关系数>0.8且近5日KDJ金叉）\n")
    exit(0)

print("\n" + "=" * 60)
print("Stage 2: Checking KDJ golden cross for high-correlation stocks")
print("=" * 60)

# Calculate KDJ for high correlation stocks
results = []
kdj_start, kdj_end = get_trading_days(END_DATE, KDJ_CHECK_DAYS + K_PERIOD + 5)

for stock_code, corr in high_corr_stocks:
    print(f"\nChecking {stock_code} (corr={corr:.4f})...")

    kdj_df = calculate_kdj(stock_code, kdj_start, kdj_end)
    if kdj_df is None:
        print(f"  Cannot calculate KDJ")
        continue

    golden_cross_date = detect_golden_cross(kdj_df, KDJ_CHECK_DAYS)
    if golden_cross_date:
        print(f"  ✓ Golden cross detected on {golden_cross_date}")
        results.append((stock_code, corr, golden_cross_date))
    else:
        print(f"  ✗ No golden cross in last {KDJ_CHECK_DAYS} days")

# Write results
output_path = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_12_catl_correlation_kdj/independent/claudecode/corr_kdj_result.txt"

print("\n" + "=" * 60)
print("Final Results")
print("=" * 60)

with open(output_path, "w") as f:
    if len(results) == 0:
        f.write("# 无符合条件的股票（相关系数>0.8且近5日KDJ金叉）\n")
        print("No stocks meet both criteria (correlation > 0.8 AND KDJ golden cross)")
    else:
        f.write("股票代码,相关系数,KDJ金叉日期\n")
        for code, corr, date in results:
            f.write(f"{code},{corr:.4f},{date}\n")
            print(f"{code}, {corr:.4f}, {date}")

print(f"\nResults written to: {output_path}")
