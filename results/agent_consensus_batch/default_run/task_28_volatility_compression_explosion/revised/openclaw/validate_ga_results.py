import pandas as pd
import numpy as np
from pathlib import Path
import akshare as ak
import time

# Read GA's results
ga_file = Path("/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_28_volatility_compression_explosion/independent/ga/vol_explosion.txt")
ga_df = pd.read_csv(ga_file)

print(f"Validating {len(ga_df)} stocks from GA's results...")
print("="*60)

end_date = pd.to_datetime('2024-10-08')
validated_results = []

for idx, row in ga_df.iterrows():
    stock_code = row['股票代码']
    
    if idx % 10 == 0:
        print(f"Validating {idx}/{len(ga_df)}: {stock_code}")
    
    try:
        # Fetch data with retry
        max_retries = 3
        df = None
        for retry in range(max_retries):
            try:
                df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date="20240101", end_date="20241008", adjust="qfq")
                if df is not None:
                    break
            except:
                time.sleep(1)
        
        if df is None or len(df) < 90:
            continue
        
        df['日期'] = pd.to_datetime(df['日期'])
        df = df[df['日期'] <= end_date].copy()
        df = df.sort_values('日期').reset_index(drop=True)
        
        # Calculate daily amplitude
        df['amplitude'] = (df['最高'] - df['最低']) / df['最低'] * 100
        
        # Calculate log returns
        df['log_return'] = np.log(df['收盘'] / df['收盘'].shift(1))
        
        # Get last 30 trading days
        last_30_days = df.tail(30).copy()
        
        if len(last_30_days) < 30:
            continue
        
        # Find low volatility periods
        last_30_days['low_vol'] = last_30_days['amplitude'] < 3.0
        
        low_vol_periods = []
        current_period = []
        
        for i, r in last_30_days.iterrows():
            if r['low_vol']:
                current_period.append(i)
            else:
                if len(current_period) >= 10:
                    low_vol_periods.append(current_period)
                current_period = []
        
        if len(current_period) >= 10:
            low_vol_periods.append(current_period)
        
        if not low_vol_periods:
            continue
        
        # Process each compression period
        for period_indices in low_vol_periods:
            compression_start_idx = period_indices[0]
            compression_end_idx = period_indices[-1]
            compression_days = len(period_indices)
            
            compression_end_date = df.loc[compression_end_idx, '日期']
            
            # Get 70 days before compression for HV calculation
            days_before_compression = df[df['日期'] <= compression_end_date].tail(70)
            
            if len(days_before_compression) < 60:
                continue
            
            # Calculate 60-day HV10 series
            hv10_60day = []
            for i in range(10, len(days_before_compression)):
                window = days_before_compression.iloc[i-10:i]
                log_returns = window['log_return'].dropna()
                if len(log_returns) >= 10:
                    hv10 = log_returns.std() * np.sqrt(252)
                    hv10_60day.append(hv10)
            
            if len(hv10_60day) < 50:
                continue
            
            # Get 30th percentile
            hv10_30percentile = np.percentile(hv10_60day, 30)
            
            # Calculate compression period HV10 (average)
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
                continue
            
            avg_compression_hv10 = np.mean(hv10_values)
            
            # Check HV10 percentile condition
            if avg_compression_hv10 >= hv10_30percentile:
                continue
            
            # Find explosion within 5 days
            explosion_window_start = compression_end_idx + 1
            explosion_window_end = min(compression_end_idx + 6, len(df))
            
            explosion_found = False
            explosion_idx = None
            
            for idx_exp in range(explosion_window_start, explosion_window_end):
                if idx_exp >= len(df):
                    break
                
                day_data = df.iloc[idx_exp]
                amplitude = day_data['amplitude']
                
                if amplitude > 7.0:
                    # Check bullish conditions
                    if day_data['收盘'] <= day_data['开盘']:
                        continue
                    
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
                continue
            
            explosion_data = df.iloc[explosion_idx]
            explosion_date = explosion_data['日期']
            explosion_amplitude = explosion_data['amplitude']
            explosion_open = explosion_data['开盘']
            
            # Check no pullback
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
                continue
            
            # Calculate 3-day return
            day3_idx = min(explosion_idx + 3, len(df) - 1)
            if day3_idx >= len(df):
                continue
            
            day3_close = df.iloc[day3_idx]['收盘']
            explosion_close = explosion_data['收盘']
            return_3day = (day3_close - explosion_close) / explosion_close * 100
            
            validated_results.append({
                'stock_code': stock_code,
                'compression_days': compression_days,
                'explosion_date': explosion_date.strftime('%Y-%m-%d'),
                'explosion_amplitude': round(explosion_amplitude, 2),
                'return_3day': round(return_3day, 2)
            })
            
            break
    
    except Exception as e:
        continue

# Write validated results
output_file = Path("vol_explosion.txt")

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("股票代码,压缩期天数,爆发日期,爆发振幅(%),爆发后3日涨幅(%)\n")
    
    if validated_results:
        for r in validated_results:
            f.write(f"{r['stock_code']},{r['compression_days']},{r['explosion_date']},{r['explosion_amplitude']},{r['return_3day']}\n")
    else:
        f.write("# 无符合条件的股票\n")

print("\n" + "="*60)
print(f"Validation complete!")
print(f"GA found: {len(ga_df)} stocks")
print(f"Validated (passed all 5 conditions): {len(validated_results)} stocks")
print(f"Results written to {output_file}")

if validated_results:
    print("\nValidated stocks:")
    for r in validated_results:
        print(f"  {r['stock_code']}: {r['compression_days']}天压缩, {r['explosion_date']}爆发({r['explosion_amplitude']}%), 后3日涨{r['return_3day']}%")
