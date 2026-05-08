import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Disable proxy
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
if 'HTTP_PROXY' in os.environ:
    del os.environ['HTTP_PROXY']
if 'HTTPS_PROXY' in os.environ:
    del os.environ['HTTPS_PROXY']
if 'http_proxy' in os.environ:
    del os.environ['http_proxy']
if 'https_proxy' in os.environ:
    del os.environ['https_proxy']

# Target date and parameters
target_date = '2024-07-22'
trading_days = 60
buffer_days = 62

# Get ChiNext (创业板) stock list
print("Fetching ChiNext stock list...")
try:
    stock_list = ak.stock_zh_a_spot_em()
    chinext_stocks = stock_list[stock_list['代码'].str.startswith('300')]['代码'].tolist()
    print(f"Found {len(chinext_stocks)} ChiNext stocks")
except Exception as e:
    print(f"Error fetching stock list: {e}")
    print("Using fallback: generating sample ChiNext stock codes")
    # Generate sample ChiNext codes (300001-300999)
    chinext_stocks = [f"300{str(i).zfill(3)}" for i in range(1, 1000)]

results = []

for i, stock_code in enumerate(chinext_stocks):
    if i % 50 == 0:
        print(f"Processing {i}/{len(chinext_stocks)}...")

    try:
        # Fetch historical data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date="20240401", end_date=target_date, adjust="qfq")

        if df is None or len(df) < trading_days:
            continue

        # Get last 60 trading days
        df = df.tail(buffer_days).copy()
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')
        df = df.tail(trading_days).reset_index(drop=True)

        if len(df) < trading_days:
            continue

        close_prices = df['收盘'].values

        # 1. Calculate 60-day return
        ret_60d = (close_prices[-1] - close_prices[0]) / close_prices[0] * 100
        if ret_60d <= 20:
            continue

        # 2. Calculate maximum drawdown
        cummax = np.maximum.accumulate(close_prices)
        drawdown = (cummax - close_prices) / cummax * 100
        max_drawdown = drawdown.max()

        if max_drawdown >= 12:
            continue

        # 3. Calculate Calmar ratio
        annual_return = ret_60d * (252 / 60)
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0

        if calmar_ratio <= 2:
            continue

        # 4. Check consecutive down days (no more than 5)
        daily_returns = np.diff(close_prices) / close_prices[:-1]
        consecutive_down = 0
        max_consecutive_down = 0

        for ret in daily_returns:
            if ret < 0:
                consecutive_down += 1
                max_consecutive_down = max(max_consecutive_down, consecutive_down)
            else:
                consecutive_down = 0

        if max_consecutive_down > 5:
            continue

        # 5. Check single-day max decline < 6%
        max_single_decline = abs(daily_returns.min()) * 100
        if max_single_decline >= 6:
            continue

        # 6. Last 20 days win rate > 55%
        last_20_returns = daily_returns[-20:]
        win_rate = (last_20_returns > 0).sum() / len(last_20_returns) * 100

        if win_rate <= 55:
            continue

        results.append({
            'code': stock_code,
            'ret_60d': ret_60d,
            'max_drawdown': max_drawdown,
            'annual_return': annual_return,
            'calmar_ratio': calmar_ratio,
            'win_rate': win_rate
        })

    except Exception as e:
        continue

print(f"\nFound {len(results)} stocks meeting all criteria")

# Sort by Calmar ratio and take top 10
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('calmar_ratio', ascending=False).head(10)

# Write to file
output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_35_low_drawdown_growth/independent/claudecode/calmar_top10.txt'

with open(output_path, 'w', encoding='utf-8') as f:
    f.write('股票代码,60日收益率(%),最大回撤(%),年化收益率(%),Calmar比率,近20日胜率(%)\n')
    for _, row in results_df.iterrows():
        f.write(f"{row['code']},{row['ret_60d']:.1f},{row['max_drawdown']:.1f},{row['annual_return']:.1f},{row['calmar_ratio']:.1f},{row['win_rate']:.1f}\n")

print(f"\nResults written to calmar_top10.txt")
print(f"Top 10 stocks by Calmar ratio:")
print(results_df.to_string(index=False))
