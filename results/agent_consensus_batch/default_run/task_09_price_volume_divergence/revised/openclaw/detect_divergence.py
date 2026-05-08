#!/usr/bin/env python3
"""
Price-Volume Divergence Detection for ChiNext (创业板)
Detects stocks where price hits new high but volume shrinks
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def get_chinext_stocks():
    """Get ChiNext stock list (codes starting with 300 or 301)"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith(('300', '301'))]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"Error getting stock list: {e}")
        return []

def get_trading_days(end_date, days=40):
    """Get trading days before end_date"""
    try:
        # Get more days to ensure we have enough trading days
        start = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days*2)).strftime('%Y-%m-%d')
        trade_dates = ak.tool_trade_date_hist_sina()
        trade_dates['trade_date'] = pd.to_datetime(trade_dates['trade_date'])
        
        valid_dates = trade_dates[
            (trade_dates['trade_date'] <= end_date) & 
            (trade_dates['trade_date'] >= start)
        ].sort_values('trade_date', ascending=False)
        
        return valid_dates['trade_date'].dt.strftime('%Y%m%d').tolist()[:days]
    except:
        return []

def check_divergence(code, end_date='2024-11-29'):
    """
    Check if a stock shows price-volume divergence
    Returns: (is_divergent, price_change%, volume_change%, divergence%)
    """
    try:
        # Get daily data
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        if df is None or len(df) < 30:
            return None
        
        df['日期'] = pd.to_datetime(df['日期'])
        df = df[df['日期'] <= end_date].sort_values('日期', ascending=False)
        
        if len(df) < 30:
            return None
        
        # Split into last 5 days and first 25 days
        last_5 = df.iloc[:5]
        first_25 = df.iloc[5:30]
        
        # Calculate metrics
        last_5_high = last_5['最高'].max()
        first_25_high = first_25['最高'].max()
        
        last_5_vol = last_5['成交量'].mean()
        first_25_vol = first_25['成交量'].mean()
        
        # Check conditions
        price_new_high = last_5_high > first_25_high
        volume_shrink = last_5_vol < first_25_vol * 0.8
        
        if price_new_high and volume_shrink:
            price_change = (last_5_high / first_25_high - 1) * 100
            volume_change = (last_5_vol / first_25_vol - 1) * 100
            divergence = price_change - volume_change
            
            return (True, price_change, volume_change, divergence)
        
        return None
        
    except Exception as e:
        return None

def main():
    print("Starting price-volume divergence detection...")
    
    # Get ChiNext stocks
    stocks = get_chinext_stocks()
    print(f"Found {len(stocks)} ChiNext stocks")
    
    results = []
    
    # Check each stock
    for i, code in enumerate(stocks):
        if i % 50 == 0:
            print(f"Progress: {i}/{len(stocks)}")
        
        result = check_divergence(code)
        if result:
            is_div, price_chg, vol_chg, div = result
            results.append({
                'code': code,
                'price_change': price_chg,
                'volume_change': vol_chg,
                'divergence': div
            })
    
    print(f"\nFound {len(results)} stocks with divergence")
    
    # Write results
    with open('divergence.txt', 'w', encoding='utf-8') as f:
        f.write('股票代码,价格涨幅(%),成交量变化(%),背离度(%)\n')
        for r in results:
            f.write(f"{r['code']},{r['price_change']:.2f},{r['volume_change']:.2f},{r['divergence']:.2f}\n")
    
    print("Results written to divergence.txt")

if __name__ == '__main__':
    main()
