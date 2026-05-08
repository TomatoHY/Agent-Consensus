#!/usr/bin/env python3
"""
分析创业板股票的52周新高突破及后续跟进情况
截止日期: 2024-11-15
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_chinext_stocks():
    """获取创业板股票列表（代码以300开头）"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except:
        # 备用方法
        return [f"300{str(i).zfill(3)}" for i in range(1, 1000)]

def get_stock_data(stock_code, end_date='2024-11-15'):
    """获取股票历史数据，需要至少282个交易日（252+30）"""
    try:
        # 获取更多数据以确保有足够的交易日
        start_date = '2023-09-01'  # 提前更多时间以确保有282个交易日

        # 尝试不同的API调用方式
        try:
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                    start_date=start_date.replace('-', ''),
                                    end_date=end_date.replace('-', ''),
                                    adjust="qfq")
        except:
            # 备用方法
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                    start_date=start_date, end_date=end_date, adjust="qfq")

        if df is None or len(df) < 282:
            return None

        # 重命名列 - 检查实际列名
        column_mapping = {}
        for col in df.columns:
            if '日期' in col or 'date' in col.lower():
                column_mapping[col] = 'date'
            elif '收盘' in col or 'close' in col.lower():
                column_mapping[col] = 'close'
            elif '成交量' in col or 'volume' in col.lower():
                column_mapping[col] = 'volume'

        df.rename(columns=column_mapping, inplace=True)

        if 'date' not in df.columns or 'close' not in df.columns or 'volume' not in df.columns:
            return None

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        return df[['date', 'close', 'volume']].reset_index(drop=True)
    except Exception as e:
        return None

def find_52week_high_breakout(df, end_date='2024-11-15'):
    """
    在最近30个交易日内找到首次突破52周（252个交易日）新高的日期
    """
    end_date = pd.to_datetime(end_date)
    df = df[df['date'] <= end_date].copy()

    if len(df) < 282:
        return None

    # 取最近282个交易日
    df = df.tail(282).reset_index(drop=True)

    # 最近30个交易日的窗口
    recent_30_days = df.tail(30).copy()

    for idx in recent_30_days.index:
        current_date = df.loc[idx, 'date']
        current_close = df.loc[idx, 'close']

        # 获取该日期之前的252个交易日的最高收盘价
        if idx < 252:
            continue

        past_252_days = df.loc[idx-252:idx-1, 'close']
        max_252 = past_252_days.max()

        # 检查是否创新高
        if current_close > max_252:
            return idx, current_date, current_close

    return None

def check_volume_confirmation(df, breakout_idx):
    """
    检查创新高日±2天（共5天窗口）的成交量均值是否 > 60日均量的1.5倍
    """
    # 5天窗口：breakout_idx-2 到 breakout_idx+2
    window_start = max(0, breakout_idx - 2)
    window_end = min(len(df) - 1, breakout_idx + 2)

    if window_end - window_start < 4:  # 至少需要5天
        return False

    window_volume = df.loc[window_start:window_end, 'volume'].mean()

    # 60日均量（在突破日之前的60天）
    if breakout_idx < 60:
        return False

    avg_60_volume = df.loc[breakout_idx-60:breakout_idx-1, 'volume'].mean()

    return window_volume > (avg_60_volume * 1.5)

def check_followthrough(df, breakout_idx, breakout_price):
    """
    检查新高后5个交易日内，至少3天收盘价高于创新高当天的收盘价
    """
    if breakout_idx + 5 >= len(df):
        return False, None

    next_5_days = df.loc[breakout_idx+1:breakout_idx+5, 'close']

    if len(next_5_days) < 5:
        return False, None

    days_above = (next_5_days > breakout_price).sum()

    # 计算第5日涨幅
    day5_close = df.loc[breakout_idx + 5, 'close']
    gain_pct = (day5_close / breakout_price - 1) * 100

    return days_above >= 3, gain_pct

def main():
    print("开始分析创业板股票52周新高突破...")

    # 获取创业板股票列表
    chinext_stocks = get_chinext_stocks()
    print(f"获取到 {len(chinext_stocks)} 只创业板股票")

    results = []
    stats = {'total': 0, 'no_data': 0, 'no_breakout': 0, 'no_volume': 0, 'no_followthrough': 0}

    for i, stock_code in enumerate(chinext_stocks, 1):  # 处理所有股票
        if i % 50 == 0:
            print(f"处理进度: {i}/{len(chinext_stocks)}")

        stats['total'] += 1

        # 获取股票数据
        df = get_stock_data(stock_code)
        if df is None:
            stats['no_data'] += 1
            continue

        # 查找52周新高突破
        breakout_info = find_52week_high_breakout(df)
        if breakout_info is None:
            stats['no_breakout'] += 1
            continue

        breakout_idx, breakout_date, breakout_price = breakout_info

        # 检查量能确认
        if not check_volume_confirmation(df, breakout_idx):
            stats['no_volume'] += 1
            continue

        # 检查持续性
        has_followthrough, gain_pct = check_followthrough(df, breakout_idx, breakout_price)
        if not has_followthrough:
            stats['no_followthrough'] += 1
            continue

        # 符合所有条件
        results.append({
            'code': stock_code,
            'breakout_date': breakout_date.strftime('%Y-%m-%d'),
            'breakout_price': round(breakout_price, 2),
            'gain_5d_pct': round(gain_pct, 2)
        })

        print(f"✓ 找到符合条件的股票: {stock_code}")

    # 写入结果
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_19_52week_high_followthrough/independent/claudecode/breakout_followthrough.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        if len(results) == 0:
            f.write("无符合条件的股票\n")
        else:
            for r in results:
                f.write(f"{r['code']},{r['breakout_date']},{r['breakout_price']},{r['gain_5d_pct']}\n")

    print(f"\n分析完成！找到 {len(results)} 只符合条件的股票")
    print(f"统计: 总处理={stats['total']}, 无数据={stats['no_data']}, 无突破={stats['no_breakout']}, 量能不足={stats['no_volume']}, 无持续性={stats['no_followthrough']}")
    print(f"结果已写入: {output_file}")

    return results

if __name__ == "__main__":
    main()
