#!/usr/bin/env python3
"""
Find ChiNext stocks with 5 consecutive days of steady rise (2%-7% daily)
Ending date: 2024-06-28
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def get_chinext_stocks():
    """Get all ChiNext stock codes (starting with 300)"""
    try:
        # Get all A-share stocks
        stock_info = ak.stock_info_a_code_name()
        # Filter ChiNext stocks (code starts with 300)
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"Error getting stock list: {e}")
        return []

def get_stock_data(stock_code, end_date, days=6):
    """Get historical data for a stock"""
    try:
        # Get daily data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="qfq")
        if df is None or df.empty:
            return None

        # Convert date column
        df['日期'] = pd.to_datetime(df['日期'])

        # Filter data up to end_date
        df = df[df['日期'] <= end_date].tail(days)

        if len(df) < days:
            return None

        return df
    except Exception as e:
        return None

def check_steady_rise(df):
    """
    Check if stock meets criteria:
    - 5 consecutive days of rising close prices
    - Each day's gain is between 2% and 7%
    """
    if df is None or len(df) < 6:
        return False, 0.0

    # Get close prices
    closes = df['收盘'].values

    # Check 5 consecutive days (indices 1-5, comparing to 0-4)
    for i in range(1, 6):
        # Check if price increased
        if closes[i] <= closes[i-1]:
            return False, 0.0

        # Calculate daily gain percentage
        daily_gain = (closes[i] - closes[i-1]) / closes[i-1] * 100

        # Check if gain is in 2%-7% range
        if daily_gain < 2.0 or daily_gain > 7.0:
            return False, 0.0

    # Calculate 5-day cumulative gain
    cumulative_gain = (closes[5] - closes[0]) / closes[0] * 100

    return True, cumulative_gain

def main():
    end_date = datetime(2024, 6, 28)

    print("Getting ChiNext stock list...")
    chinext_stocks = get_chinext_stocks()
    print(f"Found {len(chinext_stocks)} ChiNext stocks")

    qualifying_stocks = []

    print("Analyzing stocks...")
    for i, stock_code in enumerate(chinext_stocks):
        if (i + 1) % 50 == 0:
            print(f"Processed {i + 1}/{len(chinext_stocks)} stocks...")

        df = get_stock_data(stock_code, end_date, days=6)
        is_qualified, cumulative_gain = check_steady_rise(df)

        if is_qualified:
            qualifying_stocks.append((stock_code, cumulative_gain))
            print(f"Found: {stock_code}, cumulative gain: {cumulative_gain:.2f}%")

    # Write results
    output_file = "steady_rise.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        if qualifying_stocks:
            f.write("股票代码,5日累计涨幅(%)\n")
            for code, gain in qualifying_stocks:
                f.write(f"{code},{gain:.2f}\n")
            print(f"\nFound {len(qualifying_stocks)} qualifying stocks")
        else:
            f.write("无符合条件的股票\n")
            print("\nNo qualifying stocks found")

    print(f"Results written to {output_file}")

if __name__ == "__main__":
    main()
