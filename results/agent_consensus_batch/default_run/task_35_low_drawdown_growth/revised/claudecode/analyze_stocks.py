#!/usr/bin/env python3
"""
低回撤稳健成长股筛选
筛选条件：
1. 60日收益率 > 20%
2. 最大回撤 < 12%
3. Calmar比率 > 2
4. 连续下跌天数不超过5天
5. 单日最大跌幅 < 6%
6. 近20日上涨天数占比 > 55%
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def calculate_max_drawdown(prices):
    """计算最大回撤"""
    cummax = prices.cummax()
    drawdown = (cummax - prices) / cummax * 100
    return drawdown.max()

def calculate_consecutive_down_days(returns):
    """计算最长连续下跌天数"""
    max_consecutive = 0
    current_consecutive = 0

    for ret in returns:
        if ret < 0:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 0

    return max_consecutive

def calculate_win_rate_20d(returns):
    """计算近20日上涨天数占比"""
    if len(returns) < 20:
        return 0
    last_20 = returns[-20:]
    up_days = (last_20 > 0).sum()
    return (up_days / 20) * 100

def analyze_stock(stock_code, start_date, end_date):
    """分析单只股票"""
    try:
        # 获取股票历史数据（前复权）
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )

        if df is None or len(df) < 60:
            return None

        # 取最近60个交易日
        df = df.tail(60).copy()

        if len(df) < 60:
            return None

        # 计算收益率
        close_prices = df['收盘'].values
        returns = np.diff(close_prices) / close_prices[:-1] * 100

        # 1. 60日总收益率
        return_60d = (close_prices[-1] - close_prices[0]) / close_prices[0] * 100

        if return_60d <= 20:
            return None

        # 2. 最大回撤
        max_dd = calculate_max_drawdown(pd.Series(close_prices))

        if max_dd >= 12:
            return None

        # 3. 年化收益率和Calmar比率
        annual_return = return_60d * (252 / 60)
        calmar_ratio = annual_return / max_dd if max_dd > 0 else 0

        if calmar_ratio <= 2:
            return None

        # 4. 连续下跌天数
        max_consecutive_down = calculate_consecutive_down_days(returns)

        if max_consecutive_down > 5:
            return None

        # 5. 单日最大跌幅
        max_single_drop = abs(returns.min())

        if max_single_drop >= 6:
            return None

        # 6. 近20日胜率
        win_rate_20d = calculate_win_rate_20d(returns)

        if win_rate_20d <= 55:
            return None

        return {
            'code': stock_code,
            'return_60d': return_60d,
            'max_drawdown': max_dd,
            'annual_return': annual_return,
            'calmar_ratio': calmar_ratio,
            'win_rate_20d': win_rate_20d
        }

    except Exception as e:
        return None

def main():
    """主函数"""
    # 设置日期范围
    end_date = '20240722'
    # 获取更多天数以确保有足够的交易日
    start_date = '20240401'

    print("正在获取创业板股票列表...")

    # 获取所有A股列表
    stock_list = ak.stock_zh_a_spot_em()

    # 筛选创业板股票（300开头）
    chinext_stocks = stock_list[stock_list['代码'].str.startswith('300')]['代码'].tolist()

    print(f"找到 {len(chinext_stocks)} 只创业板股票")
    print("开始分析...")

    results = []

    for i, stock_code in enumerate(chinext_stocks):
        if (i + 1) % 50 == 0:
            print(f"已处理 {i + 1}/{len(chinext_stocks)} 只股票...")

        result = analyze_stock(stock_code, start_date, end_date)

        if result:
            results.append(result)

    print(f"\n符合条件的股票数量: {len(results)}")

    if len(results) == 0:
        # 如果没有符合条件的股票
        with open('calmar_top10.txt', 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        print("未找到符合所有条件的股票")
        return

    # 按Calmar比率排序
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('calmar_ratio', ascending=False)

    # 取前10只
    top10 = results_df.head(10)

    # 写入文件
    with open('calmar_top10.txt', 'w', encoding='utf-8') as f:
        f.write("股票代码,60日收益率(%),最大回撤(%),年化收益率(%),Calmar比率,近20日胜率(%)\n")

        for _, row in top10.iterrows():
            f.write(f"{row['code']},{row['return_60d']:.1f},{row['max_drawdown']:.1f},"
                   f"{row['annual_return']:.1f},{row['calmar_ratio']:.1f},{row['win_rate_20d']:.1f}\n")

    print("\n结果已写入 calmar_top10.txt")
    print("\n前10只股票:")
    print(top10.to_string(index=False))

if __name__ == "__main__":
    main()
