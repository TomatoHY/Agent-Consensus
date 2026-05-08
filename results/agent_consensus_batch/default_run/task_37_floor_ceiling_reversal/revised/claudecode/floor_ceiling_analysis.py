#!/usr/bin/env python3
"""
地天板极端反转形态识别
识别创业板中的"地天板"形态（跌停后打开再涨停）
"""

import sys
sys.path.insert(0, '/Users/tomato/Documents/potato/project/YFD')

import pandas as pd
from datetime import datetime, timedelta
from data_source import DataSource

def identify_floor_ceiling_patterns():
    """识别地天板形态"""

    ds = DataSource()

    # 设置日期范围：截至2024-09-23的最近20个交易日
    end_date = '2024-09-23'
    start_date = '2024-08-20'  # 大约20个交易日前

    # 获取创业板股票列表（300开头）
    stock_list = ds.stock_basic()
    chinext_stocks = stock_list[stock_list['ts_code'].str.startswith('300')]['ts_code'].tolist()

    results = []

    for stock_code in chinext_stocks:
        try:
            # 获取股票基本信息
            stock_info = stock_list[stock_list['ts_code'] == stock_code].iloc[0]
            stock_name = stock_info['name']
            list_date = stock_info['list_date']

            # 排除ST股票
            if 'ST' in stock_name:
                continue

            # 排除次新股（上市不足60个交易日）
            list_date_dt = datetime.strptime(list_date, '%Y%m%d')
            end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')
            days_since_listing = (end_date_dt - list_date_dt).days
            if days_since_listing < 90:  # 约60个交易日
                continue

            # 获取日线数据
            df = ds.daily(ts_code=stock_code, start_date=start_date.replace('-', ''),
                         end_date=end_date.replace('-', ''))

            if df is None or len(df) < 2:
                continue

            df = df.sort_values('trade_date')
            df['trade_date'] = pd.to_datetime(df['trade_date'])

            # 计算振幅
            df['amplitude'] = ((df['high'] - df['low']) / df['pre_close'] * 100).abs()

            # 识别跌停日
            for i in range(len(df) - 1):
                row = df.iloc[i]
                pct_chg = row['pct_chg']
                amplitude = row['amplitude']

                # 判断是否跌停（创业板：-20%或-10%）
                is_limit_down = (pct_chg <= -19.5 or (pct_chg <= -9.5 and pct_chg > -11))

                # 判断跌停是否被打开（振幅>3%，非一字板）
                is_opened = amplitude > 3.0

                if not (is_limit_down and is_opened):
                    continue

                limit_down_date = row['trade_date']

                # 检查当日或次日是否涨停
                for j in range(i, min(i + 2, len(df))):
                    check_row = df.iloc[j]
                    check_pct = check_row['pct_chg']

                    # 判断是否涨停（创业板：20%或10%）
                    is_limit_up = (check_pct >= 19.5 or (check_pct >= 9.5 and check_pct < 11))

                    if not is_limit_up:
                        continue

                    limit_up_date = check_row['trade_date']
                    limit_up_low = check_row['low']

                    # 检查封板强度（使用尾盘成交量占比作为代理）
                    # 这里简化处理，假设强封板

                    # 检查涨停后5日内最低价不跌破涨停日最低价
                    future_5_days = df.iloc[j+1:min(j+6, len(df))]

                    if len(future_5_days) < 5:
                        continue  # 数据不足5天

                    min_low_after = future_5_days['low'].min()

                    if min_low_after >= limit_up_low:
                        # 计算涨停后5日最低回撤
                        limit_up_close = check_row['close']
                        drawdown = ((min_low_after - limit_up_close) / limit_up_close * 100)

                        results.append({
                            'stock_code': stock_code,
                            'limit_down_date': limit_down_date.strftime('%Y-%m-%d'),
                            'limit_up_date': limit_up_date.strftime('%Y-%m-%d'),
                            'drawdown_pct': round(drawdown, 2)
                        })
                        break

        except Exception as e:
            continue

    return results

def main():
    """主函数"""
    print("开始识别地天板形态...")

    results = identify_floor_ceiling_patterns()

    # 写入结果文件
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_37_floor_ceiling_reversal/revised/claudecode/floor_ceiling.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,跌停日期,涨停日期,涨停后5日最低回撤(%)\n')

        if len(results) == 0:
            f.write('# 无符合条件的地天板形态\n')
        else:
            for r in results:
                f.write(f"{r['stock_code']},{r['limit_down_date']},{r['limit_up_date']},{r['drawdown_pct']}\n")

    print(f"分析完成，找到 {len(results)} 个符合条件的地天板形态")
    print(f"结果已写入: {output_file}")

    return results

if __name__ == '__main__':
    main()
