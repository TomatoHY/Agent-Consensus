#!/usr/bin/env python3
"""
调试版本：检查布林带计算和日期筛选是否正确
"""
import pandas as pd
import numpy as np
from mootdx.quotes import Quotes


def calculate_bollinger_bands(close_prices, window=20):
    """计算布林带"""
    if len(close_prices) < window:
        return None, None, None

    middle = close_prices.rolling(window=window).mean()
    std = close_prices.rolling(window=window).std()
    upper = middle + 2 * std
    lower = middle - 2 * std

    return upper, middle, lower


def calculate_bollinger_width(upper, middle, lower):
    """计算布林带宽度"""
    if middle == 0 or pd.isna(middle) or pd.isna(upper) or pd.isna(lower):
        return None
    width = (upper - lower) / middle
    return width


# 初始化客户端
client = Quotes.factory(market='std')

# 获取创业板股票列表
stocks = client.stocks(market=0)
chinext = stocks[stocks['code'].str.startswith(('300', '301'))]

# 测试前5只股票
print("=== 测试前5只股票的布林带计算 ===\n")

for i in range(min(5, len(chinext))):
    code = chinext.iloc[i]['code']
    name = chinext.iloc[i]['name']

    print(f"股票: {code} ({name})")

    try:
        # 获取500天数据
        bars = client.bars(symbol=code, frequency=9, offset=500)

        if bars is None or len(bars) < 50:
            print("  数据不足\n")
            continue

        bars = bars.sort_index()
        bars['date_str'] = bars.index.strftime('%Y-%m-%d')

        # 检查日期范围
        print(f"  数据日期范围: {bars['date_str'].iloc[0]} 到 {bars['date_str'].iloc[-1]}")

        # 筛选到2024-08-30
        target_data = bars[bars['date_str'] <= '2024-08-30']
        print(f"  2024-08-30之前的数据: {len(target_data)} 条")

        if len(target_data) < 50:
            print("  筛选后数据不足\n")
            continue

        # 计算布林带
        close = target_data['close']
        upper, middle, lower = calculate_bollinger_bands(close, window=20)

        if upper is None:
            print("  布林带计算失败\n")
            continue

        # 获取最后一天的数据
        last_date = target_data['date_str'].iloc[-1]
        last_upper = upper.iloc[-1]
        last_middle = middle.iloc[-1]
        last_lower = lower.iloc[-1]

        width = calculate_bollinger_width(last_upper, last_middle, last_lower)

        print(f"  最后交易日: {last_date}")
        print(f"  收盘价: {close.iloc[-1]:.2f}")
        print(f"  上轨: {last_upper:.2f}")
        print(f"  中轨: {last_middle:.2f}")
        print(f"  下轨: {last_lower:.2f}")
        print(f"  布林带宽度: {width:.4f} ({width*100:.2f}%)")
        print(f"  是否盘整(<5%): {'是' if width < 0.05 else '否'}")
        print()

    except Exception as e:
        print(f"  错误: {e}\n")

# 统计所有股票
print("\n=== 统计所有创业板股票 ===")
print(f"总数: {len(chinext)}")

squeeze_count = 0
valid_count = 0
width_list = []

for idx, row in chinext.iterrows():
    code = row['code']

    try:
        bars = client.bars(symbol=code, frequency=9, offset=500)

        if bars is None or len(bars) < 50:
            continue

        bars = bars.sort_index()
        bars['date_str'] = bars.index.strftime('%Y-%m-%d')
        target_data = bars[bars['date_str'] <= '2024-08-30']

        if len(target_data) < 50:
            continue

        close = target_data['close']
        upper, middle, lower = calculate_bollinger_bands(close, window=20)

        if upper is None:
            continue

        width = calculate_bollinger_width(upper.iloc[-1], middle.iloc[-1], lower.iloc[-1])

        if width is None:
            continue

        valid_count += 1
        width_list.append(width)

        if width < 0.05:
            squeeze_count += 1
            print(f"  盘整股票: {code} 宽度={width*100:.2f}%")

    except:
        pass

print(f"\n有效股票: {valid_count}")
print(f"盘整股票: {squeeze_count}")
print(f"占比: {squeeze_count/valid_count*100:.2f}%")

if width_list:
    print(f"\n宽度统计:")
    print(f"  最小: {min(width_list)*100:.2f}%")
    print(f"  最大: {max(width_list)*100:.2f}%")
    print(f"  平均: {np.mean(width_list)*100:.2f}%")
    print(f"  中位数: {np.median(width_list)*100:.2f}%")
