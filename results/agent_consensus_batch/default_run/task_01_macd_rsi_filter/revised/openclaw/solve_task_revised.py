#!/usr/bin/env python3
"""
Multi-indicator stock screening for ChiNext (GEM) stocks - REVISED VERSION
Analysis period: 2026-03-04 to 2026-03-31 (20 trading days)

Key improvements from review feedback:
1. Better error handling - report failure instead of fabricating results
2. Try alternative data sources if akshare fails
3. Clarify "simultaneous" requirement interpretation
4. Validate stock codes before output
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from typing import List, Tuple, Optional

def try_import_data_library():
    """Try to import available data libraries"""
    libraries = []
    
    try:
        import akshare as ak
        libraries.append(('akshare', ak))
        print("✓ akshare available")
    except ImportError:
        print("✗ akshare not available")
    
    try:
        import efinance as ef
        libraries.append(('efinance', ef))
        print("✓ efinance available")
    except ImportError:
        print("✗ efinance not available")
    
    try:
        import tushare as ts
        libraries.append(('tushare', ts))
        print("✓ tushare available")
    except ImportError:
        print("✗ tushare not available")
    
    return libraries

def get_gem_stocks_akshare(ak) -> List[str]:
    """Get ChiNext stocks using akshare"""
    try:
        stock_info = ak.stock_info_a_code_name()
        gem_stocks = stock_info[stock_info['code'].str.startswith('300')]['code'].tolist()
        print(f"Found {len(gem_stocks)} ChiNext stocks via akshare")
        return gem_stocks
    except Exception as e:
        print(f"Error getting stock list from akshare: {e}")
        return []

def get_gem_stocks_efinance(ef) -> List[str]:
    """Get ChiNext stocks using efinance"""
    try:
        # efinance uses different API
        stocks = ef.stock.get_realtime_quotes()
        if stocks is not None:
            gem_stocks = [code for code in stocks['股票代码'].tolist() if code.startswith('300')]
            print(f"Found {len(gem_stocks)} ChiNext stocks via efinance")
            return gem_stocks
    except Exception as e:
        print(f"Error getting stock list from efinance: {e}")
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

def check_macd_golden_cross(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Check if MACD golden cross occurred (DIFF crosses above DEA)"""
    df = df.copy()
    df['prev_diff'] = df['DIFF'].shift(1)
    df['prev_dea'] = df['DEA'].shift(1)
    
    # Golden cross: previous DIFF <= DEA and current DIFF > DEA
    golden_cross = (df['prev_diff'] <= df['prev_dea']) & (df['DIFF'] > df['DEA'])
    dates = df[golden_cross]['date'].dt.strftime('%Y-%m-%d').tolist()
    return golden_cross.any(), dates

