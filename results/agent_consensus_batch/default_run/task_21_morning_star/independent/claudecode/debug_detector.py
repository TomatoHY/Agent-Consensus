#!/usr/bin/env python3
"""Debug version to understand pattern detection"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


def get_stock_data(stock_code, end_date):
    """Get stock K-line data"""
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                 start_date="20231201", end_date=end_date, adjust="qfq")
        if df is None or len(df) == 0:
            return None

        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '涨跌幅': 'pct_change'
        })

        df = df[['date', 'open', 'close', 'high', 'low']]
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        return df
    except Exception as e:
        return None


def calculate_body_ratio(open_price, close_price, high_price, low_price):
    """Calculate body ratio: |close - open| / (high - low)"""
    body = abs(close_price - open_price)
    amplitude = high_price - low_price
    if amplitude == 0:
        return 0
    return body / amplitude


def calculate_pct_change(open_price, close_price):
    """Calculate percentage change"""
    if open_price == 0:
        return 0
    return (close_price - open_price) / open_price * 100


# Test with a few stocks
test_stocks = ['300001', '300002', '300003', '300059', '300750']
end_date = "20240308"

for stock_code in test_stocks:
    print(f"\n{'='*60}")
    print(f"Testing {stock_code}")
    print('='*60)

    df = get_stock_data(stock_code, end_date)
    if df is None or len(df) < 90:
        print(f"Insufficient data for {stock_code}")
        continue

    print(f"Total days: {len(df)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")

    # Check last 30 days for patterns
    start_idx = max(60, len(df) - 37)
    end_idx = len(df) - 7

    print(f"Checking indices {start_idx} to {end_idx}")

    pattern_count = 0
    for idx in range(start_idx, end_idx):
        if idx + 2 >= len(df):
            continue

        day1 = df.iloc[idx]
        day2 = df.iloc[idx + 1]
        day3 = df.iloc[idx + 2]

        # Calculate metrics
        day1_pct = calculate_pct_change(day1['open'], day1['close'])
        day1_body_ratio = calculate_body_ratio(day1['open'], day1['close'],
                                               day1['high'], day1['low'])

        day2_pct = calculate_pct_change(day2['open'], day2['close'])

        day3_pct = calculate_pct_change(day3['open'], day3['close'])
        day3_body_ratio = calculate_body_ratio(day3['open'], day3['close'],
                                               day3['high'], day3['low'])

        day1_midpoint = (day1['open'] + day1['close']) / 2

        # Check conditions
        cond1 = day1_pct < -3 and day1_body_ratio > 0.7
        cond2 = abs(day2_pct) < 1.5
        cond3 = day3_pct > 3 and day3_body_ratio > 0.7
        cond4 = day3['close'] > day1_midpoint

        if cond1 and cond2:
            print(f"\nPotential pattern at {day1['date'].strftime('%Y-%m-%d')}:")
            print(f"  Day1: pct={day1_pct:.2f}%, body_ratio={day1_body_ratio:.2f} [{'✓' if cond1 else '✗'}]")
            print(f"  Day2: pct={day2_pct:.2f}% [{'✓' if cond2 else '✗'}]")
            print(f"  Day3: pct={day3_pct:.2f}%, body_ratio={day3_body_ratio:.2f} [{'✓' if cond3 else '✗'}]")
            print(f"  Day3 close vs Day1 midpoint: {day3['close']:.2f} vs {day1_midpoint:.2f} [{'✓' if cond4 else '✗'}]")

            if cond1 and cond2 and cond3 and cond4:
                # Check MA60
                if idx >= 60:
                    ma60 = df.iloc[idx-60:idx]['close'].mean()
                    low_pos = day3['close'] < ma60 * 0.9
                    print(f"  Low position: {day3['close']:.2f} < {ma60*0.9:.2f} [{'✓' if low_pos else '✗'}]")

                    if low_pos:
                        # Check post validation
                        pattern_lowest = min(day1['low'], day2['low'], day3['low'])
                        if idx + 7 < len(df):
                            next_5_days = df.iloc[idx+3:idx+8]
                            no_break = all(day['low'] >= pattern_lowest for _, day in next_5_days.iterrows())
                            print(f"  Post validation (no break below {pattern_lowest:.2f}): [{'✓' if no_break else '✗'}]")

                            if no_break:
                                return_5d = (df.iloc[idx+7]['close'] - day3['close']) / day3['close'] * 100
                                print(f"  ✓✓✓ VALID PATTERN! 5-day return: {return_5d:.2f}%")
                                pattern_count += 1

    print(f"\nTotal valid patterns found: {pattern_count}")
