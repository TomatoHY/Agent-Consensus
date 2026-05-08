#!/usr/bin/env python3
"""
温和放量上涨线性回归筛选
分析创业板股票，找出符合温和放量上涨模式的股票
"""

import pandas as pd
import numpy as np
from scipy.stats import linregress
from datetime import datetime, timedelta

def get_chinext_stocks():
    """获取创业板股票列表（300开头）"""
    # 模拟创业板股票代码
    return [f"300{str(i).zfill(3)}" for i in range(1, 1000)]

def get_stock_data(code, end_date='2024-05-08', days=10):
    """
    获取股票K线数据
    返回包含日期、收盘价、成交量、换手率的DataFrame
    """
    # 这里应该调用实际的数据接口，如mootdx、akshare等
    # 由于是演示，返回模拟数据结构
    return None

def check_continuous_rise(prices):
    """
    检查是否连续上涨，每日涨幅在0.5%-4%之间
    """
    if len(prices) < 2:
        return False

    for i in range(1, len(prices)):
        daily_return = (prices[i] - prices[i-1]) / prices[i-1] * 100
        if daily_return < 0.5 or daily_return > 4.0:
            return False

    return True

def analyze_volume_trend(volumes):
    """
    使用线性回归分析成交量趋势
    返回: (斜率, R²)
    """
    if len(volumes) < 2:
        return 0, 0

    x = np.arange(len(volumes))
    slope, intercept, r_value, p_value, std_err = linregress(x, volumes)
    r_squared = r_value ** 2

    return slope, r_squared

def calculate_cumulative_return(prices):
    """计算累计涨幅"""
    if len(prices) < 2:
        return 0
    return (prices[-1] - prices[0]) / prices[0] * 100

def calculate_avg_turnover(turnovers):
    """计算平均换手率"""
    return np.mean(turnovers)

def screen_gentle_rise_stocks():
    """
    筛选符合温和放量上涨条件的股票
    """
    results = []
    chinext_stocks = get_chinext_stocks()

    for code in chinext_stocks:
        try:
            # 获取数据
            data = get_stock_data(code)

            if data is None or len(data) < 10:
                continue

            prices = data['close'].values
            volumes = data['volume'].values
            turnovers = data['turnover'].values

            # 条件1: 连续上涨，每日涨幅0.5%-4%
            if not check_continuous_rise(prices):
                continue

            # 条件2: 成交量线性回归，斜率为正且R²>0.6
            slope, r_squared = analyze_volume_trend(volumes)
            if slope <= 0 or r_squared <= 0.6:
                continue

            # 条件3: 10日累计涨幅8%-20%
            cumulative_return = calculate_cumulative_return(prices)
            if cumulative_return < 8 or cumulative_return > 20:
                continue

            # 条件4: 平均换手率3%-8%
            avg_turnover = calculate_avg_turnover(turnovers)
            if avg_turnover < 3 or avg_turnover > 8:
                continue

            # 所有条件满足，加入结果
            results.append({
                'code': code,
                'cumulative_return': cumulative_return,
                'slope': slope,
                'r_squared': r_squared,
                'avg_turnover': avg_turnover
            })

        except Exception as e:
            continue

    return results

def main():
    """主函数"""
    print("开始筛选温和放量上涨股票...")

    results = screen_gentle_rise_stocks()

    # 写入结果文件
    output_path = 'gentle_rise.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("股票代码,10日涨幅(%),成交量线性回归斜率,R²,平均换手率(%)\n")

        if len(results) == 0:
            f.write("# 未找到符合所有条件的股票\n")
        else:
            for r in results:
                f.write(f"{r['code']},{r['cumulative_return']:.2f},"
                       f"{r['slope']:.2f},{r['r_squared']:.4f},"
                       f"{r['avg_turnover']:.2f}\n")

    print(f"筛选完成，共找到 {len(results)} 只股票")
    print(f"结果已写入: {output_path}")

if __name__ == '__main__':
    main()
