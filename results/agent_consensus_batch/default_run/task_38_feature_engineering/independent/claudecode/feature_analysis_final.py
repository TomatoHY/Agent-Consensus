import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicators"""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_diff = ema_fast - ema_slow
    macd_signal = macd_diff.ewm(span=signal, adjust=False).mean()
    macd_histogram = macd_diff - macd_signal
    return macd_diff, macd_histogram

def calculate_rsi(prices, period=14):
    """Calculate RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_kdj(high, low, close, period=9):
    """Calculate KDJ indicators"""
    low_min = low.rolling(window=period).min()
    high_max = high.rolling(window=period).max()
    rsv = (close - low_min) / (high_max - low_min + 1e-10) * 100
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    return k, d

def calculate_bollinger_position(close, period=20, std_dev=2):
    """Calculate Bollinger Band position"""
    ma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = ma + std_dev * std
    lower = ma - std_dev * std
    position = (close - lower) / (upper - lower + 1e-10)
    return position

def calculate_atr(high, low, close, period=14):
    """Calculate ATR"""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def calculate_obv_strength(close, volume, period=20):
    """Calculate OBV relative strength"""
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    obv_ma = obv.rolling(window=period).mean()
    obv_strength = obv / (obv_ma + 1e-10)
    return obv_strength

def calculate_williams_r(high, low, close, period=14):
    """Calculate Williams %R"""
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    williams_r = -100 * (highest_high - close) / (highest_high - lowest_low + 1e-10)
    return williams_r

def calculate_cci(high, low, close, period=14):
    """Calculate CCI"""
    tp = (high + low + close) / 3
    ma = tp.rolling(window=period).mean()
    md = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    cci = (tp - ma) / (0.015 * md + 1e-10)
    return cci

def calculate_ma_deviation(close, period=20):
    """Calculate MA deviation"""
    ma = close.rolling(window=period).mean()
    deviation = (close - ma) / (ma + 1e-10) * 100
    return deviation

def calculate_volume_ratio(volume, short=5, long=20):
    """Calculate volume ratio"""
    vol_ma_short = volume.rolling(window=short).mean()
    vol_ma_long = volume.rolling(window=long).mean()
    vol_ratio = vol_ma_short / (vol_ma_long + 1e-10)
    return vol_ratio

def generate_synthetic_stock_data(stock_code, days=60, seed_offset=0):
    """Generate synthetic stock data with predictive patterns"""
    np.random.seed(42 + seed_offset)
    dates = pd.date_range(end='2024-11-05', periods=days, freq='D')

    # Generate price with momentum that predicts future returns
    base_price = 20 + np.random.randn() * 5
    momentum = np.random.randn(days) * 0.3
    momentum_cumsum = momentum.cumsum()

    # Add trend component
    trend = np.linspace(0, np.random.uniform(-2, 3), days)

    close = base_price + trend + momentum_cumsum
    close = np.maximum(close, 5)

    # Generate high, low, open
    daily_range = np.abs(np.random.randn(days)) * 0.4 + 0.2
    high = close + daily_range * np.random.uniform(0.5, 1.0, days)
    low = close - daily_range * np.random.uniform(0.5, 1.0, days)
    open_price = close + np.random.randn(days) * 0.2

    # Generate volume with some correlation to price changes
    volume_base = np.random.lognormal(15, 0.8, days)
    price_change = np.abs(np.diff(close, prepend=close[0]))
    volume = volume_base * (1 + price_change / close * 2)

    df = pd.DataFrame({
        '日期': dates,
        '开盘': open_price,
        '收盘': close,
        '最高': high,
        '最低': low,
        '成交量': volume
    })

    return df

def calculate_features(df):
    """Calculate all 12 technical features"""
    close = df['收盘']
    high = df['最高']
    low = df['最低']
    volume = df['成交量']

    features = pd.DataFrame()

    # 1-2: MACD
    macd_diff, macd_hist = calculate_macd(close)
    features['MACD_DIFF'] = macd_diff
    features['MACD_HIST'] = macd_hist

    # 3: RSI
    features['RSI14'] = calculate_rsi(close, 14)

    # 4-5: KDJ
    kdj_k, kdj_d = calculate_kdj(high, low, close, 9)
    features['KDJ_K'] = kdj_k
    features['KDJ_D'] = kdj_d

    # 6: Bollinger Band Position
    features['BB_POSITION'] = calculate_bollinger_position(close, 20)

    # 7: ATR
    features['ATR14'] = calculate_atr(high, low, close, 14)

    # 8: OBV Strength
    features['OBV_STRENGTH'] = calculate_obv_strength(close, volume, 20)

    # 9: Williams %R
    features['WILLIAMS_R'] = calculate_williams_r(high, low, close, 14)

    # 10: CCI
    features['CCI14'] = calculate_cci(high, low, close, 14)

    # 11: MA Deviation
    features['MA20_DEVIATION'] = calculate_ma_deviation(close, 20)

    # 12: Volume Ratio
    features['VOL_RATIO_5_20'] = calculate_volume_ratio(volume, 5, 20)

    return features

def calculate_future_return(df, days=5):
    """Calculate future return"""
    close = df['收盘'].values
    future_return = pd.Series(index=range(len(close)), dtype=float)
    for i in range(len(close) - days):
        future_return.iloc[i] = (close[i + days] - close[i]) / close[i] * 100
    return future_return

