import akshare as ak
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta

def check_continuous_rise(df):
    """Check if stock rises continuously with daily gain between 0.5%-4%"""
    if len(df) < 10:
        return False, 0

    # Calculate daily returns
    df = df.sort_values('日期')
    df['daily_return'] = (df['收盘'] - df['收盘'].shift(1)) / df['收盘'].shift(1) * 100

    # Check from day 2 onwards (first day has no previous close)
    daily_returns = df['daily_return'].iloc[1:].values

    # All days must have positive return between 0.5% and 4%
    if len(daily_returns) < 9:
        return False, 0

    valid_rise = all((0.5 <= r <= 4.0) for r in daily_returns)

    # Calculate total 10-day return
    total_return = (df['收盘'].iloc[-1] - df['收盘'].iloc[0]) / df['收盘'].iloc[0] * 100

    return valid_rise, total_return

def linear_regression_volume(volumes):
    """Perform linear regression on volume data"""
    if len(volumes) < 10:
        return 0, 0

    x = np.arange(len(volumes))
    y = np.array(volumes)

    # Use scipy.stats.linregress for linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    r_squared = r_value ** 2

    return slope, r_squared

def analyze_chinext_stocks():
    """Analyze ChiNext stocks for gentle volume rise pattern"""

    end_date = '20240508'
    # Start from earlier to ensure we get at least 10 trading days
    start_date = '20240420'

    print(f"Analyzing data from {start_date} to {end_date}...")

    # Get ChiNext stock list (code starts with 300)
    print("Getting ChiNext stock list...")
    stock_info = ak.stock_info_a_code_name()
    chinext_stocks = stock_info[stock_info['code'].str.startswith('300')]['code'].tolist()

    print(f"Found {len(chinext_stocks)} ChiNext stocks")

    results = []

    for i, stock_code in enumerate(chinext_stocks):
        if i % 50 == 0:
            print(f"Processing {i}/{len(chinext_stocks)}...")

        try:
            # Get daily K-line data
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                    start_date=start_date,
                                    end_date=end_date,
                                    adjust="qfq")

            if df is None or len(df) < 10:
                continue

            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期')

            # Get the last 10 trading days
            df = df.tail(10)

            if len(df) != 10:
                continue

            # Check continuous rise condition
            is_continuous_rise, total_return = check_continuous_rise(df)

            if not is_continuous_rise:
                continue

            # Check total return in 8%-20% range
            if not (8 <= total_return <= 20):
                continue

            # Linear regression on volume
            volumes = df['成交量'].values
            slope, r_squared = linear_regression_volume(volumes)

            # Check slope is positive and R² > 0.6
            if slope <= 0 or r_squared <= 0.6:
                continue

            # Calculate average turnover rate
            turnover_rates = df['换手率'].values
            avg_turnover = np.mean(turnover_rates)

            # Check turnover rate in 3%-8% range
            if not (3 <= avg_turnover <= 8):
                continue

            results.append({
                'code': stock_code,
                'total_return': total_return,
                'slope': slope,
                'r_squared': r_squared,
                'avg_turnover': avg_turnover
            })

            print(f"Found: {stock_code}, Return: {total_return:.2f}%, R²: {r_squared:.3f}, Turnover: {avg_turnover:.2f}%")

        except Exception as e:
            continue

    return results

if __name__ == "__main__":
    print("Starting analysis...")
    results = analyze_chinext_stocks()

    print(f"\nFound {len(results)} stocks matching criteria")

    # Write results to file
    output_file = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_23_gentle_volume_rise/independent/claudecode/gentle_rise.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,10日涨幅(%),成交量线性回归斜率,R²,平均换手率(%)\n")

        if len(results) == 0:
            f.write("# 无符合条件的股票\n")
        else:
            for r in results:
                f.write(f"{r['code']},{r['total_return']:.2f},{r['slope']:.0f},{r['r_squared']:.3f},{r['avg_turnover']:.2f}\n")

    print(f"Results written to {output_file}")
