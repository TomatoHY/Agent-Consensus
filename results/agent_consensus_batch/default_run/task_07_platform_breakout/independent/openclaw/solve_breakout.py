#!/usr/bin/env python3
"""
Task 07: Platform Breakout Pattern Recognition
Find ChiNext stocks that broke out of a price platform by 2024-09-30.

Conditions:
1) First 10 days: price in narrow range (high-low < 5% of low)
2) Last 5 days: at least 3 days close above the first 10 days' highest price
3) Breakout day volume > 1.5x average volume of first 10 days
"""

import pandas as pd
import numpy as np
from mootdx.quotes import Quotes
from datetime import datetime

def main():
    print("=== Task 07: Platform Breakout Pattern Recognition ===")
    print("Target date: 2024-09-30")
    print("Analysis window: 15 trading days before 2024-09-30\n")
    
    # Initialize mootdx client
    client = Quotes.factory(market='std')
    
    # Get ChiNext stock list (codes starting with 300 or 301)
    print("Fetching ChiNext stock list...")
    stocks = client.stocks(market=0)  # Shenzhen market
    gem_stocks = stocks[stocks['code'].str.startswith(('300', '301'))].copy()
    print(f"Total ChiNext stocks: {len(gem_stocks)}\n")
    
    breakout_stocks = []
    
    # Process each stock
    for idx, row in gem_stocks.iterrows():
        code = row['code']
        name = row['name']
        
        # Skip ST stocks
        if 'ST' in name or '*ST' in name:
            continue
        
        try:
            # Fetch 30 bars to ensure we have enough data including 2024-09-30
            # offset=30 means fetch 30 most recent bars
            df = client.bars(symbol=code, frequency=9, start=0, offset=30)
            
            if df is None or len(df) < 15:
                continue
            
            # Sort by date ascending
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # Find the index of 2024-09-30 or the closest date before it
            df['date'] = pd.to_datetime(df['datetime']).dt.date
            target_date = pd.to_datetime('2024-09-30').date()
            
            # Filter to dates <= 2024-09-30
            df = df[df['date'] <= target_date].copy()
            
            if len(df) < 15:
                continue
            
            # Take the last 15 trading days
            df_15 = df.tail(15).reset_index(drop=True)
            
            # Split into first 10 days and last 5 days
            first_10 = df_15.iloc[:10].copy()
            last_5 = df_15.iloc[10:].copy()
            
            # Condition 1: Check narrow range in first 10 days
            # range = (max_high - min_low) / min_low < 5%
            max_high_10 = first_10['high'].max()
            min_low_10 = first_10['low'].min()
            price_range = (max_high_10 - min_low_10) / min_low_10
            
            if price_range >= 0.05:  # Not narrow enough
                continue
            
            # Condition 2: At least 3 days in last 5 days close above first 10 days' highest price
            # Use the highest close price in first 10 days as breakout threshold
            highest_close_10 = first_10['close'].max()
            
            # Count how many days in last 5 days closed above this threshold
            breakout_days = (last_5['close'] > highest_close_10).sum()
            
            if breakout_days < 3:
                continue
            
            # Condition 3: Breakout day volume > 1.5x average volume of first 10 days
            avg_volume_10 = first_10['vol'].mean()
            
            # Check if any of the breakout days has volume > 1.5x average
            breakout_mask = last_5['close'] > highest_close_10
            breakout_volumes = last_5.loc[breakout_mask, 'vol']
            
            if len(breakout_volumes) == 0 or breakout_volumes.max() < avg_volume_10 * 1.5:
                continue
            
            # All conditions met!
            breakout_stocks.append({
                'code': code,
                'name': name,
                'range': price_range,
                'breakout_days': breakout_days,
                'max_breakout_volume_ratio': breakout_volumes.max() / avg_volume_10
            })
            
            print(f"✓ {code} {name}: range={price_range:.2%}, breakout_days={breakout_days}, "
                  f"vol_ratio={breakout_volumes.max() / avg_volume_10:.2f}x")
        
        except Exception as e:
            # Skip stocks with data issues
            continue
    
    # Write results
    output_file = 'breakout.txt'
    print(f"\n=== Results ===")
    print(f"Found {len(breakout_stocks)} stocks with platform breakout pattern")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        if len(breakout_stocks) == 0:
            f.write("无符合条件的股票\n")
            print("无符合条件的股票")
        else:
            for stock in breakout_stocks:
                f.write(f"{stock['code']}\n")
            print(f"\nWritten to {output_file}:")
            for stock in breakout_stocks:
                print(f"  {stock['code']} {stock['name']}")
    
    print(f"\nOutput file: {output_file}")

if __name__ == '__main__':
    main()
