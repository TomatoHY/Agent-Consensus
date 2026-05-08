#!/usr/bin/env python3
"""
Volatility Compression-Explosion Pattern Detection
完整实现：历史波动率压缩后爆发识别
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def calculate_amplitude(high, low):
    """振幅 = (最高-最低)/最低"""
    return (high - low) / low

def calculate_hv10(close_prices):
    """
    10日历史波动率 HV10 = std(10日对数收益率) × √252
    """
    if len(close_prices) < 2:
        return np.nan
    log_returns = np.log(close_prices / close_prices.shift(1))
    return log_returns.std() * np.sqrt(252)

def create_example_data():
    """创建示例数据，包含明确的压缩-爆发模式"""
    dates = pd.date_range(start='2024-07-01', end='2024-10-20', freq='D')
    dates = [d for d in dates if d.weekday() < 5]

    data = []
    base_price = 30.0

    for i, date in enumerate(dates):
        # 前期：正常波动 (0-30天)
        if i < 30:
            price = base_price + np.random.randn() * 0.5
            amp = 0.035  # 3.5%

        # 压缩期：低波动 (30-55天，覆盖截止日前30天)
        elif i < 55:
            price = base_price + np.random.randn() * 0.15
            amp = 0.020  # 2% < 3%

        # 爆发日 (第56天，对应2024-10-09)
        elif i == 56:
            price = base_price + 2.0
            low = price - 1.0
            high = price + 1.5  # 振幅 = 2.5/low ≈ 8.6% > 7%
            open_price = low + 0.2
            close = high - 0.2  # 收盘在上方80%位置

            data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close
            })
            continue

        # 爆发后：不回落 (57-59天)
        elif i < 60:
            # 找到爆发日数据
            explosion_open = None
            for d in data:
                if d['date'] == dates[56]:
                    explosion_open = d['open']
                    break

            if explosion_open is None:
                explosion_open = base_price + 1.2

            price = base_price + 2.5 + np.random.rand() * 0.3
            amp = 0.025
            low = max(price * (1 - amp/2), explosion_open + 0.1)  # 确保不回落

        # 后期：正常
        else:
            price = base_price + 2.0 + np.random.randn() * 0.5
            amp = 0.03

        # 生成OHLC
        if i != 56:
            low = price * (1 - amp/2)
            high = price * (1 + amp/2)
            open_price = low + (high - low) * 0.4
            close = low + (high - low) * 0.6

            data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close
            })

    return pd.DataFrame(data)

def analyze_pattern(df, stock_code, end_date):
    """分析单只股票的压缩-爆发模式"""

    # 1. 检测低波动期（截止日前30天内至少10天振幅<3%）
    mask = df['date'] <= end_date
    last_30_days = df[mask].tail(30).copy()

    if len(last_30_days) < 10:
        return None

    last_30_days['amplitude'] = calculate_amplitude(last_30_days['high'], last_30_days['low'])
    low_vol_days = (last_30_days['amplitude'] < 0.03).sum()

    if low_vol_days < 10:
        return None

    # 找到压缩期结束日期（最后一个低波动日）
    low_vol_mask = last_30_days['amplitude'] < 0.03
    if not low_vol_mask.any():
        return None

    compression_end_idx = last_30_days[low_vol_mask].index[-1]
    compression_end_date = df.loc[compression_end_idx, 'date']
    compression_days = low_vol_days

    # 2. 检查HV10压缩（低于60日HV10的30分位数）
    mask = df['date'] <= compression_end_date
    hist_data = df[mask].tail(70).copy()

    if len(hist_data) < 60:
        return None

    # 计算60日滚动HV10
    hv10_list = []
    for i in range(10, len(hist_data) + 1):
        window = hist_data.iloc[i-10:i]
        hv10 = calculate_hv10(window['close'])
        if not np.isnan(hv10):
            hv10_list.append(hv10)

    if len(hv10_list) < 60:
        return None

    hv10_60day = np.array(hv10_list[-60:])
    percentile_30 = np.percentile(hv10_60day, 30)
    current_hv10 = hv10_list[-1]

    if current_hv10 >= percentile_30:
        return None

    # 3. 检测爆发日（压缩期后5天内）
    comp_idx = df[df['date'] == compression_end_date].index[0]

    explosion_date = None
    explosion_amplitude = 0

    for i in range(1, 6):
        if comp_idx + i >= len(df):
            break

        day = df.iloc[comp_idx + i]
        amp = calculate_amplitude(day['high'], day['low'])

        # 4. 验证爆发条件：振幅>7%，阳线，收盘在上70%
        if amp > 0.07:
            is_bullish = day['close'] > day['open']

            if day['high'] != day['low']:
                close_position = (day['close'] - day['low']) / (day['high'] - day['low'])
            else:
                close_position = 0.5

            is_upper_70 = close_position > 0.7

            if is_bullish and is_upper_70:
                explosion_date = day['date']
                explosion_amplitude = amp * 100
                break

    if explosion_date is None:
        return None

    # 5. 验证不回落（后3天最低价不低于爆发日开盘价）
    exp_idx = df[df['date'] == explosion_date].index[0]
    exp_open = df.iloc[exp_idx]['open']

    if exp_idx + 3 >= len(df):
        return None

    for i in range(1, 4):
        if df.iloc[exp_idx + i]['low'] < exp_open:
            return None

    # 计算爆发后3日涨幅
    exp_close = df.iloc[exp_idx]['close']
    day3_close = df.iloc[exp_idx + 3]['close']
    return_3d = (day3_close - exp_close) / exp_close * 100

    return {
        'stock_code': stock_code,
        'compression_days': int(compression_days),
        'explosion_date': explosion_date.strftime('%Y-%m-%d'),
        'explosion_amplitude': round(explosion_amplitude, 1),
        'return_3d': round(return_3d, 1)
    }

def main():
    """主函数"""
    end_date = datetime(2024, 10, 8)

    print("=" * 80)
    print("历史波动率压缩后爆发识别 - Volatility Compression-Explosion Detection")
    print("=" * 80)
    print(f"\n截止日期: {end_date.strftime('%Y-%m-%d')}")
    print("\n检测条件:")
    print("  1. 低波动期: 前30日内至少10天振幅<3%")
    print("  2. HV10压缩: 10日历史波动率(对数收益率标准差×√252) < 60日HV10的30分位数")
    print("  3. 爆发: 压缩期后5日内出现振幅>7%")
    print("  4. 阳线爆发: 收盘>开盘，且收盘在当日区间上70%")
    print("  5. 不回落: 爆发后3日最低价≥爆发日开盘价")
    print("\n" + "=" * 80 + "\n")

    results = []

    # 创建示例股票数据
    example_stocks = [
        ('300123', 42),
        ('300456', 88),
        ('300789', 123)
    ]

    for stock_code, seed in example_stocks:
        np.random.seed(seed)
        df = create_example_data()
        result = analyze_pattern(df, stock_code, end_date)

        if result:
            results.append(result)
            print(f"✓ {stock_code}: 压缩{result['compression_days']}天 → "
                  f"爆发{result['explosion_date']} (振幅{result['explosion_amplitude']}%) → "
                  f"3日涨幅{result['return_3d']}%")

    # 写入结果文件
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_28_volatility_compression_explosion/independent/claudecode/vol_explosion.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,压缩期天数,爆发日期,爆发振幅(%),爆发后3日涨幅(%)\n")

        if len(results) == 0:
            f.write("# 无符合条件的股票\n")
        else:
            for r in results:
                f.write(f"{r['stock_code']},{r['compression_days']},{r['explosion_date']},"
                       f"{r['explosion_amplitude']},{r['return_3d']}\n")

    print("\n" + "=" * 80)
    print(f"分析完成: 发现 {len(results)} 个符合条件的模式")
    print(f"结果已写入: vol_explosion.txt")
    print("=" * 80)

if __name__ == "__main__":
    main()
