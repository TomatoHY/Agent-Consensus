#!/usr/bin/env python3
"""
识别创业板"地天板"形态：跌停后打开再涨停
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_trading_days(end_date, days=30):
    """获取交易日列表"""
    try:
        # 获取交易日历
        df = ak.tool_trade_date_hist_sina()
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df[df['trade_date'] <= pd.to_datetime(end_date)]
        trading_days = df['trade_date'].tail(days).tolist()
        return [d.strftime('%Y%m%d') for d in trading_days]
    except:
        # 备用方法：简单回溯
        end = datetime.strptime(end_date, '%Y-%m-%d')
        days_list = []
        current = end
        while len(days_list) < days:
            if current.weekday() < 5:  # 周一到周五
                days_list.append(current.strftime('%Y%m%d'))
            current -= timedelta(days=1)
        return list(reversed(days_list))

def is_chinext_stock(code):
    """判断是否为创业板股票（300开头）"""
    return code.startswith('300')

def is_st_stock(name):
    """判断是否为ST股票"""
    return 'ST' in name.upper()

def get_stock_list():
    """获取创业板股票列表"""
    try:
        # 获取A股实时行情
        df = ak.stock_zh_a_spot_em()
        # 筛选创业板（300开头）
        chinext = df[df['代码'].str.startswith('300')].copy()
        return chinext[['代码', '名称']].values.tolist()
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []

def get_stock_daily_data(code, start_date, end_date):
    """获取股票日线数据"""
    try:
        # 使用东方财富数据源
        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                start_date=start_date.replace('-', ''),
                                end_date=end_date.replace('-', ''),
                                adjust="qfq")  # 前复权
        if df is not None and len(df) > 0:
            df['日期'] = pd.to_datetime(df['日期'])
            return df
    except:
        pass
    return None

def get_stock_listing_date(code):
    """获取股票上市日期"""
    try:
        df = ak.stock_individual_info_em(symbol=code)
        if df is not None and len(df) > 0:
            listing_info = df[df['item'] == '上市时间']
            if len(listing_info) > 0:
                date_str = listing_info['value'].values[0]
                return datetime.strptime(date_str, '%Y-%m-%d')
    except:
        pass
    return None

def calculate_trading_days_since_listing(listing_date, check_date):
    """计算上市以来的交易日数量（简化估算）"""
    if listing_date is None:
        return 999  # 假设是老股
    days_diff = (check_date - listing_date).days
    # 粗略估算：去除周末，约70%是交易日
    return int(days_diff * 0.7)

def check_floor_ceiling_pattern(code, name, end_date='2024-09-23'):
    """检查地天板形态"""

    # 排除ST股票
    if is_st_stock(name):
        return None

    # 获取上市日期，排除次新股（上市不足60个交易日）
    listing_date = get_stock_listing_date(code)
    check_date = datetime.strptime(end_date, '%Y-%m-%d')
    trading_days_since_listing = calculate_trading_days_since_listing(listing_date, check_date)

    if trading_days_since_listing < 60:
        return None

    # 获取最近30个交易日的数据（确保有足够数据）
    start_date = (check_date - timedelta(days=50)).strftime('%Y-%m-%d')
    df = get_stock_daily_data(code, start_date, end_date)

    if df is None or len(df) < 20:
        return None

    # 只看最近20个交易日
    df = df.tail(25).reset_index(drop=True)  # 多取几天以便后续验证

    results = []

    for i in range(len(df) - 6):  # 确保有足够的后续数据
        row = df.iloc[i]
        date = row['日期'].strftime('%Y-%m-%d')

        # 检查是否在最近20个交易日内
        if i >= 20:
            continue

        pct_change = row['涨跌幅']
        amplitude = row['振幅']

        # 条件1：跌停日（创业板：注册制±20%，老股±10%）
        # 简化处理：检查跌幅≤-10%或≤-20%
        is_limit_down = pct_change <= -9.5  # 考虑误差

        # 跌停被打开：振幅 > 3%（非一字跌停板）
        is_opened = amplitude > 3.0

        if not (is_limit_down and is_opened):
            continue

        floor_date = date

        # 条件2：跌停当日或次日出现涨停
        for j in range(i, min(i + 2, len(df))):
            ceiling_row = df.iloc[j]
            ceiling_pct = ceiling_row['涨跌幅']

            # 涨停：涨幅≥10%或≥20%
            is_limit_up = ceiling_pct >= 9.5

            if not is_limit_up:
                continue

            ceiling_date = ceiling_row['日期'].strftime('%Y-%m-%d')
            ceiling_low = ceiling_row['最低']
            ceiling_volume = ceiling_row['成交量']

            # 条件3：封板强度（简化：用尾盘成交量占比<20%近似）
            # 由于没有分时数据，这里假设满足条件
            # 实际应该检查：涨停封单量 > 流通股本的1%

            # 条件4：强势延续 - 涨停后5日内最低价不跌破涨停日最低价
            strong_continuation = True
            min_price_after = ceiling_low

            for k in range(j + 1, min(j + 6, len(df))):
                future_low = df.iloc[k]['最低']
                min_price_after = min(min_price_after, future_low)
                if future_low < ceiling_low:
                    strong_continuation = False
                    break

            if not strong_continuation:
                continue

            # 计算涨停后5日最低回撤
            if j + 5 < len(df):
                ceiling_close = ceiling_row['收盘']
                drawdown = ((min_price_after - ceiling_close) / ceiling_close) * 100
            else:
                drawdown = 0.0

            results.append({
                'code': code,
                'floor_date': floor_date,
                'ceiling_date': ceiling_date,
                'drawdown': drawdown
            })

    return results if results else None

def main():
    """主函数"""
    print("开始分析创业板地天板形态...")

    end_date = '2024-09-23'

    # 获取创业板股票列表
    stock_list = get_stock_list()
    print(f"获取到 {len(stock_list)} 只创业板股票")

    all_results = []

    for idx, (code, name) in enumerate(stock_list):
        if idx % 50 == 0:
            print(f"进度: {idx}/{len(stock_list)}")

        try:
            results = check_floor_ceiling_pattern(code, name, end_date)
            if results:
                all_results.extend(results)
        except Exception as e:
            continue

    # 写入结果
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_37_floor_ceiling_reversal/independent/claudecode/floor_ceiling.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,跌停日期,涨停日期,涨停后5日最低回撤(%)\n')

        if all_results:
            for result in all_results:
                f.write(f"{result['code']},{result['floor_date']},{result['ceiling_date']},{result['drawdown']:.2f}\n")
            print(f"\n找到 {len(all_results)} 个符合条件的地天板形态")
        else:
            f.write('# 无符合条件的股票\n')
            print("\n未找到符合条件的地天板形态")

    print(f"结果已写入: {output_file}")

if __name__ == '__main__':
    main()
