#!/usr/bin/env python3
"""
三金叉共振信号检测
Find ChiNext stocks with triple golden cross within 5 trading days before 2024-07-31
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def calculate_macd(df, fast=12, slow=26, signal=9):
    """Calculate MACD indicator"""
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    diff = ema_fast - ema_slow
    dea = diff.ewm(span=signal, adjust=False).mean()
    return diff, dea

def calculate_kdj(df, n=9, m1=3, m2=3):
    """Calculate KDJ indicator"""
    low_list = df['low'].rolling(window=n, min_periods=1).min()
    high_list = df['high'].rolling(window=n, min_periods=1).max()
    
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    rsv = rsv.fillna(50)
    
    k = rsv.ewm(com=m1-1, adjust=False).mean()
    d = k.ewm(com=m2-1, adjust=False).mean()
    
    return k, d

def calculate_ma(df, period):
    """Calculate moving average"""
    return df['close'].rolling(window=period).mean()

def detect_golden_cross(series1, series2):
    """Detect golden cross: series1 crosses above series2"""
    crosses = []
    for i in range(1, len(series1)):
        if series1.iloc[i-1] <= series2.iloc[i-1] and series1.iloc[i] > series2.iloc[i]:
            crosses.append(i)
    return crosses

def main():
    end_date = '20240731'
    start_date = '20240401'  # Get more data for indicator warmup
    
    result_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_05_triple_golden_cross/independent/openclaw/triple_cross.txt'
    
    print("Getting ChiNext stock list...")
    try:
        # Get ChiNext stock list (300xxx codes)
        stock_info = ak.stock_info_a_code_name()
        chinext_stocks = stock_info[stock_info['code'].str.startswith('300')]['code'].tolist()
        print(f"Found {len(chinext_stocks)} ChiNext stocks")
    except Exception as e:
        print(f"Error getting stock list: {e}")
        return
    
    results = []
    
    for idx, stock_code in enumerate(chinext_stocks):
        if idx % 50 == 0:
            print(f"Processing {idx}/{len(chinext_stocks)}...")
        
        try:
            # Get daily K-line data
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                    start_date=start_date, end_date=end_date, adjust="qfq")
            
            if df is None or len(df) < 60:
                continue
            
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            # Calculate indicators
            diff, dea = calculate_macd(df)
            k, d = calculate_kdj(df)
            ma5 = calculate_ma(df, 5)
            ma10 = calculate_ma(df, 10)
            
            df['diff'] = diff
            df['dea'] = dea
            df['k'] = k
            df['d'] = d
            df['ma5'] = ma5
            df['ma10'] = ma10
            
            # Get last 20 trading days
            last_20_days = df.tail(20).reset_index(drop=True)
            
            if len(last_20_days) < 20:
                continue
            
            # Detect golden crosses in last 20 days
            macd_crosses = detect_golden_cross(last_20_days['diff'], last_20_days['dea'])
            kdj_crosses = detect_golden_cross(last_20_days['k'], last_20_days['d'])
            ma_crosses = detect_golden_cross(last_20_days['ma5'], last_20_days['ma10'])
            
            if not macd_crosses or not kdj_crosses or not ma_crosses:
                continue
            
            # Check if all three crosses occur within 5 trading days
            for macd_idx in macd_crosses:
                for kdj_idx in kdj_crosses:
                    for ma_idx in ma_crosses:
                        indices = [macd_idx, kdj_idx, ma_idx]
                        min_idx = min(indices)
                        max_idx = max(indices)
                        
                        # Check if within 5 trading days (index difference <= 4)
                        if max_idx - min_idx <= 4:
                            macd_date = last_20_days.iloc[macd_idx]['date'].strftime('%Y-%m-%d')
                            kdj_date = last_20_days.iloc[kdj_idx]['date'].strftime('%Y-%m-%d')
                            ma_date = last_20_days.iloc[ma_idx]['date'].strftime('%Y-%m-%d')
                            
                            results.append({
                                'code': stock_code,
                                'macd_date': macd_date,
                                'kdj_date': kdj_date,
                                'ma_date': ma_date
                            })
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break
        
        except Exception as e:
            continue
    
    # Write results
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,MACD金叉日期,KDJ金叉日期,MA金叉日期\n')
        if results:
            for r in results:
                f.write(f"{r['code']},{r['macd_date']},{r['kdj_date']},{r['ma_date']}\n")
            print(f"\nFound {len(results)} stocks with triple golden cross")
        else:
            f.write('# 无符合条件的股票\n')
            print("\nNo stocks found with triple golden cross in the specified period")
    
    print(f"Results written to {result_file}")

if __name__ == '__main__':
    main()
