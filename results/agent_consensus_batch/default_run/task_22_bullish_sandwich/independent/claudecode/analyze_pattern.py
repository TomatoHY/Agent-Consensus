#!/usr/bin/env python3
"""
识别创业板"两阳夹一阴"多方炮形态
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def is_bullish_candle(open_price, close_price, prev_close, threshold=0.02):
    """判断是否为阳线且涨幅>2%"""
    if close_price <= open_price:
        return False
    change_pct = (close_price - prev_close) / prev_close
    return change_pct > threshold

def is_bearish_candle(open_price, close_price, prev_close, threshold=0.01):
    """判断是否为阴线且跌幅<1%"""
    if close_price >= open_price:
        return False
    change_pct = (close_price - prev_close) / prev_close
    return change_pct > -threshold

def check_engulfing(day2_open, day2_close, day3_open, day3_close):
    """检查第3日阳线实体完全吞没第2日阴线"""
    # 第3日收盘价 > 第2日开盘价，第3日开盘价 < 第2日收盘价
    return day3_close > day2_open and day3_open < day2_close

def check_volume_increase(vol1, vol2, vol3):
    """检查成交量逐步放大"""
    return vol2 > vol1 and vol3 > vol2

def check_ma_trend(df, idx):
    """检查均线多头排列：5日均线 > 10日均线 > 20日均线"""
    if idx < 19:  # 需要至少20天数据计算20日均线
        return False

    # 在第3天（idx+2）位置计算均线
    check_idx = idx + 2
    if check_idx >= len(df):
        return False

    ma5 = df['收盘'].iloc[check_idx-4:check_idx+1].mean()
    ma10 = df['收盘'].iloc[check_idx-9:check_idx+1].mean()
    ma20 = df['收盘'].iloc[check_idx-19:check_idx+1].mean()

    return ma5 > ma10 > ma20

def detect_bullish_sandwich(stock_code, end_date='2024-04-08'):
    """检测单只股票的两阳夹一阴形态"""
    try:
        # 获取60日K线数据
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=90)  # 多取一些以确保有60个交易日

        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_dt.strftime('%Y%m%d'),
            end_date=end_dt.strftime('%Y%m%d'),
            adjust="qfq"
        )

        if df is None or len(df) < 40:
            return []

        df = df.sort_values('日期').reset_index(drop=True)
        df['日期'] = pd.to_datetime(df['日期'])

        # 只检查最近20个交易日
        if len(df) < 20:
            return []

        results = []
        start_check_idx = max(20, len(df) - 20)  # 从倒数第20个交易日开始

        # 遍历最近20个交易日，检查每个3日窗口
        for i in range(start_check_idx, len(df) - 2):
            day1 = df.iloc[i]
            day2 = df.iloc[i + 1]
            day3 = df.iloc[i + 2]

            # 获取前一日收盘价用于计算涨跌幅
            prev_close_day1 = df.iloc[i - 1]['收盘'] if i > 0 else day1['开盘']
            prev_close_day2 = day1['收盘']
            prev_close_day3 = day2['收盘']

            # 条件1：第1日、第3日为阳线且涨幅>2%
            if not is_bullish_candle(day1['开盘'], day1['收盘'], prev_close_day1, 0.02):
                continue
            if not is_bullish_candle(day3['开盘'], day3['收盘'], prev_close_day3, 0.02):
                continue

            # 条件1：第2日为阴线但跌幅<1%
            if not is_bearish_candle(day2['开盘'], day2['收盘'], prev_close_day2, 0.01):
                continue

            # 条件2：第3日阳线实体完全吞没第2日阴线
            if not check_engulfing(day2['开盘'], day2['收盘'], day3['开盘'], day3['收盘']):
                continue

            # 条件3：三日成交量逐步放大
            vol1 = day1['成交量']
            vol2 = day2['成交量']
            vol3 = day3['成交量']

            if not check_volume_increase(vol1, vol2, vol3):
                continue

            # 条件4：形态出现在上升趋势中（均线多头排列）
            if not check_ma_trend(df, i):
                continue

            # 计算成交量比
            vol_ratio_2_1 = vol2 / vol1
            vol_ratio_3_2 = vol3 / vol2

            results.append({
                'code': stock_code,
                'date': day1['日期'].strftime('%Y-%m-%d'),
                'vol_ratio_2_1': vol_ratio_2_1,
                'vol_ratio_3_2': vol_ratio_3_2
            })

        return results

    except Exception as e:
        print(f"处理 {stock_code} 时出错: {e}")
        return []

def main():
    """主函数"""
    print("开始获取创业板股票列表...")

    # 获取创业板股票列表（代码以300开头）
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext_stocks = stock_info[stock_info['code'].str.startswith('300')]['code'].tolist()
        print(f"找到 {len(chinext_stocks)} 只创业板股票")
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return

    all_results = []

    # 遍历每只股票
    for idx, stock_code in enumerate(chinext_stocks[:50], 1):  # 限制处理数量以避免超时
        print(f"处理 {idx}/{min(50, len(chinext_stocks))}: {stock_code}")
        results = detect_bullish_sandwich(stock_code)
        all_results.extend(results)

    # 写入结果文件
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_22_bullish_sandwich/independent/claudecode/bullish_sandwich.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        if all_results:
            for result in all_results:
                f.write(f"{result['code']},{result['date']},{result['vol_ratio_2_1']:.2f},{result['vol_ratio_3_2']:.2f}\n")
            print(f"\n找到 {len(all_results)} 个符合条件的形态")
        else:
            f.write("无符合条件的形态\n")
            print("\n无符合条件的形态")

    print(f"结果已写入: {output_file}")

if __name__ == "__main__":
    main()
