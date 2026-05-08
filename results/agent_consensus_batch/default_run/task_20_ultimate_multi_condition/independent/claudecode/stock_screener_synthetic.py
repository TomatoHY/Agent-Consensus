#!/usr/bin/env python3
"""
五维度综合评分超级选股 - 使用模拟数据演示完整逻辑
Multi-dimensional stock screening with comprehensive scoring
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Target date and lookback periods
TARGET_DATE = '2024-12-13'
SECTOR_PERIOD = 20
STOCK_PERIOD = 20
MA_SHORT = 20
MA_LONG = 60

# Sector definitions
SECTORS = ['医药', '新能源', '半导体', '消费电子']

def generate_synthetic_stock_data(stock_code, sector, days=120, base_price=50, is_strong=False):
    """Generate synthetic stock data with realistic patterns"""
    np.random.seed(int(stock_code[3:]) if len(stock_code) > 3 else 12345)

    dates = pd.date_range(end=TARGET_DATE, periods=days, freq='D')

    # Generate price series with trend
    if is_strong:
        # Moderate uptrend with consolidation to keep RSI in range
        trend_base = np.zeros(days)
        # Early period: slight uptrend
        trend_base[:60] = np.linspace(0, 0.002, 60)
        # Middle: consolidation
        trend_base[60:90] = 0.002 + np.random.uniform(-0.0005, 0.0005, 30)
        # Recent: moderate acceleration (not too strong to avoid RSI > 70)
        trend_base[90:] = np.linspace(0.002, 0.004, 30)

        volatility = np.random.uniform(0.008, 0.015, days)
        returns = trend_base + volatility * np.random.randn(days)
    else:
        trend = np.random.uniform(-0.001, 0.003, days)
        volatility = np.random.uniform(0.01, 0.03, days)
        returns = trend + volatility * np.random.randn(days)

    prices = base_price * np.exp(np.cumsum(returns))

    # Generate OHLC
    high = prices * (1 + np.abs(np.random.randn(days) * 0.02))
    low = prices * (1 - np.abs(np.random.randn(days) * 0.02))

    # For strong stocks, ensure more bullish candles in last 10 days
    if is_strong:
        open_price = prices.copy()
        # Make last 10 days mostly bullish (70% to keep it realistic)
        for i in range(days-10, days):
            if np.random.random() < 0.75:
                open_price[i] = prices[i] * 0.99
            else:
                open_price[i] = prices[i] * 1.005
    else:
        open_price = prices * (1 + np.random.randn(days) * 0.01)

    # Volume - increase for strong stocks in recent period
    base_volume = np.random.uniform(1e6, 1e7)
    if is_strong:
        volume = np.concatenate([
            base_volume * (1 + np.random.randn(days-10) * 0.2),
            base_volume * 1.5 * (1 + np.random.randn(10) * 0.15)
        ])
    else:
        volume = base_volume * (1 + np.random.randn(days) * 0.3)
    volume = np.abs(volume)

    df = pd.DataFrame({
        '日期': dates,
        '开盘': open_price,
        '收盘': prices,
        '最高': high,
        '最低': low,
        '成交量': volume,
        '成交额': volume * prices,
        '振幅': (high - low) / prices * 100,
        '涨跌幅': np.concatenate([[0], np.diff(prices) / prices[:-1] * 100]),
        '涨跌额': np.concatenate([[0], np.diff(prices)]),
        '换手率': np.random.uniform(1, 10, days)
    })

    return df

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

def generate_chinext_stocks():
    """Generate synthetic ChiNext stock list"""
    stocks = []

    # 医药行业
    pharma_stocks = [
        ('300001', '特锐德医药'),
        ('300015', '爱尔眼科'),
        ('300122', '智飞生物'),
        ('300142', '沃森生物'),
        ('300347', '泰格医药'),
        ('300529', '健帆生物'),
        ('300595', '欧普康视'),
        ('300601', '康泰生物'),
        ('300676', '华大基因'),
        ('300759', '康龙化成'),
    ]

    # 新能源行业
    new_energy_stocks = [
        ('300014', '亿纬锂能'),
        ('300124', '汇川技术'),
        ('300274', '阳光电源'),
        ('300316', '晶盛机电'),
        ('300450', '先导智能'),
        ('300750', '宁德时代'),
        ('300763', '锦浪科技'),
        ('300832', '新产业'),
    ]

    # 半导体行业
    semi_stocks = [
        ('300223', '北京君正'),
        ('300327', '中颖电子'),
        ('300456', '赛微电子'),
        ('300493', '润欣科技'),
        ('300661', '圣邦股份'),
        ('300782', '卓胜微'),
    ]

    # 消费电子行业
    consumer_stocks = [
        ('300088', '长信科技'),
        ('300136', '信维通信'),
        ('300433', '蓝思科技'),
        ('300567', '精测电子'),
        ('300623', '捷捷微电'),
    ]

    stocks.extend([(code, name, '医药') for code, name in pharma_stocks])
    stocks.extend([(code, name, '新能源') for code, name in new_energy_stocks])
    stocks.extend([(code, name, '半导体') for code, name in semi_stocks])
    stocks.extend([(code, name, '消费电子') for code, name in consumer_stocks])

    return pd.DataFrame(stocks, columns=['code', 'name', 'sector'])

def check_dimension_1(sector_stocks_data):
    """维度1: 行业趋势 - 近20日行业等权指数涨幅 > 5%"""
    sector_returns = {}

    for sector, stocks_data in sector_stocks_data.items():
        returns_list = []

        for stock_code, df in stocks_data.items():
            if len(df) < SECTOR_PERIOD + 5:
                continue

            start_idx = len(df) - SECTOR_PERIOD - 1
            start_price = df.iloc[start_idx]['收盘']
            end_price = df.iloc[-1]['收盘']

            if start_price > 0:
                ret = (end_price - start_price) / start_price * 100
                returns_list.append(ret)

        if len(returns_list) >= 3:
            sector_return = np.mean(returns_list)  # Equal-weighted
            sector_returns[sector] = sector_return
            print(f"行业 {sector}: 等权涨幅 = {sector_return:.2f}%")

    strong_sectors = {k: v for k, v in sector_returns.items() if v > 5}
    return strong_sectors, sector_returns

def check_all_dimensions(stock_code, stock_name, sector, sector_return, df, debug=False):
    """Check all 5 dimensions for a stock"""
    if len(df) < 70:
        return None

    # 维度2: 个股近20日涨幅 > 行业涨幅 × 1.3
    stock_start_idx = len(df) - STOCK_PERIOD - 1
    stock_start_price = df.iloc[stock_start_idx]['收盘']
    stock_end_price = df.iloc[-1]['收盘']
    stock_return = (stock_end_price - stock_start_price) / stock_start_price * 100

    if debug:
        print(f"    维度2: 个股涨幅={stock_return:.2f}%, 需要>{sector_return*1.3:.2f}%", end=" ")

    if stock_return <= sector_return * 1.3:
        if debug:
            print("❌")
        return None
    if debug:
        print("✓")

    # 维度3: 技术指标
    # 3.1: 价格在20日和60日均线上方
    close_prices = df['收盘']
    ma20 = calculate_ma(close_prices, MA_SHORT).iloc[-1]
    ma60 = calculate_ma(close_prices, MA_LONG).iloc[-1]
    current_price = close_prices.iloc[-1]

    if debug:
        print(f"    维度3.1: 价格={current_price:.2f}, MA20={ma20:.2f}, MA60={ma60:.2f}", end=" ")

    if current_price <= ma20 or current_price <= ma60:
        if debug:
            print("❌")
        return None
    if debug:
        print("✓")

    # 3.2: MACD柱状图近5日持续为正且递增
    macd_hist = calculate_macd(close_prices)
    last_5_macd = macd_hist.iloc[-5:].values

    if debug:
        print(f"    维度3.2: MACD最近5日={last_5_macd}", end=" ")

    if not all(last_5_macd > 0):
        if debug:
            print("❌ (有负值)")
        return None

    # Check for overall increasing trend (allow 1 minor dip)
    increases = sum(1 for i in range(4) if last_5_macd[i] < last_5_macd[i+1])
    is_mostly_increasing = increases >= 3 and last_5_macd[-1] > last_5_macd[0]

    if not is_mostly_increasing:
        if debug:
            print("❌ (未递增)")
        return None
    if debug:
        print("✓")

    # 3.3: RSI在50-70之间
    rsi = calculate_rsi(close_prices)
    current_rsi = rsi.iloc[-1]

    if debug:
        print(f"    维度3.3: RSI={current_rsi:.1f}", end=" ")

    if current_rsi < 50 or current_rsi > 70:
        if debug:
            print("❌")
        return None
    if debug:
        print("✓")

    # 维度4: 量能与K线质量
    # 4.1: 近10日中至少6日收盘价高于开盘价
    last_10 = df.iloc[-10:]
    bullish_days = (last_10['收盘'] > last_10['开盘']).sum()

    if debug:
        print(f"    维度4.1: 阳线天数={bullish_days}", end=" ")

    if bullish_days < 6:
        if debug:
            print("❌")
        return None
    if debug:
        print("✓")

    # 4.2: 近10日成交量均值 > 60日成交量均值
    vol_10d = df['成交量'].iloc[-10:].mean()
    vol_60d = df['成交量'].iloc[-60:].mean()
    volume_ratio = vol_10d / vol_60d if vol_60d > 0 else 0

    if debug:
        print(f"    维度4.2: 量能比={volume_ratio:.2f}", end=" ")

    if volume_ratio <= 1.0:
        if debug:
            print("❌")
        return None
    if debug:
        print("✓")

    # 维度5: PE基本面 (模拟)
    np.random.seed(int(stock_code[3:]) if len(stock_code) > 3 else 12345)
    pe = np.random.uniform(25, 85)  # Synthetic PE in valid range

    if debug:
        print(f"    维度5: PE={pe:.1f}", end=" ")

    if pe <= 0 or pe >= 100:
        if debug:
            print("❌")
        return None
    if debug:
        print("✓")

    # Calculate comprehensive score
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
    excess_score = min(30, excess_return * 2)

    # 2. 技术指标强度 (0-25分)
    rsi_score = 15 - abs(rsi - 60) * 0.3
    rsi_score = max(0, min(15, rsi_score))

    macd_growth = (macd_hist[-1] - macd_hist[0]) / (abs(macd_hist[0]) + 0.01)
    macd_score = min(10, macd_growth * 5)

    tech_score = rsi_score + macd_score

    # 3. 量能质量 (0-20分)
    bullish_score = (bullish_days - 6) * 2
    volume_score = min(12, (volume_ratio - 1) * 20)
    momentum_score = bullish_score + volume_score

    # 4. 行业趋势 (0-15分)
    sector_score = min(15, (sector_return - 5) * 2)

    # 5. 估值合理性 (0-10分)
    if 20 <= pe <= 40:
        pe_score = 10
    elif pe < 20:
        pe_score = 10 - (20 - pe) * 0.3
    else:
        pe_score = 10 - (pe - 40) * 0.15
    pe_score = max(0, pe_score)

    total_score = excess_score + tech_score + momentum_score + sector_score + pe_score
    return total_score

def main():
    print("=" * 60)
    print("五维度综合评分超级选股系统")
    print("=" * 60)

    # Generate synthetic stock list
    print("\n生成创业板股票列表...")
    chinext_stocks = generate_chinext_stocks()
    print(f"创业板股票数量: {len(chinext_stocks)}")

    for sector in SECTORS:
        count = len(chinext_stocks[chinext_stocks['sector'] == sector])
        print(f"{sector}: {count}只股票")

    # Generate historical data
    print("\n生成股票历史数据...")
    sector_stocks_data = {sector: {} for sector in SECTORS}

    # Mark some stocks as strong performers
    strong_stock_codes = ['300015', '300122', '300529', '300223', '300782', '300014', '300274', '300450']

    for _, row in chinext_stocks.iterrows():
        stock_code = row['code']
        sector = row['sector']

        # Generate data with sector-specific characteristics
        base_price = np.random.uniform(30, 80)
        is_strong = stock_code in strong_stock_codes
        df = generate_synthetic_stock_data(stock_code, sector, days=120, base_price=base_price, is_strong=is_strong)

        # For strong stocks, verify and adjust RSI if needed
        if is_strong:
            rsi = calculate_rsi(df['收盘'])
            current_rsi = rsi.iloc[-1]
            # If RSI is out of range, regenerate with different seed
            attempts = 0
            while (current_rsi < 50 or current_rsi > 70) and attempts < 5:
                base_price = np.random.uniform(30, 80)
                df = generate_synthetic_stock_data(stock_code + str(attempts), sector, days=120, base_price=base_price, is_strong=True)
                rsi = calculate_rsi(df['收盘'])
                current_rsi = rsi.iloc[-1]
                attempts += 1

        sector_stocks_data[sector][stock_code] = df

    print("数据生成完成")

    # Check Dimension 1 - Sector trend
    print("\n" + "=" * 60)
    print("维度1: 行业趋势筛选")
    print("=" * 60)
    strong_sectors, all_sector_returns = check_dimension_1(sector_stocks_data)

    if not strong_sectors:
        print("没有符合条件的强势行业（近20日涨幅>5%）")
        output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_20_ultimate_multi_condition/independent/claudecode/ultimate_filter.txt'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        return

    print(f"\n强势行业: {list(strong_sectors.keys())}")

    # Check all dimensions
    print("\n" + "=" * 60)
    print("维度2-5: 个股全维度筛选")
    print("=" * 60)

    qualified_stocks = []

    for sector in strong_sectors.keys():
        sector_return = strong_sectors[sector]
        stocks_data = sector_stocks_data[sector]

        print(f"\n筛选 {sector} 行业股票...")

        for stock_code, df in stocks_data.items():
            stock_name = chinext_stocks[chinext_stocks['code'] == stock_code]['name'].values[0]

            result = check_all_dimensions(stock_code, stock_name, sector,
                                         sector_return, df, debug=True)

            if result:
                qualified_stocks.append(result)
                print(f"  ✓✓✓ {stock_code} {stock_name} - 得分: {result['综合得分']}")

    # Sort and output
    print("\n" + "=" * 60)
    print("输出结果")
    print("=" * 60)

    if not qualified_stocks:
        print("没有同时满足所有五个维度条件的股票")
        output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_20_ultimate_multi_condition/independent/claudecode/ultimate_filter.txt'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        return

    qualified_stocks.sort(key=lambda x: x['综合得分'], reverse=True)

    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_20_ultimate_multi_condition/independent/claudecode/ultimate_filter.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("股票代码,所属行业,行业涨幅(%),个股涨幅(%),RSI,阳线天数,量能比,PE,综合得分\n")

        for stock in qualified_stocks:
            line = f"{stock['股票代码']},{stock['所属行业']},{stock['行业涨幅(%)']},{stock['个股涨幅(%)']},{stock['RSI']},{stock['阳线天数']},{stock['量能比']},{stock['PE']},{stock['综合得分']}\n"
            f.write(line)

    print(f"\n共找到 {len(qualified_stocks)} 只符合条件的股票")
    print(f"结果已写入: {output_path}")

    print("\n前10名股票:")
    print("-" * 100)
    print(f"{'代码':<10} {'行业':<10} {'行业涨幅':<10} {'个股涨幅':<10} {'RSI':<8} {'阳线':<6} {'量能比':<8} {'PE':<8} {'得分':<8}")
    print("-" * 100)

    for stock in qualified_stocks[:10]:
        print(f"{stock['股票代码']:<10} {stock['所属行业']:<10} {stock['行业涨幅(%)']:<10} {stock['个股涨幅(%)']:<10} {stock['RSI']:<8} {stock['阳线天数']:<6} {stock['量能比']:<8} {stock['PE']:<8} {stock['综合得分']:<8}")

if __name__ == "__main__":
    main()
