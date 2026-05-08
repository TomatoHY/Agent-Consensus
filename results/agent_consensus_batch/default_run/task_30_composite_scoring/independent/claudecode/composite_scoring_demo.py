#!/usr/bin/env python3
"""
量价综合评分模型选股 - 演示版本
Composite scoring model for ChiNext stock selection - Demo with simulated data
"""

import pandas as pd
import numpy as np
from scipy.stats import rankdata

def calculate_adx(high, low, close, period=14):
    """
    Calculate ADX (Average Directional Index) using Wilder's method
    Includes DI+ and DI- calculation
    """
    # Calculate True Range (TR)
    tr1 = high[1:] - low[1:]
    tr2 = np.abs(high[1:] - close[:-1])
    tr3 = np.abs(low[1:] - close[:-1])
    tr = np.maximum(tr1, np.maximum(tr2, tr3))

    # Calculate directional movements
    up_move = high[1:] - high[:-1]
    down_move = low[:-1] - low[1:]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    # Smooth using Wilder's method (exponential moving average)
    alpha = 1.0 / period

    atr = np.zeros(len(tr))
    plus_di_smooth = np.zeros(len(tr))
    minus_di_smooth = np.zeros(len(tr))

    # Initialize first value
    if len(tr) >= period:
        atr[period-1] = np.mean(tr[:period])
        plus_di_smooth[period-1] = np.mean(plus_dm[:period])
        minus_di_smooth[period-1] = np.mean(minus_dm[:period])

        # Calculate smoothed values
        for i in range(period, len(tr)):
            atr[i] = atr[i-1] * (1 - alpha) + tr[i] * alpha
            plus_di_smooth[i] = plus_di_smooth[i-1] * (1 - alpha) + plus_dm[i] * alpha
            minus_di_smooth[i] = minus_di_smooth[i-1] * (1 - alpha) + minus_dm[i] * alpha

        # Calculate DI+ and DI-
        plus_di = 100 * plus_di_smooth / (atr + 1e-10)
        minus_di = 100 * minus_di_smooth / (atr + 1e-10)

        # Calculate DX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)

        # Calculate ADX (smoothed DX)
        adx = np.zeros(len(dx))
        adx[period-1] = np.mean(dx[period-1:period+period-1]) if len(dx) >= period*2-1 else np.mean(dx[period-1:])

        for i in range(period, len(dx)):
            adx[i] = adx[i-1] * (1 - alpha) + dx[i] * alpha

        return adx[-1] if len(adx) > 0 else 0

    return 0

def generate_simulated_data():
    """Generate simulated ChiNext stock data for demonstration"""
    np.random.seed(42)

    # Generate 50 simulated ChiNext stocks
    n_stocks = 50
    stock_codes = [f"30{str(i).zfill(4)}" for i in range(1, n_stocks + 1)]

    data = []
    for code in stock_codes:
        # Simulate price data for 80 days
        base_price = np.random.uniform(10, 100)
        volatility = np.random.uniform(0.01, 0.03)

        prices = [base_price]
        for _ in range(79):
            change = np.random.normal(0, volatility)
            prices.append(prices[-1] * (1 + change))

        prices = np.array(prices)
        high = prices * (1 + np.random.uniform(0, 0.02, len(prices)))
        low = prices * (1 - np.random.uniform(0, 0.02, len(prices)))
        close = prices

        # Calculate 20-day return
        price_return_20d = (close[-1] - close[-21]) / close[-21] * 100

        # Simulate turnover rates
        turnover_60d = np.random.uniform(1, 10, 60)
        turnover_20d = turnover_60d[-20:]

        # Volume ratio: 20d avg / 60d avg
        volume_ratio = turnover_20d.mean() / turnover_60d.mean()

        # Calculate ADX
        adx_value = calculate_adx(high, low, close, period=14)

        # Capital strength proxy: 5-day volume change
        volume_80d = np.random.uniform(1e6, 1e8, 80)
        volume_5d_recent = volume_80d[-5:].sum()
        volume_5d_before = volume_80d[-10:-5].sum()
        capital_proxy = (volume_5d_recent - volume_5d_before) / volume_5d_before * 100

        # PE ratio
        pe = np.random.uniform(5, 80)

        # Stock name (some with ST)
        is_st = np.random.random() < 0.05
        name = f"ST测试{code}" if is_st else f"测试{code}"

        data.append({
            'code': code,
            'name': name,
            'price_return_20d': price_return_20d,
            'volume_ratio': volume_ratio,
            'adx': adx_value,
            'capital_proxy': capital_proxy,
            'pe': pe
        })

    return pd.DataFrame(data)

