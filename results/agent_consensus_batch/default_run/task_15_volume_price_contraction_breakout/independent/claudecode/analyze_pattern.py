#!/usr/bin/env python3
"""
识别缩量整理后放量突破形态
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_trading_days_before(end_date, days=80):
    """获取指定日期前的交易日数据"""
    # 获取A股交易日历
    try:
        trade_cal = ak.tool_trade_date_hist_sina()
        trade_cal['trade_date'] = pd.to_datetime(trade_cal['trade_date'])

        end_dt = pd.to_datetime(end_date)
        valid_dates = trade_cal[trade_cal['trade_date'] <= end_dt]['trade_date'].sort_values(ascending=False)

        return valid_dates.head(days).sort_values().tolist()
    except:
        return []

def get_stock_data(stock_code, start_date, end_date):
    """获取股票K线数据"""
    try:
        # 使用akshare获取股票历史数据
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=start_date.replace('-', ''),
                                end_date=end_date.replace('-', ''),
                                adjust="qfq")

        if df is None or len(df) == 0:
            return None

        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')

        # 重命名列
        df = df.rename(columns={
            '日期': 'date',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        })

        return df[['date', 'close', 'high', 'low', 'volume']]
    except Exception as e:
        return None

def calculate_60d_avg_volume(df):
    """计算60日均量"""
    if len(df) < 60:
        return df['volume'].mean()
    return df['volume'].tail(60).mean()

def find_contraction_periods(df, avg_volume_60):
    """使用滑动窗口搜索缩量期"""
    contraction_periods = []

    # 标记缩量日（成交量低于60日均量的70%）
    df['is_low_volume'] = df['volume'] < (avg_volume_60 * 0.7)

    # 滑动窗口搜索连续至少8天的缩量期
    i = 0
    while i < len(df):
        if df.iloc[i]['is_low_volume']:
            # 找到缩量日的起点，向后延伸
            start_idx = i
            end_idx = i

            # 连续缩量日计数
            while end_idx < len(df) and df.iloc[end_idx]['is_low_volume']:
                end_idx += 1

            # 检查是否至少8天
            if end_idx - start_idx >= 8:
                period_df = df.iloc[start_idx:end_idx]

                # 验证价格整理：波动幅度 < 5%
                period_high = period_df['high'].max()
                period_low = period_df['low'].min()
                price_volatility = (period_high - period_low) / period_low

                if price_volatility < 0.05:
                    contraction_periods.append({
                        'start_idx': start_idx,
                        'end_idx': end_idx - 1,
                        'start_date': df.iloc[start_idx]['date'],
                        'end_date': df.iloc[end_idx - 1]['date'],
                        'period_high': period_high,
                        'period_low': period_low,
                        'volatility': price_volatility
                    })

            i = end_idx
        else:
            i += 1

    return contraction_periods

def check_breakout(df, contraction_period, avg_volume_60):
    """检查放量突破"""
    end_idx = contraction_period['end_idx']
    period_high = contraction_period['period_high']

    # 在缩量期结束后的5个交易日内寻找放量突破
    for i in range(end_idx + 1, min(end_idx + 6, len(df))):
        day_data = df.iloc[i]

        # 条件3：成交量超过60日均量的2.5倍
        if day_data['volume'] > avg_volume_60 * 2.5:
            # 条件4：收盘价突破缩量期最高价
            if day_data['close'] > period_high:
                # 计算突破涨幅
                breakout_gain = ((day_data['close'] - period_high) / period_high) * 100

                # 条件5：检查放量突破后无大幅回调（单日跌幅不超过5%）
                has_drawdown = False
                for j in range(i + 1, len(df)):
                    if j >= len(df):
                        break
                    prev_close = df.iloc[j - 1]['close']
                    curr_close = df.iloc[j]['close']
                    daily_decline = ((curr_close - prev_close) / prev_close) * 100

                    if daily_decline < -5:
                        has_drawdown = True
                        break

                if not has_drawdown:
                    return {
                        'breakout_date': day_data['date'],
                        'breakout_gain': breakout_gain,
                        'breakout_close': day_data['close']
                    }

    return None

def analyze_stock(stock_code, end_date):
    """分析单只股票"""
    # 获取前80个交易日的数据（留出余量）
    start_date = (pd.to_datetime(end_date) - timedelta(days=150)).strftime('%Y-%m-%d')

    df = get_stock_data(stock_code, start_date, end_date)

    if df is None or len(df) < 60:
        return []

    # 只取最近60个交易日
    df = df.tail(60).reset_index(drop=True)

    # 计算60日均量
    avg_volume_60 = calculate_60d_avg_volume(df)

    # 使用滑动窗口搜索缩量期
    contraction_periods = find_contraction_periods(df, avg_volume_60)

    results = []
    for period in contraction_periods:
        # 检查放量突破
        breakout = check_breakout(df, period, avg_volume_60)

        if breakout:
            results.append({
                'stock_code': stock_code,
                'contraction_start': period['start_date'].strftime('%Y-%m-%d'),
                'contraction_end': period['end_date'].strftime('%Y-%m-%d'),
                'breakout_date': breakout['breakout_date'].strftime('%Y-%m-%d'),
                'breakout_gain': round(breakout['breakout_gain'], 2)
            })

    return results

def main():
    end_date = '2024-07-15'

    # 获取创业板股票列表
    print("获取创业板股票列表...")
    try:
        stock_list = ak.stock_zh_a_spot_em()
        chinext_stocks = stock_list[stock_list['代码'].str.startswith('300')]['代码'].tolist()
        print(f"找到 {len(chinext_stocks)} 只创业板股票")
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return

    all_results = []

    # 分析每只股票
    for idx, stock_code in enumerate(chinext_stocks[:50], 1):  # 限制数量以加快测试
        print(f"分析 {idx}/{min(50, len(chinext_stocks))}: {stock_code}")
        try:
            results = analyze_stock(stock_code, end_date)
            all_results.extend(results)
        except Exception as e:
            print(f"  分析失败: {e}")
            continue

    # 写入结果
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_15_volume_price_contraction_breakout/independent/claudecode/contraction_breakout.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        if len(all_results) == 0:
            f.write("无符合条件的股票\n")
        else:
            f.write("股票代码,缩量期开始日期,缩量期结束日期,放量突破日期,突破涨幅(%)\n")
            for result in all_results:
                f.write(f"{result['stock_code']},{result['contraction_start']},{result['contraction_end']},{result['breakout_date']},{result['breakout_gain']}\n")

    print(f"\n分析完成！找到 {len(all_results)} 个符合条件的形态")
    print(f"结果已写入: {output_file}")

if __name__ == '__main__':
    main()
