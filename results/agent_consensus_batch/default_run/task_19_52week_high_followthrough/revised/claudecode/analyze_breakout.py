#!/usr/bin/env python3
"""
52周新高突破跟进分析
找出创业板中创52周新高、量能放大且持续上涨的股票
使用mootdx数据源
"""
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
from mootdx.quotes import Quotes
from datetime import datetime

client = Quotes.factory(market='std')

def find_52week_high_breakout(df, end_date='2024-11-15'):
    """
    在最近30个交易日内找到首次突破52周(252个交易日)新高的日期

    返回: (breakout_idx, breakout_price) 或 None
    """
    # 过滤到截止日期
    end_date_ts = pd.to_datetime(end_date)
    df_filtered = df[df.index <= end_date_ts]

    # 确保有足够数据: 252 + 30 = 282个交易日
    if len(df_filtered) < 282:
        return None

    # 最近30个交易日的窗口
    for i in range(len(df_filtered) - 30, len(df_filtered)):
        if i < 252:
            continue

        current_close = df_filtered.iloc[i]['close']

        # 获取过去252个交易日的最高收盘价（不包括当天）
        past_252_days = df_filtered.iloc[i-252:i]
        max_close_252 = past_252_days['close'].max()

        # 检查是否创新高
        if current_close > max_close_252:
            return (i, current_close, df_filtered)

    return None

def check_volume_confirmation(df, breakout_idx):
    """
    检查量能确认：创新高日±2天(共5天)的成交量均值 > 60日均量的1.5倍
    """
    # 5天窗口：breakout_idx-2 到 breakout_idx+2
    window_start = max(0, breakout_idx - 2)
    window_end = min(len(df), breakout_idx + 3)  # +3 因为是左闭右开

    if window_end - window_start < 5:
        return False

    volume_window = df.iloc[window_start:window_end]['vol']
    avg_volume_window = volume_window.mean()

    # 60日均量（在突破日之前）
    if breakout_idx < 60:
        return False

    past_60_days = df.iloc[breakout_idx-60:breakout_idx]
    avg_volume_60 = past_60_days['vol'].mean()

    return avg_volume_window > (avg_volume_60 * 1.5)

def check_followthrough(df, breakout_idx, breakout_price):
    """
    检查持续性：新高后5个交易日内，至少3天收盘价高于创新高价

    返回: (is_valid, gain_pct) 或 (False, None)
    """
    # 需要突破日后至少5个交易日
    if breakout_idx + 5 >= len(df):
        return False, None

    next_5_days = df.iloc[breakout_idx+1:breakout_idx+6]

    # 统计有多少天收盘价高于突破价
    days_above = (next_5_days['close'] > breakout_price).sum()

    if days_above < 3:
        return False, None

    # 计算新高后5日涨幅 = (第5日收盘 / 创新高日收盘 - 1) * 100
    day5_close = df.iloc[breakout_idx + 5]['close']
    gain_pct = (day5_close / breakout_price - 1) * 100

    return True, gain_pct

def main():
    print("开始分析创业板52周新高突破跟进...")
    print(f"截止日期: 2024-11-15")
    print(f"分析窗口: 最近30个交易日")
    print()

    # 获取创业板股票列表
    print("获取创业板股票列表...")
    stocks = client.stocks(market=0)
    gem = stocks[stocks['code'].str.match(r'^3\d{5}$')]
    codes = gem['code'].tolist()
    total = len(codes)
    print(f"共 {total} 只创业板股票")

    results = []

    for i, code in enumerate(codes):
        if (i + 1) % 100 == 0:
            print(f"进度: {i+1}/{total}")

        try:
            # 获取足够的数据：252 + 30 + 5 = 287个交易日，取300个确保足够
            df = client.bars(symbol=code, frequency=9, start=0, offset=300)

            if df is None or len(df) < 287:
                continue

            # mootdx返回的数据是从旧到新排序的，datetime既是索引又是列
            # 确保数据按时间正序排列
            df = df.sort_index()

            # 1. 找到52周新高突破点
            breakout_info = find_52week_high_breakout(df)
            if breakout_info is None:
                continue

            breakout_idx, breakout_price, df_filtered = breakout_info

            # 2. 检查量能确认
            if not check_volume_confirmation(df_filtered, breakout_idx):
                continue

            # 3. 检查持续性
            is_valid, gain_pct = check_followthrough(df_filtered, breakout_idx, breakout_price)
            if not is_valid:
                continue

            # 获取突破日期
            breakout_date = df_filtered.index[breakout_idx]
            if isinstance(breakout_date, pd.Timestamp):
                breakout_date_str = breakout_date.strftime('%Y-%m-%d')
            else:
                breakout_date_str = str(breakout_date)[:10]

            results.append({
                'code': code,
                'breakout_date': breakout_date_str,
                'breakout_price': round(float(breakout_price), 2),
                'gain_5d_pct': round(float(gain_pct), 2)
            })

            print(f"✓ {code}: {breakout_date_str}, "
                  f"价格 {breakout_price:.2f}, 5日涨幅 {gain_pct:.2f}%")

        except Exception as e:
            continue

    print(f"\n分析完成，共找到 {len(results)} 只符合条件的股票")

    # 写入结果文件
    output_file = 'breakout_followthrough.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        if len(results) == 0:
            f.write("无符合条件的股票\n")
        else:
            f.write("股票代码,创新高日期,创新高价格,新高后5日涨幅(%)\n")
            for r in results:
                f.write(f"{r['code']},{r['breakout_date']},{r['breakout_price']},{r['gain_5d_pct']}\n")

    print(f"结果已写入 {output_file}")

if __name__ == '__main__':
    main()
