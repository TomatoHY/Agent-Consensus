#!/usr/bin/env python3
"""
分析创业板股票MACD柱状图从负转正后连续增长超过5天的情况
"""
import sys
sys.path.insert(0, '/Users/tomato/Documents/potato/project/YFD')

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm

def calculate_ema(data, period):
    """计算指数移动平均"""
    return data.ewm(span=period, adjust=False).mean()

def calculate_macd(df):
    """计算MACD指标"""
    # 计算EMA12和EMA26
    ema12 = calculate_ema(df['close'], 12)
    ema26 = calculate_ema(df['close'], 26)

    # 计算DIFF
    diff = ema12 - ema26

    # 计算DEA (DIFF的9日EMA)
    dea = calculate_ema(diff, 9)

    # 计算histogram
    histogram = diff - dea

    return histogram

def check_consecutive_increase(histogram_series, start_idx, days=5):
    """
    检查从start_idx开始，histogram是否连续递增至少days天
    """
    if start_idx + days >= len(histogram_series):
        return False

    for i in range(days):
        if histogram_series.iloc[start_idx + i + 1] <= histogram_series.iloc[start_idx + i]:
            return False

    return True

def analyze_stock(stock_code, end_date='2024-12-31'):
    """
    分析单只股票的MACD histogram
    返回是否满足条件
    """
    try:
        # 获取股票数据，需要更多天数用于预热
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date="20240801", end_date=end_date, adjust="qfq")

        if df is None or len(df) < 90:
            return False

        # 计算MACD histogram
        df['histogram'] = calculate_macd(df)

        # 获取最后60个交易日
        df_60 = df.tail(60).reset_index(drop=True)

        if len(df_60) < 60:
            return False

        # 查找histogram从负转正的位置
        found = False
        for i in range(len(df_60) - 6):  # 至少需要后续5天
            # 检查是否从负转正
            if i > 0 and df_60['histogram'].iloc[i-1] < 0 and df_60['histogram'].iloc[i] > 0:
                # 检查后续5天是否连续递增
                if check_consecutive_increase(df_60['histogram'], i, 5):
                    found = True
                    break

        return found

    except Exception as e:
        return False

def main():
    print("开始分析创业板MACD柱状图趋势...")

    # 获取创业板股票列表
    print("获取创业板股票列表...")
    try:
        stock_list = ak.stock_info_a_code_name()
        cyb_stocks = stock_list[stock_list['code'].str.startswith(('300', '301'))]
        print(f"找到 {len(cyb_stocks)} 只创业板股票")
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return

    # 分析每只股票
    count = 0
    for idx, row in tqdm(cyb_stocks.iterrows(), total=len(cyb_stocks), desc="分析进度"):
        stock_code = row['code']
        if analyze_stock(stock_code):
            count += 1

    print(f"\n分析完成！")
    print(f"符合条件的股票总数: {count}")

    # 写入结果文件
    result_path = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_10_macd_histogram_trend/revised/claudecode/macd_strength_count.txt"
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(f"符合条件的股票总数: {count}\n")

    print(f"结果已写入: {result_path}")

if __name__ == "__main__":
    main()
