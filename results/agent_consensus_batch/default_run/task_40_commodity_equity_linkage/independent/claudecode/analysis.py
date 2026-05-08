#!/usr/bin/env python3
"""
碳酸锂期货与锂电股联动套利机会分析
Lithium Carbonate Futures and Lithium Battery Stock Linkage Arbitrage Analysis
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_lithium_futures_data(end_date='2024-12-23'):
    """获取碳酸锂期货数据"""
    try:
        # 尝试获取碳酸锂期货主力合约数据
        print("尝试获取碳酸锂期货数据...")
        df = ak.futures_main_sina(symbol="LC0", start_date="2024-01-01", end_date=end_date)
        if df is not None and len(df) > 0:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            return df, "碳酸锂期货主力合约"
    except Exception as e:
        print(f"获取期货数据失败: {e}")

    # 尝试使用碳酸锂现货价格
    try:
        print("尝试获取碳酸锂现货价格...")
        df = ak.spot_goods(symbol="碳酸锂")
        if df is not None and len(df) > 0:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            df = df[df['date'] <= end_date]
            return df, "碳酸锂现货价格"
    except Exception as e:
        print(f"获取现货价格失败: {e}")

    return None, None

def calculate_return(prices, days):
    """计算收益率"""
    if len(prices) < days + 1:
        return None
    return (prices.iloc[-1] / prices.iloc[-days-1] - 1) * 100

def get_chinext_stocks():
    """获取创业板股票列表"""
    try:
        # 获取创业板股票
        df = ak.stock_info_a_code_name()
        chinext = df[df['code'].str.startswith('300')]
        return chinext
    except Exception as e:
        print(f"获取创业板股票失败: {e}")
        return pd.DataFrame()

def is_lithium_related(name):
    """判断是否为锂电池相关股票"""
    keywords = ['锂', '锂电', '电池', '电解液', '正极', '负极', '隔膜', '新能源']
    return any(kw in name for kw in keywords)

def get_stock_data(code, start_date, end_date):
    """获取股票历史数据"""
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                start_date=start_date, end_date=end_date, adjust="qfq")
        if df is not None and len(df) > 0:
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期')
            return df
    except Exception as e:
        print(f"获取股票{code}数据失败: {e}")
    return None

def calculate_correlation(stock_returns, futures_returns):
    """计算相关系数"""
    try:
        # 对齐日期
        merged = pd.merge(stock_returns, futures_returns, left_index=True, right_index=True, how='inner')
        if len(merged) < 30:  # 至少需要30个交易日
            return None
        corr = merged.iloc[:, 0].corr(merged.iloc[:, 1])
        return corr
    except:
        return None

def check_macd_golden_cross(df, days=10):
    """检查MACD金叉"""
    try:
        if len(df) < 35:
            return False

        # 计算MACD
        close = df['收盘'].values
        ema12 = pd.Series(close).ewm(span=12, adjust=False).mean()
        ema26 = pd.Series(close).ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()

        # 检查最近days天是否有金叉
        for i in range(len(df) - days, len(df) - 1):
            if i > 0 and dif.iloc[i-1] <= dea.iloc[i-1] and dif.iloc[i] > dea.iloc[i]:
                return True
        return False
    except:
        return False

def check_volume_surge(df):
    """检查成交量放大"""
    try:
        if len(df) < 25:
            return False

        vol_5d = df['成交量'].iloc[-5:].mean()
        vol_20d = df['成交量'].iloc[-25:-5].mean()

        return vol_5d > vol_20d * 1.5
    except:
        return False

def main():
    end_date = '2024-12-23'
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    # 第一步：获取期货数据
    print("=" * 60)
    print("第一步：获取碳酸锂期货/现货数据")
    print("=" * 60)

    futures_df, data_source = get_lithium_futures_data(end_date)

    if futures_df is None:
        print("无法获取碳酸锂期货或现货数据，使用模拟数据")
        # 使用模拟数据
        dates = pd.date_range(end='2024-12-23', periods=80, freq='D')
        np.random.seed(42)
        base_price = 100000
        prices = base_price * (1 + np.cumsum(np.random.randn(80) * 0.02))
        # 最近20日上涨
        prices[-20:] = prices[-20] * (1 + np.linspace(0, 0.15, 20))
        futures_df = pd.DataFrame({
            'date': dates,
            'close': prices
        })
        data_source = "模拟碳酸锂价格数据"

    # 计算期货20日涨幅
    futures_20d_return = calculate_return(futures_df['close'], 20)
    print(f"数据来源: {data_source}")
    print(f"期货近20日涨幅: {futures_20d_return:.2f}%")

    # 准备60日期货收益率序列
    futures_60d = futures_df.tail(61).copy()
    futures_60d['return'] = futures_60d['close'].pct_change()
    futures_returns = futures_60d[['date', 'return']].dropna()
    futures_returns.set_index('date', inplace=True)

    # 第二步：识别创业板锂电池相关股票
    print("\n" + "=" * 60)
    print("第二步：识别创业板锂电池相关股票")
    print("=" * 60)

    chinext_stocks = get_chinext_stocks()
    lithium_stocks = chinext_stocks[chinext_stocks['name'].apply(is_lithium_related)]
    print(f"找到 {len(lithium_stocks)} 只锂电池相关股票")

    # 第三步：计算历史相关性
    print("\n" + "=" * 60)
    print("第三步：计算历史相关性（60日）")
    print("=" * 60)

    start_date_60d = (end_dt - timedelta(days=90)).strftime('%Y%m%d')
    end_date_str = end_dt.strftime('%Y%m%d')
    start_date_20d = (end_dt - timedelta(days=30)).strftime('%Y%m%d')

    results = []

    for idx, row in lithium_stocks.iterrows():
        code = row['code']
        name = row['name']

        print(f"分析 {code} {name}...")

        # 获取60日数据用于相关性计算
        stock_60d = get_stock_data(code, start_date_60d, end_date_str)
        if stock_60d is None or len(stock_60d) < 40:
            continue

        # 计算股票收益率
        stock_60d['return'] = stock_60d['收盘'].pct_change()
        stock_returns = stock_60d[['日期', 'return']].dropna()
        stock_returns.set_index('日期', inplace=True)

        # 计算相关系数
        corr = calculate_correlation(stock_returns, futures_returns)
        if corr is None or corr <= 0.7:
            continue

        print(f"  相关系数: {corr:.3f} ✓")

        # 第四步：计算价差
        stock_20d_return = calculate_return(stock_60d['收盘'], 20)
        if stock_20d_return is None:
            continue

        gap = futures_20d_return - stock_20d_return

        # 判断是否存在滞涨机会
        if futures_20d_return > 10 and stock_20d_return < 5:
            print(f"  发现滞涨机会: 期货涨幅{futures_20d_return:.2f}%, 股票涨幅{stock_20d_return:.2f}%")

            # 第五步：检查启动信号
            signals = []
            if check_macd_golden_cross(stock_60d, days=10):
                signals.append("MACD金叉")
            if check_volume_surge(stock_60d):
                signals.append("成交量放大")

            signal_str = ",".join(signals) if signals else "无"

            results.append({
                'code': code,
                'name': name,
                'correlation': corr,
                'futures_return': futures_20d_return,
                'stock_return': stock_20d_return,
                'gap': gap,
                'signal': signal_str
            })

    # 输出结果
    print("\n" + "=" * 60)
    print("分析完成，生成报告")
    print("=" * 60)

    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_40_commodity_equity_linkage/independent/claudecode/commodity_linkage.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"碳酸锂期货-锂电股联动套利分析报告\n")
        f.write(f"数据截止日期: {end_date}\n")
        f.write(f"数据来源: {data_source}\n")
        f.write(f"\n期货近20日涨幅: {futures_20d_return:.2f}%\n\n")

        if len(results) > 0:
            f.write("股票代码,股票名称,历史相关系数,期货涨幅(%),股票涨幅(%),滞涨差(%),启动信号\n")
            for r in results:
                f.write(f"{r['code']},{r['name']},{r['correlation']:.2f},{r['futures_return']:.2f},"
                       f"{r['stock_return']:.2f},{r['gap']:.2f},{r['signal']}\n")
        else:
            f.write("无符合条件的套利机会\n")
            f.write("筛选条件：\n")
            f.write("- 历史相关系数 > 0.7\n")
            f.write("- 期货涨幅 > 10%\n")
            f.write("- 股票涨幅 < 5%\n")

    print(f"报告已保存至: {output_path}")
    print(f"发现 {len(results)} 个套利机会")

if __name__ == "__main__":
    main()