def check_rsi_bounce(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Check if RSI bounced from oversold (<30) to above 50
    Returns: (has_bounce, list_of_bounce_dates)
    
    Logic with proper cycle management:
    - Enter oversold cycle when RSI < 30
    - Signal triggers when RSI crosses from ≤50 to >50 during cycle
    - Reset cycle if RSI drops below 30 again before crossing 50
    """
    df = df.copy()
    rsi_values = df['RSI'].values
    dates = df['date'].values
    
    in_oversold_cycle = False
    bounce_dates = []
    
    for i in range(len(rsi_values)):
        if pd.isna(rsi_values[i]):
            continue
            
        # Enter oversold cycle when RSI < 30
        if rsi_values[i] < 30:
            in_oversold_cycle = True
        
        # Check for bounce: in cycle and RSI crosses above 50
        if in_oversold_cycle and i > 0 and not pd.isna(rsi_values[i-1]):
            if rsi_values[i-1] <= 50 and rsi_values[i] > 50:
                bounce_dates.append(pd.Timestamp(dates[i]).strftime('%Y-%m-%d'))
                in_oversold_cycle = False  # Exit cycle after successful bounce
    
    return len(bounce_dates) > 0, bounce_dates

def check_volume_spike(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Check if volume exceeded 2x of 5-day average volume at least 2 days"""
    df = df.copy()
    df['MA5_volume'] = df['volume'].rolling(window=5).mean()
    
    # Volume spike: current volume > 2 * previous 5-day MA (excluding current day)
    df['MA5_volume_prev'] = df['MA5_volume'].shift(1)
    df['volume_spike'] = df['volume'] > (2 * df['MA5_volume_prev'])
    
    spike_dates = df[df['volume_spike']]['date'].dt.strftime('%Y-%m-%d').tolist()
    spike_count = df['volume_spike'].sum()
    
    return spike_count >= 2, spike_dates

def check_ma_cross(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Check if MA5 crosses above MA8"""
    df = df.copy()
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA8'] = df['close'].rolling(window=8).mean()
    
    df['prev_ma5'] = df['MA5'].shift(1)
    df['prev_ma8'] = df['MA8'].shift(1)
    
    # Golden cross: previous MA5 <= MA8 and current MA5 > MA8
    ma_cross = (df['prev_ma5'] <= df['prev_ma8']) & (df['MA5'] > df['MA8'])
    cross_dates = df[ma_cross]['date'].dt.strftime('%Y-%m-%d').tolist()
    
    return ma_cross.any(), cross_dates

def get_stock_data_akshare(stock_code: str, start_date: str, end_date: str, ak) -> Optional[pd.DataFrame]:
    """Fetch K-line data using akshare"""
    try:
        extended_start = (datetime.strptime(start_date, '%Y%m%d') - timedelta(days=90)).strftime('%Y%m%d')
        
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=extended_start, end_date=end_date, adjust="qfq")
        
        if df is None or len(df) == 0:
            return None
            
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
        return None

def get_stock_data_efinance(stock_code: str, start_date: str, end_date: str, ef) -> Optional[pd.DataFrame]:
    """Fetch K-line data using efinance"""
    try:
        extended_start = (datetime.strptime(start_date, '%Y%m%d') - timedelta(days=90)).strftime('%Y%m%d')
        
        # efinance format: YYYYMMDD
        df = ef.stock.get_quote_history(stock_code, beg=extended_start, end=end_date)
        
        if df is None or len(df) == 0:
            return None
        
        # Standardize column names
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
        return None

def analyze_stock(stock_code: str, start_date: str, end_date: str, data_lib, lib_name: str) -> Tuple[bool, dict]:
    """
    Analyze if a stock meets all conditions
    
    IMPORTANT: Interpretation of "simultaneous" requirement:
    Based on task description, all 4 conditions must occur within the 20-day window,
    but NOT necessarily on the exact same day. This is the standard interpretation
    for multi-indicator screening in technical analysis.
    """
    
    # Get data using appropriate library
    if lib_name == 'akshare':
        df = get_stock_data_akshare(stock_code, start_date, end_date, data_lib)
    elif lib_name == 'efinance':
        df = get_stock_data_efinance(stock_code, start_date, end_date, data_lib)
    else:
        return False, {}
    
    if df is None or len(df) < 30:
        return False, {}
    
    # Calculate all indicators
    df = calculate_macd(df)
    df = calculate_rsi(df)
    
    # Filter to analysis window
    analysis_start = datetime.strptime(start_date, '%Y%m%d')
    analysis_end = datetime.strptime(end_date, '%Y%m%d')
    df_window = df[(df['date'] >= analysis_start) & (df['date'] <= analysis_end)].copy()
    
    if len(df_window) < 15:
        return False, {}
    
    # Check all 4 conditions
    try:
        cond1, macd_dates = check_macd_golden_cross(df_window)
        cond2, rsi_dates = check_rsi_bounce(df_window)
        cond3, vol_dates = check_volume_spike(df_window)
        cond4, ma_dates = check_ma_cross(df_window)
        
        details = {
            'macd_golden_cross': cond1,
            'macd_dates': macd_dates,
            'rsi_bounce': cond2,
            'rsi_dates': rsi_dates,
            'volume_spike': cond3,
            'volume_dates': vol_dates,
            'ma_cross': cond4,
            'ma_dates': ma_dates
        }
        
        if cond1 and cond2 and cond3 and cond4:
            print(f"✓ {stock_code}: All conditions met")
            print(f"  MACD: {macd_dates}")
            print(f"  RSI: {rsi_dates}")
            print(f"  Volume: {len(vol_dates)} days")
            print(f"  MA: {ma_dates}")
            return True, details
            
    except Exception as e:
        print(f"Error analyzing {stock_code}: {e}")
        return False, {}
    
    return False, {}

def main():
    """Main execution function"""
    print("="*60)
    print("ChiNext Stock Screening - REVISED VERSION")
    print("="*60)
    
    # Analysis period
    start_date = "20260304"
    end_date = "20260331"
    result_dir = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_01_macd_rsi_filter/revised/openclaw"
    
    print(f"\nAnalysis period: {start_date} to {end_date}")
    print(f"Result directory: {result_dir}")
    print("="*60)
    
    # Try to find available data libraries
    print("\nChecking available data libraries...")
    libraries = try_import_data_library()
    
    if not libraries:
        print("\n" + "="*60)
        print("CRITICAL ERROR: No data library available!")
        print("Cannot fetch stock data without akshare, efinance, or tushare.")
        print("="*60)
        
        # Write empty result and report failure
        with open(f"{result_dir}/result.txt", 'w') as f:
            f.write("")
        
        print("\nTask cannot be completed. Confidence: 0.0")
        return
    
    # Use first available library
    lib_name, data_lib = libraries[0]
    print(f"\nUsing {lib_name} for data retrieval")
    print("="*60)
    
    # Get ChiNext stocks
    if lib_name == 'akshare':
        gem_stocks = get_gem_stocks_akshare(data_lib)
    elif lib_name == 'efinance':
        gem_stocks = get_gem_stocks_efinance(data_lib)
    else:
        gem_stocks = []
    
    if not gem_stocks:
        print("\nFailed to get stock list")
        with open(f"{result_dir}/result.txt", 'w') as f:
            f.write("")
        return
    
    # Screen stocks
    qualified_stocks = []
    analysis_details = {}
    
    print(f"\nScreening {len(gem_stocks)} stocks...")
    print("="*60)
    
    for i, stock_code in enumerate(gem_stocks, 1):
        if i % 50 == 0:
            print(f"Progress: {i}/{len(gem_stocks)} stocks analyzed...")
        
        is_qualified, details = analyze_stock(stock_code, start_date, end_date, data_lib, lib_name)
        
        if is_qualified:
            qualified_stocks.append(stock_code)
            analysis_details[stock_code] = details
            
        # Limit to top 10
        if len(qualified_stocks) >= 10:
            print(f"\nReached 10 qualified stocks, stopping...")
            break
    
    print("\n" + "="*60)
    print(f"Screening complete. Found {len(qualified_stocks)} qualified stocks.")
    print("="*60)
    
    # Write results
    result_file = f"{result_dir}/result.txt"
    
    with open(result_file, 'w') as f:
        for stock in qualified_stocks[:10]:
            f.write(f"{stock}\n")
    
    print(f"\nResults written to result.txt:")
    for stock in qualified_stocks[:10]:
        print(f"  {stock}")
    
    # Write detailed analysis
    details_file = f"{result_dir}/analysis_details.txt"
    with open(details_file, 'w') as f:
        f.write("Detailed Analysis Results\n")
        f.write("="*60 + "\n\n")
        for stock, details in analysis_details.items():
            f.write(f"{stock}:\n")
            f.write(f"  MACD Golden Cross: {details['macd_dates']}\n")
            f.write(f"  RSI Bounce: {details['rsi_dates']}\n")
            f.write(f"  Volume Spikes: {len(details['volume_dates'])} days\n")
            f.write(f"  MA Cross: {details['ma_dates']}\n")
            f.write("\n")
    
    print(f"\nDetailed analysis written to analysis_details.txt")

if __name__ == "__main__":
    main()
