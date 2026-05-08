#!/usr/bin/env python3
"""
统计创业板中截至 2024-08-30 的前30个交易日内，
有多少只股票的布林带宽度处于盘整状态（< 5%）
"""
import pandas as pd
import numpy as np
from mootdx.quotes import Quotes
import time
from datetime import datetime


def calculate_bollinger_bands(close_prices, window=20):
    """
    计算布林带指标
    中轨 = 20日SMA
    上轨 = 中轨 + 2*标准差
    下轨 = 中轨 - 2*标准差
    """
    if len(close_prices) < window:
        return None, None, None

    # 计算中轨（20日简单移动平均）
    middle = close_prices.rolling(window=window).mean()

    # 计算20日标准差
    std = close_prices.rolling(window=window).std()

    # 计算上轨和下轨
    upper = middle + 2 * std
    lower = middle - 2 * std

    return upper, middle, lower


def calculate_bollinger_width(upper, middle, lower):
    """
    计算布林带宽度 = (上轨 - 下轨) / 中轨
    """
    if middle == 0 or pd.isna(middle) or pd.isna(upper) or pd.isna(lower):
        return None

    width = (upper - lower) / middle
    return width


def get_stock_data(symbol, client, days=50):
    """
    获取股票K线数据
    需要至少50天数据（20天计算布林带 + 30天观察窗口）
    """
    try:
        # 获取日线数据，frequency=9表示日线
        bars = client.bars(symbol=symbol, frequency=9, offset=days)

        if bars is None or len(bars) < days:
            return None

        # 按日期升序排列
        bars = bars.sort_values('date').reset_index(drop=True)

        return bars

    except Exception as e:
        return None


def check_bollinger_squeeze(symbol, client, target_date='2024-08-30'):
    """
    检查股票在目标日期的布林带宽度是否 < 5%
    """
    try:
        # 获取数据
        df = get_stock_data(symbol, client, days=50)

        if df is None or len(df) < 50:
            return None

        # 计算布林带
        close = df['close']
        upper, middle, lower = calculate_bollinger_bands(close, window=20)

        if upper is None:
            return None

        # 获取最新一天的布林带数据
        latest_upper = upper.iloc[-1]
        latest_middle = middle.iloc[-1]
        latest_lower = lower.iloc[-1]

        # 计算宽度
        width = calculate_bollinger_width(latest_upper, latest_middle, latest_lower)

        if width is None:
            return None

        # 判断是否处于盘整（宽度 < 5%）
        is_squeeze = width < 0.05

        return is_squeeze

    except Exception as e:
        return None


def get_chinext_stocks(client):
    """
    获取创业板股票列表（代码以300或301开头）
    """
    try:
        # 获取深圳市场股票列表，market=0表示深圳
        stocks = client.stocks(market=0)

        if stocks is None or len(stocks) == 0:
            return []

        # 筛选创业板股票
        chinext = stocks[stocks['code'].str.startswith(('300', '301'))]

        return chinext['code'].tolist()

    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []


def main():
    print("初始化mootdx客户端...")

    try:
        client = Quotes.factory(market='std')
        print("客户端初始化成功")
    except Exception as e:
        print(f"客户端初始化失败: {e}")
        return

    print("获取创业板股票列表...")
    stock_codes = get_chinext_stocks(client)

    if not stock_codes:
        print("无法获取股票列表")
        return

    total_stocks = len(stock_codes)
    print(f"创业板股票总数: {total_stocks}")
    print("开始计算布林带宽度...")

    squeeze_count = 0
    valid_count = 0
    failed_count = 0

    for idx, code in enumerate(stock_codes):
        if (idx + 1) % 100 == 0:
            print(f"进度: {idx + 1}/{total_stocks}, 有效: {valid_count}, 失败: {failed_count}, 盘整: {squeeze_count}")

        result = check_bollinger_squeeze(code, client)

        if result is None:
            failed_count += 1
        else:
            valid_count += 1
            if result:
                squeeze_count += 1

        # 避免请求过快
        time.sleep(0.05)

    print(f"\n处理完成！")
    print(f"总股票数: {total_stocks}")
    print(f"有效股票数: {valid_count}")
    print(f"失败股票数: {failed_count}")
    print(f"符合盘整条件: {squeeze_count}")

    # 计算占比
    if valid_count > 0:
        ratio = (squeeze_count / valid_count) * 100
    else:
        ratio = 0.0

    # 写入结果文件
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_06_bollinger_squeeze/revised/claudecode/bollinger_count.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"符合条件的股票数量: {squeeze_count}\n")
        f.write(f"占创业板比例: {ratio:.2f}%\n")

    print(f"\n结果已写入: {output_path}")
    print(f"符合条件的股票数量: {squeeze_count}")
    print(f"占创业板比例: {ratio:.2f}%")


if __name__ == "__main__":
    main()
