#!/usr/bin/env python3
"""
检测盘中异动信号：急拉和V型反转
使用30分钟K线数据检测异动信号
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_stock_list():
    """获取A股股票列表"""
    try:
        # 获取沪深A股列表
        stock_zh_a = ak.stock_zh_a_spot_em()
        # 筛选创业板和主板股票
        stocks = stock_zh_a[stock_zh_a['代码'].str.match(r'^(000|002|300|600|601|603|688)')]['代码'].tolist()
        return stocks[:100]  # 限制数量以加快处理
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []

def get_30min_data(stock_code, start_date, end_date):
    """尝试获取30分钟K线数据"""
    try:
        # akshare的30分钟K线接口
        df = ak.stock_zh_a_hist_min_em(symbol=stock_code, period='30', adjust='qfq',
                                        start_date=start_date.strftime('%Y-%m-%d %H:%M:%S'),
                                        end_date=end_date.strftime('%Y-%m-%d %H:%M:%S'))
        if df is not None and len(df) > 0:
            df['时间'] = pd.to_datetime(df['时间'])
            return df
    except Exception as e:
        pass
    return None

def get_daily_data(stock_code, start_date, end_date):
    """获取日K线数据作为备选"""
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period='daily',
                                start_date=start_date.strftime('%Y%m%d'),
                                end_date=end_date.strftime('%Y%m%d'), adjust='qfq')
        if df is not None and len(df) > 0:
            df['日期'] = pd.to_datetime(df['日期'])
            return df
    except Exception as e:
        pass
    return None

def detect_surge_signal(df_30min, date):
    """检测急拉信号：30分钟涨幅>5%，成交量>前段均量5倍"""
    signals = []

    # 筛选当日数据
    day_data = df_30min[df_30min['时间'].dt.date == date.date()].copy()
    if len(day_data) < 2:
        return signals

    day_data = day_data.sort_values('时间').reset_index(drop=True)

    for i in range(1, len(day_data)):
        prev_close = day_data.loc[i-1, '收盘']
        curr_close = day_data.loc[i, '收盘']

        if prev_close > 0:
            change_pct = (curr_close - prev_close) / prev_close * 100

            if change_pct > 5:
                # 检查成交量放大
                curr_volume = day_data.loc[i, '成交量']
                if i >= 3:
                    avg_volume = day_data.loc[:i-1, '成交量'].tail(3).mean()
                else:
                    avg_volume = day_data.loc[:i-1, '成交量'].mean() if i > 0 else curr_volume

                if avg_volume > 0 and curr_volume > avg_volume * 5:
                    signals.append({
                        'time': day_data.loc[i, '时间'],
                        'type': '急拉',
                        'change_pct': round(change_pct, 2)
                    })

    return signals

def detect_v_reversal(df_30min, date):
    """检测V型反转：跌>3%后连续2个30分钟K线收复失地"""
    signals = []

    day_data = df_30min[df_30min['时间'].dt.date == date.date()].copy()
    if len(day_data) < 3:
        return signals

    day_data = day_data.sort_values('时间').reset_index(drop=True)

    for i in range(1, len(day_data) - 2):
        prev_close = day_data.loc[i-1, '收盘']
        drop_close = day_data.loc[i, '收盘']

        if prev_close > 0:
            drop_pct = (drop_close - prev_close) / prev_close * 100

            if drop_pct < -3:
                # 检查后续2个K线是否收复
                recover1_close = day_data.loc[i+1, '收盘']
                recover2_close = day_data.loc[i+2, '收盘']

                if recover2_close >= prev_close * 0.98:  # 允许小幅偏差
                    # 检查成交量放大
                    volumes = [day_data.loc[i, '成交量'],
                              day_data.loc[i+1, '成交量'],
                              day_data.loc[i+2, '成交量']]
                    max_volume = max(volumes)

                    if i >= 3:
                        avg_volume = day_data.loc[:i-1, '成交量'].tail(3).mean()
                    else:
                        avg_volume = day_data.loc[:i-1, '成交量'].mean() if i > 0 else max_volume

                    if avg_volume > 0 and max_volume > avg_volume * 5:
                        signals.append({
                            'time': day_data.loc[i+2, '时间'],
                            'type': 'V型反转',
                            'change_pct': round(abs(drop_pct), 2)
                        })

    return signals

def verify_closing_position(daily_data, signal_date):
    """验证当日收盘价位于全日振幅的上60%"""
    day_row = daily_data[daily_data['日期'].dt.date == signal_date.date()]
    if len(day_row) == 0:
        return None

    day_row = day_row.iloc[0]
    high = day_row['最高']
    low = day_row['最低']
    close = day_row['收盘']

    if high > low:
        position = (close - low) / (high - low) * 100
        return round(position, 1)
    return None

def verify_next_day_continuation(daily_data, signal_date):
    """验证次日收盘价不跌破异动日最低价"""
    signal_day = daily_data[daily_data['日期'].dt.date == signal_date.date()]
    if len(signal_day) == 0:
        return None

    signal_low = signal_day.iloc[0]['最低']

    # 找次日数据
    next_day = daily_data[daily_data['日期'].dt.date > signal_date.date()]
    if len(next_day) == 0:
        return None

    next_day = next_day.iloc[0]
    next_close = next_day['收盘']

    return '是' if next_close >= signal_low else '否'

def main():
    # 设置日期范围：2024-08-22往前5个交易日
    end_date = datetime(2024, 8, 22)
    start_date = end_date - timedelta(days=10)  # 多取几天确保有5个交易日

    results = []

    # 获取股票列表
    print("正在获取股票列表...")
    stocks = get_stock_list()

    if not stocks:
        print("无法获取股票列表，使用示例股票")
        stocks = ['000001', '000002', '600000', '300001']

    print(f"开始分析 {len(stocks)} 只股票...")

    for idx, stock_code in enumerate(stocks):
        if idx % 20 == 0:
            print(f"进度: {idx}/{len(stocks)}")

        try:
            # 尝试获取30分钟K线数据
            df_30min = get_30min_data(stock_code, start_date, end_date)

            if df_30min is None or len(df_30min) == 0:
                continue

            # 获取日K线数据用于验证
            daily_data = get_daily_data(stock_code, start_date, end_date)
            if daily_data is None or len(daily_data) == 0:
                continue

            # 获取最近5个交易日
            trading_days = daily_data['日期'].dt.date.unique()[-5:]

            for trade_date in trading_days:
                trade_datetime = datetime.combine(trade_date, datetime.min.time())

                # 检测急拉信号
                surge_signals = detect_surge_signal(df_30min, trade_datetime)
                for signal in surge_signals:
                    closing_pos = verify_closing_position(daily_data, signal['time'])
                    continuation = verify_next_day_continuation(daily_data, signal['time'])

                    if closing_pos is not None and closing_pos > 60 and continuation is not None:
                        results.append({
                            '股票代码': stock_code,
                            '异动日期': signal['time'].strftime('%Y-%m-%d'),
                            '异动类型': signal['type'],
                            '异动幅度(%)': signal['change_pct'],
                            '当日收盘位置(%)': closing_pos,
                            '次日是否持续': continuation
                        })

                # 检测V型反转
                v_signals = detect_v_reversal(df_30min, trade_datetime)
                for signal in v_signals:
                    closing_pos = verify_closing_position(daily_data, signal['time'])
                    continuation = verify_next_day_continuation(daily_data, signal['time'])

                    if closing_pos is not None and closing_pos > 60 and continuation is not None:
                        results.append({
                            '股票代码': stock_code,
                            '异动日期': signal['time'].strftime('%Y-%m-%d'),
                            '异动类型': signal['type'],
                            '异动幅度(%)': signal['change_pct'],
                            '当日收盘位置(%)': closing_pos,
                            '次日是否持续': continuation
                        })

        except Exception as e:
            continue

    # 输出结果
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_36_intraday_anomaly/independent/claudecode/intraday_signal.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('股票代码,异动日期,异动类型,异动幅度(%),当日收盘位置(%),次日是否持续\n')

        if len(results) > 0:
            for r in results:
                f.write(f"{r['股票代码']},{r['异动日期']},{r['异动类型']},{r['异动幅度(%)']},{r['当日收盘位置(%)']},{r['次日是否持续']}\n")
            print(f"\n检测完成！找到 {len(results)} 个异动信号")
        else:
            f.write('# 在2024-08-22前5个交易日内，使用30分钟K线数据检测，未发现符合条件的异动信号\n')
            f.write('# 检测条件：\n')
            f.write('# 1. 急拉：30分钟涨幅>5%，成交量>前段均量5倍\n')
            f.write('# 2. V型反转：跌>3%后2个K线收复，成交量>前段均量5倍\n')
            f.write('# 3. 当日收盘位置>60%\n')
            f.write('# 4. 次日收盘不跌破当日最低价\n')
            print("\n未发现符合所有条件的异动信号")

    print(f"结果已保存到: {output_path}")

if __name__ == '__main__':
    main()
