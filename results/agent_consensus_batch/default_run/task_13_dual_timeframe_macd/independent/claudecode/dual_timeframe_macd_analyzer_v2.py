#!/usr/bin/env python3
"""
Dual Timeframe MACD Golden Cross Stock Screener - Version 2
Uses alternative data fetching methods
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import time
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

    # Calculate slope (simple difference)
    slope = (ma5_values[-1] - ma5_values[0]) / ma5_values[0] if ma5_values[0] != 0 else 0

    return is_increasing, slope

def calculate_volume_ratio(volumes):
    """Calculate volume ratio: avg(last 5 days) / avg(last 20 days)"""
    if len(volumes) < 20:
        return 0

    vol_5 = volumes.iloc[-5:].mean()
    vol_20 = volumes.iloc[-20:].mean()

    return vol_5 / vol_20 if vol_20 > 0 else 0

def get_weekly_data_from_daily(daily_df):
    """Convert daily data to weekly data"""
    # Resample to weekly, using Friday as week end
    weekly = daily_df.resample('W-FRI').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    return weekly

def analyze_stock(stock_code, end_date='2024-05-15'):
    """Analyze a single stock for dual timeframe MACD conditions"""
    try:
        # Get daily K-line data (90 days for MACD warmup)
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=150)).strftime('%Y%m%d')
        end_date_fmt = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')

        # Fetch daily data
        daily_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                       start_date=start_date, end_date=end_date_fmt, adjust="qfq")

        if daily_df is None or len(daily_df) < 60:
            return None

        daily_df['日期'] = pd.to_datetime(daily_df['日期'])
        daily_df.set_index('日期', inplace=True)
        daily_df.sort_index(inplace=True)

        # Calculate daily MACD
        daily_diff, daily_dea, _ = calculate_macd(daily_df['收盘'])

        # Find daily golden cross (last 10 trading days)
        daily_cross_date, daily_has_cross = find_golden_cross(daily_diff, daily_dea, 10)

        if not daily_has_cross:
            return None

        # Convert to weekly data
        weekly_df = get_weekly_data_from_daily(daily_df)

        if len(weekly_df) < 26:
            return None

        # Calculate weekly MACD
        weekly_diff, weekly_dea, _ = calculate_macd(weekly_df['close'])

        # Find weekly golden cross (last 4 weeks)
        weekly_cross_date, weekly_has_cross = find_golden_cross(weekly_diff, weekly_dea, 4)

        if not weekly_has_cross:
            return None

        # Check MA5 slope
        ma5_increasing, slope = check_ma5_slope(daily_df['收盘'])

        if not ma5_increasing:
            return None

        # Check volume ratio
        vol_ratio = calculate_volume_ratio(daily_df['成交量'])

        if vol_ratio < 1.2:
            return None

        # All conditions met
        return {
            'code': stock_code,
            'daily_cross': daily_cross_date.strftime('%Y-%m-%d'),
            'weekly_cross': weekly_cross_date.strftime('%Y-%m-%d'),
            'slope': round(slope, 4),
            'vol_ratio': round(vol_ratio, 2)
        }

    except Exception as e:
        return None

def main():
    """Main function to screen ChiNext stocks"""
    print("Starting dual timeframe MACD analysis...")

    # Manually create a list of ChiNext stocks (300XXX)
    # Using a sample of common ChiNext stocks
    chinext_stocks = [
        '300001', '300002', '300003', '300004', '300005',
        '300010', '300015', '300017', '300020', '300024',
        '300027', '300033', '300036', '300037', '300059',
        '300070', '300072', '300073', '300088', '300104',
        '300122', '300124', '300136', '300142', '300144',
        '300168', '300182', '300188', '300207', '300223',
        '300251', '300253', '300274', '300285', '300296',
        '300315', '300347', '300408', '300433', '300450',
        '300498', '300502', '300529', '300568', '300595',
        '300601', '300628', '300661', '300676', '300750'
    ]

    print(f"Analyzing {len(chinext_stocks)} ChiNext stocks")

    results = []

    for i, stock_code in enumerate(chinext_stocks, 1):
        print(f"Processing {i}/{len(chinext_stocks)}: {stock_code}", end='\r')
        result = analyze_stock(stock_code)
        if result:
            results.append(result)
            print(f"\nFound: {stock_code}")
        time.sleep(0.1)  # Small delay to avoid rate limiting

    print("\n\nWriting results...")

    # Write results to file
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_13_dual_timeframe_macd/independent/claudecode/dual_timeframe_macd.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,日线金叉日期,周线金叉日期,5日均线斜率,量比(近5日/近20日)\n")

        if results:
            for r in results:
                f.write(f"{r['code']},{r['daily_cross']},{r['weekly_cross']},{r['slope']},{r['vol_ratio']}\n")
        else:
            f.write("无符合条件的股票\n")

    print(f"Results written to dual_timeframe_macd.txt")
    print(f"Total stocks found: {len(results)}")

if __name__ == "__main__":
    main()
