#!/usr/bin/env python3
"""
Debug script to check why no stocks are found
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicator"""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    diff = ema_fast - ema_slow
    dea = diff.ewm(span=signal, adjust=False).mean()
    macd = (diff - dea) * 2
    return diff, dea, macd

def find_golden_cross(diff, dea, lookback_days):
    """Find MACD golden cross within lookback period"""
    if len(diff) < lookback_days + 1:
        return None, False

    # Check last lookback_days for golden cross
    for i in range(len(diff) - lookback_days, len(diff)):
        if i > 0:
            # Golden cross: DIFF crosses above DEA
            if diff.iloc[i-1] <= dea.iloc[i-1] and diff.iloc[i] > dea.iloc[i]:
                return diff.index[i], True
    return None, False

def check_ma5_slope(prices):
    """Check if 5-day MA has positive slope (monotonically increasing)"""
    if len(prices) < 5:
        return False, 0

    ma5_values = []
    for i in range(len(prices) - 4, len(prices) + 1):
        ma5_values.append(prices.iloc[i-5:i].mean())

    # Check if monotonically increasing
    is_increasing = all(ma5_values[i] < ma5_values[i+1] for i in range(len(ma5_values)-1))

    # Calculate slope
    slope = (ma5_values[-1] - ma5_values[0]) / ma5_values[0] if ma5_values[0] != 0 else 0

    return is_increasing, slope, ma5_values

def calculate_volume_ratio(volumes):
    """Calculate volume ratio: avg(last 5 days) / avg(last 20 days)"""
    if len(volumes) < 20:
        return 0

    vol_5 = volumes.iloc[-5:].mean()
    vol_20 = volumes.iloc[-20:].mean()

    return vol_5 / vol_20 if vol_20 > 0 else 0

def get_weekly_data_from_daily(daily_df):
    """Convert daily data to weekly data"""
    weekly = daily_df.resample('W-FRI').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    return weekly

# Test with one stock
stock_code = '300750'
end_date = '2024-05-15'

print(f"Analyzing {stock_code}...")

start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=150)).strftime('%Y%m%d')
end_date_fmt = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')

daily_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                               start_date=start_date, end_date=end_date_fmt, adjust="qfq")

print(f"Daily data rows: {len(daily_df)}")

daily_df['日期'] = pd.to_datetime(daily_df['日期'])
daily_df.set_index('日期', inplace=True)
daily_df.sort_index(inplace=True)

print(f"\nLast 5 dates: {daily_df.index[-5:].tolist()}")

# Calculate daily MACD
daily_diff, daily_dea, _ = calculate_macd(daily_df['收盘'])

print(f"\nDaily MACD (last 10 days):")
for i in range(-10, 0):
    print(f"{daily_df.index[i].strftime('%Y-%m-%d')}: DIFF={daily_diff.iloc[i]:.4f}, DEA={daily_dea.iloc[i]:.4f}")

# Find daily golden cross
daily_cross_date, daily_has_cross = find_golden_cross(daily_diff, daily_dea, 10)
print(f"\nDaily golden cross: {daily_has_cross}, Date: {daily_cross_date}")

# Convert to weekly
weekly_df = get_weekly_data_from_daily(daily_df)
print(f"\nWeekly data rows: {len(weekly_df)}")
print(f"Last 5 weekly dates: {weekly_df.index[-5:].tolist()}")

# Calculate weekly MACD
weekly_diff, weekly_dea, _ = calculate_macd(weekly_df['close'])

print(f"\nWeekly MACD (last 5 weeks):")
for i in range(-5, 0):
    print(f"{weekly_df.index[i].strftime('%Y-%m-%d')}: DIFF={weekly_diff.iloc[i]:.4f}, DEA={weekly_dea.iloc[i]:.4f}")

# Find weekly golden cross
weekly_cross_date, weekly_has_cross = find_golden_cross(weekly_diff, weekly_dea, 4)
print(f"\nWeekly golden cross: {weekly_has_cross}, Date: {weekly_cross_date}")

# Check MA5 slope
ma5_increasing, slope, ma5_values = check_ma5_slope(daily_df['收盘'])
print(f"\nMA5 slope: {slope:.4f}, Increasing: {ma5_increasing}")
print(f"MA5 values: {[f'{v:.2f}' for v in ma5_values]}")

# Check volume ratio
vol_ratio = calculate_volume_ratio(daily_df['成交量'])
print(f"\nVolume ratio (5d/20d): {vol_ratio:.2f}")
print(f"Threshold: 1.2, Pass: {vol_ratio >= 1.2}")
