#!/usr/bin/env python3
"""
Calculate volatility ranking for ChiNext stocks
"""
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_chinext_stocks():
    """Get all ChiNext (创业板) stock codes"""
    try:
        # Get stock info from akshare
        stock_info = ak.stock_info_a_code_name()
        # Filter for ChiNext stocks (code starts with 300)
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"Error getting stock list: {e}")
        return []

def get_trading_days(end_date, days=10):
    """Get the last N trading days before end_date"""
    try:
        # Get trading calendar
        tool = ak.tool_trade_date_hist_sina()
        tool['trade_date'] = pd.to_datetime(tool['trade_date'])
        
        end = pd.to_datetime(end_date)
        # Filter dates <= end_date
        valid_dates = tool[tool['trade_date'] <= end].sort_values('trade_date', ascending=False)
        
        # Get last N trading days
        trading_days = valid_dates.head(days)['trade_date'].tolist()
        return sorted(trading_days)
    except Exception as e:
        print(f"Error getting trading days: {e}")
        return []

def calculate_volatility(stock_code, end_date='2024-05-31', days=10):
    """Calculate volatility for a stock over the last N trading days"""
    try:
        # Fetch historical data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="qfq")
        df['日期'] = pd.to_datetime(df['日期'])
        
        # Filter data up to end_date
        end = pd.to_datetime(end_date)
        df = df[df['日期'] <= end].sort_values('日期', ascending=False)
        
        # Get last N days
        recent = df.head(days)
        
        if len(recent) < days:
            return None
        
        # Get closing prices
        closes = recent['收盘'].values
        
        # Calculate volatility (coefficient of variation)
        mean_price = np.mean(closes)
        std_price = np.std(closes, ddof=1)
        
        if mean_price == 0:
            return None
        
        volatility = (std_price / mean_price) * 100
        
        return volatility
    except Exception as e:
        print(f"Error calculating volatility for {stock_code}: {e}")
        return None

def main():
    end_date = '2024-05-31'
    days = 10
    
    print(f"Getting ChiNext stock list...")
    stocks = get_chinext_stocks()
    print(f"Found {len(stocks)} ChiNext stocks")
    
    if not stocks:
        print("No stocks found, exiting")
        return
    
    # Calculate volatility for each stock
    results = []
    total = len(stocks)
    
    for i, code in enumerate(stocks, 1):
        if i % 50 == 0:
            print(f"Processing {i}/{total}...")
        
        vol = calculate_volatility(code, end_date, days)
        if vol is not None:
            results.append({
                'code': code,
                'volatility': vol
            })
    
    print(f"\nSuccessfully calculated volatility for {len(results)} stocks")
    
    # Sort by volatility descending
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('volatility', ascending=False)
    
    # Get top 5
    top5 = results_df.head(5)
    
    print("\nTop 5 stocks by volatility:")
    print(top5)
    
    # Write to file
    output_file = 'volatility_top5.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,波动率(%)\n')
        for _, row in top5.iterrows():
            f.write(f"{row['code']},{row['volatility']:.2f}\n")
    
    print(f"\nResults written to {output_file}")

if __name__ == '__main__':
    main()
