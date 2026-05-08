import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import akshare as ak

# Get ChiNext stock list (300xxx)
print("Fetching ChiNext stock list...")
stock_info = ak.stock_info_a_code_name()
chinext_stocks = stock_info[stock_info['code'].str.startswith('300')]['code'].tolist()
print(f"Found {len(chinext_stocks)} ChiNext stocks")

# Analysis parameters
end_date = pd.to_datetime('2024-10-08')
results = []

# Debug counters
debug_stats = {
    'total_processed': 0,
    'failed_data_fetch': 0,
    'insufficient_history': 0,
    'no_low_vol_period': 0,
    'failed_hv10_percentile': 0,
    'no_explosion': 0,
    'failed_bullish_check': 0,
    'failed_no_pullback': 0,
    'passed_all': 0
}

# Process each stock
for idx, stock_code in enumerate(chinext_stocks):
    if idx % 50 == 0:
        print(f"Processing {idx}/{len(chinext_stocks)}: {stock_code}")
    
    debug_stats['total_processed'] += 1
    
    try:
        # Fetch daily data - extended window for better HV10 calculation
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date="20240101", end_date="20241008", adjust="qfq")
        
        if df is None or len(df) < 90:
            debug_stats['insufficient_history'] += 1
            continue
        
        df['日期'] = pd.to_datetime(df['日期'])
        df = df[df['日期'] <= end_date].copy()
        df = df.sort_values('日期').reset_index(drop=True)
        
        # Calculate daily amplitude
        df['amplitude'] = (df['最高'] - df['最低']) / df['最低'] * 100
        
        # Calculate log returns for HV calculation
        df['log_return'] = np.log(df['收盘'] / df['收盘'].shift(1))
        
        # Focus on last 30 trading days
        last_30_days = df.tail(30).copy()
        
        if len(last_30_days) < 30:
            debug_stats['insufficient_history'] += 1
            continue
        
        # Step 1: Find low volatility periods (amplitude < 3%) in last 30 days
        last_30_days['low_vol'] = last_30_days['amplitude'] < 3.0
        
        # Find consecutive low volatility periods of at least 10 days
        low_vol_periods = []
        current_period = []
        
        for i, row in last_30_days.iterrows():
            if row['low_vol']:
                current_period.append(i)
            else:
                if len(current_period) >= 10:
                    low_vol_periods.append(current_period)
                current_period = []
        
        if len(current_period) >= 10:
            low_vol_periods.append(current_period)
        
        if not low_vol_periods:
            debug_stats['no_low_vol_period'] += 1
            continue
        
        # Process each low volatility period
        for period_indices in low_vol_periods:
            compression_start_idx = period_indices[0]
            compression_end_idx = period_indices[-1]
            compression_days = len(period_indices)
            
            # Step 2: Calculate HV10 during compression period
            # Get data for HV calculation (need more history)
            compression_end_date = df.loc[compression_end_idx, '日期']
            
            # Get 70 days before compression end for 60-day HV window
            days_before_compression = df[df['日期'] <= compression_end_date].tail(70)
            
            if len(days_before_compression) < 60:
                debug_stats['insufficient_history'] += 1
                continue
            
            # Calculate HV10 for each day in the 60-day window
            hv10_60day = []
            for i in range(10, len(days_before_compression)):
                window = days_before_compression.iloc[i-10:i]
                log_returns = window['log_return'].dropna()
                if len(log_returns) >= 10:
                    hv10 = log_returns.std() * np.sqrt(252)
                    hv10_60day.append(hv10)
            
            if len(hv10_60day) < 50:
                debug_stats['insufficient_history'] += 1
                continue
            
            # Get 30th percentile of 60-day HV10
            hv10_30percentile = np.percentile(hv10_60day, 30)
            
            # Calculate HV10 during compression period - USE AVERAGE instead of minimum
            compression_period_df = df.loc[compression_start_idx:compression_end_idx]
            hv10_values = []
            for i in range(len(compression_period_df)):
                if i < 9:
                    continue
                window_data = compression_period_df.iloc[i-9:i+1]
                log_returns = window_data['log_return'].dropna()
                if len(log_returns) >= 10:
                    hv10 = log_returns.std() * np.sqrt(252)
                    hv10_values.append(hv10)
            
            if not hv10_values:
                debug_stats['insufficient_history'] += 1
                continue
            
            # KEY CHANGE: Use average HV10 instead of minimum
            avg_compression_hv10 = np.mean(hv10_values)
            
            # Check if compression HV10 is below 30th percentile
            if avg_compression_hv10 >= hv10_30percentile:
                debug_stats['failed_hv10_percentile'] += 1
                continue
            
            # Step 3: Find explosion within 5 days after compression
            explosion_window_start = compression_end_idx + 1
            explosion_window_end = min(compression_end_idx + 6, len(df))
            
            explosion_found = False
            explosion_idx = None
            
            for idx_exp in range(explosion_window_start, explosion_window_end):
                if idx_exp >= len(df):
                    break
                
                day_data = df.iloc[idx_exp]
                amplitude = day_data['amplitude']
                
                # Check explosion condition: amplitude > 7%
                if amplitude > 7.0:
                    # Step 4: Check bullish explosion conditions
                    # 4a: Close > Open (bullish)
                    if day_data['收盘'] <= day_data['开盘']:
                        continue
                    
                    # 4b: Close in upper 70% of daily range
                    daily_range = day_data['最高'] - day_data['最低']
                    if daily_range == 0:
                        continue
                    
                    close_position = (day_data['收盘'] - day_data['最低']) / daily_range
                    if close_position <= 0.7:
                        continue
                    
                    explosion_idx = idx_exp
                    explosion_found = True
                    break
            
            if not explosion_found:
                debug_stats['no_explosion'] += 1
                continue
            
            explosion_data = df.iloc[explosion_idx]
            explosion_date = explosion_data['日期']
            explosion_amplitude = explosion_data['amplitude']
            explosion_open = explosion_data['开盘']
            
            # Step 5: Check no pullback in next 3 days
            # Low price should not fall below explosion day's open price
            pullback_window_start = explosion_idx + 1
            pullback_window_end = min(explosion_idx + 4, len(df))
            
            no_pullback = True
            for idx_pb in range(pullback_window_start, pullback_window_end):
                if idx_pb >= len(df):
                    break
                
                if df.iloc[idx_pb]['最低'] < explosion_open:
                    no_pullback = False
                    break
            
            if not no_pullback:
                debug_stats['failed_no_pullback'] += 1
                continue
            
            # Calculate 3-day return after explosion
            day3_idx = min(explosion_idx + 3, len(df) - 1)
            if day3_idx >= len(df):
                continue
            
            day3_close = df.iloc[day3_idx]['收盘']
            explosion_close = explosion_data['收盘']
            return_3day = (day3_close - explosion_close) / explosion_close * 100
            
            debug_stats['passed_all'] += 1
            
            results.append({
                'stock_code': stock_code,
                'compression_days': compression_days,
                'explosion_date': explosion_date.strftime('%Y-%m-%d'),
                'explosion_amplitude': round(explosion_amplitude, 2),
                'return_3day': round(return_3day, 2)
            })
            
            # Only take first valid pattern per stock
            break
    
    except Exception as e:
        debug_stats['failed_data_fetch'] += 1
        continue

# Print debug statistics
print("\n" + "="*60)
print("DEBUG STATISTICS")
print("="*60)
for key, value in debug_stats.items():
    print(f"{key}: {value}")

# Write results
output_file = Path("vol_explosion.txt")

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("股票代码,压缩期天数,爆发日期,爆发振幅(%),爆发后3日涨幅(%)\n")
    
    if results:
        for r in results:
            f.write(f"{r['stock_code']},{r['compression_days']},{r['explosion_date']},{r['explosion_amplitude']},{r['return_3day']}\n")
    else:
        f.write("# 无符合条件的股票\n")

print(f"\nAnalysis complete!")
print(f"Found {len(results)} stocks matching volatility compression-explosion criteria")
print(f"Results written to {output_file}")

if results:
    print("\nSample results:")
    for r in results[:10]:
        print(f"  {r['stock_code']}: {r['compression_days']}天压缩, {r['explosion_date']}爆发({r['explosion_amplitude']}%), 后3日涨{r['return_3day']}%")