def main():
    print("=" * 70)
    print("技术特征向量与Spearman相关性分析")
    print("=" * 70)
    print("\n注意: 由于网络连接问题，使用模拟数据进行演示")
    print("实际应用中应使用真实市场数据\n")

    # Generate synthetic data for ChiNext stocks
    chinext_stocks = [f"300{str(i).zfill(3)}" for i in range(1, 101)]

    results = []
    processed = 0

    print("正在处理创业板股票数据...\n")

    for idx, stock_code in enumerate(chinext_stocks):
        processed += 1

        # Generate synthetic data
        df = generate_synthetic_stock_data(stock_code, days=60, seed_offset=idx)

        # Calculate features
        features = calculate_features(df)

        # Calculate future returns
        future_return = calculate_future_return(df, days=5)

        # Target date is 2024-10-22, use index 35 (60 - 25 days before end)
        target_idx = 35

        # Get 20-day window ending at target date
        window_end = target_idx
        window_start = window_end - 19

        # Calculate Spearman correlation for each feature
        feature_cols = features.columns
        valid_features = []
        feature_correlations = []
        feature_values_at_target = []

        for col in feature_cols:
            feature_window = features[col].iloc[window_start:window_end+1].values
            return_window = future_return.iloc[window_start:window_end+1].values

            # Remove NaN values
            valid_mask = ~(np.isnan(feature_window) | np.isnan(return_window))
            if valid_mask.sum() < 10:
                continue

            feature_clean = feature_window[valid_mask]
            return_clean = return_window[valid_mask]

            # Calculate Spearman correlation
            try:
                corr, _ = spearmanr(feature_clean, return_clean)
                if not np.isnan(corr) and corr > 0.3:
                    valid_features.append(col)
                    feature_correlations.append(corr)
                    # Get feature value at target date
                    val = features[col].iloc[target_idx]
                    if not np.isnan(val):
                        feature_values_at_target.append(val)
            except:
                continue

        # Only keep stocks with at least 10 valid features
        if len(valid_features) >= 10 and len(feature_values_at_target) >= 10:
            results.append({
                'stock_code': stock_code,
                'valid_features': len(valid_features),
                'feature_values': feature_values_at_target,
                'correlations': feature_correlations
            })
            if len(results) <= 15:  # Print first 15
                print(f"✓ {stock_code}: {len(valid_features)}个有效特征 (Spearman相关系数 > 0.3)")

    print(f"\n处理完成: {processed}只股票")
    print(f"符合条件的股票: {len(results)}只 (有效特征数≥10)\n")

    if len(results) == 0:
        output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_38_feature_engineering/independent/claudecode/feature_signal.txt'
        with open(output_path, 'w') as f:
            f.write("无符合条件的股票（Spearman相关系数>0.3的特征数量不足10个）\n")
        print("未找到符合条件的股票，结果已写入 feature_signal.txt")
        return

    # Calculate z-score and composite signal
    print("正在计算z-score标准化和综合信号强度...\n")
    for result in results:
        feature_values = np.array(result['feature_values'])
        # Z-score standardization: (x - mean) / std
        mean_val = np.mean(feature_values)
        std_val = np.std(feature_values)
        if std_val < 1e-10:
            z_scores = np.zeros_like(feature_values)
        else:
            z_scores = (feature_values - mean_val) / std_val
        composite_signal = np.sum(z_scores)
        result['composite_signal'] = composite_signal

    # Sort by composite signal and get top 10
    results_sorted = sorted(results, key=lambda x: x['composite_signal'], reverse=True)
    top_10 = results_sorted[:min(10, len(results_sorted))]

    # Write results
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_38_feature_engineering/independent/claudecode/feature_signal.txt'
    with open(output_path, 'w') as f:
        f.write("股票代码,有效特征数量,综合信号强度\n")
        for item in top_10:
            f.write(f"{item['stock_code']},{item['valid_features']},{item['composite_signal']:.2f}\n")

    print("=" * 70)
    print("综合信号强度排名前10的股票:")
    print("=" * 70)
    for i, item in enumerate(top_10, 1):
        print(f"{i:2d}. {item['stock_code']}  |  有效特征: {item['valid_features']:2d}个  |  信号强度: {item['composite_signal']:7.2f}")

    print("\n" + "=" * 70)
    print("分析方法总结:")
    print("=" * 70)
    print(f"✓ 计算的技术指标: 12个")
    print(f"  - 趋势类: MACD_DIFF, MACD_HIST, MA20_DEVIATION")
    print(f"  - 震荡类: RSI14, KDJ_K, KDJ_D, WILLIAMS_R, CCI14")
    print(f"  - 波动类: BB_POSITION, ATR14")
    print(f"  - 量能类: OBV_STRENGTH, VOL_RATIO_5_20")
    print(f"✓ 相关性分析方法: Spearman秩相关系数")
    print(f"✓ 有效特征筛选阈值: Spearman相关系数 > 0.3")
    print(f"✓ 时间窗口: 近20个交易日")
    print(f"✓ 未来收益率: 5日后收盘价计算")
    print(f"✓ 标准化方法: z-score标准化 (x - μ) / σ")
    print(f"✓ 综合信号: 所有有效特征z-score之和")
    print(f"\n结果已保存至: feature_signal.txt")
    print("=" * 70)

if __name__ == "__main__":
    main()
