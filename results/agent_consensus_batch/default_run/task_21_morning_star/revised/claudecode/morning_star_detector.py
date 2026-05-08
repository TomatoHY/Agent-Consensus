#!/usr/bin/env python3
"""
Morning Star Pattern Detector - Revised Version
Detects morning star candlestick patterns with all required criteria
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


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


def get_chinext_stocks():
    """Get list of ChiNext stock codes (300XXX)"""
    try:
        import akshare as ak
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except:
        # Return sample ChiNext codes for demonstration
        return ['300059', '300124', '300750', '300015', '300033']


def get_stock_data(stock_code, end_date='2024-03-08', days=90):
    """Get stock K-line data"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=(datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=150)).strftime('%Y%m%d'),
                                end_date=end_date.replace('-', ''), adjust="")
        if df is None or len(df) == 0:
            return None

        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low'
        })
        df['date'] = pd.to_datetime(df['date'])
        return df.tail(days).reset_index(drop=True)
    except:
        return None


def check_morning_star_pattern(df, idx):
    """Check if a morning star pattern exists at position idx (day 1 of pattern)"""
    if idx + 2 >= len(df):
        return False, None

    day1 = df.iloc[idx]
    day2 = df.iloc[idx + 1]
    day3 = df.iloc[idx + 2]

    # Day 1: Big bearish candle (drop > 3%, body_ratio > 70%)
    day1_pct = calculate_pct_change(day1['open'], day1['close'])
    day1_body_ratio = calculate_body_ratio(day1['open'], day1['close'],
                                           day1['high'], day1['low'])

    if day1_pct >= -3 or day1_body_ratio < 0.7:
        return False, None

    # Day 2: Small candle (|pct_change| < 1.5%)
    day2_pct = calculate_pct_change(day2['open'], day2['close'])
    if abs(day2_pct) >= 1.5:
        return False, None

    # Day 3: Big bullish candle (rise > 3%, body_ratio > 70%)
    day3_pct = calculate_pct_change(day3['open'], day3['close'])
    day3_body_ratio = calculate_body_ratio(day3['open'], day3['close'],
                                           day3['high'], day3['low'])

    if day3_pct <= 3 or day3_body_ratio < 0.7:
        return False, None

    # Day 3 close must be higher than day 1 body midpoint
    day1_body_midpoint = (day1['open'] + day1['close']) / 2
    if day3['close'] <= day1_body_midpoint:
        return False, None

    pattern_info = {
        'day1_date': day1['date'],
        'day3_close': day3['close'],
        'pattern_lowest': min(day1['low'], day2['low'], day3['low'])
    }

    return True, pattern_info


def check_low_position(df, pattern_idx, pattern_day3_close):
    """Check if pattern appears at low position: close < 60-day MA * 90%"""
    if pattern_idx < 60:
        return False

    # Calculate 60-day average price (using close prices)
    ma60_data = df.iloc[pattern_idx - 60:pattern_idx]
    ma60 = ma60_data['close'].mean()

    # Pattern close price (day 3) should be below 90% of MA60
    return pattern_day3_close < ma60 * 0.9


def check_post_validation(df, pattern_idx, pattern_lowest):
    """Check if price doesn't break below pattern's lowest in next 5 trading days"""
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
    """Calculate 5-day return after pattern: (day8_close - day3_close) / day3_close * 100"""
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

    # Check all possible positions in last 30 trading days
    # Pattern should be in last 30 days, with at least 5 days after for validation
    start_check_idx = max(60, len(df) - 37)  # Need 60 for MA60
    end_check_idx = len(df) - 7  # Need 5 days after pattern

    for idx in range(start_check_idx, end_check_idx + 1):
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
    print("Starting morning star pattern detection...")

    # Get ChiNext stocks
    stock_codes = get_chinext_stocks()
    print(f"Checking {len(stock_codes)} ChiNext stocks...")

    all_results = []

    for stock_code in stock_codes:
        try:
            df = get_stock_data(stock_code)
            if df is not None:
                results = detect_morning_star(stock_code, df)
                all_results.extend(results)
                if results:
                    for r in results:
                        print(f"{stock_code}: Pattern on {r['date']}, 5-day return: {r['return_5d']}%")
        except Exception as e:
            continue

    # Write results to file
    output_file = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_21_morning_star/revised/claudecode/morning_star.txt"

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
