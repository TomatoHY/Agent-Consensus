import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Target date and parameters
target_date = '20240913'
lookback_days = 5
obv_period = 20
ma_period = 20
ma_slope_days = 5

print("Step 1: Getting ChiNext stock list...")
stock_info = ak.stock_info_a_code_name()
chinext_stocks = stock_info[stock_info['code'].str.startswith('300')]['code'].tolist()
print(f"Found {len(chinext_stocks)} ChiNext stocks")

start_date = '20240801'
end_date = target_date

# Debug counters
total_processed = 0
failed_data = 0
failed_consecutive = 0
failed_obv = 0
failed_ma_slope = 0
failed_price_above_ma = 0
passed_all = 0

results = []

print("\nStep 2: Analyzing stocks (first 100 with debug info)...")
for i, stock_code in enumerate(chinext_stocks[:100]):
    try:
        total_processed += 1

        # Get daily stock data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=start_date, end_date=end_date, adjust="qfq")

        if df is None or len(df) < 25:
            failed_data += 1
            continue

        df = df.sort_values('日期')
        df['日期'] = pd.to_datetime(df['日期'])

        target_idx = df[df['日期'] == pd.to_datetime(target_date)].index
        if len(target_idx) == 0:
            failed_data += 1
            continue
        target_idx = target_idx[0]

        if target_idx < 20:
            failed_data += 1
            continue

        # Check large order net inflow
        prev_5_days = df.iloc[target_idx-4:target_idx+1].copy()
        prev_5_days['price_change'] = prev_5_days['收盘'].pct_change()
        prev_5_days['large_order_inflow'] = prev_5_days.apply(
            lambda row: row['成交量'] * 0.4 if pd.notna(row['price_change']) and row['price_change'] > 0
            else (-row['成交量'] * 0.3 if pd.notna(row['price_change']) and row['price_change'] < 0 else 0),
            axis=1
        )

        inflow_positive = (prev_5_days['large_order_inflow'] > 0).astype(int)
        max_consecutive = 0
        current_consecutive = 0

        for val in inflow_positive.values:
            if val == 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        if max_consecutive < 3:
            failed_consecutive += 1
            continue

        # Calculate OBV
        last_20_days = df.iloc[target_idx-19:target_idx+1].copy()
        obv_values = []
        obv = 0
        prev_close = None

        for idx, row in last_20_days.iterrows():
            if prev_close is not None:
                if row['收盘'] > prev_close:
                    obv += row['成交量']
                elif row['收盘'] < prev_close:
                    obv -= row['成交量']
            obv_values.append(obv)
            prev_close = row['收盘']

        last_20_days['OBV'] = obv_values
        obv_mean = last_20_days['OBV'].mean()
        current_obv = obv_values[-1]

        if obv_mean <= 0:
            failed_obv += 1
            continue

        obv_strength = current_obv / obv_mean

        if obv_strength <= 1.1:
            failed_obv += 1
            continue

        # Calculate 20-day MA
        df['MA20'] = df['收盘'].rolling(window=20).mean()
        last_5_ma = df.iloc[target_idx-4:target_idx+1]['MA20'].values

        ma_increasing = all(last_5_ma[i] < last_5_ma[i+1] for i in range(len(last_5_ma)-1))

        if not ma_increasing:
            failed_ma_slope += 1
            continue

        current_close = df.iloc[target_idx]['收盘']
        current_ma20 = df.iloc[target_idx]['MA20']

        if current_close <= current_ma20:
            failed_price_above_ma += 1
            continue

        ma_deviation = (current_close - current_ma20) / current_ma20 * 100

        passed_all += 1
        results.append({
            'stock_code': stock_code,
            'consecutive_inflow_days': max_consecutive,
            'obv_strength': round(obv_strength, 2),
            'ma_deviation': round(ma_deviation, 2)
        })

    except Exception as e:
        failed_data += 1
        continue

print(f"\n=== Debug Statistics ===")
print(f"Total processed: {total_processed}")
print(f"Failed data retrieval: {failed_data}")
print(f"Failed consecutive inflow (< 3 days): {failed_consecutive}")
print(f"Failed OBV strength (≤ 1.1): {failed_obv}")
print(f"Failed MA slope (not increasing): {failed_ma_slope}")
print(f"Failed price above MA: {failed_price_above_ma}")
print(f"Passed all filters: {passed_all}")

print(f"\nFound {len(results)} stocks meeting all criteria")

# Write results
output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_17_fund_flow_obv/independent/claudecode/fund_flow_result.txt'

with open(output_path, 'w', encoding='utf-8') as f:
    f.write('股票代码,大单净流入天数,OBV相对强度,均线偏离度(%)\n')

    if len(results) == 0:
        f.write('# 无符合条件的股票\n')
    else:
        for result in results:
            f.write(f"{result['stock_code']},{result['consecutive_inflow_days']},{result['obv_strength']},{result['ma_deviation']}\n")

print(f"\nResults written to fund_flow_result.txt")
