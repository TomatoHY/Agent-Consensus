#!/usr/bin/env python3
"""
Price-Volume Divergence Detection for ChiNext Stocks using Tushare
Detects stocks where price hits new high but volume shrinks
"""

import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time

def get_chinext_stocks():
    """Get ChiNext (创业板) stock list - codes starting with 300"""
    try:
        pro = ts.pro_api()
        # Get all stocks
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
        # Filter ChiNext stocks (code starts with 300)
        chinext = df[df['symbol'].str.startswith('300')]
        return chinext['ts_code'].tolist()
    except Exception as e:
        print(f"Error getting stock list: {e}")
        # Fallback: generate common ChiNext codes
        codes = []
        for i in range(1, 1000):
            codes.append(f"300{i:03d}.SZ")
        return codes

def get_stock_data(pro, ts_code, end_date, days=50):
    """Get historical K-line data for a stock"""
    try:
        # Calculate start date
        start_date = (end_date - timedelta(days=days*2)).strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')

        # Get daily data
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date_str)

        if df is None or len(df) == 0:
            return None

        # Sort by date
        df = df.sort_values('trade_date')

        # Select needed columns: trade_date, high, vol
        df = df[['trade_date', 'high', 'vol']].copy()

        return df
    except Exception as e:
        print(f"Error getting data for {ts_code}: {e}")
        return None

def check_divergence(df):
    """
    Check if stock meets divergence criteria
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

    # Calculate metrics
    first_25_max_price = first_25['high'].max()
    last_5_max_price = last_5['high'].max()

    first_25_avg_volume = first_25['vol'].mean()
    last_5_avg_volume = last_5['vol'].mean()

    # Check conditions
    # Condition 1: Price new high (last 5 days max > first 25 days max)
    price_new_high = last_5_max_price > first_25_max_price

    # Condition 2: Volume shrinkage (last 5 days avg < 80% of first 25 days avg)
    volume_shrinkage = last_5_avg_volume < (first_25_avg_volume * 0.8)

    # Calculate metrics
    price_change_pct = (last_5_max_price / first_25_max_price - 1) * 100
    volume_change_pct = (last_5_avg_volume / first_25_avg_volume - 1) * 100
    divergence_pct = price_change_pct - volume_change_pct

    meets_criteria = price_new_high and volume_shrinkage

    return meets_criteria, price_change_pct, volume_change_pct, divergence_pct

def main():
    # Set end date
    end_date = datetime(2024, 11, 29)

    print(f"Detecting price-volume divergence as of {end_date.date()}")
    print("Initializing Tushare...")

    try:
        pro = ts.pro_api()
    except Exception as e:
        print(f"Error initializing Tushare: {e}")
        print("Please set TUSHARE_TOKEN environment variable or configure tushare token")
        # Create empty result file
        output_path = Path(__file__).parent / "divergence.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("股票代码,价格涨幅(%),成交量变化(%),背离度(%)\n")
            f.write("# 无法连接数据源\n")
        return

    print("Getting ChiNext stock list...")

    # Get ChiNext stocks
    chinext_stocks = get_chinext_stocks()
    print(f"Found {len(chinext_stocks)} ChiNext stocks")

    # Results list
    results = []

    # Check each stock
    for i, ts_code in enumerate(chinext_stocks, 1):
        if i % 50 == 0:
            print(f"Processing {i}/{len(chinext_stocks)}...")

        # Get stock data
        df = get_stock_data(pro, ts_code, end_date)

        # Rate limiting
        time.sleep(0.1)

        # Check divergence
        meets_criteria, price_chg, vol_chg, divergence = check_divergence(df)

        if meets_criteria:
            # Convert ts_code to simple code (remove .SZ suffix)
            simple_code = ts_code.split('.')[0]
            results.append({
                'code': simple_code,
                'price_change': price_chg,
                'volume_change': vol_chg,
                'divergence': divergence
            })
            print(f"Found: {simple_code} - Price: {price_chg:.2f}%, Volume: {vol_chg:.2f}%, Divergence: {divergence:.2f}%")

    # Write results
    output_path = Path(__file__).parent / "divergence.txt"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("股票代码,价格涨幅(%),成交量变化(%),背离度(%)\n")

        if len(results) == 0:
            f.write("# 无符合条件的股票\n")
        else:
            # Sort by divergence (descending)
            results.sort(key=lambda x: x['divergence'], reverse=True)

            for r in results:
                f.write(f"{r['code']},{r['price_change']:.2f},{r['volume_change']:.2f},{r['divergence']:.2f}\n")

    print(f"\nResults written to {output_path}")
    print(f"Total stocks with divergence: {len(results)}")

if __name__ == "__main__":
    main()
