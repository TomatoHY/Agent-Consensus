#!/usr/bin/env python3
"""
找出创业板中以 2024-06-28 为截止交易日的前5个交易日内连续上涨且每天涨幅都在2%-7%之间的股票
"""
import sys
sys.path.insert(0, '/Users/tomato/Documents/potato/project/YFD')

from mootdx.quotes import Quotes
import pandas as pd
from datetime import datetime

def get_chinext_stocks():
    """获取创业板股票列表（300开头）"""
    client = Quotes.factory(market='std')

    # 获取所有股票
    stocks = client.stocks(market=0)  # market=0 for 上海+深圳

    # 筛选创业板（300开头）
    chinext = stocks[stocks['code'].str.startswith('300')]
    return chinext['code'].tolist()

def check_steady_rise(code, end_date='2024-06-28'):
    """
    检查股票是否满足连续5天上涨且每天涨幅在2%-7%之间

    需要6个交易日数据：
    - 第0日作为基准
    - 第1-5日为检查的5个交易日
    """
    try:
        client = Quotes.factory(market='std')

        # 获取日线数据，frequency=9表示日线
        # offset=500 to get enough historical data to include 2024-06-28
        df = client.bars(symbol=code, frequency=9, offset=500)

        if df is None or len(df) < 6:
            return None, None

        # 按日期排序（升序）
        df = df.sort_index()

        # 找到截止日期2024-06-28的位置
        # The index has timestamps with time component, so we need to match by date
        target_date = pd.to_datetime(end_date).date()

        # Filter to dates on or before target date
        df = df[df.index.date <= target_date]

        if len(df) < 6:
            return None, None

        # 取最后6个交易日
        df = df.tail(6)

        # 获取收盘价
        closes = df['close'].values

        # 检查5天是否连续上涨
        for i in range(1, 6):
            if closes[i] <= closes[i-1]:
                return None, None

        # 计算每日涨幅并检查是否在2%-7%之间
        daily_returns = []
        for i in range(1, 6):
            daily_return = (closes[i] - closes[i-1]) / closes[i-1] * 100
            daily_returns.append(daily_return)

            if daily_return < 2.0 or daily_return > 7.0:
                return None, None

        # 计算5日累计涨幅
        cumulative_return = (closes[5] / closes[0] - 1) * 100

        return True, cumulative_return

    except Exception as e:
        return None, None

def main():
    """主函数"""
    print("开始获取创业板股票列表...")
    chinext_stocks = get_chinext_stocks()
    print(f"共获取到 {len(chinext_stocks)} 只创业板股票")

    results = []

    print("开始检查每只股票...")
    for i, code in enumerate(chinext_stocks):
        if (i + 1) % 50 == 0:
            print(f"已处理 {i+1}/{len(chinext_stocks)} 只股票...")

        is_qualified, cumulative_return = check_steady_rise(code)

        if is_qualified:
            results.append({
                'code': code,
                'cumulative_return': cumulative_return
            })
            print(f"找到符合条件的股票: {code}, 累计涨幅: {cumulative_return:.2f}%")

    # 写入结果文件
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_04_consecutive_rise/revised/claudecode/steady_rise.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        if len(results) == 0:
            f.write("无符合条件的股票\n")
        else:
            f.write("股票代码,5日累计涨幅(%)\n")
            for r in results:
                f.write(f"{r['code']},{r['cumulative_return']:.2f}\n")

    print(f"\n结果已写入: {output_path}")
    print(f"共找到 {len(results)} 只符合条件的股票")

    return results

if __name__ == '__main__':
    results = main()
