#!/usr/bin/env python3
"""
Morning Star Pattern Detector for ChiNext Stocks
Detects morning star candlestick patterns with specific criteria
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


def get_chinext_stocks():
    """Get all ChiNext (创业板) stock codes starting with 300"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except:
        # Fallback: generate common ChiNext codes
        return [f"300{str(i).zfill(3)}" for i in range(1, 1000)]


def get_stock_data(stock_code, end_date):
    """Get stock K-line data for 90 trading days before end_date"""
    try:
        # Get historical data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                 start_date="20231201", end_date=end_date, adjust="qfq")
        if df is None or len(df) == 0:
            return None

        # Rename columns to English
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '涨跌幅': 'pct_change'
        })

        # Keep only needed columns
        df = df[['date', 'open', 'close', 'high', 'low']]
        df['date'] = pd.to_datetime(df['date'])

        # Sort by date
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
        'day1_low': day1['low'],
        'day2_low': day2['low'],
        'day3_low': day3['low'],
        'day3_close': day3['close'],
        'pattern_lowest': min(day1['low'], day2['low'], day3['low'])
    }

    return True, pattern_info


def check_low_position(df, pattern_idx, pattern_day3_close):
    """
    Check if pattern appears at low position:
    Close price < 60-day average price * 90%
    """
    # Need at least 60 days before pattern for MA60
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
    # Need 5 days after pattern (pattern ends at idx+2, so need idx+2+5 = idx+7)
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


def detect_morning_star(stock_code, end_date):
    """Detect morning star patterns for a single stock"""
    results = []

    # Get stock data
    df = get_stock_data(stock_code, end_date)
    if df is None or len(df) < 90:
        return results

    # Get last 30 trading days (need to check patterns within this window)
    # But we need 90 days total for MA60 calculation
    if len(df) < 90:
        return results

    # The pattern should appear in the last 30 trading days
    # So we check from position (len-30-7) to (len-7) to ensure we have 5 days after for validation
    start_check_idx = max(60, len(df) - 37)  # At least 60 for MA60
    end_check_idx = len(df) - 7  # Need 5 days after pattern

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
    end_date = "20240308"

    print("Getting ChiNext stock list...")
    stock_codes = get_chinext_stocks()
    print(f"Found {len(stock_codes)} ChiNext stocks")

    all_results = []
    total_to_check = min(500, len(stock_codes))  # Check more stocks

    print("Detecting morning star patterns...")
    for i, stock_code in enumerate(stock_codes[:total_to_check], 1):
        if i % 50 == 0:
            print(f"Processing {i}/{total_to_check}... Found {len(all_results)} patterns so far")

        results = detect_morning_star(stock_code, end_date)
        all_results.extend(results)

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


if __name__ == "__main__":
    main()
