#!/usr/bin/env python3
"""
识别"周线突破+日线回踩确认"跨周期形态
Weekly breakout + daily pullback confirmation pattern detection
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_stock_list():
    """获取A股股票列表"""
    try:
        stock_info = ak.stock_zh_a_spot_em()
        return stock_info['代码'].tolist()[:100]  # 限制数量以加快测试
    except:
        # 备用股票列表
        return ['000001', '000002', '000858', '300750', '600519', '601318']

def get_weekly_data(stock_code, weeks=80):
    """获取周线数据"""
    try:
        # 获取周线数据
        df = ak.stock_zh_a_hist(symbol=stock_code, period="weekly", adjust="qfq")
        if df is None or len(df) < 60:
            return None

        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')
        df = df.tail(weeks)

        # 计算60周均线
        df['MA60'] = df['收盘'].rolling(window=60).mean()

        return df
    except:
        return None

def get_daily_data(stock_code, start_date):
    """获取日线数据"""
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="qfq")
        if df is None or len(df) < 20:
            return None

        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')

        # 只获取start_date之后的数据
        df = df[df['日期'] >= pd.to_datetime(start_date)]

        # 计算20日均线和20日均量
        df['MA20'] = df['收盘'].rolling(window=20).mean()
        df['VOL_MA20'] = df['成交量'].rolling(window=20).mean()

        return df
    except:
        return None

def detect_weekly_breakout(weekly_df, target_date):
    """检测周线突破60周均线"""
    target_date = pd.to_datetime(target_date)

    # 找到近4周内的突破
    four_weeks_ago = target_date - timedelta(weeks=4)
    recent_weeks = weekly_df[weekly_df['日期'] <= target_date].tail(5)

    if len(recent_weeks) < 2:
        return None

    breakout_date = None

    for i in range(1, len(recent_weeks)):
        prev_row = recent_weeks.iloc[i-1]
        curr_row = recent_weeks.iloc[i]

        # 检查是否在近4周内
        if curr_row['日期'] < four_weeks_ago:
            continue

        # 检测突破：前一周收盘 < 60周均线，本周收盘 > 60周均线
        if pd.notna(prev_row['MA60']) and pd.notna(curr_row['MA60']):
            if prev_row['收盘'] < prev_row['MA60'] and curr_row['收盘'] > curr_row['MA60']:
                breakout_date = curr_row['日期']

                # 验证突破有效性：突破后未再次跌破
                after_breakout = weekly_df[weekly_df['日期'] > breakout_date]
                if len(after_breakout) > 0:
                    # 检查突破后所有周的收盘价是否都在60周均线之上
                    valid = True
                    for _, row in after_breakout.iterrows():
                        if pd.notna(row['MA60']) and row['收盘'] < row['MA60']:
                            valid = False
                            break

                    if valid:
                        return breakout_date

    return None

def detect_daily_pullback(daily_df, breakout_date):
    """检测日线回踩确认形态"""
    breakout_date = pd.to_datetime(breakout_date)

    # 只看突破后的日线数据
    after_breakout = daily_df[daily_df['日期'] > breakout_date].copy()

    if len(after_breakout) < 3:
        return None

    results = []

    for i in range(len(after_breakout) - 2):
        row = after_breakout.iloc[i]

        # 检查是否有足够的数据计算均线
        if pd.isna(row['MA20']) or pd.isna(row['VOL_MA20']):
            continue

        # 条件1：价格回踩到20日均线附近（±2%）
        close_price = row['收盘']
        ma20 = row['MA20']
        price_diff_pct = abs(close_price - ma20) / ma20 * 100

        if price_diff_pct > 2:
            continue

        # 条件2：回踩时成交量萎缩（< 20日均量的80%）
        volume = row['成交量']
        vol_ma20 = row['VOL_MA20']

        if volume >= vol_ma20 * 0.8:
            continue

        # 条件3：回踩后出现反弹日（次日或后天收阳且成交量 > 20日均量）
        pullback_date = row['日期']

        for j in range(i+1, min(i+3, len(after_breakout))):
            next_row = after_breakout.iloc[j]
            prev_close = after_breakout.iloc[j-1]['收盘']

            # 收阳（收盘价 > 前一日收盘价）且放量
            if (next_row['收盘'] > prev_close and
                pd.notna(next_row['VOL_MA20']) and
                next_row['成交量'] > next_row['VOL_MA20']):

                bounce_date = next_row['日期']
                bounce_pct = (next_row['收盘'] - prev_close) / prev_close * 100

                results.append({
                    'pullback_date': pullback_date,
                    'bounce_date': bounce_date,
                    'bounce_pct': bounce_pct
                })
                break

    return results[0] if results else None

def main():
    """主函数"""
    print("开始识别周线突破+日线回踩确认形态...")

    target_date = "2024-04-22"
    stock_list = get_stock_list()

    results = []

    for idx, stock_code in enumerate(stock_list):
        if idx % 10 == 0:
            print(f"处理进度: {idx}/{len(stock_list)}")

        # 获取周线数据
        weekly_df = get_weekly_data(stock_code)
        if weekly_df is None:
            continue

        # 检测周线突破
        breakout_date = detect_weekly_breakout(weekly_df, target_date)
        if breakout_date is None:
            continue

        print(f"股票 {stock_code} 在 {breakout_date.strftime('%Y-%m-%d')} 发生周线突破")

        # 获取日线数据
        daily_df = get_daily_data(stock_code, breakout_date)
        if daily_df is None:
            continue

        # 检测日线回踩
        pullback_result = detect_daily_pullback(daily_df, breakout_date)
        if pullback_result is None:
            continue

        results.append({
            'stock_code': stock_code,
            'breakout_date': breakout_date.strftime('%Y-%m-%d'),
            'pullback_date': pullback_result['pullback_date'].strftime('%Y-%m-%d'),
            'bounce_date': pullback_result['bounce_date'].strftime('%Y-%m-%d'),
            'bounce_pct': pullback_result['bounce_pct']
        })

        print(f"  找到回踩确认: 回踩日期={pullback_result['pullback_date'].strftime('%Y-%m-%d')}, "
              f"反弹日期={pullback_result['bounce_date'].strftime('%Y-%m-%d')}, "
              f"反弹涨幅={pullback_result['bounce_pct']:.2f}%")

    # 写入结果文件
    output_path = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_32_weekly_breakout_daily_pullback/independent/claudecode/weekly_pullback.txt"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("股票代码,周线突破日期,日线回踩日期,反弹日期,反弹日涨幅(%)\n")

        if results:
            for r in results:
                f.write(f"{r['stock_code']},{r['breakout_date']},{r['pullback_date']},"
                       f"{r['bounce_date']},{r['bounce_pct']:.2f}\n")
        else:
            f.write("# 无符合条件的股票\n")

    print(f"\n完成！共找到 {len(results)} 只符合条件的股票")
    print(f"结果已写入: {output_path}")

    return results

if __name__ == "__main__":
    main()
