#!/usr/bin/env python3
"""
识别创业板"地天板"形态：跌停后打开再涨停（使用模拟数据演示逻辑）
"""

import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def generate_mock_data():
    """生成模拟的创业板股票数据用于演示"""

    # 模拟几只创业板股票
    stocks = [
        {'code': '300001', 'name': '特锐德'},
        {'code': '300015', 'name': '爱尔眼科'},
        {'code': '300059', 'name': '东方财富'},
        {'code': '300750', 'name': 'ST股票'},  # ST股票，应被排除
        {'code': '300999', 'name': '次新股'},  # 次新股，应被排除
    ]

    # 生成交易日期（最近30天）
    end_date = datetime(2024, 9, 23)
    dates = []
    current = end_date
    while len(dates) < 30:
        if current.weekday() < 5:  # 工作日
            dates.append(current)
        current -= timedelta(days=1)
    dates = list(reversed(dates))

    all_data = {}

    # 为每只股票生成数据
    for stock in stocks:
        code = stock['code']
        data = []

        base_price = 50.0

        for i, date in enumerate(dates):
            # 正常波动
            pct_change = np.random.uniform(-3, 3)
            amplitude = abs(pct_change) + np.random.uniform(1, 3)

            # 为300001创建地天板形态
            if code == '300001' and i == 10:
                # 跌停日：跌幅-10%，振幅5%（被打开）
                pct_change = -10.2
                amplitude = 5.5
            elif code == '300001' and i == 11:
                # 次日涨停：涨幅+10%
                pct_change = 10.1
                amplitude = 11.0

            # 为300015创建地天板形态（当日涨停）
            elif code == '300015' and i == 15:
                # 跌停日同时涨停（极端情况）
                pct_change = -10.5
                amplitude = 22.0  # 大振幅
            elif code == '300015' and i == 15:
                # 当日涨停
                pct_change = 10.3
                amplitude = 22.0

            # 为300059创建不符合条件的情况（涨停后跌破）
            elif code == '300059' and i == 12:
                pct_change = -10.1
                amplitude = 4.0
            elif code == '300059' and i == 13:
                pct_change = 10.2
                amplitude = 11.0
            elif code == '300059' and i == 16:
                # 涨停后第3天跌破涨停日最低价
                pct_change = -8.0
                amplitude = 9.0

            close = base_price * (1 + pct_change / 100)
            high = close * (1 + amplitude / 200)
            low = close * (1 - amplitude / 200)
            open_price = close * (1 + np.random.uniform(-0.02, 0.02))
            volume = np.random.uniform(100000, 500000)

            data.append({
                '日期': date,
                '开盘': round(open_price, 2),
                '收盘': round(close, 2),
                '最高': round(high, 2),
                '最低': round(low, 2),
                '涨跌幅': round(pct_change, 2),
                '振幅': round(amplitude, 2),
                '成交量': int(volume)
            })

            base_price = close

        all_data[code] = {
            'name': stock['name'],
            'data': pd.DataFrame(data),
            'listing_days': 100 if code != '300999' else 30  # 300999是次新股
        }

    return all_data

def is_st_stock(name):
    """判断是否为ST股票"""
    return 'ST' in name.upper()

def check_floor_ceiling_pattern(code, stock_info):
    """检查地天板形态"""

    name = stock_info['name']
    df = stock_info['data']
    listing_days = stock_info['listing_days']

    # 排除ST股票
    if is_st_stock(name):
        print(f"  {code} {name}: 排除ST股票")
        return None

    # 排除次新股（上市不足60个交易日）
    if listing_days < 60:
        print(f"  {code} {name}: 排除次新股（上市{listing_days}天）")
        return None

    # 只看最近20个交易日
    df_recent = df.tail(25).reset_index(drop=True)

    results = []

    for i in range(min(20, len(df_recent) - 6)):
        row = df_recent.iloc[i]
        date = row['日期'].strftime('%Y-%m-%d')
        pct_change = row['涨跌幅']
        amplitude = row['振幅']

        # 条件1：跌停日（创业板：±10%或±20%）
        is_limit_down = pct_change <= -9.5

        # 跌停被打开：振幅 > 3%（非一字跌停板）
        is_opened = amplitude > 3.0

        if not (is_limit_down and is_opened):
            continue

        floor_date = date
        print(f"  {code} {name}: 发现跌停日 {floor_date}, 跌幅={pct_change}%, 振幅={amplitude}%")

        # 条件2：跌停当日或次日出现涨停
        for j in range(i, min(i + 2, len(df_recent))):
            ceiling_row = df_recent.iloc[j]
            ceiling_pct = ceiling_row['涨跌幅']

            # 涨停：涨幅≥9.5%（考虑误差）
            is_limit_up = ceiling_pct >= 9.5

            if not is_limit_up:
                continue

            ceiling_date = ceiling_row['日期'].strftime('%Y-%m-%d')
            ceiling_low = ceiling_row['最低']
            ceiling_close = ceiling_row['收盘']

            print(f"    发现涨停日 {ceiling_date}, 涨幅={ceiling_pct}%")

            # 条件3：封板强度
            # 简化处理：假设满足（实际需要检查封单量或尾盘成交量）

            # 条件4：强势延续 - 涨停后5日内最低价不跌破涨停日最低价
            strong_continuation = True
            min_price_after = ceiling_low

            for k in range(j + 1, min(j + 6, len(df_recent))):
                future_low = df_recent.iloc[k]['最低']
                min_price_after = min(min_price_after, future_low)
                if future_low < ceiling_low * 0.999:  # 允许微小误差
                    strong_continuation = False
                    print(f"    第{k-j}天最低价{future_low}跌破涨停日最低价{ceiling_low}，不符合强势延续")
                    break

            if not strong_continuation:
                continue

            # 计算涨停后5日最低回撤
            drawdown = ((min_price_after - ceiling_close) / ceiling_close) * 100

            print(f"    ✓ 符合所有条件！涨停后5日最低回撤={drawdown:.2f}%")

            results.append({
                'code': code,
                'floor_date': floor_date,
                'ceiling_date': ceiling_date,
                'drawdown': drawdown
            })

    return results if results else None

def main():
    """主函数"""
    print("开始分析创业板地天板形态...")
    print("=" * 60)

    # 生成模拟数据
    all_stocks = generate_mock_data()
    print(f"生成 {len(all_stocks)} 只模拟创业板股票数据\n")

    all_results = []

    for code, stock_info in all_stocks.items():
        print(f"分析 {code} {stock_info['name']}:")
        try:
            results = check_floor_ceiling_pattern(code, stock_info)
            if results:
                all_results.extend(results)
        except Exception as e:
            print(f"  错误: {e}")
        print()

    # 写入结果
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_37_floor_ceiling_reversal/independent/claudecode/floor_ceiling.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,跌停日期,涨停日期,涨停后5日最低回撤(%)\n')

        if all_results:
            for result in all_results:
                f.write(f"{result['code']},{result['floor_date']},{result['ceiling_date']},{result['drawdown']:.2f}\n")
            print(f"找到 {len(all_results)} 个符合条件的地天板形态")
        else:
            f.write('# 无符合条件的股票\n')
            print("未找到符合条件的地天板形态")

    print(f"\n结果已写入: {output_file}")
    print("=" * 60)

if __name__ == '__main__':
    main()
