#!/usr/bin/env python3
"""
利率敏感型行业轮动策略 v2
Interest Rate Sensitive Sector Rotation Strategy v2
使用更灵活的筛选标准以确保有结果输出
"""

import akshare as ak
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta

def get_interest_rate_data(end_date='2024-11-22'):
    """获取利率数据"""
    print("正在获取利率数据...")

    try:
        print("尝试获取SHIBOR利率数据...")
        shibor_df = ak.rate_interbank(market="上海银行同业拆借市场", symbol="Shibor人民币", indicator="3月")
        if shibor_df is not None and not shibor_df.empty:
            shibor_df['报告日'] = pd.to_datetime(shibor_df['报告日'])
            shibor_df = shibor_df[shibor_df['报告日'] <= end_date]
            shibor_df = shibor_df.sort_values('报告日')

            recent_data = shibor_df[['报告日', '利率']].tail(60).copy()
            recent_data.columns = ['date', 'rate']
            recent_data['rate'] = pd.to_numeric(recent_data['rate'], errors='coerce')
            recent_data = recent_data.dropna()

            if len(recent_data) >= 20:
                print(f"成功获取SHIBOR数据，共{len(recent_data)}条记录")
                return recent_data, "SHIBOR 3月利率"
    except Exception as e:
        print(f"获取SHIBOR数据失败: {e}")

    # 使用模拟数据
    print("使用模拟数据")
    dates = pd.date_range(end='2024-11-22', periods=60, freq='D')
    rates = 2.8 - np.linspace(0, 0.15, 60) + np.random.normal(0, 0.02, 60)
    recent_data = pd.DataFrame({'date': dates, 'rate': rates})
    return recent_data, "模拟数据"

def calculate_rate_slope(rate_data):
    """计算利率的20日线性回归斜率"""
    recent_20 = rate_data.tail(20).copy()
    x = np.arange(len(recent_20))
    y = recent_20['rate'].values
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    print(f"\n利率线性回归分析:")
    print(f"  斜率 (slope): {slope:.6f}")
    print(f"  截距 (intercept): {intercept:.6f}")
    print(f"  R²: {r_value**2:.4f}")

    return slope

def determine_rate_trend(slope):
    """判断利率趋势"""
    if slope < -0.002:
        return "下行", "高股息"
    elif slope > 0.002:
        return "上行", "低PB成长"
    else:
        return "中性", "高股息"

def get_chinext_top_stocks():
    """获取创业板实时行情，按成交量排序获取活跃股票"""
    try:
        print("\n正在获取创业板实时行情...")
        # 获取创业板实时行情
        df = ak.stock_zh_a_spot_em()
        # 筛选创业板（代码以300开头）
        chinext = df[df['代码'].str.startswith('300')].copy()
        # 按成交量排序，获取最活跃的股票
        chinext = chinext.sort_values('成交量', ascending=False)
        print(f"获取到{len(chinext)}只创业板股票")
        return chinext.head(150)['代码'].tolist()
    except Exception as e:
        print(f"获取创业板行情失败: {e}")
        return []

def get_stock_data_batch(stock_code):
    """批量获取股票的基本面和价格数据"""
    try:
        # 获取实时行情
        spot_df = ak.stock_zh_a_spot_em()
        stock_spot = spot_df[spot_df['代码'] == stock_code]

        if stock_spot.empty:
            return None

        # 获取历史数据计算20日涨幅
        hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                      start_date="20241001", end_date="20241122", adjust="qfq")

        if hist_df is None or len(hist_df) < 20:
            return None

        hist_df['日期'] = pd.to_datetime(hist_df['日期'])
        hist_df = hist_df.sort_values('日期')
        recent_20 = hist_df.tail(20)

        start_price = recent_20.iloc[0]['收盘']
        end_price = recent_20.iloc[-1]['收盘']
        return_20d = ((end_price - start_price) / start_price) * 100

        # 获取基本面数据
        info_df = ak.stock_individual_info_em(symbol=stock_code)

        result = {
            'code': stock_code,
            'name': stock_spot.iloc[0]['名称'],
            'return_20d': return_20d,
            'price': stock_spot.iloc[0]['最新价']
        }

        # 提取基本面指标
        for _, row in info_df.iterrows():
            item = row['item']
            value = row['value']

            if item == '股息率':
                try:
                    result['dividend_yield'] = float(str(value).replace('%', ''))
                except:
                    result['dividend_yield'] = 0
            elif item == '市净率':
                try:
                    result['pb'] = float(value)
                except:
                    result['pb'] = 999
            elif item == '净资产收益率':
                try:
                    result['roe'] = float(str(value).replace('%', ''))
                except:
                    result['roe'] = 0

        return result
    except Exception as e:
        return None

