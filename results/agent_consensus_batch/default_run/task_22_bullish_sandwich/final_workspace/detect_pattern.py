#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
两阳夹一阴多方炮形态识别
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def get_trading_days(end_date, days=60):
    """获取交易日列表"""
    tool = ak.tool_trade_date_hist_sina()
    tool['trade_date'] = pd.to_datetime(tool['trade_date'])
    tool = tool[tool['trade_date'] <= end_date].tail(days)
    return tool['trade_date'].tolist()

def calculate_ma(close_prices, period):
    """计算移动平均线"""
    if len(close_prices) < period:
        return None
    return sum(close_prices[-period:]) / period

def check_bullish_sandwich(df, idx):
    """
    检查从idx开始的3天是否满足两阳夹一阴形态
    idx: 第1天的索引
    """
    if idx + 2 >= len(df):
        return False, None

    day1 = df.iloc[idx]
    day2 = df.iloc[idx + 1]
    day3 = df.iloc[idx + 2]

    # 条件1: 第1日、第3日为阳线且涨幅>2%
    # 阳线: 收盘价 > 开盘价
    is_day1_bullish = day1['收盘'] > day1['开盘']
    is_day3_bullish = day3['收盘'] > day3['开盘']

    if not (is_day1_bullish and is_day3_bullish):
        return False, None

    # 获取前一日收盘价计算涨跌幅
    if idx > 0:
        prev_close = df.iloc[idx - 1]['收盘']
        day1_change = (day1['收盘'] - prev_close) / prev_close * 100
    else:
        # 如果是第一天，无法计算涨跌幅，跳过
        return False, None

    day2_change = (day2['收盘'] - day1['收盘']) / day1['收盘'] * 100
    day3_change = (day3['收盘'] - day2['收盘']) / day2['收盘'] * 100

    if not (day1_change > 2 and day3_change > 2):
        return False, None

    # 条件1续: 第2日为阴线但跌幅<1%
    is_day2_bearish = day2['收盘'] < day2['开盘']
    if not is_day2_bearish:
        return False, None

    if not (day2_change > -1):  # 跌幅<1%意味着涨跌幅>-1%
        return False, None

    # 条件2: 第3日阳线实体完全吞没第2日阴线
    # 第3日收盘价 > 第2日开盘价，第3日开盘价 < 第2日收盘价
    engulfing = (day3['收盘'] > day2['开盘']) and (day3['开盘'] < day2['收盘'])
    if not engulfing:
        return False, None

    # 条件3: 三日成交量逐步放大
    vol1 = day1['成交量']
    vol2 = day2['成交量']
    vol3 = day3['成交量']

    if not (vol2 > vol1 and vol3 > vol2):
        return False, None

    vol_ratio_2_1 = vol2 / vol1
    vol_ratio_3_2 = vol3 / vol2

    # 条件4: 形态出现在上升趋势中（5日均线 > 10日均线 > 20日均线）
    # 在第3天验证均线排列
    close_prices = df.iloc[:idx+3]['收盘'].tolist()

    if len(close_prices) < 20:
        return False, None

    ma5 = calculate_ma(close_prices, 5)
    ma10 = calculate_ma(close_prices, 10)
    ma20 = calculate_ma(close_prices, 20)

    if ma5 is None or ma10 is None or ma20 is None:
        return False, None

    if not (ma5 > ma10 > ma20):
        return False, None

    # 所有条件满足
    pattern_date = day1['日期']
    return True, {
        'date': pattern_date,
        'vol_ratio_2_1': round(vol_ratio_2_1, 2),
        'vol_ratio_3_2': round(vol_ratio_3_2, 2)
    }

def main():
    end_date = datetime(2024, 4, 8)

    # 获取创业板股票列表
    stock_list = ak.stock_zh_a_spot_em()
    cyb_stocks = stock_list[stock_list['代码'].str.startswith('300')]['代码'].tolist()

    results = []

    for stock_code in cyb_stocks:
        try:
            # 获取股票K线数据
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                     start_date="20240101", end_date="20240408", adjust="qfq")

            if df is None or len(df) < 60:
                continue

            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期').reset_index(drop=True)

            # 获取最近20个交易日的索引范围
            total_days = len(df)
            start_idx = max(20, total_days - 20)  # 确保有足够的历史数据计算均线

            # 遍历最近20个交易日，检查每个3日窗口
            for i in range(start_idx, total_days - 2):
                is_pattern, pattern_info = check_bullish_sandwich(df, i)
                if is_pattern:
                    results.append({
                        'code': stock_code,
                        'date': pattern_info['date'].strftime('%Y-%m-%d'),
                        'vol_ratio_2_1': pattern_info['vol_ratio_2_1'],
                        'vol_ratio_3_2': pattern_info['vol_ratio_3_2']
                    })
                    break  # 找到一个形态就停止，避免重复

        except Exception as e:
            # 跳过获取失败的股票
            continue

    # 写入结果文件
    output_file = 'bullish_sandwich.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        if len(results) == 0:
            f.write('无符合条件的股票\n')
        else:
            for r in results:
                f.write(f"{r['code']},{r['date']},{r['vol_ratio_2_1']},{r['vol_ratio_3_2']}\n")

    print(f"检测完成，共找到 {len(results)} 个符合条件的形态")
    print(f"结果已写入 {output_file}")

if __name__ == '__main__':
    main()
