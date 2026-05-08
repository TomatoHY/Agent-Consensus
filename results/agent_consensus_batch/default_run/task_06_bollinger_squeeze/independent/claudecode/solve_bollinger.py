import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import time

# Disable proxy
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    if key in os.environ:
        del os.environ[key]

# Get ChiNext (创业板) stock list
print("获取创业板股票列表...")
try:
    stock_list = ak.stock_info_a_code_name()
    gem_stocks = stock_list[stock_list['code'].str.startswith(('300', '301'))]
    print(f"创业板股票总数: {len(gem_stocks)}")
except Exception as e:
    print(f"Error: {e}")
    exit(1)

# Target date
end_date = "20240830"
start_date = "20240701"

count_consolidation = 0
total_checked = 0
failed_count = 0

print("\n开始计算布林带...")
print("注意：需要至少30个交易日数据，且最后20日用于计算布林带\n")

for idx, row in gem_stocks.iterrows():
    stock_code = row['code']

    try:
        # Get historical data with retry
        df = None
        for attempt in range(3):
            try:
                df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                        start_date=start_date, end_date=end_date, adjust="qfq")
                if df is not None and len(df) > 0:
                    break
                time.sleep(0.1)
            except:
                time.sleep(0.2)
                continue

        if df is None or len(df) < 30:
            failed_count += 1
            continue

        # Get last 30 trading days
        df = df.tail(30)

        if len(df) < 20:
            failed_count += 1
            continue

        # Get close prices
        close_prices = df['收盘'].astype(float).values

        if len(close_prices) < 20:
            failed_count += 1
            continue

        # Use last 20 days for Bollinger Bands calculation
        last_20 = close_prices[-20:]

        # Middle band: 20-day SMA
        middle_band = np.mean(last_20)

        # Standard deviation (sample std)
        std_dev = np.std(last_20, ddof=1)

        # Upper and lower bands
        upper_band = middle_band + 2 * std_dev
        lower_band = middle_band - 2 * std_dev

        # Bollinger Band width = (upper - lower) / middle
        if middle_band > 0:
            bb_width = (upper_band - lower_band) / middle_band

            # Debug first few stocks
            if total_checked < 5:
                print(f"{stock_code}: middle={middle_band:.2f}, upper={upper_band:.2f}, lower={lower_band:.2f}, width={bb_width:.4f} ({bb_width*100:.2f}%)")

            # Check if in consolidation (< 5% = 0.05)
            if bb_width < 0.05:
                count_consolidation += 1
                if count_consolidation <= 10:
                    print(f"  ✓ {stock_code} 符合条件: width={bb_width*100:.2f}%")

        total_checked += 1

        if total_checked % 100 == 0:
            print(f"\n进度: 已处理 {total_checked} 只, 符合条件 {count_consolidation} 只, 失败 {failed_count} 只\n")

        # Small delay to avoid rate limiting
        if total_checked % 10 == 0:
            time.sleep(0.1)

    except Exception as e:
        failed_count += 1
        continue

print(f"\n" + "="*60)
print(f"统计完成!")
print(f"总共检查了 {total_checked} 只股票")
print(f"失败 {failed_count} 只股票")
print(f"符合条件的股票数量: {count_consolidation}")

# Calculate ratio
if total_checked > 0:
    ratio = (count_consolidation / total_checked) * 100
else:
    ratio = 0.0

print(f"占创业板比例: {ratio:.2f}%")
print("="*60)

# Write results
output_path = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_06_bollinger_squeeze/independent/claudecode/bollinger_count.txt"

with open(output_path, 'w', encoding='utf-8') as f:
    f.write(f"符合条件的股票数量: {count_consolidation}\n")
    f.write(f"占创业板比例: {ratio:.2f}%\n")

print(f"\n结果已写入 bollinger_count.txt")
