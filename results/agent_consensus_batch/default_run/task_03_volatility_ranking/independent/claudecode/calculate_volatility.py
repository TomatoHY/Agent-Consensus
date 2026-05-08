import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Get ChiNext stock list (stocks starting with 300)
print("Fetching ChiNext stock list...")
stock_info = ak.stock_info_a_code_name()
chinext_stocks = stock_info[stock_info['code'].str.startswith('300')]['code'].tolist()
print(f"Found {len(chinext_stocks)} ChiNext stocks")

# Target date and calculate 10 trading days before
end_date = "20240531"
start_date = "20240501"  # Get more data to ensure we have 10 trading days

results = []

for i, stock_code in enumerate(chinext_stocks):
    if (i + 1) % 50 == 0:
        print(f"Processing {i+1}/{len(chinext_stocks)} stocks...")

    try:
        # Fetch historical data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=start_date, end_date=end_date, adjust="qfq")

        if df is not None and len(df) >= 10:
            # Get last 10 trading days
            last_10 = df.tail(10)
            close_prices = last_10['收盘'].values

            # Calculate volatility (coefficient of variation)
            mean_price = np.mean(close_prices)
            std_price = np.std(close_prices, ddof=1)

            if mean_price > 0:
                volatility = (std_price / mean_price) * 100
                results.append({
                    'code': stock_code,
                    'volatility': volatility
                })
    except Exception as e:
        # Skip stocks with errors
        continue

# Sort by volatility descending and get top 5
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('volatility', ascending=False)
top5 = results_df.head(5)

print("\nTop 5 stocks with highest volatility:")
print(top5)

# Write to file
output_path = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_03_volatility_ranking/independent/claudecode/volatility_top5.txt"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write("股票代码,波动率(%)\n")
    for _, row in top5.iterrows():
        f.write(f"{row['code']},{row['volatility']:.2f}\n")

print(f"\nResults written to {output_path}")
