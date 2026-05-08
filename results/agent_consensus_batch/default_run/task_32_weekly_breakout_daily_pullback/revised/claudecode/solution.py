#!/usr/bin/env python3
"""
周线突破+日线回踩确认形态检测
Weekly Breakout + Daily Pullback Pattern Detection

检测逻辑：
1. 周线层面：近4周内出现周线收盘价上穿60周均线，且突破后未再跌破
2. 日线层面：价格回踩20日均线±2%，成交量萎缩(<80%均量)，随后反弹(收阳且放量)
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from mootdx.quotes import Quotes
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please install: pip install mootdx pandas numpy")
    sys.exit(1)


def get_weekly_data(client, symbol, market, weeks=100):
    """获取周线数据"""
    try:
        # 获取足够的日线数据用于转换为周线
        df = client.bars(symbol=symbol, frequency=9, offset=0)
        if df is None or df.empty:
            return None

        # 转换为周线
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')

        # 重采样为周线 (W-FRI: 周五为一周结束)
        weekly = df.resample('W-FRI').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        return weekly.tail(weeks)
    except Exception as e:
        return None


def get_daily_data(client, symbol, market, days=200):
    """获取日线数据"""
    try:
        df = client.bars(symbol=symbol, frequency=9, offset=0)
        if df is None or df.empty:
            return None

        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        return df.tail(days)
    except Exception as e:
        return None


def calculate_ma(data, period):
    """计算移动平均线"""
    return data['close'].rolling(window=period).mean()


def detect_weekly_breakout(weekly_df, cutoff_date):
    """
    检测周线突破
    返回: (是否突破, 突破日期)
    """
    if len(weekly_df) < 60:
        return False, None

    # 计算60周均线
    weekly_df['ma60'] = calculate_ma(weekly_df, 60)

    # 找到截止日期前4周的数据
    cutoff = pd.Timestamp(cutoff_date)
    four_weeks_ago = cutoff - timedelta(weeks=4)

    recent_weeks = weekly_df[(weekly_df.index >= four_weeks_ago) & (weekly_df.index <= cutoff)]

    if len(recent_weeks) < 2:
        return False, None

    # 检测突破：前一周收盘 < 60周均线，本周收盘 > 60周均线
    breakout_date = None
    for i in range(1, len(recent_weeks)):
        prev_close = recent_weeks.iloc[i-1]['close']
        prev_ma60 = recent_weeks.iloc[i-1]['ma60']
        curr_close = recent_weeks.iloc[i]['close']
        curr_ma60 = recent_weeks.iloc[i]['ma60']

        if pd.notna(prev_ma60) and pd.notna(curr_ma60):
            if prev_close < prev_ma60 and curr_close > curr_ma60:
                breakout_date = recent_weeks.index[i]
                break

    if breakout_date is None:
        return False, None

    # 验证突破有效性：突破后未再跌破
    after_breakout = weekly_df[weekly_df.index > breakout_date]
    for idx, row in after_breakout.iterrows():
        if pd.notna(row['ma60']) and row['close'] < row['ma60']:
            return False, None  # 突破后又跌破，无效

    return True, breakout_date


def detect_daily_pullback(daily_df, breakout_date):
    """
    检测日线回踩和反弹
    返回: (回踩日期, 反弹日期, 反弹涨幅)
    """
    # 只看突破后的日线数据
    after_breakout = daily_df[daily_df.index > breakout_date]

    if len(after_breakout) < 25:  # 需要足够数据计算20日均线
        return None, None, None

    # 计算20日均线和20日平均成交量
    after_breakout['ma20'] = calculate_ma(after_breakout, 20)
    after_breakout['vol_ma20'] = after_breakout['volume'].rolling(window=20).mean()

    # 寻找回踩日：收盘价在20日均线±2%范围内，且成交量萎缩
    pullback_candidates = []
    for idx, row in after_breakout.iterrows():
        if pd.notna(row['ma20']) and pd.notna(row['vol_ma20']):
            ma20 = row['ma20']
            close = row['close']
            volume = row['volume']
            vol_ma20 = row['vol_ma20']

            # 回踩条件：价格在MA20的±2%范围内
            if abs(close - ma20) / ma20 <= 0.02:
                # 成交量萎缩：< 80%均量
                if volume < vol_ma20 * 0.8:
                    pullback_candidates.append(idx)

    # 对每个回踩候选，检查是否有反弹
    for pullback_date in pullback_candidates:
        pullback_idx = after_breakout.index.get_loc(pullback_date)

        # 检查次日或后天是否反弹
        for offset in [1, 2]:
            if pullback_idx + offset >= len(after_breakout):
                continue

            bounce_date = after_breakout.index[pullback_idx + offset]
            bounce_row = after_breakout.iloc[pullback_idx + offset]
            pullback_close = after_breakout.loc[pullback_date, 'close']

            # 反弹条件：收阳(收盘>开盘) 且 成交量>20日均量
            if pd.notna(bounce_row['vol_ma20']):
                is_positive = bounce_row['close'] > bounce_row['open']
                is_volume_up = bounce_row['volume'] > bounce_row['vol_ma20']

                if is_positive and is_volume_up:
                    # 计算反弹涨幅
                    gain_pct = (bounce_row['close'] - pullback_close) / pullback_close * 100
                    return pullback_date, bounce_date, gain_pct

    return None, None, None


def scan_stocks(output_file, cutoff_date="2024-04-22"):
    """扫描股票寻找符合条件的形态"""
    client = Quotes.factory(market='std')

    # 获取股票列表 (创业板300开头)
    try:
        stocks_df = client.stocks(market=0)  # 深圳市场
        if stocks_df is None or stocks_df.empty:
            print("无法获取股票列表")
            return []

        # 筛选创业板股票
        gem_stocks = stocks_df[stocks_df['code'].str.startswith('300')]
        print(f"找到 {len(gem_stocks)} 只创业板股票")
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        # 使用示例股票代码
        gem_stocks = pd.DataFrame({'code': ['300001', '300002', '300003']})

    results = []

    for idx, stock in gem_stocks.iterrows():
        code = stock['code']

        try:
            # 获取周线数据
            weekly_df = get_weekly_data(client, code, market=0, weeks=100)
            if weekly_df is None or len(weekly_df) < 60:
                continue

            # 检测周线突破
            has_breakout, breakout_date = detect_weekly_breakout(weekly_df, cutoff_date)
            if not has_breakout:
                continue

            print(f"股票 {code} 检测到周线突破: {breakout_date}")

            # 获取日线数据
            daily_df = get_daily_data(client, code, market=0, days=200)
            if daily_df is None or len(daily_df) < 25:
                continue

            # 检测日线回踩
            pullback_date, bounce_date, gain_pct = detect_daily_pullback(daily_df, breakout_date)

            if pullback_date is not None and bounce_date is not None:
                results.append({
                    'code': code,
                    'breakout_date': breakout_date.strftime('%Y-%m-%d'),
                    'pullback_date': pullback_date.strftime('%Y-%m-%d'),
                    'bounce_date': bounce_date.strftime('%Y-%m-%d'),
                    'gain_pct': round(gain_pct, 2)
                })
                print(f"  ✓ 找到完整形态: 回踩{pullback_date}, 反弹{bounce_date}, 涨幅{gain_pct:.2f}%")

        except Exception as e:
            continue

    # 写入结果
    with open(output_file, 'w', encoding='utf-8') as f:
        if results:
            f.write("股票代码,周线突破日期,日线回踩日期,反弹日期,反弹日涨幅(%)\n")
            for r in results:
                f.write(f"{r['code']},{r['breakout_date']},{r['pullback_date']},{r['bounce_date']},{r['gain_pct']}\n")
        else:
            f.write("无符合条件的股票\n")

    return results


if __name__ == "__main__":
    result_dir = Path(__file__).parent
    output_file = result_dir / "weekly_pullback.txt"

    print("开始扫描周线突破+日线回踩形态...")
    print(f"截止日期: 2024-04-22")
    print(f"输出文件: {output_file}")
    print()

    results = scan_stocks(output_file)

    print(f"\n扫描完成，找到 {len(results)} 只符合条件的股票")
    print(f"结果已写入: {output_file}")
