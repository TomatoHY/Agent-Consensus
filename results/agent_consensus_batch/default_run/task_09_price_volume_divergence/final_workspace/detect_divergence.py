#!/usr/bin/env python3
"""
Price-Volume Divergence Detection for ChiNext (创业板) stocks
Detects stocks with price new high but volume shrinkage in the last 5 trading days
"""

import sys
import os
from pathlib import Path

# Add YFD project to path
yfd_path = Path("/Users/tomato/Documents/potato/project/YFD")
if yfd_path.exists():
    sys.path.insert(0, str(yfd_path))

try:
    import akshare as ak
    import pandas as pd
    from datetime import datetime
    print("Successfully imported akshare")
except ImportError as e:
    print(f"Import error: {e}")
    print("Attempting to install akshare...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "akshare", "-q"])
    import akshare as ak
    import pandas as pd
    from datetime import datetime

def get_chinext_stocks():
    """Get list of ChiNext (创业板) stocks - codes starting with 300/301"""
    try:
        # Get all A-share stocks
        stock_info = ak.stock_info_a_code_name()

        # Filter for ChiNext stocks (300xxx and 301xxx)
        chinext = stock_info[stock_info['code'].str.startswith(('300', '301'))]

        print(f"Found {len(chinext)} ChiNext stocks")
        return chinext['code'].tolist()
    except Exception as e:
        print(f"Error getting stock list: {e}")
        return []

def get_stock_data(stock_code, end_date='2024-11-29'):
    """Get historical K-line data for a stock"""
    try:
        # Get daily K-line data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date="2024-10-01", end_date=end_date,
                                adjust="qfq")

        if df is None or len(df) == 0:
            return None

        # Rename columns to English
        df = df.rename(columns={
            '日期': 'date',
            '最高': 'high',
            '成交量': 'volume'
        })

        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'])

        # Sort by date
        df = df.sort_values('date')

        return df[['date', 'high', 'volume']]
    except Exception as e:
        return None

def check_divergence(df):
    """
    Check if stock meets divergence criteria

    Criteria:
    1. Price new high: last 5 days max high > first 25 days max high
    2. Volume shrinkage: last 5 days avg volume < 80% of first 25 days avg volume

    Returns: (meets_criteria, price_change_pct, volume_change_pct, divergence_pct)
    """
    if df is None or len(df) < 30:
        return False, None, None, None

    # Get last 30 trading days
    df_30 = df.tail(30).copy()

    if len(df_30) < 30:
        return False, None, None, None

    # Split into first 25 days and last 5 days
    first_25 = df_30.iloc[:25]
    last_5 = df_30.iloc[25:]

    # Calculate metrics for first 25 days
    first_25_max_price = first_25['high'].max()
    first_25_avg_volume = first_25['volume'].mean()

    # Calculate metrics for last 5 days
    last_5_max_price = last_5['high'].max()
    last_5_avg_volume = last_5['volume'].mean()

    # Check Condition 1: Price new high (last 5 days max > first 25 days max)
    price_new_high = last_5_max_price > first_25_max_price

    # Check Condition 2: Volume shrinkage (last 5 days avg < 80% of first 25 days avg)
    volume_threshold = first_25_avg_volume * 0.8
    volume_shrinkage = last_5_avg_volume < volume_threshold

    # Calculate the three required metrics
    # 1. Price change percentage (should be positive)
    price_change_pct = (last_5_max_price / first_25_max_price - 1) * 100

    # 2. Volume change percentage (should be negative for shrinkage)
    volume_change_pct = (last_5_avg_volume / first_25_avg_volume - 1) * 100

    # 3. Divergence degree (absolute difference between price change and volume change)
    divergence_pct = price_change_pct - volume_change_pct

    # Both conditions must be met
    meets_criteria = price_new_high and volume_shrinkage

    return meets_criteria, price_change_pct, volume_change_pct, divergence_pct

def main():
    print("=" * 70)
    print("Price-Volume Divergence Detection for ChiNext Stocks")
    print("Target date: 2024-11-29")
    print("=" * 70)

    # Get ChiNext stock list
    stock_list = get_chinext_stocks()

    if not stock_list:
        print("Failed to get stock list")
        return

    results = []
    processed = 0

    print(f"\nProcessing {len(stock_list)} stocks...")

    for stock_code in stock_list:
        processed += 1

        if processed % 100 == 0:
            print(f"Processed {processed}/{len(stock_list)} stocks, found {len(results)} with divergence")

        # Get stock data
        df = get_stock_data(stock_code, end_date='2024-11-29')

        if df is None:
            continue

        # Check divergence
        meets_criteria, price_chg, vol_chg, divergence = check_divergence(df)

        if meets_criteria:
            results.append({
                'code': stock_code,
                'price_change': price_chg,
                'volume_change': vol_chg,
                'divergence': divergence
            })
            print(f"  ✓ {stock_code}: price +{price_chg:.2f}%, volume {vol_chg:.2f}%, divergence {divergence:.2f}%")

    print(f"\n{'=' * 70}")
    print(f"Processing complete: {processed} stocks analyzed")
    print(f"Found {len(results)} stocks with price-volume divergence")

    # Write results to file in the result directory
    output_path = Path(__file__).parent / "divergence.txt"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("股票代码,价格涨幅(%),成交量变化(%),背离度(%)\n")

        if len(results) == 0:
            f.write("# 无符合条件的股票\n")
        else:
            # Sort by divergence degree (descending)
            results.sort(key=lambda x: x['divergence'], reverse=True)

            for r in results:
                f.write(f"{r['code']},{r['price_change']:.2f},{r['volume_change']:.2f},{r['divergence']:.2f}\n")

    print(f"Results written to: {output_path}")
    print(f"{'=' * 70}")

if __name__ == "__main__":
    main()
