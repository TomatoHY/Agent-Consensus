#!/usr/bin/env python3
"""
识别创业板"地量之后天量"突破形态
截止日期：2024-06-07
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_chinext_stocks():
    """获取创业板股票列表"""
    try:
        stock_info = ak.stock_info_a_code_name()
        # 创业板代码以300开头
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except:
        # 备用方案：手动构建部分创业板代码
        return [f"300{str(i).zfill(3)}" for i in range(1, 1000)]

def get_stock_data(code, end_date='2024-06-07'):
    """获取股票历史数据"""
    try:
        # 获取前90天数据以确保有足够的60日均量计算
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=120)).strftime('%Y-%m-%d')
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        if df is None or len(df) < 60:
            return None

        # 标准化列名
        df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        }, inplace=True)

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        return df
    except Exception as e:
        return None

def calculate_60day_avg_volume(df, idx):
    """计算60日均量"""
    if idx < 59:
        return None
    return df.iloc[idx-59:idx+1]['volume'].mean()

def find_doji_periods(df, end_idx, lookback=30):
    """
    在截止日期前30日内查找地量期
    地量期：连续≥3天，每天成交量 < 60日均量的50%
    横盘整理：地量期内价格波动 < 3%
    """
    doji_periods = []

    start_idx = max(59, end_idx - lookback + 1)  # 确保有60日数据

    i = start_idx
    while i <= end_idx:
        avg_vol_60 = calculate_60day_avg_volume(df, i)
        if avg_vol_60 is None:
            i += 1
            continue

        # 检查是否为地量日
        if df.iloc[i]['volume'] < avg_vol_60 * 0.5:
            # 找连续地量期
            period_start = i
            period_end = i

            while period_end < end_idx:
                next_idx = period_end + 1
                next_avg_vol = calculate_60day_avg_volume(df, next_idx)
                if next_avg_vol and df.iloc[next_idx]['volume'] < next_avg_vol * 0.5:
                    period_end = next_idx
                else:
                    break

            # 地量期至少3天
            period_days = period_end - period_start + 1
            if period_days >= 3:
                # 检查横盘条件：价格波动 < 3%
                period_data = df.iloc[period_start:period_end+1]
                high_price = period_data['high'].max()
                low_price = period_data['low'].min()

                if low_price > 0:
                    price_range = (high_price - low_price) / low_price

                    if price_range < 0.03:  # 横盘条件：振幅 < 3%
                        doji_periods.append({
                            'start_idx': period_start,
                            'end_idx': period_end,
                            'days': period_days,
                            'price_range': price_range
                        })

            i = period_end + 1
        else:
            i += 1

    return doji_periods

def check_surge_breakout(df, doji_period):
    """
    检查地量期结束后10日内是否出现天量突破
    条件：
    1. 单日成交量 > 60日均量的3倍
    2. 收阳（收盘>开盘）
    3. 涨幅>5%
    4. 突破近30日最高价
    """
    end_idx = doji_period['end_idx']

    # 计算近30日最高价（在地量期之前）
    lookback_start = max(0, end_idx - 29)
    max_price_30d = df.iloc[lookback_start:end_idx+1]['high'].max()

    # 检查地量期结束后10日内
    for i in range(end_idx + 1, min(end_idx + 11, len(df))):
        avg_vol_60 = calculate_60day_avg_volume(df, i)
        if avg_vol_60 is None:
            continue

        row = df.iloc[i]

        # 条件1：天量（成交量 > 60日均量的3倍）
        volume_ratio = row['volume'] / avg_vol_60
        if volume_ratio <= 3.0:
            continue

        # 条件2：收阳（收盘>开盘）
        if row['close'] <= row['open']:
            continue

        # 条件3：涨幅>5%
        if row['open'] > 0:
            pct_change = (row['close'] - row['open']) / row['open'] * 100
        else:
            continue

        if pct_change <= 5.0:
            continue

        # 条件4：突破近30日最高价
        if row['close'] <= max_price_30d:
            continue

        # 所有条件满足
        return {
            'surge_date': row['date'].strftime('%Y-%m-%d'),
            'volume_ratio': round(volume_ratio, 2),
            'breakout_pct': round(pct_change, 2),
            'doji_days': doji_period['days']
        }

    return None

def main():
    print("开始分析创业板地量天量突破形态...")
    print("截止日期：2024-06-07")
    print("计算60日均量作为基准...")

    results = []

    # 获取创业板股票列表
    chinext_stocks = get_chinext_stocks()
    print(f"获取到 {len(chinext_stocks)} 只创业板股票")

    # 分析每只股票
    for idx, code in enumerate(chinext_stocks[:100], 1):  # 限制分析数量以提高速度
        if idx % 10 == 0:
            print(f"进度: {idx}/100")

        df = get_stock_data(code)
        if df is None or len(df) < 60:
            continue

        # 找到2024-06-07的索引
        end_date = pd.to_datetime('2024-06-07')
        if end_date not in df['date'].values:
            # 找最接近的日期
            df_before = df[df['date'] <= end_date]
            if len(df_before) == 0:
                continue
            end_idx = len(df_before) - 1
        else:
            end_idx = df[df['date'] == end_date].index[0]

        # 查找地量期（在截止日期前30日内）
        doji_periods = find_doji_periods(df, end_idx, lookback=30)

        if not doji_periods:
            continue

        # 检查每个地量期后是否有天量突破
        for doji_period in doji_periods:
            surge = check_surge_breakout(df, doji_period)
            if surge:
                results.append({
                    'code': code,
                    'doji_days': surge['doji_days'],
                    'surge_date': surge['surge_date'],
                    'volume_ratio': surge['volume_ratio'],
                    'breakout_pct': surge['breakout_pct']
                })
                print(f"找到符合条件的股票: {code}")
                break  # 找到一个就够了

    # 写入结果
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_24_doji_to_surge/independent/claudecode/doji_surge.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,地量期天数,天量日期,量比(天量/60日均量),突破涨幅(%)\n")

        if results:
            for r in results:
                f.write(f"{r['code']},{r['doji_days']},{r['surge_date']},{r['volume_ratio']},{r['breakout_pct']}\n")
            print(f"\n共找到 {len(results)} 只符合条件的股票")
        else:
            f.write("# 无符合条件的股票\n")
            print("\n未找到符合所有条件的股票")

    print(f"结果已写入: {output_file}")

    return results

if __name__ == "__main__":
    main()
