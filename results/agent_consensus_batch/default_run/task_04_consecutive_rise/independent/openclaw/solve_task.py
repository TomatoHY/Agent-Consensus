#!/usr/bin/env python3
"""
Task 04: 连续稳健上涨股票识别
Find ChiNext stocks with 5 consecutive rising days (2%-7% daily gain) ending 2024-06-28
"""

from mootdx.quotes import Quotes
import pandas as pd
from datetime import datetime

def main():
    client = Quotes.factory(market='std')
    
    # Get ChiNext stock list (300xxx and 301xxx)
    print("Fetching ChiNext stock list...")
    stocks = client.stocks(market=0)  # Shenzhen market
    gem = stocks[stocks['code'].str.startswith(('300', '301'))].copy()
    print(f"Total ChiNext stocks: {len(gem)}")
    
    target_date = '2024-06-28'
    results = []
    
    # Need 6 trading days (5 days + 1 previous day for baseline)
    for idx, row in gem.iterrows():
        code = row['code']
        
        try:
            # Fetch recent daily K-lines (get more to ensure we have enough)
            df = client.bars(symbol=code, frequency=9, start=0, offset=20)
            
            if df is None or len(df) < 6:
                continue
            
            # Sort by date ascending
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # Find the target date
            df['date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
            
            if target_date not in df['date'].values:
                continue
            
            # Get index of target date
            target_idx = df[df['date'] == target_date].index[0]
            
            # Need 5 days before target (indices: target_idx-5 to target_idx-1)
            # Plus one more day before that for baseline (target_idx-6)
            if target_idx < 5:
                continue
            
            # Extract the 6-day window (day 0 = baseline, days 1-5 = the 5 consecutive days)
            window = df.iloc[target_idx-5:target_idx+1].copy()
            
            if len(window) != 6:
                continue
            
            # Calculate daily returns
            window['prev_close'] = window['close'].shift(1)
            window['daily_return'] = (window['close'] - window['prev_close']) / window['prev_close'] * 100
            
            # Check the 5 days (indices 1-5 in window)
            five_days = window.iloc[1:].copy()
            
            # Check conditions:
            # 1) All 5 days have positive returns (close > prev_close)
            # 2) All daily returns are between 2% and 7%
            if len(five_days) != 5:
                continue
            
            # Check consecutive rising
            if not all(five_days['close'] > five_days['prev_close']):
                continue
            
            # Check daily return range [2%, 7%]
            daily_returns = five_days['daily_return'].values
            if not all((daily_returns >= 2.0) & (daily_returns <= 7.0)):
                continue
            
            # Calculate 5-day cumulative return
            # (day5_close / day0_close - 1) * 100
            day0_close = window.iloc[0]['close']
            day5_close = window.iloc[5]['close']
            cumulative_return = (day5_close / day0_close - 1) * 100
            
            results.append({
                'code': code,
                'cumulative_return': cumulative_return
            })
            
            print(f"✓ {code}: 5-day cumulative return = {cumulative_return:.2f}%")
            
        except Exception as e:
            # Skip stocks with data issues
            continue
    
    # Write results
    output_file = 'steady_rise.txt'
    
    if len(results) == 0:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        print(f"\n无符合条件的股票")
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("股票代码,5日累计涨幅(%)\n")
            for r in results:
                f.write(f"{r['code']},{r['cumulative_return']:.2f}\n")
        print(f"\n找到 {len(results)} 只符合条件的股票，已写入 {output_file}")
    
    print(f"\nTask completed. Output: {output_file}")

if __name__ == '__main__':
    main()
