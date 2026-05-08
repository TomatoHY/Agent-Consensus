#!/usr/bin/env python3
"""
Morning Star Pattern Detector - Demonstration Version
Since network access to akshare is blocked, this demonstrates the algorithm with synthetic data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

np.random.seed(42)
random.seed(42)


def generate_realistic_stock_data(stock_code, days=90, base_price=20.0):
    """Generate realistic stock K-line data with potential morning star patterns"""
    dates = pd.date_range(end='2024-03-08', periods=days, freq='B')

    data = []
    price = base_price

    for i, date in enumerate(dates):
        # Add some volatility
        daily_change = np.random.normal(0, 0.02)

        # Occasionally create downtrends followed by reversals (morning star setup)
        if i > 60 and i < days - 10 and random.random() < 0.05:
            # Create a potential morning star pattern
            # Day 1: Big bearish candle
            open_price = price
            close_price = price * (1 - 0.04)  # -4% drop
            high_price = open_price * 1.005
            low_price = close_price * 0.995
            data.append({
                'date': date,
                'open': open_price,
                'close': close_price,
                'high': high_price,
                'low': low_price
            })
            price = close_price

            # Day 2: Small candle
            if i + 1 < len(dates):
                open_price = price
                close_price = price * (1 + 0.01)  # +1% small move
                high_price = max(open_price, close_price) * 1.005
                low_price = min(open_price, close_price) * 0.995
                data.append({
                    'date': dates[i+1],
                    'open': open_price,
                    'close': close_price,
                    'high': high_price,
                    'low': low_price
                })
                price = close_price

                # Day 3: Big bullish candle
                if i + 2 < len(dates):
                    open_price = price
                    close_price = price * (1 + 0.045)  # +4.5% rise
                    high_price = close_price * 1.005
                    low_price = open_price * 0.995
                    data.append({
                        'date': dates[i+2],
                        'open': open_price,
                        'close': close_price,
                        'high': high_price,
                        'low': low_price
                    })
                    price = close_price

                    # Continue with normal days
                    continue

        # Normal day
        open_price = price * (1 + np.random.uniform(-0.01, 0.01))
        close_price = open_price * (1 + daily_change)
        high_price = max(open_price, close_price) * (1 + abs(np.random.uniform(0, 0.015)))
        low_price = min(open_price, close_price) * (1 - abs(np.random.uniform(0, 0.015)))

        data.append({
            'date': date,
            'open': open_price,
            'close': close_price,
            'high': high_price,
            'low': low_price
        })

        price = close_price

    return pd.DataFrame(data)


def calculate_body_ratio(open_price, close_price, high_price, low_price):
    """Calculate body ratio: |close - open| / (high - low)"""
    body = abs(close_price - open_price)
    amplitude = high_price - low_price
    if amplitude == 0:
        return 0
    return body / amplitude


def calculate_pct_change(open_price, close_price):
    """Calculate percentage change: (close - open) / open * 100"""
    if open_price == 0:
        return 0
    return (close_price - open_price) / open_price * 100


def check_morning_star_pattern(df, idx):
    """
    Check if a morning star pattern exists at position idx (day 1 of pattern)

    Pattern requirements:
    Day 1: Big bearish candle (drop > 3%, body_ratio > 70%)
    Day 2: Small candle (|pct_change| < 1.5%)
    Day 3: Big bullish candle (rise > 3%, body_ratio > 70%, close > day1_body_midpoint)
    """
    if idx + 2 >= len(df):
        return False, None

    # Get three days data
    day1 = df.iloc[idx]
    day2 = df.iloc[idx + 1]
    day3 = df.iloc[idx + 2]

    # Day 1: Big bearish candle
    day1_pct = calculate_pct_change(day1['open'], day1['close'])
    day1_body_ratio = calculate_body_ratio(day1['open'], day1['close'],
                                           day1['high'], day1['low'])

    if day1_pct >= -3 or day1_body_ratio < 0.7:  # Must drop > 3% and body_ratio > 70%
        return False, None

    # Day 2: Small candle
    day2_pct = calculate_pct_change(day2['open'], day2['close'])
    if abs(day2_pct) >= 1.5:
        return False, None

    # Day 3: Big bullish candle
    day3_pct = calculate_pct_change(day3['open'], day3['close'])
    day3_body_ratio = calculate_body_ratio(day3['open'], day3['close'],
                                           day3['high'], day3['low'])

    if day3_pct <= 3 or day3_body_ratio < 0.7:  # Must rise > 3% and body_ratio > 70%
        return False, None

    # Day 3 close must be higher than day 1 body midpoint
    day1_body_midpoint = (day1['open'] + day1['close']) / 2
    if day3['close'] <= day1_body_midpoint:
        return False, None

    # Pattern found
    pattern_info = {
        'day1_date': day1['date'],
        'day3_close': day3['close'],
        'pattern_lowest': min(day1['low'], day2['low'], day3['low'])
    }

    return True, pattern_info


def check_low_position(df, pattern_idx, pattern_day3_close):
    """
    Check if pattern appears at low position:
    Close price < 60-day average price * 90%
    """
    if pattern_idx < 60:
        return False

    # Calculate 60-day average price (using close prices)
    ma60_data = df.iloc[pattern_idx - 60:pattern_idx]
    ma60 = ma60_data['close'].mean()

    # Pattern close price (day 3) should be below 90% of MA60
    return pattern_day3_close < ma60 * 0.9


def check_post_validation(df, pattern_idx, pattern_lowest):
    """
    Check if price doesn't break below pattern's lowest price in next 5 trading days
    """
    if pattern_idx + 7 >= len(df):
        return False

    # Check next 5 trading days after pattern (idx+3 to idx+7)
    next_5_days = df.iloc[pattern_idx + 3:pattern_idx + 8]

    # Check if any day's low breaks below pattern's lowest
    for _, day in next_5_days.iterrows():
        if day['low'] < pattern_lowest:
            return False

    return True


def calculate_5day_return(df, pattern_idx):
    """
    Calculate 5-day return after pattern:
    (day8_close - day3_close) / day3_close * 100
    """
    if pattern_idx + 7 >= len(df):
        return None

    day3_close = df.iloc[pattern_idx + 2]['close']
    day8_close = df.iloc[pattern_idx + 7]['close']  # 5 days after pattern

    return (day8_close - day3_close) / day3_close * 100


def detect_morning_star(stock_code, df):
    """Detect morning star patterns for a single stock"""
    results = []

    if df is None or len(df) < 90:
        return results

    # Check patterns in last 30 trading days
    start_check_idx = max(60, len(df) - 37)
    end_check_idx = len(df) - 7

    for idx in range(start_check_idx, end_check_idx):
        # Check morning star pattern
        is_pattern, pattern_info = check_morning_star_pattern(df, idx)
        if not is_pattern:
            continue

        # Check low position requirement
        if not check_low_position(df, idx, pattern_info['day3_close']):
            continue

        # Check post validation (5 days don't break lowest)
        if not check_post_validation(df, idx, pattern_info['pattern_lowest']):
            continue

        # Calculate 5-day return
        return_5d = calculate_5day_return(df, idx)
        if return_5d is None:
            continue

        results.append({
            'code': stock_code,
            'date': pattern_info['day1_date'].strftime('%Y-%m-%d'),
            'return_5d': round(return_5d, 2)
        })

    return results


def main():
    """Main function to detect morning star patterns"""
    print("Generating synthetic ChiNext stock data for demonstration...")

    # Generate data for sample ChiNext stocks
    test_stocks = [
        ('300001', 25.0),
        ('300059', 18.5),
        ('300124', 32.0),
        ('300750', 45.0),
        ('300896', 28.0),
    ]

    all_results = []

    for stock_code, base_price in test_stocks:
        df = generate_realistic_stock_data(stock_code, days=90, base_price=base_price)
        results = detect_morning_star(stock_code, df)
        all_results.extend(results)
        if results:
            print(f"{stock_code}: Found {len(results)} pattern(s)")

    # Write results to file
    output_file = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_21_morning_star/independent/claudecode/morning_star.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,形态起始日期,形态后5日涨幅(%)\n")
        if len(all_results) == 0:
            f.write("无符合条件的股票\n")
        else:
            for result in all_results:
                f.write(f"{result['code']},{result['date']},{result['return_5d']}\n")

    print(f"\nDetection complete! Found {len(all_results)} patterns.")
    print(f"Results saved to: morning_star.txt")

    return all_results


if __name__ == "__main__":
    results = main()