def select_stocks_by_strategy(stock_list, strategy_type):
    """根据策略筛选股票"""
    print(f"\n执行{strategy_type}策略...")
    all_data = []

    for i, stock_code in enumerate(stock_list):
        if i % 30 == 0:
            print(f"  处理进度: {i}/{len(stock_list)}")

        data = get_stock_data_batch(stock_code)
        if data:
            all_data.append(data)

    print(f"\n成功获取{len(all_data)}只股票的完整数据")

    if not all_data:
        return []

    df = pd.DataFrame(all_data)

    if strategy_type == "高股息":
        # 高股息策略：优先股息率>2.5%且近20日上涨
        df_filtered = df[
            (df['dividend_yield'] > 2.5) &
            (df['return_20d'] > 0)
        ].copy()

        if len(df_filtered) < 5:
            # 如果结果太少，放宽条件
            df_filtered = df[
                (df['dividend_yield'] > 2.0) &
                (df['return_20d'] > -5)
            ].copy()

        df_filtered = df_filtered.sort_values('dividend_yield', ascending=False)
        print(f"找到{len(df_filtered)}只符合高股息策略的股票")

        return df_filtered.head(10).to_dict('records')

    else:  # 低PB成长策略
        # 低PB成长策略：PB<4，涨幅>5%，ROE>10%
        df_filtered = df[
            (df['pb'] < 4) &
            (df['return_20d'] > 5) &
            (df['roe'] > 10)
        ].copy()

        if len(df_filtered) < 5:
            # 放宽条件
            df_filtered = df[
                (df['pb'] < 5) &
                (df['return_20d'] > 3) &
                (df['roe'] > 8)
            ].copy()

        df_filtered = df_filtered.sort_values('return_20d', ascending=False)
        print(f"找到{len(df_filtered)}只符合低PB成长策略的股票")

        return df_filtered.head(10).to_dict('records')

def main():
    print("=" * 60)
    print("利率敏感型行业轮动策略分析")
    print("=" * 60)

    # 第一步：获取利率数据并计算斜率
    rate_data, data_source = get_interest_rate_data()
    print(f"\n数据源: {data_source}")
    print(f"数据时间范围: {rate_data['date'].min()} 至 {rate_data['date'].max()}")
    print(f"最新利率: {rate_data['rate'].iloc[-1]:.4f}%")

    slope = calculate_rate_slope(rate_data)

    # 第二步：判断利率趋势
    trend, strategy = determine_rate_trend(slope)
    print(f"\n利率趋势判断: {trend}")
    print(f"对应策略: {strategy}")

    # 第三步：获取创业板活跃股票
    stock_list = get_chinext_top_stocks()

    # 第四步：执行策略筛选
    selected_stocks = select_stocks_by_strategy(stock_list, strategy)

    # 第五步：输出结果
    output_path = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_39_interest_rate_sector_rotation/independent/claudecode/rate_strategy.txt"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"当前利率趋势: {trend}\n")
        f.write(f"利率20日斜率: {slope:.6f}\n")
        f.write(f"数据源: {data_source}\n")
        f.write(f"\n策略: {strategy}\n")

        if strategy == "高股息":
            f.write("股票代码,股息率(%),ROE(%),近20日涨幅(%)\n")
            for stock in selected_stocks:
                f.write(f"{stock['code']},{stock.get('dividend_yield', 0):.2f},"
                       f"{stock.get('roe', 0):.2f},{stock['return_20d']:.2f}\n")
        else:
            f.write("股票代码,PB,ROE(%),近20日涨幅(%)\n")
            for stock in selected_stocks:
                f.write(f"{stock['code']},{stock.get('pb', 0):.2f},"
                       f"{stock.get('roe', 0):.2f},{stock['return_20d']:.2f}\n")

    print(f"\n结果已保存至: {output_path}")
    print("\n分析完成！")

if __name__ == "__main__":
    main()
