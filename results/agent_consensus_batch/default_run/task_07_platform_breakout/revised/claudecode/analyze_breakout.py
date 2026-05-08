#!/usr/bin/env python3
"""
Platform Breakout Pattern Detection for ChiNext Stocks
Finds stocks that broke out of a narrow trading range with volume confirmation
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def get_chinext_stocks():
    """Get list of ChiNext (创业板) stock codes"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('3')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"Error getting ChiNext stocks: {e}")
        return []

def get_stock_data(code, end_date, days=15):
    """Get historical K-line data for a stock"""
    try:
        # Calculate start date (need more days to ensure we get 15 trading days)
        start_date = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=30)).strftime('%Y%m%d')

        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                start_date=start_date, end_date=end_date, adjust="")

        if df is None or len(df) < days:
            return None

        # Get the last 15 trading days
        df = df.tail(days).reset_index(drop=True)

        if len(df) < days:
            return None

        return df
    except Exception as e:
        return None

def check_breakout_pattern(df):
    """
    Check if stock meets platform breakout criteria:
    1. First 10 days: narrow range (high-low < 5% of low)
    2. Last 5 days: at least 3 days close above first 10 days' high
    3. Breakout day volume > 1.5x average volume of first 10 days
    """
    if len(df) < 15:
        return False

    # Split into first 10 days and last 5 days
    first_10 = df.iloc[:10]
    last_5 = df.iloc[10:]

    # Condition 1: Check narrow range in first 10 days
    max_high = first_10['最高'].max()
    min_low = first_10['最低'].min()
    price_range = (max_high - min_low) / min_low

    if price_range >= 0.05:  # Must be < 5%
        return False

    # Condition 2: At least 3 of last 5 days close above first 10 days' high
    max_high_first_10 = first_10['最高'].max()
    breakout_days = (last_5['收盘'] > max_high_first_10).sum()

    if breakout_days < 3:
        return False

    # Condition 3: At least one breakout day has volume > 1.5x avg volume of first 10 days
    avg_volume_first_10 = first_10['成交量'].mean()
    threshold_volume = avg_volume_first_10 * 1.5

    # Check if any of the breakout days has sufficient volume
    breakout_mask = last_5['收盘'] > max_high_first_10
    breakout_volumes = last_5[breakout_mask]['成交量']

    if len(breakout_volumes) == 0 or breakout_volumes.max() < threshold_volume:
        return False

    return True

def main():
    """Main function to find platform breakout stocks"""
    end_date = "20240930"  # 2024-09-30

    print(f"Analyzing ChiNext stocks for platform breakout pattern...")
    print(f"End date: {end_date}")
    print(f"Criteria:")
    print(f"  1. First 10 days: price range < 5%")
    print(f"  2. Last 5 days: ≥3 days close above first 10 days' high")
    print(f"  3. Breakout day volume > 1.5x first 10 days' avg volume")
    print()

    # Get ChiNext stock list
    chinext_stocks = get_chinext_stocks()
    print(f"Found {len(chinext_stocks)} ChiNext stocks")

    breakout_stocks = []

    # Analyze each stock
    for i, code in enumerate(chinext_stocks):
        if (i + 1) % 100 == 0:
            print(f"Progress: {i+1}/{len(chinext_stocks)} stocks analyzed...")

        df = get_stock_data(code, end_date, days=15)

        if df is None:
            continue

        if check_breakout_pattern(df):
            breakout_stocks.append(code)
            print(f"Found breakout: {code}")

    # Write results
    with open('breakout.txt', 'w', encoding='utf-8') as f:
        if breakout_stocks:
            for code in breakout_stocks:
                f.write(f"{code}\n")
            print(f"\nFound {len(breakout_stocks)} stocks with platform breakout pattern")
        else:
            f.write("无符合条件的股票\n")
            print("\nNo stocks found matching the platform breakout criteria")

    print(f"Results written to breakout.txt")

if __name__ == "__main__":
    main()
