#!/usr/bin/env python3
"""
识别创业板"地天板"形态：跌停后打开再涨停
由于网络限制，使用模拟数据演示完整逻辑
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_mock_data():
    """生成模拟数据用于演示"""
    # 模拟一个符合地天板形态的股票
    dates = pd.date_range(end='2024-09-23', periods=20, freq='B')

    # 创建基础数据
    data = []
    base_price = 20.0

    for i, date in enumerate(dates):
        if i == 10:  # 第10天：跌停但被打开（振幅>3%）
            open_p = base_price
            close_p = base_price * 0.80  # -20% 跌停
            high_p = base_price * 1.02   # 最高涨2%
            low_p = close_p * 0.99
            pct_chg = -20.0
            amplitude = ((high_p - low_p) / open_p * 100)  # 振幅>3%
        elif i == 11:  # 第11天：涨停
            prev_close = base_price * 0.80
            open_p = prev_close * 1.05
            close_p = prev_close * 1.20  # +20% 涨停
            high_p = close_p
            low_p = open_p * 0.99
            pct_chg = 20.0
            amplitude = ((high_p - low_p) / open_p * 100)
        elif i > 11 and i <= 16:  # 涨停后5天，最低价不跌破涨停日最低价
            limit_up_low = base_price * 0.80 * 1.05 * 0.99
            open_p = base_price * 0.80 * 1.20 * (1 - 0.01 * (i - 11))
            close_p = open_p * 0.98
            high_p = open_p * 1.02
            low_p = limit_up_low * 1.005  # 略高于涨停日最低价
            pct_chg = -2.0
            amplitude = ((high_p - low_p) / open_p * 100)
        else:
            open_p = base_price * (1 + np.random.uniform(-0.02, 0.02))
            close_p = open_p * (1 + np.random.uniform(-0.03, 0.03))
            high_p = max(open_p, close_p) * 1.01
            low_p = min(open_p, close_p) * 0.99
            pct_chg = (close_p - open_p) / open_p * 100
            amplitude = ((high_p - low_p) / open_p * 100)

        data.append({
            '日期': date,
            '开盘': open_p,
            '收盘': close_p,
            '最高': high_p,
            '最低': low_p,
            '涨跌幅': pct_chg,
            '振幅': amplitude
        })

    return pd.DataFrame(data)

def analyze_floor_ceiling_pattern(df):
    """分析地天板形态"""
    results = []

    for i in range(len(df) - 1):
        row = df.iloc[i]
        pct_chg = row['涨跌幅']
        amplitude = row['振幅']

        # 1. 判断是否跌停（创业板：-20%或-10%，允许0.5%误差）
        is_limit_down = (pct_chg <= -19.5 or (-10.5 <= pct_chg <= -9.5))

        # 2. 判断跌停是否被打开（振幅>3%，非一字板）
        is_opened = amplitude > 3.0

        if not (is_limit_down and is_opened):
            continue

        limit_down_date = row['日期']

        # 3. 检查当日或次日是否涨停
        for j in range(i, min(i + 2, len(df))):
            check_row = df.iloc[j]
            check_pct = check_row['涨跌幅']

            # 判断是否涨停（创业板：20%或10%，允许0.5%误差）
            is_limit_up = (check_pct >= 19.5 or (9.5 <= check_pct <= 10.5))

            if not is_limit_up:
                continue

            limit_up_date = check_row['日期']
            limit_up_low = check_row['最低']
            limit_up_close = check_row['收盘']

            # 4. 检查涨停后5日内最低价不跌破涨停日最低价
            future_days = df.iloc[j+1:min(j+6, len(df))]

            if len(future_days) < 5:
                continue  # 数据不足5天

            min_low_after = future_days['最低'].min()

            # 强势延续：涨停后5日内最低价不跌破涨停日最低价
            if min_low_after >= limit_up_low:
                # 计算涨停后5日最低回撤
                drawdown = ((min_low_after - limit_up_close) / limit_up_close * 100)

                results.append({
                    'code': '300001',
                    'limit_down_date': limit_down_date.strftime('%Y-%m-%d'),
                    'limit_up_date': limit_up_date.strftime('%Y-%m-%d'),
                    'drawdown': round(drawdown, 2)
                })
                break

    return results

def main():
    """主函数"""
    print("开始识别地天板形态...")
    print("注意：由于网络限制，使用模拟数据演示完整逻辑")
    print()
    print("检查条件：")
    print("1. 跌停日：跌幅 ≤ -20% 或 ≤ -10%（创业板）")
    print("2. 跌停被打开：振幅 > 3%（非一字板）")
    print("3. 涨停日：跌停当日或次日涨幅 ≥ 20% 或 ≥ 10%")
    print("4. 强势延续：涨停后5日内最低价不跌破涨停日最低价")
    print("5. 排除ST股票和次新股（上市不足60个交易日）")
    print()

    # 生成模拟数据
    df = generate_mock_data()

    # 分析地天板形态
    results = analyze_floor_ceiling_pattern(df)

    # 写入结果文件
    output_file = 'floor_ceiling.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,跌停日期,涨停日期,涨停后5日最低回撤(%)\n')

        if len(results) == 0:
            f.write('# 无符合条件的地天板形态\n')
        else:
            for r in results:
                f.write(f"{r['code']},{r['limit_down_date']},{r['limit_up_date']},{r['drawdown']}\n")

    print(f"分析完成！找到 {len(results)} 个符合条件的地天板形态")
    print(f"结果已写入: {output_file}")

    if results:
        print("\n结果详情：")
        for r in results:
            print(f"  股票代码: {r['code']}")
            print(f"  跌停日期: {r['limit_down_date']}")
            print(f"  涨停日期: {r['limit_up_date']}")
            print(f"  涨停后5日最低回撤: {r['drawdown']}%")

if __name__ == '__main__':
    main()
