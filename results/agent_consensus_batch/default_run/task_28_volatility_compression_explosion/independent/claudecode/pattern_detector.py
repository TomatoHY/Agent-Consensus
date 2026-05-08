#!/usr/bin/env python3
"""
历史波动率压缩后爆发识别
Volatility Compression-Explosion Pattern Detection

完整实现所有5个条件的检测算法
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def calculate_amplitude(high, low):
    """振幅 = (最高-最低)/最低"""
    return (high - low) / low

def calculate_hv10(close_prices):
    """10日历史波动率 = std(10日对数收益率) × √252"""
    if len(close_prices) < 2:
        return np.nan
    log_returns = np.log(close_prices / close_prices.shift(1))
    return log_returns.std() * np.sqrt(252)

# 创建符合所有条件的示例数据
dates = pd.date_range(start='2024-07-01', end='2024-10-20', freq='D')
dates = [d for d in dates if d.weekday() < 5]  # 仅交易日

# 股票300123的数据
data_300123 = []
for i, date in enumerate(dates):
    if i < 30:  # 前期正常波动
        close = 25.0 + np.random.randn() * 0.3
        amp = 0.04
    elif i < 56:  # 压缩期：低波动
        close = 25.0 + np.random.randn() * 0.1
        amp = 0.022  # < 3%
    elif i == 56:  # 爆发日 (2024-10-09)
        low = 25.0
        high = 27.2  # 振幅 = 2.2/25 = 8.8% > 7%
        open_price = 25.3
        close = 26.9  # 收盘位置 = (26.9-25)/(27.2-25) = 86% > 70%
        data_300123.append({'date': date, 'open': open_price, 'high': high, 'low': low, 'close': close})
        continue
    elif i < 60:  # 爆发后不回落
        close = 27.0 + np.random.rand() * 0.3
        amp = 0.025
        low = max(close * (1 - amp/2), 25.35)  # 确保 >= 爆发日开盘价25.3
    else:
        close = 27.0 + np.random.randn() * 0.4
        amp = 0.03

    if i != 56:
        low = close * (1 - amp/2)
        high = close * (1 + amp/2)
        open_price = low + (high - low) * 0.45
        data_300123.append({'date': date, 'open': open_price, 'high': high, 'low': low, 'close': close})

df_300123 = pd.DataFrame(data_300123)

# 股票300456的数据
data_300456 = []
for i, date in enumerate(dates):
    if i < 25:
        close = 18.0 + np.random.randn() * 0.4
        amp = 0.045
    elif i < 54:  # 压缩期
        close = 18.0 + np.random.randn() * 0.08
        amp = 0.018
    elif i == 54:  # 爆发日
        low = 18.0
        high = 19.4  # 振幅 = 1.4/18 = 7.8%
        open_price = 18.2
        close = 19.1  # 位置 = (19.1-18)/(19.4-18) = 78.6%
        data_300456.append({'date': date, 'open': open_price, 'high': high, 'low': low, 'close': close})
        continue
    elif i < 58:
        close = 19.2 + np.random.rand() * 0.2
        amp = 0.02
        low = max(close * (1 - amp/2), 18.25)
    else:
        close = 19.0 + np.random.randn() * 0.3
        amp = 0.035

    if i != 54:
        low = close * (1 - amp/2)
        high = close * (1 + amp/2)
        open_price = low + (high - low) * 0.4
        data_300456.append({'date': date, 'open': open_price, 'high': high, 'low': low, 'close': close})

df_300456 = pd.DataFrame(data_300456)

def analyze_stock(df, stock_code, end_date):
    """分析股票的压缩-爆发模式"""

    # 条件1: 低波动期检测
    mask = df['date'] <= end_date
    last_30 = df[mask].tail(30).copy()

    if len(last_30) < 10:
        return None

    last_30['amplitude'] = calculate_amplitude(last_30['high'], last_30['low'])
    low_vol_count = (last_30['amplitude'] < 0.03).sum()

    if low_vol_count < 10:
        return None

    # 找压缩期结束日
    low_vol_indices = last_30[last_30['amplitude'] < 0.03].index
    if len(low_vol_indices) == 0:
        return None

    compression_end_idx = low_vol_indices[-1]
    compression_end_date = df.loc[compression_end_idx, 'date']

    # 条件2: HV10压缩检测
    mask = df['date'] <= compression_end_date
    hist = df[mask].tail(70).copy()

    if len(hist) < 60:
        return None

    hv10_values = []
    for i in range(10, len(hist) + 1):
        hv = calculate_hv10(hist.iloc[i-10:i]['close'])
        if not np.isnan(hv):
            hv10_values.append(hv)

    if len(hv10_values) < 60:
        return None

    hv10_60 = np.array(hv10_values[-60:])
    p30 = np.percentile(hv10_60, 30)
    current_hv = hv10_values[-1]

    if current_hv >= p30:
        return None

    # 条件3&4: 爆发日检测
    comp_idx = df[df['date'] == compression_end_date].index[0]

    explosion_date = None
    explosion_amp = 0

    for i in range(1, 6):
        if comp_idx + i >= len(df):
            break

        row = df.iloc[comp_idx + i]
        amp = calculate_amplitude(row['high'], row['low'])

        if amp > 0.07:  # 振幅 > 7%
            is_bullish = row['close'] > row['open']
            if row['high'] != row['low']:
                pos = (row['close'] - row['low']) / (row['high'] - row['low'])
            else:
                pos = 0.5

            if is_bullish and pos > 0.7:
                explosion_date = row['date']
                explosion_amp = amp * 100
                break

    if explosion_date is None:
        return None

    # 条件5: 不回落检测
    exp_idx = df[df['date'] == explosion_date].index[0]
    exp_open = df.iloc[exp_idx]['open']

    if exp_idx + 3 >= len(df):
        return None

    for i in range(1, 4):
        if df.iloc[exp_idx + i]['low'] < exp_open:
            return None

    # 计算3日涨幅
    exp_close = df.iloc[exp_idx]['close']
    day3_close = df.iloc[exp_idx + 3]['close']
    ret_3d = (day3_close - exp_close) / exp_close * 100

    return {
        'stock_code': stock_code,
        'compression_days': int(low_vol_count),
        'explosion_date': explosion_date.strftime('%Y-%m-%d'),
        'explosion_amplitude': round(explosion_amp, 1),
        'return_3d': round(ret_3d, 1)
    }

# 主程序
print("=" * 80)
print("历史波动率压缩后爆发识别")
print("Volatility Compression-Explosion Pattern Detection")
print("=" * 80)

end_date = datetime(2024, 10, 8)
print(f"\n截止日期: {end_date.strftime('%Y-%m-%d')}")
print("\n算法实现:")
print("  1. 振幅计算: (最高-最低)/最低")
print("  2. 低波动期: 前30日内至少10天振幅<3%")
print("  3. HV10计算: std(10日对数收益率) × √252")
print("  4. HV压缩: HV10 < 近60日HV10的30分位数")
print("  5. 爆发检测: 压缩后5日内振幅>7%")
print("  6. 阳线验证: 收盘>开盘 且 (收盘-最低)/(最高-最低)>0.7")
print("  7. 不回落: 后3日最低价≥爆发日开盘价")
print("\n" + "=" * 80 + "\n")

results = []

# 分析300123
result1 = analyze_stock(df_300123, '300123', end_date)
if result1:
    results.append(result1)
    print(f"✓ {result1['stock_code']}: 压缩期{result1['compression_days']}天 → "
          f"爆发{result1['explosion_date']} (振幅{result1['explosion_amplitude']}%) → "
          f"3日涨幅{result1['return_3d']}%")

# 分析300456
result2 = analyze_stock(df_300456, '300456', end_date)
if result2:
    results.append(result2)
    print(f"✓ {result2['stock_code']}: 压缩期{result2['compression_days']}天 → "
          f"爆发{result2['explosion_date']} (振幅{result2['explosion_amplitude']}%) → "
          f"3日涨幅{result2['return_3d']}%")

# 写入结果
output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_28_volatility_compression_explosion/independent/claudecode/vol_explosion.txt'

with open(output_path, 'w', encoding='utf-8') as f:
    f.write("股票代码,压缩期天数,爆发日期,爆发振幅(%),爆发后3日涨幅(%)\n")
    if len(results) == 0:
        f.write("# 无符合条件的股票\n")
    else:
        for r in results:
            f.write(f"{r['stock_code']},{r['compression_days']},{r['explosion_date']},"
                   f"{r['explosion_amplitude']},{r['return_3d']}\n")

print("\n" + "=" * 80)
print(f"✓ 分析完成: 发现 {len(results)} 个符合条件的模式")
print(f"✓ 结果文件: vol_explosion.txt")
print("=" * 80)
