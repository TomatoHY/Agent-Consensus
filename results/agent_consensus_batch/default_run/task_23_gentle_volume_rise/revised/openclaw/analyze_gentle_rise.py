import akshare as ak
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime

def check_continuous_rise(df):
    """
    Check if stock rises continuously for 10 days with daily gain between 0.5%-4%
    Returns: (is_valid, total_return)
    """
    if len(df) != 10:
        return False, 0
    
    # Sort by date
    df = df.sort_values('日期').reset_index(drop=True)
    
    # Calculate daily returns
    daily_returns = []
    for i in range(1, len(df)):
        daily_return = (df.loc[i, '收盘'] - df.loc[i-1, '收盘']) / df.loc[i-1, '收盘'] * 100
        daily_returns.append(daily_return)
    
    # Check all 9 daily returns are between 0.5% and 4%
    if len(daily_returns) != 9:
        return False, 0
    
    for ret in daily_returns:
        if ret < 0.5 or ret > 4.0:
            return False, 0
    
    # Calculate total 10-day return
    total_return = (df.loc[9, '收盘'] - df.loc[0, '收盘']) / df.loc[0, '收盘'] * 100
    
    return True, total_return

def linear_regression_volume(volumes):
    """
    Perform linear regression on volume sequence
    Returns: (slope, r_squared)
    """
    if len(volumes) != 10:
        return 0, 0
    
    x = np.arange(10)  # Time index: 0, 1, 2, ..., 9
    y = np.array(volumes, dtype=float)
    
    # Use scipy.stats.linregress for linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    r_squared = r_value ** 2
    
    return slope, r_squared

def main():
    """Main function to analyze ChiNext stocks"""
    
    # Target date: 2024-05-08
    end_date = '20240508'
    start_date = '20240415'  # Start earlier to ensure we get 10 trading days
    
    print(f"Analyzing ChiNext stocks from {start_date} to {end_date}...")
    
    # Get ChiNext stock list (codes starting with 300)
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext_stocks = stock_info[stock_info['code'].str.startswith('300')]['code'].tolist()
        print(f"Found {len(chinext_stocks)} ChiNext stocks")
    except Exception as e:
        print(f"Error getting stock list: {e}")
        return []
    
    results = []
    
    for idx, stock_code in enumerate(chinext_stocks):
        if idx % 100 == 0:
            print(f"Progress: {idx}/{len(chinext_stocks)}")
        
        try:
            # Get historical K-line data with forward adjustment
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if df is None or len(df) < 10:
                continue
            
            # Convert date column
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期').reset_index(drop=True)
            
            # Get last 10 trading days
            df_10 = df.tail(10).reset_index(drop=True)
            
            if len(df_10) != 10:
                continue
            
            # Condition 1: Check continuous rise with daily gain 0.5%-4%
            is_continuous, total_return = check_continuous_rise(df_10)
            if not is_continuous:
                continue
            
            # Condition 3: Total return must be 8%-20%
            if total_return < 8 or total_return > 20:
                continue
            
            # Condition 2: Linear regression on volume
            volumes = df_10['成交量'].values
            slope, r_squared = linear_regression_volume(volumes)
            
            # Slope must be positive and R² > 0.6
            if slope <= 0 or r_squared <= 0.6:
                continue
            
            # Condition 4: Average turnover rate 3%-8%
            if '换手率' in df_10.columns:
                turnover_rates = df_10['换手率'].values
                avg_turnover = np.mean(turnover_rates)
                
                if avg_turnover < 3 or avg_turnover > 8:
                    continue
            else:
                # If turnover rate not available, skip
                continue
            
            # All conditions met
            results.append({
                'code': stock_code,
                'total_return': total_return,
                'slope': slope,
                'r_squared': r_squared,
                'avg_turnover': avg_turnover
            })
            
            print(f"✓ Found: {stock_code}, Return: {total_return:.2f}%, R²: {r_squared:.3f}, Turnover: {avg_turnover:.2f}%")
            
        except Exception as e:
            # Skip stocks with errors
            continue
    
    return results

if __name__ == "__main__":
    print("=" * 60)
    print("温和放量上涨线性回归筛选")
    print("=" * 60)
    
    results = main()
    
    print(f"\n{'=' * 60}")
    print(f"Analysis complete. Found {len(results)} stocks matching all criteria.")
    print(f"{'=' * 60}\n")
    
    # Write results to gentle_rise.txt
    output_file = "gentle_rise.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,10日涨幅(%),成交量线性回归斜率,R²,平均换手率(%)\n")
        
        if len(results) == 0:
            f.write("# 无符合条件的股票\n")
        else:
            for r in results:
                f.write(f"{r['code']},{r['total_return']:.2f},{r['slope']:.0f},{r['r_squared']:.3f},{r['avg_turnover']:.2f}\n")
    
    print(f"Results written to {output_file}")
