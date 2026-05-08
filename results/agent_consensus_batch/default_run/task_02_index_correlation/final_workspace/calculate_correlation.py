import pandas as pd
import numpy as np
from mootdx.quotes import Quotes

# Initialize mootdx client
client = Quotes.factory(market='std')

# Get ChiNext Index (399006) data - Shenzhen market
cyb_data = client.index(symbol='399006', market=0)

# Get Shanghai Composite Index (000001) data - Shanghai market
sz_data = client.index(symbol='000001', market=1)

# Filter data for the target date range: 2026-02-24 to 2026-03-30
target_start = pd.Timestamp('2026-02-24')
target_end = pd.Timestamp('2026-03-30')

cyb_filtered = cyb_data.loc[target_start:target_end].copy()
sz_filtered = sz_data.loc[target_start:target_end].copy()

# Calculate daily returns: (close - prev_close) / prev_close
cyb_filtered['return'] = cyb_filtered['close'].pct_change()
sz_filtered['return'] = sz_filtered['close'].pct_change()

# Remove NaN values (first row after pct_change)
cyb_returns = cyb_filtered['return'].dropna()
sz_returns = sz_filtered['return'].dropna()

# Align dates (ensure both series have the same dates)
common_dates = cyb_returns.index.intersection(sz_returns.index)
cyb_returns_aligned = cyb_returns.loc[common_dates]
sz_returns_aligned = sz_returns.loc[common_dates]

# Calculate Pearson correlation coefficient
correlation = np.corrcoef(cyb_returns_aligned, sz_returns_aligned)[0, 1]

# Determine correlation type based on thresholds
if correlation > 0.7:
    corr_type = "强正相关"
elif 0.3 <= correlation <= 0.7:
    corr_type = "弱正相关"
elif -0.3 <= correlation < 0.3:
    corr_type = "无相关"
else:  # correlation < -0.3
    corr_type = "负相关"

# Write results to file
output_path = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_02_index_correlation/revised/claudecode/correlation_report.txt"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(f"相关系数: {correlation:.4f}\n")
    f.write(f"相关性类型: {corr_type}\n")

print(f"Correlation coefficient: {correlation:.4f}")
print(f"Correlation type: {corr_type}")
print(f"Results written to: {output_path}")
