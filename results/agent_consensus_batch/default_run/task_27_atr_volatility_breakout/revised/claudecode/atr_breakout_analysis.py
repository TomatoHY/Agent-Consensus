#!/usr/bin/env python3
"""
ATR波动率扩张突破识别
筛选创业板中波动率扩张的股票
"""
from mootdx.quotes import Quotes
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_atr(df, period=14):
    """
    计算ATR（Average True Range）使用Wilder平滑法
    """
    # 计算True Range
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values

    tr = np.zeros(len(df))
    for i in range(len(df)):
        if i == 0:
            tr[i] = high[i] - low[i]
        else:
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )

    # Wilder平滑法计算ATR
    atr = np.zeros(len(df))
    atr[period-1] = np.mean(tr[:period])

    for i in range(period, len(df)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

    return atr

def analyze_stock(client, code, target_date='2024-09-09'):
    """
    分析单只股票是否符合ATR突破条件
    """
    try:
        # 获取足够的历史数据（需要更多数据以覆盖2024-09-09）
        # offset参数获取最近N条，需要足够大以包含目标日期
        bars = client.bars(symbol=code, frequency=9, offset=800)

        if bars is None or len(bars) < 80:
            return None

        # 重置索引以避免datetime既是索引又是列的问题
        bars = bars.reset_index(drop=True)

        # 确保datetime列存在
        if 'datetime' in bars.columns:
            bars['datetime'] = pd.to_datetime(bars['datetime'])
            bars = bars.sort_values('datetime').reset_index(drop=True)

        # 计算ATR
        atr = calculate_atr(bars, period=14)
        bars['atr'] = atr

        # 找到目标日期或最接近的日期
        bars['date_str'] = bars['datetime'].dt.strftime('%Y-%m-%d')
        target_idx = bars[bars['date_str'] <= target_date].index

        if len(target_idx) == 0:
            return None

        current_idx = target_idx[-1]

        # 确保有足够的历史数据
        if current_idx < 60:
            return None

        # 获取当前ATR
        current_atr = bars.loc[current_idx, 'atr']

        if current_atr == 0 or np.isnan(current_atr):
            return None

        # 计算近60日ATR的80分位数
        atr_60d = bars.loc[current_idx-59:current_idx, 'atr'].values
        atr_80pct = np.percentile(atr_60d[atr_60d > 0], 80)

        # 条件1: ATR突破80分位数
        if current_atr <= atr_80pct:
            return None

        # 条件2: 收盘价突破近20日最高价
        if current_idx < 20:
            return None

        high_20d = bars.loc[current_idx-20:current_idx-1, 'high'].max()
        current_close = bars.loc[current_idx, 'close']

        if current_close <= high_20d:
            return None

        # 条件3: 成交量 > 20日均量的2倍
        vol_20d_avg = bars.loc[current_idx-20:current_idx-1, 'volume'].mean()
        current_vol = bars.loc[current_idx, 'volume']

        if current_vol <= vol_20d_avg * 2:
            return None

        # 条件4: 收阳且涨幅>3%
        current_open = bars.loc[current_idx, 'open']

        if current_close <= current_open:
            return None

        pct_change = (current_close - current_open) / current_open * 100

        if pct_change <= 3.0:
            return None

        # 所有条件满足，返回结果
        breakout_date = bars.loc[current_idx, 'date_str']

        return {
            'code': code,
            'atr': round(current_atr, 2),
            'atr_80pct': round(atr_80pct, 2),
            'breakout_date': breakout_date,
            'pct_change': round(pct_change, 2)
        }

    except Exception as e:
        print(f"处理股票 {code} 时出错: {e}")
        return None

def main():
    print("初始化mootdx客户端...")
    client = Quotes.factory(market='std')

    print("获取创业板股票列表...")
    stocks = client.stocks(market=0)
    chinext = stocks[stocks['code'].str.startswith(('300', '301'))]

    print(f"找到 {len(chinext)} 只创业板股票")
    print("开始筛选符合条件的股票...")

    results = []
    total = len(chinext)

    for idx, row in chinext.iterrows():
        code = row['code']
        if (idx + 1) % 50 == 0:
            print(f"进度: {idx + 1}/{total}")

        result = analyze_stock(client, code)
        if result:
            results.append(result)
            print(f"✓ 找到符合条件的股票: {code}")

    print(f"\n筛选完成! 共找到 {len(results)} 只符合条件的股票")

    # 写入结果文件
    output_file = 'atr_breakout.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        if len(results) == 0:
            f.write("无符合条件的股票\n")
        else:
            f.write("股票代码,截至2024-09-09的ATR,ATR的60日80分位数,突破日期,当日涨幅(%)\n")
            for r in results:
                f.write(f"{r['code']},{r['atr']},{r['atr_80pct']},{r['breakout_date']},{r['pct_change']}\n")

    print(f"结果已写入 {output_file}")

    return results

if __name__ == '__main__':
    results = main()
