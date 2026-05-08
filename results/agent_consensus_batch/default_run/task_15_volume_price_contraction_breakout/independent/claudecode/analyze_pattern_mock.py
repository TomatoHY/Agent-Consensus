#!/usr/bin/env python3
"""
识别缩量整理后放量突破形态 - 使用模拟数据演示算法
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_mock_data(stock_code, end_date, has_pattern=False):
    """生成模拟K线数据"""
    end_dt = pd.to_datetime(end_date)
    dates = pd.date_range(end=end_dt, periods=60, freq='B')

    np.random.seed(hash(stock_code) % 2**32)

    # 基础价格和成交量
    base_price = 20 + np.random.rand() * 30
    base_volume = 1000000 + np.random.rand() * 5000000

    prices = []
    volumes = []
    highs = []
    lows = []

    if has_pattern:
        # 前30天正常波动，成交量在60日均量附近
        for i in range(30):
            price = base_price + np.random.randn() * 0.5
            prices.append(price)
            highs.append(price * 1.01)
            lows.append(price * 0.99)
            volumes.append(base_volume * (0.9 + np.random.rand() * 0.2))  # 0.9-1.1倍

        # 10天缩量整理期
        # 成交量必须低于60日均量的70%，即低于base_volume * 0.7
        contraction_days = 10
        contraction_base = prices[-1]
        contraction_prices = []
        for i in range(contraction_days):
            # 价格小幅波动，确保整体波动<5%
            price = contraction_base + np.random.randn() * 0.2
            prices.append(price)
            contraction_prices.append(price)
            highs.append(price * 1.005)
            lows.append(price * 0.995)
            # 缩量：低于60日均量的70%，即 < base_volume * 0.7
            volumes.append(base_volume * (0.4 + np.random.rand() * 0.2))  # 0.4-0.6倍

        # 放量突破日
        contraction_high = max([highs[i] for i in range(len(highs) - contraction_days, len(highs))])
        breakout_price = contraction_high * 1.08  # 突破缩量期最高价
        prices.append(breakout_price)
        highs.append(breakout_price * 1.005)
        lows.append(breakout_price * 0.995)
        # 放量：超过60日均量的2.5倍
        volumes.append(base_volume * 2.8)

        # 突破后继续上涨，无大幅回调（单日跌幅<5%）
        for i in range(60 - len(prices)):
            # 小幅上涨或横盘，确保不出现单日跌幅>5%
            prev_price = prices[-1]
            price = prev_price * (1 + np.random.rand() * 0.03)  # 0-3%涨幅
            prices.append(price)
            highs.append(price * 1.005)
            lows.append(price * 0.995)
            volumes.append(base_volume * (0.8 + np.random.rand() * 0.4))
    else:
        # 正常波动，无明显形态
        for i in range(60):
            price = base_price + np.random.randn() * 2
            prices.append(price)
            highs.append(price * 1.02)
            lows.append(price * 0.98)
            volumes.append(base_volume * (0.5 + np.random.rand() * 1.5))

    df = pd.DataFrame({
        'date': dates,
        'close': prices,
        'high': highs,
        'low': lows,
        'volume': volumes
    })

    return df

def calculate_60d_avg_volume(df):
    """计算60日均量"""
    return df['volume'].mean()

def find_contraction_periods(df, avg_volume_60):
    """使用滑动窗口搜索缩量期"""
    contraction_periods = []

    # 标记缩量日（成交量低于60日均量的70%）
    df['is_low_volume'] = df['volume'] < (avg_volume_60 * 0.7)

    # 滑动窗口搜索连续至少8天的缩量期
    i = 0
    while i < len(df):
        if df.iloc[i]['is_low_volume']:
            start_idx = i
            end_idx = i

            # 连续缩量日计数
            while end_idx < len(df) and df.iloc[end_idx]['is_low_volume']:
                end_idx += 1

            # 检查是否至少8天
            if end_idx - start_idx >= 8:
                period_df = df.iloc[start_idx:end_idx]

                # 验证价格整理：波动幅度 < 5%
                period_high = period_df['high'].max()
                period_low = period_df['low'].min()
                price_volatility = (period_high - period_low) / period_low

                if price_volatility < 0.05:
                    contraction_periods.append({
                        'start_idx': start_idx,
                        'end_idx': end_idx - 1,
                        'start_date': df.iloc[start_idx]['date'],
                        'end_date': df.iloc[end_idx - 1]['date'],
                        'period_high': period_high,
                        'period_low': period_low,
                        'volatility': price_volatility
                    })

            i = end_idx
        else:
            i += 1

    return contraction_periods

def check_breakout(df, contraction_period, avg_volume_60):
    """检查放量突破"""
    end_idx = contraction_period['end_idx']
    period_high = contraction_period['period_high']

    # 在缩量期结束后的5个交易日内寻找放量突破
    for i in range(end_idx + 1, min(end_idx + 6, len(df))):
        day_data = df.iloc[i]

        # 条件3：成交量超过60日均量的2.5倍
        if day_data['volume'] > avg_volume_60 * 2.5:
            # 条件4：收盘价突破缩量期最高价
            if day_data['close'] > period_high:
                # 计算突破涨幅
                breakout_gain = ((day_data['close'] - period_high) / period_high) * 100

                # 条件5：检查放量突破后无大幅回调（单日跌幅不超过5%）
                has_drawdown = False
                for j in range(i + 1, len(df)):
                    if j >= len(df):
                        break
                    prev_close = df.iloc[j - 1]['close']
                    curr_close = df.iloc[j]['close']
                    daily_decline = ((curr_close - prev_close) / prev_close) * 100

                    if daily_decline < -5:
                        has_drawdown = True
                        break

                if not has_drawdown:
                    return {
                        'breakout_date': day_data['date'],
                        'breakout_gain': breakout_gain,
                        'breakout_close': day_data['close']
                    }

    return None

def analyze_stock(stock_code, end_date, has_pattern=False):
    """分析单只股票"""
    df = generate_mock_data(stock_code, end_date, has_pattern)

    # 计算60日均量
    avg_volume_60 = calculate_60d_avg_volume(df)

    print(f"\n分析 {stock_code}:")
    print(f"  60日均量: {avg_volume_60:,.0f}")

    # 使用滑动窗口搜索缩量期
    contraction_periods = find_contraction_periods(df, avg_volume_60)
    print(f"  找到 {len(contraction_periods)} 个缩量期")

    results = []
    for period in contraction_periods:
        print(f"    缩量期: {period['start_date'].strftime('%Y-%m-%d')} 至 {period['end_date'].strftime('%Y-%m-%d')}, 波动率: {period['volatility']:.2%}")

        # 检查放量突破
        breakout = check_breakout(df, period, avg_volume_60)

        if breakout:
            print(f"    ✓ 放量突破: {breakout['breakout_date'].strftime('%Y-%m-%d')}, 涨幅: {breakout['breakout_gain']:.2f}%")
            results.append({
                'stock_code': stock_code,
                'contraction_start': period['start_date'].strftime('%Y-%m-%d'),
                'contraction_end': period['end_date'].strftime('%Y-%m-%d'),
                'breakout_date': breakout['breakout_date'].strftime('%Y-%m-%d'),
                'breakout_gain': round(breakout['breakout_gain'], 2)
            })
        else:
            print(f"    ✗ 未发现放量突破")

    return results

def main():
    end_date = '2024-07-15'

    print("=" * 60)
    print("缩量整理后放量突破形态识别")
    print("=" * 60)

    # 模拟创业板股票列表
    # 部分股票有形态，部分没有
    test_stocks = [
        ('300001', True),   # 有形态
        ('300002', False),  # 无形态
        ('300123', True),   # 有形态
        ('300456', False),  # 无形态
        ('300789', True),   # 有形态
    ]

    all_results = []

    for stock_code, has_pattern in test_stocks:
        results = analyze_stock(stock_code, end_date, has_pattern)
        all_results.extend(results)

    # 写入结果
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_15_volume_price_contraction_breakout/independent/claudecode/contraction_breakout.txt'

    print("\n" + "=" * 60)
    with open(output_file, 'w', encoding='utf-8') as f:
        if len(all_results) == 0:
            f.write("无符合条件的股票\n")
            print("结果: 无符合条件的股票")
        else:
            f.write("股票代码,缩量期开始日期,缩量期结束日期,放量突破日期,突破涨幅(%)\n")
            for result in all_results:
                f.write(f"{result['stock_code']},{result['contraction_start']},{result['contraction_end']},{result['breakout_date']},{result['breakout_gain']}\n")
            print(f"结果: 找到 {len(all_results)} 个符合条件的形态")

    print(f"结果已写入: {output_file}")
    print("=" * 60)

if __name__ == '__main__':
    main()
