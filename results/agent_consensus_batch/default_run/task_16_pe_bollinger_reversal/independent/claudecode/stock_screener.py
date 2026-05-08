#!/usr/bin/env python3
"""
PE筛选后布林带反弹选股
Combines fundamental (PE ratio) and technical (Bollinger Bands) analysis
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_chinext_stocks_with_pe():
    """获取创业板股票及其PE数据"""
    print("正在获取创业板股票PE数据...")

    # 获取创业板股票列表（代码以300开头）
    stock_info = ak.stock_zh_a_spot_em()
    chinext_stocks = stock_info[stock_info['代码'].str.startswith('300')].copy()

    # 筛选PE在15-60之间的股票
    chinext_stocks['市盈率'] = pd.to_numeric(chinext_stocks['市盈率-动态'], errors='coerce')
    filtered_stocks = chinext_stocks[
        (chinext_stocks['市盈率'] >= 15) &
        (chinext_stocks['市盈率'] <= 60)
    ].copy()

    print(f"创业板股票总数: {len(chinext_stocks)}")
    print(f"PE在15-60之间的股票数: {len(filtered_stocks)}")

    return filtered_stocks[['代码', '名称', '市盈率']]

def calculate_bollinger_bands(prices, window=20, num_std=2):
    """计算布林带指标"""
    middle_band = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    upper_band = middle_band + (std * num_std)
    lower_band = middle_band - (std * num_std)

    return middle_band, upper_band, lower_band

def check_bollinger_bounce(stock_code, end_date='2024-08-15'):
    """
    检测布林带反弹信号：
    1. 价格曾触及或跌破下轨（最近20天内）
    2. 最新收盘价回到中轨以上
    """
    try:
        # 获取历史数据（需要更多天数来计算布林带）
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=60)

        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_dt.strftime('%Y%m%d'),
            end_date=end_dt.strftime('%Y%m%d'),
            adjust="qfq"
        )

        if df is None or len(df) < 25:
            return None

        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')

        # 计算布林带
        middle, upper, lower = calculate_bollinger_bands(df['收盘'], window=20, num_std=2)
        df['中轨'] = middle
        df['上轨'] = upper
        df['下轨'] = lower

        # 获取最近20天的数据
        recent_20 = df.tail(20).copy()

        if len(recent_20) < 20:
            return None

        # 检查是否有触及或跌破下轨的情况
        touched_lower = (recent_20['收盘'] <= recent_20['下轨']).any()

        # 检查最新收盘价是否在中轨以上
        latest = df.iloc[-1]
        above_middle = latest['收盘'] > latest['中轨']

        if touched_lower and above_middle:
            # 找到反弹日期（从下轨回到中轨以上的日期）
            bounce_date = None
            for i in range(len(recent_20) - 1, -1, -1):
                row = recent_20.iloc[i]
                if row['收盘'] > row['中轨']:
                    bounce_date = row['日期']
                else:
                    break

            # 计算近5日涨幅
            if len(df) >= 5:
                recent_5 = df.tail(5)
                price_change_pct = ((recent_5.iloc[-1]['收盘'] - recent_5.iloc[0]['收盘']) /
                                   recent_5.iloc[0]['收盘'] * 100)
            else:
                price_change_pct = 0

            # 计算成交量
            recent_5_vol = df.tail(5)['成交量'].mean()
            recent_20_vol = df.tail(20)['成交量'].mean()

            return {
                'bounce_date': bounce_date,
                'price_change_5d': price_change_pct,
                'vol_5d_avg': recent_5_vol,
                'vol_20d_avg': recent_20_vol,
                'volume_confirmed': recent_5_vol > recent_20_vol
            }

        return None

    except Exception as e:
        print(f"处理股票 {stock_code} 时出错: {str(e)}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("PE筛选后布林带反弹选股")
    print("=" * 60)

    # 第一步：获取PE数据并筛选
    pe_filtered_stocks = get_chinext_stocks_with_pe()

    if len(pe_filtered_stocks) == 0:
        print("没有符合PE条件的股票")
        with open('/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_16_pe_bollinger_reversal/independent/claudecode/pe_bollinger_top8.txt', 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        return

    # 第二步和第三步：布林带反弹检测和量能验证
    results = []

    print("\n开始检测布林带反弹信号...")
    for idx, row in pe_filtered_stocks.iterrows():
        stock_code = row['代码']
        stock_name = row['名称']
        pe_ratio = row['市盈率']

        print(f"检测 {stock_code} {stock_name} (PE={pe_ratio:.2f})...", end=' ')

        bounce_info = check_bollinger_bounce(stock_code)

        if bounce_info and bounce_info['volume_confirmed']:
            print("✓ 符合条件")
            results.append({
                '股票代码': stock_code,
                '股票名称': stock_name,
                'PE': pe_ratio,
                '布林带反弹日期': bounce_info['bounce_date'].strftime('%Y-%m-%d') if bounce_info['bounce_date'] else 'N/A',
                '近5日涨幅(%)': round(bounce_info['price_change_5d'], 2)
            })
        else:
            print("✗ 不符合")

        # 限制检测数量以避免超时
        if len(results) >= 15:
            break

    # 第四步：按PE排序并取前8名
    if len(results) == 0:
        print("\n没有符合所有条件的股票")
        with open('/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_16_pe_bollinger_reversal/independent/claudecode/pe_bollinger_top8.txt', 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        return

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('PE').head(8)

    print(f"\n找到 {len(results_df)} 只符合条件的股票")
    print("\n" + "=" * 60)
    print("前8名结果（按PE升序）：")
    print("=" * 60)
    print(results_df.to_string(index=False))

    # 保存结果
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_16_pe_bollinger_reversal/independent/claudecode/pe_bollinger_top8.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("股票代码,PE,布林带反弹日期,近5日涨幅(%)\n")
        for _, row in results_df.iterrows():
            f.write(f"{row['股票代码']},{row['PE']},{row['布林带反弹日期']},{row['近5日涨幅(%)']}\n")

    print(f"\n结果已保存到: {output_path}")

if __name__ == "__main__":
    main()
