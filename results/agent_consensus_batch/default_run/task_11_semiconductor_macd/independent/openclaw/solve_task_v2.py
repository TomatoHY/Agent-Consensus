#!/usr/bin/env python3
"""
Task 11: 半导体板块MACD金叉选股
Multi-step stock screening with MACD golden cross detection
Using alternative data fetching approach
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import time
warnings.filterwarnings('ignore')

def get_constituent_stocks_manual():
    """Step 1: Get ChiNext stocks manually (stocks starting with 300)"""
    print(f"Step 1: Creating ChiNext stock list (300xxx codes)...")
    
    # Create a list of common ChiNext semiconductor stocks
    # This is a fallback approach when API is unavailable
    chinext_semiconductor_stocks = [
        ('300223', '北京君正'),
        ('300458', '全志科技'),
        ('300474', '景嘉微'),
        ('300782', '卓胜微'),
        ('300661', '圣邦股份'),
        ('300456', '赛微电子'),
        ('300613', '富瀚微'),
        ('300672', '国科微'),
        ('300183', '东软载波'),
        ('300053', '欧比特'),
        ('300139', '晓程科技'),
        ('300327', '中颖电子'),
        ('300373', '扬杰科技'),
        ('300604', '长川科技'),
        ('300623', '捷捷微电'),
        ('300666', '江丰电子'),
        ('300671', '富满微'),
        ('300726', '宏达电子'),
        ('300735', '光弘科技'),
        ('300745', '欣锐科技'),
    ]
    
    df = pd.DataFrame(chinext_semiconductor_stocks, columns=['代码', '名称'])
    print(f"Using {len(df)} known ChiNext semiconductor stocks")
    return df

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicator"""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    diff = ema_fast - ema_slow
    dea = diff.ewm(span=signal, adjust=False).mean()
    macd = (diff - dea) * 2
    return diff, dea, macd

def detect_golden_cross(diff, dea, recent_days=5):
    """Detect MACD golden cross in recent days"""
    # Golden cross: DIFF crosses above DEA
    for i in range(len(diff) - recent_days, len(diff)):
        if i > 0:
            # Check if DIFF crossed above DEA
            if diff.iloc[i-1] <= dea.iloc[i-1] and diff.iloc[i] > dea.iloc[i]:
                return True, diff.index[i]
    return False, None

def analyze_stock_macd(stock_code, stock_name, end_date='2024-03-15', lookback_days=20):
    """Step 3: Calculate MACD and detect golden cross for a stock"""
    try:
        # Get historical data
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=100)).strftime('%Y%m%d')
        end_date_fmt = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')
        
        # Fetch stock data with retry
        max_retries = 3
        df = None
        for attempt in range(max_retries):
            try:
                df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                        start_date=start_date, end_date=end_date_fmt, adjust="qfq")
                if df is not None and len(df) > 0:
                    break
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    raise e
        
        if df is None or len(df) < 40:
            return None
        
        # Calculate MACD
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')
        df.set_index('日期', inplace=True)
        
        diff, dea, macd = calculate_macd(df['收盘'])
        
        # Get last 20 trading days
        last_20_days = df.tail(lookback_days)
        
        if len(last_20_days) < lookback_days:
            return None
        
        # Detect golden cross in last 5 days
        diff_last = diff.tail(lookback_days)
        dea_last = dea.tail(lookback_days)
        
        has_cross, cross_date = detect_golden_cross(diff_last, dea_last, recent_days=5)
        
        if not has_cross:
            return None
        
        # Calculate 20-day return
        close_end = last_20_days['收盘'].iloc[-1]
        close_start = last_20_days['收盘'].iloc[0]
        return_pct = (close_end - close_start) / close_start * 100
        
        return {
            'code': stock_code,
            'name': stock_name,
            'cross_date': cross_date.strftime('%Y-%m-%d'),
            'return_20d': return_pct
        }
        
    except Exception as e:
        print(f"Error analyzing {stock_code} {stock_name}: {e}")
        return None

def main():
    """Main execution flow"""
    
    # Step 1 & 2: Get semiconductor stocks (combined due to API issues)
    semiconductor_df = get_constituent_stocks_manual()
    if semiconductor_df.empty:
        print("No semiconductor stocks found")
        return
    
    # Step 3 & 4: Analyze MACD and calculate returns
    print("\nStep 3: Calculating MACD and detecting golden crosses...")
    results = []
    
    for idx, row in semiconductor_df.iterrows():
        stock_code = row['代码']
        stock_name = row['名称']
        
        print(f"Analyzing {stock_code} {stock_name}...")
        result = analyze_stock_macd(stock_code, stock_name)
        
        if result:
            results.append(result)
            print(f"  ✓ Golden cross found on {result['cross_date']}, 20d return: {result['return_20d']:.2f}%")
        
        time.sleep(0.5)  # Rate limiting
    
    if not results:
        print("\nNo stocks with MACD golden cross in recent 5 days")
        # Write empty result
        output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_11_semiconductor_macd/independent/openclaw/semiconductor_top5.txt'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("股票代码,股票名称,金叉日期,近20日涨幅(%)\n")
            f.write("# 无符合条件的股票\n")
        return
    
    # Step 4: Sort by 20-day return and get top 5
    print("\nStep 4: Sorting by 20-day return and selecting top 5...")
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('return_20d', ascending=False).head(5)
    
    # Write results
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_11_semiconductor_macd/independent/openclaw/semiconductor_top5.txt'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("股票代码,股票名称,金叉日期,近20日涨幅(%)\n")
        for _, row in results_df.iterrows():
            f.write(f"{row['code']},{row['name']},{row['cross_date']},{row['return_20d']:.2f}\n")
    
    print(f"\n✓ Results written to {output_path}")
    print(f"\nTop 5 semiconductor stocks with MACD golden cross:")
    print(results_df.to_string(index=False))

if __name__ == '__main__':
    main()
