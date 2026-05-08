import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicator"""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    diff = ema_fast - ema_slow
    dea = diff.ewm(span=signal, adjust=False).mean()
    macd = (diff - dea) * 2
    return diff, dea, macd

def find_golden_cross(diff, dea, recent_days=5):
    """Find MACD golden cross (DIFF crosses above DEA) in recent days"""
    for i in range(len(diff) - recent_days, len(diff)):
        if i > 0:
            if diff.iloc[i-1] <= dea.iloc[i-1] and diff.iloc[i] > dea.iloc[i]:
                return True, diff.index[i]
    return False, None

# Step 1: Get ChiNext Index (399006) constituent stocks
print("Step 1: Getting ChiNext Index (399006) constituent stocks...")
try:
    # Get all ChiNext stocks (300xxx) as constituents
    stock_info = ak.stock_info_a_code_name()
    constituents = stock_info[stock_info['code'].str.startswith('300')].copy()
    print(f"Found {len(constituents)} constituent stocks (ChiNext stocks starting with 300)")
except Exception as e:
    print(f"Error getting constituents: {e}")
    constituents = pd.DataFrame()

# Step 2: Filter for semiconductor/chip industry stocks
print("\nStep 2: Filtering semiconductor/chip industry stocks...")
semiconductor_keywords = ['半导体', '芯片', '微电子', '集成电路', '晶圆', '封测', '光刻', 'IC']
semiconductor_stocks = []

if not constituents.empty:
    for idx, row in constituents.iterrows():
        # Handle different possible column names
        stock_code = row.get('成分券代码', row.get('code', row.get('stock_code', '')))
        stock_name = row.get('成分券名称', row.get('name', row.get('stock_name', '')))

        # Check if stock name contains semiconductor keywords
        if any(keyword in str(stock_name) for keyword in semiconductor_keywords):
            semiconductor_stocks.append({
                'code': stock_code,
                'name': stock_name
            })
            print(f"  Found: {stock_code} {stock_name}")

print(f"Found {len(semiconductor_stocks)} semiconductor stocks")

# Step 3: Calculate MACD and find golden crosses
print("\nStep 3: Calculating MACD and finding golden crosses...")
end_date = "20240315"
start_date = "20231201"  # Get more data for MACD calculation

results = []

for stock in semiconductor_stocks:
    try:
        stock_code = stock['code']
        stock_name = stock['name']

        # Get historical data with retry logic
        max_retries = 3
        df = None
        for attempt in range(max_retries):
            try:
                df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                        start_date=start_date, end_date=end_date, adjust="qfq")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  Retry {attempt + 1} for {stock_code}...")
                    time.sleep(2)
                else:
                    print(f"  Error processing {stock_code} after {max_retries} attempts: {e}")
                    continue

        if df is None or len(df) < 40:
            continue

        # Calculate MACD
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')
        df.set_index('日期', inplace=True)

        diff, dea, macd = calculate_macd(df['收盘'])

        # Get last 20 trading days
        last_20_days = df.tail(20)

        if len(last_20_days) < 20:
            continue

        # Find golden cross in last 5 trading days
        diff_last_20 = diff.loc[last_20_days.index]
        dea_last_20 = dea.loc[last_20_days.index]

        has_cross, cross_date = find_golden_cross(diff_last_20, dea_last_20, recent_days=5)

        if has_cross:
            # Calculate 20-day return
            close_end = last_20_days.iloc[-1]['收盘']
            close_start = last_20_days.iloc[0]['收盘']
            return_20d = (close_end - close_start) / close_start * 100

            results.append({
                'code': stock_code,
                'name': stock_name,
                'cross_date': cross_date.strftime('%Y-%m-%d'),
                'return_20d': round(return_20d, 2)
            })

            print(f"  {stock_code} {stock_name}: Golden cross on {cross_date.strftime('%Y-%m-%d')}, 20d return: {return_20d:.2f}%")

    except Exception as e:
        print(f"  Error processing {stock.get('code', 'unknown')}: {e}")
        continue

# Step 4: Sort by 20-day return and select top 5
print("\nStep 4: Sorting by 20-day return and selecting top 5...")
results_df = pd.DataFrame(results)

if not results_df.empty:
    results_df = results_df.sort_values('return_20d', ascending=False).head(5)

    # Write to file
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_11_semiconductor_macd/independent/claudecode/semiconductor_top5.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,股票名称,金叉日期,近20日涨幅(%)\n')
        for _, row in results_df.iterrows():
            f.write(f"{row['code']},{row['name']},{row['cross_date']},{row['return_20d']}\n")

    print(f"\nResults written to semiconductor_top5.txt")
    print(f"Top 5 stocks:")
    for _, row in results_df.iterrows():
        print(f"  {row['code']},{row['name']},{row['cross_date']},{row['return_20d']}%")
else:
    # No stocks found
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_11_semiconductor_macd/independent/claudecode/semiconductor_top5.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,股票名称,金叉日期,近20日涨幅(%)\n')
        f.write('# 无符合条件的股票\n')
    print("\nNo stocks found matching the criteria")

print("\nTask completed!")
