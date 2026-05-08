#!/usr/bin/env python3
"""
Task 11: 半导体板块MACD金叉选股
Multi-step stock screening with MACD golden cross detection
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_constituent_stocks(index_code='399006'):
    """Step 1: Get constituent stocks of ChiNext Index (399006)"""
    print(f"Step 1: Fetching constituent stocks for index {index_code}...")
    try:
        # Try different methods to get ChiNext constituent stocks
        try:
            # Method 1: Try index_stock_cons
            df = ak.index_stock_cons(symbol=index_code)
            print(f"Found {len(df)} constituent stocks")
            return df
        except:
            pass
        
        try:
            # Method 2: Try stock_board_concept_cons_em for ChiNext
            df = ak.stock_board_concept_cons_em(symbol="创业板")
            print(f"Found {len(df)} constituent stocks")
            return df
        except:
            pass
        
        try:
            # Method 3: Get all ChiNext stocks (code starts with 300)
            df = ak.stock_zh_a_spot_em()
            df = df[df['代码'].str.startswith('300')].copy()
            df = df.rename(columns={'代码': '成分券代码', '名称': '成分券名称'})
            print(f"Found {len(df)} ChiNext stocks")
            return df
        except:
            pass
            
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching constituents: {e}")
        return pd.DataFrame()

def filter_semiconductor_stocks(constituent_df):
    """Step 2: Filter semiconductor/chip related stocks"""
    print("\nStep 2: Filtering semiconductor/chip related stocks...")
    
    # Keywords for semiconductor industry
    keywords = ['半导体', '芯片', '微电子', '集成电路', '晶圆', '封测', 
                '光刻', '存储器', 'IC', '电子', '科技']
    
    # Filter by stock name containing keywords
    mask = constituent_df['成分券名称'].str.contains('|'.join(keywords), na=False)
    semiconductor_stocks = constituent_df[mask].copy()
    
    print(f"Found {len(semiconductor_stocks)} semiconductor-related stocks")
    return semiconductor_stocks

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
        # Need more data for MACD calculation (at least 26 + 9 + lookback_days)
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=100)).strftime('%Y%m%d')
        end_date_fmt = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')
        
        # Fetch stock data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=start_date, end_date=end_date_fmt, adjust="qfq")
        
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
    
    # Step 1: Get constituent stocks
    constituent_df = get_constituent_stocks('399006')
    if constituent_df.empty:
        print("Failed to get constituent stocks")
        return
    
    # Step 2: Filter semiconductor stocks
    semiconductor_df = filter_semiconductor_stocks(constituent_df)
    if semiconductor_df.empty:
        print("No semiconductor stocks found")
        return
    
    # Step 3 & 4: Analyze MACD and calculate returns
    print("\nStep 3: Calculating MACD and detecting golden crosses...")
    results = []
    
    for idx, row in semiconductor_df.iterrows():
        stock_code = row['成分券代码']
        stock_name = row['成分券名称']
        
        print(f"Analyzing {stock_code} {stock_name}...")
        result = analyze_stock_macd(stock_code, stock_name)
        
        if result:
            results.append(result)
            print(f"  ✓ Golden cross found on {result['cross_date']}, 20d return: {result['return_20d']:.2f}%")
    
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