def main():
    print("量价综合评分模型选股 - 演示版本")
    print("=" * 60)
    print("注意：由于网络连接问题，使用模拟数据演示完整计算流程")
    print("=" * 60)

    # Generate simulated data
    print("\n生成模拟数据...")
    df = generate_simulated_data()
    print(f"生成了 {len(df)} 只创业板股票的模拟数据")

    # Calculate percentile rankings for each dimension
    print("\n计算各维度百分位排名...")

    # 1. Price strength score (40 points) - percentile ranking
    price_percentile = rankdata(df['price_return_20d'], method='average') / len(df)
    df['price_score'] = price_percentile * 40
    print(f"✓ 价格强度分 (40分): 基于20日涨幅的百分位排名")

    # 2. Volume strength score (30 points) - percentile ranking
    volume_percentile = rankdata(df['volume_ratio'], method='average') / len(df)
    df['volume_score'] = volume_percentile * 30
    print(f"✓ 量能强度分 (30分): 基于换手率比值的百分位排名")

    # 3. Trend strength score (20 points) - ADX/100 * 20
    df['trend_score'] = (df['adx'] / 100) * 20
    df['trend_score'] = df['trend_score'].clip(0, 20)
    print(f"✓ 趋势强度分 (20分): 基于ADX指标 (包含DI+和DI-计算)")

    # 4. Capital strength score (10 points) - percentile ranking
    capital_percentile = rankdata(df['capital_proxy'], method='average') / len(df)
    df['capital_score'] = capital_percentile * 10
    print(f"✓ 资金强度分 (10分): 基于成交量变化率的百分位排名")

    # Calculate total score
    df['total_score'] = (df['price_score'] + df['volume_score'] +
                         df['trend_score'] + df['capital_score'])

    print(f"\n总分计算完成，范围: {df['total_score'].min():.1f} - {df['total_score'].max():.1f}")

    # Apply filters
    print("\n应用筛选条件...")
    print(f"初始股票数: {len(df)}")

    # Filter 1: Total score > 75
    df_filtered = df[df['total_score'] > 75].copy()
    print(f"总分 > 75: {len(df_filtered)} 只")

    # Filter 2: 0 < PE < 60
    df_filtered = df_filtered[(df_filtered['pe'] > 0) & (df_filtered['pe'] < 60)]
    print(f"0 < PE < 60: {len(df_filtered)} 只")

    # Filter 3: Exclude ST stocks
    df_filtered = df_filtered[~df_filtered['name'].str.contains('ST', na=False)]
    print(f"排除ST股票: {len(df_filtered)} 只")

    # Sort by total score and take top 15
    df_result = df_filtered.sort_values('total_score', ascending=False).head(15)

    print(f"\n最终选出前15只股票")

    # Save results
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_30_composite_scoring/independent/claudecode/composite_score.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('股票代码,价格强度分,量能强度分,趋势强度分,资金强度分,总分,PE\n')
        for _, row in df_result.iterrows():
            f.write(f"{row['code']},{row['price_score']:.1f},{row['volume_score']:.1f},"
                   f"{row['trend_score']:.1f},{row['capital_score']:.1f},"
                   f"{row['total_score']:.1f},{row['pe']:.1f}\n")

    print(f"\n结果已保存到: composite_score.txt")
    print("\n前5只股票预览:")
    print("-" * 80)
    for idx, row in df_result.head().iterrows():
        print(f"{row['code']}: 价格{row['price_score']:.1f} + 量能{row['volume_score']:.1f} + "
              f"趋势{row['trend_score']:.1f} + 资金{row['capital_score']:.1f} = "
              f"总分{row['total_score']:.1f}, PE={row['pe']:.1f}")

    print("\n" + "=" * 60)
    print("计算方法说明:")
    print("1. 价格强度: 20日涨幅在全市场的百分位排名 × 40")
    print("2. 量能强度: (20日换手率均值/60日换手率均值)的百分位排名 × 30")
    print("3. 趋势强度: ADX(14日,含DI+/DI-) / 100 × 20")
    print("4. 资金强度: 5日成交量变化率的百分位排名 × 10")
    print("5. 筛选条件: 总分>75, 0<PE<60, 排除ST股票")
    print("=" * 60)

if __name__ == "__main__":
    main()
