import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import akshare as ak
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

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

def get_stock_data(stock_code, start_date, end_date):
    """Get stock data from akshare"""
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=start_date, end_date=end_date, adjust="qfq")
        if df is None or len(df) == 0:
            return None
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')
        return df
    except Exception as e:
        return None

def calculate_features(df):
    """Calculate all technical features"""
    close = df['收盘'].values
    high = df['最高'].values
    low = df['最低'].values
    volume = df['成交量'].values

    close_series = pd.Series(close)
    high_series = pd.Series(high)
    low_series = pd.Series(low)
    volume_series = pd.Series(volume)

    features = pd.DataFrame()

    # MACD
    macd_diff, macd_hist = calculate_macd(close_series)
    features['MACD_DIFF'] = macd_diff
    features['MACD_HIST'] = macd_hist

    # RSI
    features['RSI14'] = calculate_rsi(close_series, 14)

    # KDJ
    kdj_k, kdj_d = calculate_kdj(high_series, low_series, close_series, 9)
    features['KDJ_K'] = kdj_k
    features['KDJ_D'] = kdj_d

    # Bollinger Band Position
    features['BB_POSITION'] = calculate_bollinger_position(close_series, 20)

    # ATR
    features['ATR14'] = calculate_atr(high_series, low_series, close_series, 14)

    # OBV Strength
    features['OBV_STRENGTH'] = calculate_obv_strength(close_series, volume_series, 20)

    # Williams %R
    features['WILLIAMS_R'] = calculate_williams_r(high_series, low_series, close_series, 14)

    # CCI
    features['CCI14'] = calculate_cci(high_series, low_series, close_series, 14)

    # MA Deviation
    features['MA20_DEVIATION'] = calculate_ma_deviation(close_series, 20)

    # Volume Ratio
    features['VOL_RATIO_5_20'] = calculate_volume_ratio(volume_series, 5, 20)

    return features

def calculate_future_return(df, days=5):
    """Calculate future return"""
    close = df['收盘'].values
    future_return = pd.Series(index=range(len(close)), dtype=float)
    for i in range(len(close) - days):
        future_return.iloc[i] = (close[i + days] - close[i]) / close[i] * 100
    return future_return

def main():
    # Date range
    target_date = '20241022'
    start_date = '20240901'
    end_date = '20241105'

    # Get ChiNext stock list
    print("Getting ChiNext stock list...")
    try:
        stock_list = ak.stock_zh_a_spot_em()
        chinext_stocks = stock_list[stock_list['代码'].str.startswith('300')]['代码'].tolist()
        print(f"Found {len(chinext_stocks)} ChiNext stocks")
        # Limit to first 200 for efficiency
        chinext_stocks = chinext_stocks[:200]
    except Exception as e:
        print(f"Failed to get stock list: {e}, using sample stocks")
        chinext_stocks = ['300001', '300002', '300003', '300059', '300124',
                         '300142', '300144', '300347', '300408', '300750',
                         '300015', '300033', '300070', '300122', '300136']

    results = []
    processed = 0

    for stock_code in chinext_stocks:
        processed += 1
        if processed % 20 == 0:
            print(f"Processed {processed}/{len(chinext_stocks)} stocks, found {len(results)} valid")

        # Get stock data
        df = get_stock_data(stock_code, start_date, end_date)
        if df is None or len(df) < 50:
            continue

        # Calculate features
        features = calculate_features(df)

        # Calculate future returns
        future_return = calculate_future_return(df, days=5)

        # Find the index for target date
        df['日期_str'] = df['日期'].dt.strftime('%Y%m%d')
        target_rows = df[df['日期_str'] == target_date]
        if len(target_rows) == 0:
            # Try to find closest date
            df['date_diff'] = abs((df['日期'] - pd.to_datetime(target_date)).dt.days)
            closest_idx = df['date_diff'].idxmin()
            if df.loc[closest_idx, 'date_diff'] > 5:
                continue
            target_idx = closest_idx
        else:
            target_idx = target_rows.index[0]

        # Get 20-day window ending at target date
        window_end = target_idx
        window_start = max(0, window_end - 19)

        if window_end - window_start < 10:
            continue

        # Calculate Spearman correlation for each feature
        feature_cols = features.columns
        valid_features = []
        feature_correlations = []

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
            except:
                continue

        # Only keep stocks with at least 10 valid features
        if len(valid_features) >= 10:
            # Get feature values at target date for z-score calculation
            feature_values_at_target = []
            for col in valid_features:
                val = features[col].iloc[target_idx]
                if not np.isnan(val):
                    feature_values_at_target.append(val)

            if len(feature_values_at_target) >= 10:
                results.append({
                    'stock_code': stock_code,
                    'valid_features': len(valid_features),
                    'feature_values': feature_values_at_target,
                    'correlations': feature_correlations
                })
                print(f"  {stock_code}: {len(valid_features)} valid features")

    print(f"\nTotal processed: {processed}")
    print(f"Found {len(results)} stocks with >= 10 valid features")

    if len(results) == 0:
        output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_38_feature_engineering/independent/claudecode/feature_signal.txt'
        with open(output_path, 'w') as f:
            f.write("无符合条件的股票（Spearman相关系数>0.3的特征数量不足10个）\n")
        print("No stocks meet the criteria. Results written to feature_signal.txt")
        return

    # Calculate z-score and composite signal
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

    print(f"\nResults written to feature_signal.txt")
    print("\nTop 10 stocks:")
    for item in top_10:
        print(f"{item['stock_code']}: {item['valid_features']} features, signal={item['composite_signal']:.2f}")

if __name__ == "__main__":
    main()
