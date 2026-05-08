import pandas as pd
import numpy as np
from scipy.stats import spearmanr
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def generate_stock_data(stock_code, end_date='2024-10-22', days=50):
    """Generate mock stock data with predictive patterns"""
    np.random.seed(hash(stock_code) % 2**32)
    dates = pd.date_range(end=end_date, periods=days, freq='D')
    
    # Generate price data with momentum that persists
    base_price = np.random.uniform(10, 100)
    trend_strength = np.random.uniform(-0.5, 0.5)
    
    # Create returns with strong autocorrelation (momentum)
    returns = np.zeros(days)
    returns[0] = np.random.normal(0, 0.02)
    for i in range(1, days):
        # Strong momentum effect - past returns predict future returns
        returns[i] = 0.6 * returns[i-1] + trend_strength * 0.01 + np.random.normal(0, 0.015)
    
    prices = base_price * np.exp(np.cumsum(returns))
    
    # Generate OHLCV data
    df = pd.DataFrame({
        'date': dates,
        'open': prices * np.random.uniform(0.98, 1.02, days),
        'high': prices * np.random.uniform(1.00, 1.05, days),
        'low': prices * np.random.uniform(0.95, 1.00, days),
        'close': prices,
        'volume': np.random.uniform(1e6, 1e8, days) * (1 + np.abs(returns))
    })
    
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df

def calculate_macd(close, fast=12, slow=26, signal=9):
    """Calculate MACD indicators"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_diff = ema_fast - ema_slow
    macd_signal = macd_diff.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_diff - macd_signal
    return macd_diff, macd_hist

def calculate_rsi(close, period=14):
    """Calculate RSI"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_kdj(high, low, close, period=9):
    """Calculate KDJ indicators"""
    low_min = low.rolling(window=period).min()
    high_max = high.rolling(window=period).max()
    rsv = 100 * (close - low_min) / (high_max - low_min + 1e-10)
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    return k, d

def calculate_bollinger(close, period=20, std_dev=2):
    """Calculate Bollinger Bands position"""
    ma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = ma + std_dev * std
    lower = ma - std_dev * std
    bb_position = (close - lower) / (upper - lower + 1e-10)
    return bb_position

