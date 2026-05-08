#!/usr/bin/env python3
"""
识别创业板"地天板"形态：跌停后打开再涨停
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_chinext_stocks():
    """获取创业板股票列表"""
    try:
        df = ak.stock_zh_a_spot_em()
        chinext = df[df['代码'].str.startswith('300')].copy()
        return chinext[['代码', '名称']].values.tolist()
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []

def get_stock_data(code, start_date, end_date):
    """获取股票日线数据"""
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                start_date=start_date.replace('-', ''),
                                end_date=end_date.replace('-', ''),
                                adjust="qfq")
        if df is not None and len(df) > 0:
            df['日期'] = pd.to_datetime(df['日期'])
            return df
    except:
        pass
    return None

def get_listing_date(code):
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

def is_st_stock(name):
    """判断是否为ST股票"""
    return 'ST' in name.upper()

def calculate_amplitude(row):
    """计算振幅"""
    if row['开盘'] == 0:
        return 0
    return ((row['最高'] - row['最低']) / row['开盘'] * 100)

def analyze_floor_ceiling(code, name, end_date='2024-09-23'):
    """分析地天板形态"""

    # 排除ST股票
    if is_st_stock(name):
        return None

    # 检查上市日期，排除次新股（上市不足60个交易日）
    listing_date = get_listing_date(code)
    check_date = datetime.strptime(end_date, '%Y-%m-%d')

    if listing_date:
        days_diff = (check_date - listing_date).days
        trading_days_approx = int(days_diff * 0.7)  # 估算交易日
        if trading_days_approx < 60:
            return None

    # 获取最近30个交易日数据（确保覆盖20个交易日）
    start_date = (check_date - timedelta(days=45)).strftime('%Y-%m-%d')
    df = get_stock_data(code, start_date, end_date)

    if df is None or len(df) < 10:
        return None

    df = df.sort_values('日期').reset_index(drop=True)

    # 只分析最近20个交易日
    df = df.tail(20).reset_index(drop=True)

    results = []

    for i in range(len(df) - 1):
        row = df.iloc[i]
        pct_chg = row['涨跌幅']

        # 计算振幅
        amplitude = calculate_amplitude(row)

        # 判断是否跌停（创业板：-20%或-10%，允许0.5%误差）
        is_limit_down = (pct_chg <= -19.5 or (-10.5 <= pct_chg <= -9.5))

        # 判断跌停是否被打开（振幅>3%，非一字板）
        is_opened = amplitude > 3.0

        if not (is_limit_down and is_opened):
            continue

        limit_down_date = row['日期']

        # 检查当日或次日是否涨停
        for j in range(i, min(i + 2, len(df))):
            check_row = df.iloc[j]
            check_pct = check_row['涨跌幅']

            # 判断是否涨停（创业板：20%或10%，允许0.5%误差）
            is_limit_up = (check_pct >= 19.5 or (9.5 <= check_pct <= 10.5))

            if not is_limit_up:
                continue

            limit_up_date = check_row['日期']
            limit_up_low = check_row['最低']
            limit_up_close = check_row['收盘']

            # 检查涨停后5日内最低价不跌破涨停日最低价
            future_days = df.iloc[j+1:min(j+6, len(df))]

            if len(future_days) < 5:
                continue  # 数据不足5天

            min_low_after = future_days['最低'].min()

            # 强势延续：涨停后5日内最低价不跌破涨停日最低价
            if min_low_after >= limit_up_low:
                # 计算涨停后5日最低回撤
                drawdown = ((min_low_after - limit_up_close) / limit_up_close * 100)

                results.append({
                    'code': code,
                    'limit_down_date': limit_down_date.strftime('%Y-%m-%d'),
                    'limit_up_date': limit_up_date.strftime('%Y-%m-%d'),
                    'drawdown': round(drawdown, 2)
                })
                break

    return results if results else None

def main():
    """主函数"""
    print("开始识别地天板形态...")

    # 获取创业板股票列表
    stocks = get_chinext_stocks()
    print(f"获取到 {len(stocks)} 只创业板股票")

    all_results = []

    for i, (code, name) in enumerate(stocks):
        if (i + 1) % 50 == 0:
            print(f"进度: {i+1}/{len(stocks)}")

        try:
            results = analyze_floor_ceiling(code, name)
            if results:
                all_results.extend(results)
        except Exception as e:
            continue

    # 写入结果文件
    output_file = 'floor_ceiling.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,跌停日期,涨停日期,涨停后5日最低回撤(%)\n')

        if len(all_results) == 0:
            f.write('# 无符合条件的地天板形态\n')
        else:
            for r in all_results:
                f.write(f"{r['code']},{r['limit_down_date']},{r['limit_up_date']},{r['drawdown']}\n")

    print(f"\n分析完成！找到 {len(all_results)} 个符合条件的地天板形态")
    print(f"结果已写入: {output_file}")

if __name__ == '__main__':
    main()
