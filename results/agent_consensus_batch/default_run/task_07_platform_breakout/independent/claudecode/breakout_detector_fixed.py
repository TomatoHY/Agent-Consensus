import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import os

# Disable proxy to avoid connection issues
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

def get_chinext_stocks():
    """获取创业板股票列表（代码以300开头）"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []

def get_trading_days_before(end_date, days=20):
    """获取指定日期之前的交易日数据（多获取一些以确保有足够的交易日）"""
    start_date = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=days*2)).strftime('%Y%m%d')
    return start_date

def check_breakout_pattern(stock_code, end_date='20240930'):
    """
    检查股票是否满足平台突破形态

    条件：
    1) 前10天价格在窄幅区间波动（最高价 - 最低价 < 5%，以最低价为基准）
    2) 最后5个交易日里至少有3天收盘价突破前10天的最高价
    3) 突破时成交量放大（突破日的成交量超过前10天均量的1.5倍）
    """
    try:
        # 获取K线数据
        start_date = get_trading_days_before(end_date, 20)
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=start_date, end_date=end_date, adjust="qfq")

        if df is None or len(df) < 15:
            return False

        # 取最近15个交易日
        df = df.tail(15).reset_index(drop=True)

        if len(df) < 15:
            return False

        # 分割数据：前10天和最后5天
        first_10_days = df.iloc[:10]
        last_5_days = df.iloc[10:]

        # 条件1: 前10天窄幅波动（range < 5%）
        max_high = first_10_days['最高'].max()
        min_low = first_10_days['最低'].min()
        price_range = (max_high - min_low) / min_low

        if price_range >= 0.05:  # 不满足窄幅条件
            return False

        # 条件2: 最后5天中至少3天收盘价突破前10天最高价
        breakout_threshold = first_10_days['最高'].max()
        breakout_days = (last_5_days['收盘'] > breakout_threshold).sum()

        if breakout_days < 3:
            return False

        # 条件3: 突破日成交量放大（突破日成交量 > 前10天均量 * 1.5）
        avg_volume_10days = first_10_days['成交量'].mean()

        # 找出突破的那些天
        breakout_mask = last_5_days['收盘'] > breakout_threshold
        breakout_volumes = last_5_days.loc[breakout_mask, '成交量']

        # 至少有一个突破日的成交量满足放大条件
        volume_amplified = (breakout_volumes > avg_volume_10days * 1.5).any()

        if not volume_amplified:
            return False

        return True

    except Exception as e:
        # Silently skip errors
        return False

def main():
    print("开始获取创业板股票列表...")
    chinext_stocks = get_chinext_stocks()
    print(f"共获取到 {len(chinext_stocks)} 只创业板股票")

    breakout_stocks = []

    print("\n开始检测平台突破形态...")
    for i, stock_code in enumerate(chinext_stocks, 1):
        if i % 100 == 0:
            print(f"进度: {i}/{len(chinext_stocks)}")

        if check_breakout_pattern(stock_code):
            breakout_stocks.append(stock_code)
            print(f"找到符合条件的股票: {stock_code}")

    # 写入结果
    result_path = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_07_platform_breakout/independent/claudecode/breakout.txt"

    with open(result_path, 'w') as f:
        if breakout_stocks:
            for stock in breakout_stocks:
                f.write(f"{stock}\n")
        else:
            f.write("无符合条件的股票\n")

    print(f"\n检测完成！共找到 {len(breakout_stocks)} 只符合条件的股票")
    print(f"结果已写入: {result_path}")

if __name__ == "__main__":
    main()
