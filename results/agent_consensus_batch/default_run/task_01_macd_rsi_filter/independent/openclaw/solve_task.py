#!/usr/bin/env python3
"""
Multi-indicator stock screening for ChiNext (GEM) stocks
Analysis period: 2026-03-04 to 2026-03-31 (20 trading days)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak
from typing import List, Tuple

def get_gem_stocks() -> List[str]:
    """Get all ChiNext (GEM) stock codes starting with 300"""
    try:
        # Get all A-share stocks
        stock_info = ak.stock_info_a_code_name()
        # Filter for ChiNext stocks (starting with 300)
        gem_stocks = stock_info[stock_info['code'].str.startswith('300')]['code'].tolist()
        print(f"Found {len(gem_stocks)} ChiNext stocks")
        return gem_stocks
    except Exception as e:
        print(f"Error getting stock list: {e}")
        return []

def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return data.ewm(span=period, adjust=False).mean()

def calculate_macd(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate MACD indicator (EMA12, EMA26, DEA9)"""
    df = df.copy()
    df['EMA12'] = calculate_ema(df['close'], 12)
    df['EMA26'] = calculate_ema(df['close'], 26)
    df['DIFF'] = df['EMA12'] - df['EMA26']
    df['DEA'] = calculate_ema(df['DIFF'], 9)
    df['MACD'] = 2 * (df['DIFF'] - df['DEA'])
    return df

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Calculate RSI indicator"""
    df = df.copy()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def check_macd_golden_cross(df: pd.DataFrame) -> bool:
    """Check if MACD golden cross occurred (DIFF crosses above DEA)"""
    df = df.copy()
    df['prev_diff'] = df['DIFF'].shift(1)
    df['prev_dea'] = df['DEA'].shift(1)
    
    # Golden cross: previous DIFF <= DEA and current DIFF > DEA
    golden_cross = (df['prev_diff'] <= df['prev_dea']) & (df['DIFF'] > df['DEA'])
    return golden_cross.any()

def check_rsi_bounce(df: pd.DataFrame) -> bool:
    """
    Check if RSI bounced from oversold (<30) to above 50
    Logic: RSI drops below 30, then rises above 50
    """
    df = df.copy()
    rsi_values = df['RSI'].values
    
    in_oversold_cycle = False
    
    for i in range(len(rsi_values)):
        if pd.isna(rsi_values[i]):
            continue
            
        # Enter oversold cycle when RSI < 30
        if rsi_values[i] < 30:
            in_oversold_cycle = True
        
        # Check for bounce: in cycle and RSI crosses above 50
        if in_oversold_cycle:
            if i > 0 and not pd.isna(rsi_values[i-1]):
                if rsi_values[i-1] <= 50 and rsi_values[i] > 50:
                    return True
            # Reset cycle if drops below 30 again before crossing 50
            if rsi_values[i] < 30:
                continue
    
    return False

def check_volume_spike(df: pd.DataFrame) -> bool:
    """Check if volume exceeded 2x of 5-day average volume at least 2 days"""
    df = df.copy()
    df['MA5_volume'] = df['volume'].rolling(window=5).mean()
    
    # Volume spike: current volume > 2 * MA5 volume (excluding current day)
    df['MA5_volume_prev'] = df['MA5_volume'].shift(1)
    df['volume_spike'] = df['volume'] > (2 * df['MA5_volume_prev'])
    
    spike_count = df['volume_spike'].sum()
    return spike_count >= 2

def check_ma_cross(df: pd.DataFrame) -> bool:
    """Check if MA5 crosses above MA8"""
    df = df.copy()
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA8'] = df['close'].rolling(window=8).mean()
    
    df['prev_ma5'] = df['MA5'].shift(1)
    df['prev_ma8'] = df['MA8'].shift(1)
    
    # Golden cross: previous MA5 <= MA8 and current MA5 > MA8
    ma_cross = (df['prev_ma5'] <= df['prev_ma8']) & (df['MA5'] > df['MA8'])
    return ma_cross.any()

def get_stock_data(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch K-line data for a stock"""
    try:
        # Need extra data for indicator calculation
        # Start from 60 days before to ensure enough data for indicators
        extended_start = (datetime.strptime(start_date, '%Y%m%d') - timedelta(days=90)).strftime('%Y%m%d')
        
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=extended_start, end_date=end_date, adjust="qfq")
        
        if df is None or len(df) == 0:
            return None
            
        # Rename columns to standard names
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount'
        })
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        return df
    except Exception as e:
        print(f"Error fetching data for {stock_code}: {e}")
        return None

def analyze_stock(stock_code: str, start_date: str, end_date: str) -> bool:
    """Analyze if a stock meets all conditions"""
    df = get_stock_data(stock_code, start_date, end_date)
    
    if df is None or len(df) < 30:  # Need enough data for indicators
        return False
    
    # Calculate all indicators
    df = calculate_macd(df)
    df = calculate_rsi(df)
    
    # Filter to analysis window
    analysis_start = datetime.strptime(start_date, '%Y%m%d')
    analysis_end = datetime.strptime(end_date, '%Y%m%d')
    df_window = df[(df['date'] >= analysis_start) & (df['date'] <= analysis_end)].copy()
    
    if len(df_window) < 15:  # Need reasonable amount of data in window
        return False
    
    # Check all 4 conditions
    try:
        condition1 = check_macd_golden_cross(df_window)
        condition2 = check_rsi_bounce(df_window)
        condition3 = check_volume_spike(df_window)
        condition4 = check_ma_cross(df_window)
        
        if condition1 and condition2 and condition3 and condition4:
            print(f"✓ {stock_code}: All conditions met")
            return True
    except Exception as e:
        print(f"Error analyzing {stock_code}: {e}")
        return False
    
    return False

def main():
    """Main execution function"""
    print("Starting ChiNext stock screening...")
    print("=" * 60)
    
    # Analysis period
    start_date = "20260304"
    end_date = "20260331"
    
    print(f"Analysis period: {start_date} to {end_date}")
    print("=" * 60)
    
    # Get all ChiNext stocks
    gem_stocks = get_gem_stocks()
    
    if not gem_stocks:
        print("Failed to get stock list")
        return
    
    # Screen stocks
    qualified_stocks = []
    
    for i, stock_code in enumerate(gem_stocks, 1):
        print(f"\n[{i}/{len(gem_stocks)}] Analyzing {stock_code}...", end=" ")
        
        if analyze_stock(stock_code, start_date, end_date):
            qualified_stocks.append(stock_code)
            
        # Limit to top 10
        if len(qualified_stocks) >= 10:
            print("\nReached 10 qualified stocks, stopping...")
            break
    
    print("\n" + "=" * 60)
    print(f"Screening complete. Found {len(qualified_stocks)} qualified stocks.")
    print("=" * 60)
    
    # Write results
    result_file = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_01_macd_rsi_filter/independent/openclaw/result.txt"
    
    with open(result_file, 'w') as f:
        for stock in qualified_stocks[:10]:  # Ensure max 10
            f.write(f"{stock}\n")
    
    print(f"\nResults written to result.txt:")
    for stock in qualified_stocks[:10]:
        print(f"  {stock}")

if __name__ == "__main__":
    main()
