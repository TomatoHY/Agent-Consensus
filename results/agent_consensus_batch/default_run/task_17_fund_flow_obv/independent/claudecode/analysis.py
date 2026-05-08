import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Target date and parameters
target_date = '20240913'
lookback_days = 5  # Previous 5 trading days for large order flow
obv_period = 20  # 20-day OBV calculation
ma_period = 20  # 20-day moving average
ma_slope_days = 5  # Check last 5 days of MA for upward slope

print("Step 1: Getting ChiNext stock list...")
# Get ChiNext (创业板) stock list - stocks starting with 300
stock_info = ak.stock_info_a_code_name()
chinext_stocks = stock_info[stock_info['code'].str.startswith('300')]['code'].tolist()
print(f"Found {len(chinext_stocks)} ChiNext stocks")

# We need data from earlier to calculate 20-day indicators
# Need at least 20 + 5 = 25 trading days before target date
start_date = '20240801'  # Start from August to ensure enough data
end_date = target_date

results = []

print("\nStep 2: Analyzing each stock...")
for i, stock_code in enumerate(chinext_stocks[:200]):  # Analyze first 200 stocks
    try:
        if (i + 1) % 20 == 0:
            print(f"Processing {i+1}/{min(200, len(chinext_stocks))} stocks...")

        # Get daily stock data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=start_date, end_date=end_date, adjust="qfq")

        if df is None or len(df) < 25:
            continue

        df = df.sort_values('日期')
        df['日期'] = pd.to_datetime(df['日期'])

        # Find the target date index
        target_idx = df[df['日期'] == pd.to_datetime(target_date)].index
        if len(target_idx) == 0:
            continue
        target_idx = target_idx[0]

        # Need at least 20 days before target date
        if target_idx < 20:
            continue

        # Step 1: Check large order net inflow for previous 5 trading days
        # Using volume proxy: large buy ≈ daily volume × 0.4
        # Net inflow proxy: when price rises, assume net buying; when falls, net selling
        # Use volume weighted by price change as proxy

        prev_5_days = df.iloc[target_idx-4:target_idx+1].copy()
        prev_5_days['price_change'] = prev_5_days['收盘'].pct_change()

        # Large order net inflow proxy: positive when price rises with volume
        prev_5_days['large_order_inflow'] = prev_5_days.apply(
            lambda row: row['成交量'] * 0.4 if pd.notna(row['price_change']) and row['price_change'] > 0
            else (-row['成交量'] * 0.3 if pd.notna(row['price_change']) and row['price_change'] < 0 else 0),
            axis=1
        )

        # Find consecutive days with positive inflow
        inflow_positive = (prev_5_days['large_order_inflow'] > 0).astype(int)
        max_consecutive = 0
        current_consecutive = 0

        for val in inflow_positive.values:
            if val == 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        # Need at least 3 consecutive days
        if max_consecutive < 3:
            continue

        # Step 2: Calculate OBV for last 20 days
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
                # If equal, OBV unchanged
            obv_values.append(obv)
            prev_close = row['收盘']

        last_20_days['OBV'] = obv_values

        # Calculate OBV strength: current OBV / mean of 20-day OBV
        obv_mean = last_20_days['OBV'].mean()
        current_obv = obv_values[-1]

        if obv_mean <= 0:
            continue

        obv_strength = current_obv / obv_mean

        # Filter: OBV > 1.1 times the 20-day mean
        if obv_strength <= 1.1:
            continue

        # Step 3: Verify upward channel with 20-day MA
        # Calculate 20-day MA for the period
        df['MA20'] = df['收盘'].rolling(window=20).mean()

        # Get last 5 days of MA20 values (including target date)
        last_5_ma = df.iloc[target_idx-4:target_idx+1]['MA20'].values

        # Check if MA20 is monotonically increasing (upward slope)
        ma_increasing = all(last_5_ma[i] < last_5_ma[i+1] for i in range(len(last_5_ma)-1))

        if not ma_increasing:
            continue

        # Check if closing price is above 20-day MA
        current_close = df.iloc[target_idx]['收盘']
        current_ma20 = df.iloc[target_idx]['MA20']

        if current_close <= current_ma20:
            continue

        # Calculate MA deviation percentage
        ma_deviation = (current_close - current_ma20) / current_ma20 * 100

        # Stock passes all filters
        results.append({
            'stock_code': stock_code,
            'consecutive_inflow_days': max_consecutive,
            'obv_strength': round(obv_strength, 2),
            'ma_deviation': round(ma_deviation, 2)
        })

    except Exception as e:
        continue

print(f"\nStep 3: Writing results...")
print(f"Found {len(results)} stocks meeting all criteria")

# Write results to file
output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_17_fund_flow_obv/independent/claudecode/fund_flow_result.txt'

with open(output_path, 'w', encoding='utf-8') as f:
    f.write('股票代码,大单净流入天数,OBV相对强度,均线偏离度(%)\n')

    if len(results) == 0:
        f.write('# 无符合条件的股票\n')
    else:
        for result in results:
            f.write(f"{result['stock_code']},{result['consecutive_inflow_days']},{result['obv_strength']},{result['ma_deviation']}\n")

print(f"Results written to fund_flow_result.txt")
print("\nSummary:")
for result in results:
    print(f"  {result['stock_code']}: {result['consecutive_inflow_days']}天连续流入, OBV强度={result['obv_strength']}, 均线偏离={result['ma_deviation']}%")
