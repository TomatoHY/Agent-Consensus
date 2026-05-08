#!/usr/bin/env python3
"""
五维度综合评分超级选股
Multi-dimensional stock screening with comprehensive scoring
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Target date and lookback periods
TARGET_DATE = '2024-12-13'
SECTOR_PERIOD = 20  # days for sector trend
STOCK_PERIOD = 20   # days for stock performance
MA_SHORT = 20
MA_LONG = 60

# Sector keywords mapping
SECTOR_KEYWORDS = {
    '医药': ['医药', '生物', '制药', '医疗', '药业', '健康'],
    '新能源': ['新能源', '光伏', '锂电', '电池', '储能', '风电', '太阳能'],
    '半导体': ['半导体', '芯片', '集成电路', '微电子', '晶圆'],
    '消费电子': ['消费电子', '电子', '通信', '智能终端', '显示']
}

def get_chinext_stocks():
    """Get ChiNext (创业板) stock list"""
    print("获取创业板股票列表...")
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        print(f"创业板股票数量: {len(chinext)}")
        return chinext
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return pd.DataFrame()

def classify_sector(stock_name):
    """Classify stock into sectors based on name"""
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw in stock_name for kw in keywords):
            return sector
    return None

def get_stock_data(stock_code, days=120):
    """Get historical stock data"""
    try:
        # akshare requires specific format
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date="20240701", end_date="20241231", adjust="qfq")
        if df is None or len(df) == 0:
            return None
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')
        return df
    except Exception as e:
        return None

def calculate_ma(prices, period):
    """Calculate moving average"""
    return prices.rolling(window=period).mean()

def calculate_macd(prices):
    """Calculate MACD indicator"""
    ema12 = prices.ewm(span=12, adjust=False).mean()
    ema26 = prices.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    histogram = (dif - dea) * 2
    return histogram

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_pe_ratio(stock_code):
    """Get PE ratio"""
    try:
        df = ak.stock_a_lg_indicator(symbol=stock_code)
        if df is None or len(df) == 0:
            return None
        latest = df.iloc[-1]
        pe = latest.get('市盈率', None)
        return float(pe) if pe and pe != '-' else None
    except:
        return None

def check_dimension_1(sector_stocks_data, target_date):
    """维度1: 行业趋势 - 近20日行业等权指数涨幅 > 5%"""
    sector_returns = {}

    for sector, stocks_data in sector_stocks_data.items():
        returns_list = []
        for stock_code, df in stocks_data.items():
            if df is None or len(df) < SECTOR_PERIOD + 5:
                continue

            target_idx = df[df['日期'] <= target_date].index
            if len(target_idx) == 0:
                continue

            end_idx = target_idx[-1]
            if end_idx < SECTOR_PERIOD:
                continue

            start_idx = end_idx - SECTOR_PERIOD
            start_price = df.loc[start_idx, '收盘']
            end_price = df.loc[end_idx, '收盘']

            if start_price > 0:
                ret = (end_price - start_price) / start_price * 100
                returns_list.append(ret)

        if len(returns_list) >= 3:  # At least 3 stocks for sector index
            sector_return = np.mean(returns_list)  # Equal-weighted
            sector_returns[sector] = sector_return
            print(f"行业 {sector}: 等权涨幅 = {sector_return:.2f}%")

    # Filter sectors with return > 5%
    strong_sectors = {k: v for k, v in sector_returns.items() if v > 5}
    return strong_sectors, sector_returns

def check_all_dimensions(stock_code, stock_name, sector, sector_return, target_date):
    """Check all 5 dimensions for a stock"""
    df = get_stock_data(stock_code, days=120)
    if df is None or len(df) < 70:
        return None

    target_idx = df[df['日期'] <= target_date].index
    if len(target_idx) == 0:
        return None

    end_idx = target_idx[-1]
    if end_idx < 65:
        return None

    # Get data slice
    df_slice = df.loc[:end_idx].copy()

    # 维度2: 个股近20日涨幅 > 行业涨幅 × 1.3
    if len(df_slice) < STOCK_PERIOD + 1:
        return None

    stock_start_idx = len(df_slice) - STOCK_PERIOD - 1
    stock_start_price = df_slice.iloc[stock_start_idx]['收盘']
    stock_end_price = df_slice.iloc[-1]['收盘']
    stock_return = (stock_end_price - stock_start_price) / stock_start_price * 100

    if stock_return <= sector_return * 1.3:
        return None

    # 维度3: 技术指标
    # 3.1: 价格在20日和60日均线上方
    if len(df_slice) < MA_LONG:
        return None

    close_prices = df_slice['收盘'].values
    ma20 = calculate_ma(df_slice['收盘'], MA_SHORT).iloc[-1]
    ma60 = calculate_ma(df_slice['收盘'], MA_LONG).iloc[-1]
    current_price = close_prices[-1]

    if current_price <= ma20 or current_price <= ma60:
        return None

    # 3.2: MACD柱状图近5日持续为正且递增
    macd_hist = calculate_macd(df_slice['收盘'])
    last_5_macd = macd_hist.iloc[-5:].values

    if not all(last_5_macd > 0):
        return None

    is_increasing = all(last_5_macd[i] < last_5_macd[i+1] for i in range(4))
    if not is_increasing:
        return None

    # 3.3: RSI在50-70之间
    rsi = calculate_rsi(df_slice['收盘'])
    current_rsi = rsi.iloc[-1]

    if current_rsi < 50 or current_rsi > 70:
        return None

    # 维度4: 量能与K线质量
    # 4.1: 近10日中至少6日收盘价高于开盘价
    last_10 = df_slice.iloc[-10:]
    bullish_days = (last_10['收盘'] > last_10['开盘']).sum()

    if bullish_days < 6:
        return None

    # 4.2: 近10日成交量均值 > 60日成交量均值
    vol_10d = df_slice['成交量'].iloc[-10:].mean()
    vol_60d = df_slice['成交量'].iloc[-60:].mean()
    volume_ratio = vol_10d / vol_60d if vol_60d > 0 else 0

    if volume_ratio <= 1.0:
        return None

    # 维度5: PE基本面
    pe = get_pe_ratio(stock_code)
    if pe is None or pe <= 0 or pe >= 100:
        return None

    # All dimensions passed - calculate comprehensive score
    score = calculate_comprehensive_score(
        sector_return, stock_return, current_rsi,
        bullish_days, volume_ratio, pe, last_5_macd
    )

    return {
        '股票代码': stock_code,
        '所属行业': sector,
        '行业涨幅(%)': round(sector_return, 2),
        '个股涨幅(%)': round(stock_return, 2),
        'RSI': round(current_rsi, 1),
        '阳线天数': bullish_days,
        '量能比': round(volume_ratio, 2),
        'PE': round(pe, 1),
        '综合得分': round(score, 1)
    }

def calculate_comprehensive_score(sector_return, stock_return, rsi,
                                  bullish_days, volume_ratio, pe, macd_hist):
    """
    综合评分模型 (0-100分)

    权重分配:
    - 个股超额收益 (30%): 相对行业的超额表现
    - 技术指标强度 (25%): RSI位置 + MACD递增幅度
    - 量能质量 (20%): 阳线占比 + 量能放大
    - 行业趋势 (15%): 行业整体涨幅
    - 估值合理性 (10%): PE在合理区间的位置
    """

    # 1. 个股超额收益得分 (0-30分)
    excess_return = stock_return - sector_return
    excess_score = min(30, excess_return * 2)  # 超额15%得满分

    # 2. 技术指标强度 (0-25分)
    # RSI位置: 60最优，偏离扣分
    rsi_score = 15 - abs(rsi - 60) * 0.3
    rsi_score = max(0, min(15, rsi_score))

    # MACD递增幅度
    macd_growth = (macd_hist[-1] - macd_hist[0]) / (abs(macd_hist[0]) + 0.01)
    macd_score = min(10, macd_growth * 5)

    tech_score = rsi_score + macd_score

    # 3. 量能质量 (0-20分)
    # 阳线占比
    bullish_score = (bullish_days - 6) * 2  # 6天起步，10天满分8分

    # 量能放大
    volume_score = min(12, (volume_ratio - 1) * 20)  # 放大60%得满分

    momentum_score = bullish_score + volume_score

    # 4. 行业趋势 (0-15分)
    sector_score = min(15, (sector_return - 5) * 2)  # 超过5%部分计分

    # 5. 估值合理性 (0-10分)
    # PE在20-40最优，偏离扣分
    if 20 <= pe <= 40:
        pe_score = 10
    elif pe < 20:
        pe_score = 10 - (20 - pe) * 0.3
    else:  # pe > 40
        pe_score = 10 - (pe - 40) * 0.15
    pe_score = max(0, pe_score)

    total_score = excess_score + tech_score + momentum_score + sector_score + pe_score
    return total_score

def main():
    print("=" * 60)
    print("五维度综合评分超级选股系统")
    print("=" * 60)

    # Step 1: Get ChiNext stocks
    chinext_stocks = get_chinext_stocks()
    if chinext_stocks.empty:
        print("无法获取创业板股票列表")
        return

    # Step 2: Classify stocks by sector
    print("\n分类股票到目标行业...")
    sector_stocks = {sector: [] for sector in SECTOR_KEYWORDS.keys()}

    for _, row in chinext_stocks.iterrows():
        sector = classify_sector(row['name'])
        if sector:
            sector_stocks[sector].append((row['code'], row['name']))

    for sector, stocks in sector_stocks.items():
        print(f"{sector}: {len(stocks)}只股票")

    # Step 3: Get historical data for sector stocks
    print("\n获取股票历史数据...")
    sector_stocks_data = {}

    for sector, stocks in sector_stocks.items():
        if len(stocks) == 0:
            continue

        print(f"\n处理 {sector} 行业...")
        sector_data = {}

        for stock_code, stock_name in stocks[:50]:  # Limit for performance
            df = get_stock_data(stock_code)
            if df is not None and len(df) > 0:
                sector_data[stock_code] = df
                print(f"  获取 {stock_code} 数据成功")

        sector_stocks_data[sector] = sector_data
        print(f"  成功获取 {len(sector_data)} 只股票数据")

    # Step 4: Check Dimension 1 - Sector trend
    print("\n" + "=" * 60)
    print("维度1: 行业趋势筛选")
    print("=" * 60)
    strong_sectors, all_sector_returns = check_dimension_1(sector_stocks_data, TARGET_DATE)

    if not strong_sectors:
        print("没有符合条件的强势行业（近20日涨幅>5%）")
        with open('/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_20_ultimate_multi_condition/independent/claudecode/ultimate_filter.txt', 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        return

    print(f"\n强势行业: {list(strong_sectors.keys())}")

    # Step 5: Check all dimensions for stocks in strong sectors
    print("\n" + "=" * 60)
    print("维度2-5: 个股全维度筛选")
    print("=" * 60)

    qualified_stocks = []

    for sector in strong_sectors.keys():
        sector_return = strong_sectors[sector]
        stocks_data = sector_stocks_data[sector]

        print(f"\n筛选 {sector} 行业股票...")

        for stock_code, df in stocks_data.items():
            stock_name = chinext_stocks[chinext_stocks['code'] == stock_code]['name'].values
            stock_name = stock_name[0] if len(stock_name) > 0 else stock_code

            result = check_all_dimensions(stock_code, stock_name, sector,
                                         sector_return, TARGET_DATE)

            if result:
                qualified_stocks.append(result)
                print(f"  ✓ {stock_code} {stock_name} - 得分: {result['综合得分']}")

    # Step 6: Sort by comprehensive score and output
    print("\n" + "=" * 60)
    print("输出结果")
    print("=" * 60)

    if not qualified_stocks:
        print("没有同时满足所有五个维度条件的股票")
        with open('/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_20_ultimate_multi_condition/independent/claudecode/ultimate_filter.txt', 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        return

    # Sort by score descending
    qualified_stocks.sort(key=lambda x: x['综合得分'], reverse=True)

    # Write to file
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_20_ultimate_multi_condition/independent/claudecode/ultimate_filter.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        # Header
        f.write("股票代码,所属行业,行业涨幅(%),个股涨幅(%),RSI,阳线天数,量能比,PE,综合得分\n")

        # Data rows
        for stock in qualified_stocks:
            line = f"{stock['股票代码']},{stock['所属行业']},{stock['行业涨幅(%)']},{stock['个股涨幅(%)']},{stock['RSI']},{stock['阳线天数']},{stock['量能比']},{stock['PE']},{stock['综合得分']}\n"
            f.write(line)

    print(f"\n共找到 {len(qualified_stocks)} 只符合条件的股票")
    print(f"结果已写入: {output_path}")

    # Display top 10
    print("\n前10名股票:")
    print("-" * 100)
    print(f"{'代码':<10} {'行业':<10} {'行业涨幅':<10} {'个股涨幅':<10} {'RSI':<8} {'阳线':<6} {'量能比':<8} {'PE':<8} {'得分':<8}")
    print("-" * 100)

    for stock in qualified_stocks[:10]:
        print(f"{stock['股票代码']:<10} {stock['所属行业']:<10} {stock['行业涨幅(%)']:<10} {stock['个股涨幅(%)']:<10} {stock['RSI']:<8} {stock['阳线天数']:<6} {stock['量能比']:<8} {stock['PE']:<8} {stock['综合得分']:<8}")

if __name__ == "__main__":
    main()
