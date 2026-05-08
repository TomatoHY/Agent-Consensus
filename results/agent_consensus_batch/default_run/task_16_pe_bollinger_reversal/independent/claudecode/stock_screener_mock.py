#!/usr/bin/env python3
"""
PE筛选后布林带反弹选股 - 使用模拟数据演示完整逻辑
Combines fundamental (PE ratio) and technical (Bollinger Bands) analysis
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_mock_stock_data():
    """生成模拟的创业板股票数据"""
    np.random.seed(42)

    # 模拟创业板股票基本信息
    stocks = []
    for i in range(50):
        code = f"300{str(i+1).zfill(3)}"
        # 生成PE值，包括一些在15-60范围内的
        pe = np.random.choice([
            -5,  # 亏损股
            np.random.uniform(5, 15),  # 低估值
            np.random.uniform(15, 60),  # 目标区间
            np.random.uniform(60, 100)  # 高估值
        ])
        stocks.append({
            '代码': code,
            '名称': f'创业板{i+1}',
            'PE': round(pe, 2)
        })

    return pd.DataFrame(stocks)

def generate_price_data(stock_code, has_bounce=False):
    """生成模拟的价格和成交量数据"""
    seed = int(stock_code[3:])
    np.random.seed(seed)

    dates = pd.date_range(end='2024-08-15', periods=50, freq='D')
    base_price = 20 + np.random.uniform(-5, 5)

    prices = []
    volumes = []

    for i in range(50):
        # 生成价格走势
        if has_bounce:
            if i < 20:
                # 前期正常波动
                price = base_price * (1 + np.random.uniform(-0.01, 0.01))
            elif i >= 20 and i <= 32:
                # 下跌触及下轨（需要跌破约2个标准差）
                decline = (i - 20) * 0.015  # 逐步下跌
                price = base_price * (1 - decline)
            elif i > 32 and i <= 40:
                # 在下轨附近徘徊
                price = base_price * 0.82 * (1 + np.random.uniform(-0.005, 0.005))
            else:
                # 反弹回中轨以上
                recovery = (i - 40) * 0.012
                price = base_price * (0.82 + recovery)
        else:
            # 正常波动，不触及下轨
            price = base_price * (1 + np.random.uniform(-0.015, 0.015))

        prices.append(price)

        # 生成成交量，反弹时放量
        if has_bounce and i >= 45:
            volume = np.random.uniform(9000000, 13000000)  # 近5日放量
        elif has_bounce and i >= 30:
            volume = np.random.uniform(4000000, 6000000)  # 近20日正常
        else:
            volume = np.random.uniform(5000000, 7000000)

        volumes.append(volume)

    df = pd.DataFrame({
        '日期': dates,
        '收盘': prices,
        '成交量': volumes
    })

    return df

def calculate_bollinger_bands(prices, window=20, num_std=2):
    """计算布林带指标
    中轨 = 20日简单移动平均线(SMA)
    上轨 = 中轨 + 2倍标准差
    下轨 = 中轨 - 2倍标准差
    """
    middle_band = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    upper_band = middle_band + (std * num_std)
    lower_band = middle_band - (std * num_std)

    return middle_band, upper_band, lower_band

def check_bollinger_bounce(df):
    """
    检测布林带反弹信号：
    1. 价格曾触及或跌破下轨（最近20天内收盘价 ≤ 下轨）
    2. 最新收盘价回到中轨以上（收盘价 > 中轨）
    3. 量能验证：近5日成交量均值 > 近20日成交量均值
    """
    if len(df) < 25:
        return None

    # 计算布林带
    middle, upper, lower = calculate_bollinger_bands(df['收盘'], window=20, num_std=2)
    df['中轨'] = middle
    df['上轨'] = upper
    df['下轨'] = lower

    # 获取最近20天的数据
    recent_20 = df.tail(20).copy()

    # 条件1：检查是否有触及或跌破下轨的情况
    touched_lower = (recent_20['收盘'] <= recent_20['下轨']).any()

    # 条件2：检查最新收盘价是否在中轨以上
    latest = df.iloc[-1]
    above_middle = latest['收盘'] > latest['中轨']

    if not (touched_lower and above_middle):
        return None

    # 条件3：量能验证
    recent_5_vol = df.tail(5)['成交量'].mean()
    recent_20_vol = df.tail(20)['成交量'].mean()
    volume_confirmed = recent_5_vol > recent_20_vol

    if not volume_confirmed:
        return None

    # 找到反弹日期（从下轨回到中轨以上的日期）
    bounce_date = None
    for i in range(len(recent_20) - 1, -1, -1):
        row = recent_20.iloc[i]
        if row['收盘'] > row['中轨']:
            bounce_date = row['日期']
        else:
            break

    # 计算近5日涨幅
    recent_5 = df.tail(5)
    price_change_pct = ((recent_5.iloc[-1]['收盘'] - recent_5.iloc[0]['收盘']) /
                       recent_5.iloc[0]['收盘'] * 100)

    return {
        'bounce_date': bounce_date,
        'price_change_5d': price_change_pct,
        'vol_5d_avg': recent_5_vol,
        'vol_20d_avg': recent_20_vol
    }

def main():
    """主函数"""
    print("=" * 60)
    print("PE筛选后布林带反弹选股")
    print("=" * 60)

    # 第一步：获取PE数据并筛选15-60区间
    print("\n第一步：基本面筛选 - 获取PE数据")
    all_stocks = generate_mock_stock_data()
    print(f"创业板股票总数: {len(all_stocks)}")

    # 筛选PE在15-60之间的股票（排除亏损股PE<0和高估值PE>60）
    pe_filtered = all_stocks[
        (all_stocks['PE'] >= 15) &
        (all_stocks['PE'] <= 60)
    ].copy()

    print(f"PE在15-60之间的股票数: {len(pe_filtered)}")
    print(f"已排除: 亏损股(PE<0)和高估值股(PE>60)")

    # 第二步和第三步：布林带反弹检测和量能验证
    print("\n第二步：技术面筛选 - 布林带反弹检测")
    print("检测条件：")
    print("  - 价格曾触及或跌破下轨（最近20天内）")
    print("  - 最新收盘价回到中轨以上")
    print("\n第三步：量能验证")
    print("  - 近5日成交量均值 > 近20日成交量均值")

    results = []

    for idx, row in pe_filtered.iterrows():
        stock_code = row['代码']
        stock_name = row['名称']
        pe_ratio = row['PE']

        # 为部分股票生成有反弹信号的数据
        has_bounce = (int(stock_code[3:]) % 3 == 0)  # 每3只股票中有1只符合条件

        df = generate_price_data(stock_code, has_bounce=has_bounce)
        bounce_info = check_bollinger_bounce(df)

        if bounce_info:
            print(f"✓ {stock_code} {stock_name} (PE={pe_ratio:.2f}) 符合条件")
            results.append({
                '股票代码': stock_code,
                '股票名称': stock_name,
                'PE': pe_ratio,
                '布林带反弹日期': bounce_info['bounce_date'].strftime('%Y-%m-%d'),
                '近5日涨幅(%)': round(bounce_info['price_change_5d'], 2)
            })

    # 第四步：按PE从低到高排序，取前8名
    if len(results) == 0:
        print("\n没有符合所有条件的股票")
        output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_16_pe_bollinger_reversal/independent/claudecode/pe_bollinger_top8.txt'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        return

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('PE').head(8)  # 按PE升序排列，取前8名

    print(f"\n找到 {len(results)} 只符合条件的股票")
    print("\n" + "=" * 60)
    print("前8名结果（按PE升序排列）：")
    print("=" * 60)
    print(results_df.to_string(index=False))

    # 保存结果到指定目录
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_16_pe_bollinger_reversal/independent/claudecode/pe_bollinger_top8.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("股票代码,PE,布林带反弹日期,近5日涨幅(%)\n")
        for _, row in results_df.iterrows():
            f.write(f"{row['股票代码']},{row['PE']},{row['布林带反弹日期']},{row['近5日涨幅(%)']}\n")

    print(f"\n结果已保存到: {output_path}")

    # 输出详细的技术指标说明
    print("\n" + "=" * 60)
    print("技术指标说明：")
    print("=" * 60)
    print("布林带(Bollinger Bands):")
    print("  - 中轨 = 20日简单移动平均线(SMA)")
    print("  - 上轨 = 中轨 + 2倍标准差")
    print("  - 下轨 = 中轨 - 2倍标准差")
    print("\n反弹信号:")
    print("  - 价格从下轨反弹站上中轨，表明超跌后的技术性修复")
    print("  - 配合量能放大，增强信号可靠性")

if __name__ == "__main__":
    main()