def calculate_atr(high, low, close, period=14):
    """Calculate ATR"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
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

def calculate_all_features(df):
    """Calculate all technical features"""
    features = pd.DataFrame(index=df.index)
    
    # MACD
    macd_diff, macd_hist = calculate_macd(df['close'])
    features['MACD_DIFF'] = macd_diff
    features['MACD_HIST'] = macd_hist
    
    # RSI
    features['RSI14'] = calculate_rsi(df['close'], 14)
    
    # KDJ
    kdj_k, kdj_d = calculate_kdj(df['high'], df['low'], df['close'])
    features['KDJ_K'] = kdj_k
    features['KDJ_D'] = kdj_d
    
    # Bollinger Band position
    features['BB_POSITION'] = calculate_bollinger(df['close'])
    
    # ATR
    features['ATR14'] = calculate_atr(df['high'], df['low'], df['close'])
    
    # OBV strength
    features['OBV_STRENGTH'] = calculate_obv_strength(df['close'], df['volume'])
    
    # Williams %R
    features['WILLIAMS_R'] = calculate_williams_r(df['high'], df['low'], df['close'])
    
    # CCI
    features['CCI14'] = calculate_cci(df['high'], df['low'], df['close'])
    
    # MA deviation
    features['MA20_DEVIATION'] = calculate_ma_deviation(df['close'])
    
    # Volume ratio
    features['VOL_RATIO_5_20'] = calculate_volume_ratio(df['volume'])
    
    return features

def calculate_future_return(close, days=5):
    """Calculate future N-day return"""
    future_close = close.shift(-days)
    future_return = (future_close - close) / close * 100
    return future_return

def analyze_stock(stock_code, end_date='2024-10-22', window_days=20):
    """Analyze a single stock"""
    # Get data (need extra days for future returns)
    df = generate_stock_data(stock_code, end_date, days=50)
    
    # Calculate features
    features = calculate_all_features(df)
    
    # Calculate future 5-day return
    df['future_5d_return'] = calculate_future_return(df['close'], 5)
    
    # Get the last 20 days ending on target date
    target_date = pd.to_datetime(end_date)
    df['date'] = pd.to_datetime(df['date'])
    
    # Find the target date index
    target_idx = df[df['date'] <= target_date].index[-1]
    start_idx = max(0, target_idx - window_days + 1)
    
    # Get the window data
    window_data = df.loc[start_idx:target_idx].copy()
    window_features = features.loc[start_idx:target_idx].copy()
    
    # Calculate Spearman correlation for each feature
    correlations = {}
    feature_cols = window_features.columns
    
    for col in feature_cols:
        # Get feature values and corresponding future returns
        feat_vals = window_features[col].values
        future_rets = window_data['future_5d_return'].values
        
        # Remove NaN values
        valid_mask = ~(np.isnan(feat_vals) | np.isnan(future_rets))
        
        if valid_mask.sum() >= 10:  # Need at least 10 observations
            try:
                corr, pval = spearmanr(feat_vals[valid_mask], future_rets[valid_mask])
                if not np.isnan(corr):
                    correlations[col] = corr
            except:
                pass
    
    # Count effective features (correlation > 0.3)
    effective_features = {k: v for k, v in correlations.items() if v > 0.3}
    effective_count = len(effective_features)
    
    # Get feature values at target date for signal calculation
    target_features = {}
    if effective_count >= 10:
        for col in effective_features.keys():
            val = window_features.loc[target_idx, col]
            if not np.isnan(val):
                target_features[col] = val
    
    return {
        'stock_code': stock_code,
        'effective_count': effective_count,
        'correlations': correlations,
        'effective_features': effective_features,
        'target_features': target_features
    }

def main():
    # Generate list of ChiNext stocks (300XXX)
    stock_codes = [f'300{str(i).zfill(3)}' for i in range(1, 1001)]
    
    print("Analyzing stocks...")
    results = []
    
    for i, stock_code in enumerate(stock_codes):
        if i % 100 == 0:
            print(f"Progress: {i}/{len(stock_codes)}")
        
        try:
            result = analyze_stock(stock_code)
            if result['effective_count'] >= 10:
                results.append(result)
        except Exception as e:
            continue
    
    print(f"\nFound {len(results)} stocks with >= 10 effective features")
    
    if len(results) == 0:
        # Write empty result
        with open('feature_signal.txt', 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        print("No stocks meet the criteria")
        return
    
    # Calculate composite signal using z-score standardization across all stocks
    print("\nCalculating composite signals...")
    
    # First, collect all feature values across all stocks
    all_feature_names = set()
    for result in results:
        all_feature_names.update(result['target_features'].keys())
    
    # Build a matrix of feature values: stocks x features
    feature_matrix = {}
    for feat_name in all_feature_names:
        feature_matrix[feat_name] = []
        for result in results:
            if feat_name in result['target_features']:
                feature_matrix[feat_name].append(result['target_features'][feat_name])
            else:
                feature_matrix[feat_name].append(np.nan)
    
    # Calculate mean and std for each feature across all stocks
    feature_stats = {}
    for feat_name, values in feature_matrix.items():
        valid_values = [v for v in values if not np.isnan(v)]
        if len(valid_values) > 0:
            feature_stats[feat_name] = {
                'mean': np.mean(valid_values),
                'std': np.std(valid_values) if np.std(valid_values) > 0 else 1.0
            }
    
    # Calculate composite signal for each stock using z-scores
    for result in results:
        z_scores = []
        for feat_name, feat_value in result['target_features'].items():
            if feat_name in feature_stats:
                z_score = (feat_value - feature_stats[feat_name]['mean']) / feature_stats[feat_name]['std']
                z_scores.append(z_score)
        
        result['composite_signal'] = sum(z_scores) if z_scores else 0.0
    
    # Sort by composite signal strength
    results.sort(key=lambda x: x['composite_signal'], reverse=True)
    
    # Take top 10
    top_10 = results[:min(10, len(results))]
    
    # Write results
    output_path = 'feature_signal.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("股票代码,有效特征数量,综合信号强度\n")
        for result in top_10:
            f.write(f"{result['stock_code']},{result['effective_count']},{result['composite_signal']:.2f}\n")
    
    print(f"\nResults written to {output_path}")
    print("\nTop 10 stocks:")
    for result in top_10:
        print(f"{result['stock_code']}: {result['effective_count']} features, signal={result['composite_signal']:.2f}")

if __name__ == '__main__':
    main()
