import akshare as ak
import pandas as pd

# Test with a specific stock
test_stock = '300750'  # A known ChiNext stock

print(f"Testing data retrieval for {test_stock}...")

try:
    df = ak.stock_zh_a_hist(symbol=test_stock, period="daily",
                            start_date='20240801', end_date='20240913', adjust="qfq")

    print(f"Data retrieved: {len(df)} rows")
    print(f"\nFirst few rows:")
    print(df.head())
    print(f"\nLast few rows:")
    print(df.tail())
    print(f"\nColumn names: {df.columns.tolist()}")

    # Check for target date
    df['日期'] = pd.to_datetime(df['日期'])
    target_date = pd.to_datetime('20240913')

    print(f"\nLooking for date: {target_date}")
    matching = df[df['日期'] == target_date]
    print(f"Found target date: {len(matching) > 0}")

    if len(matching) > 0:
        print(f"Target date index: {matching.index[0]}")

    # Check date range
    print(f"\nDate range in data:")
    print(f"  Min: {df['日期'].min()}")
    print(f"  Max: {df['日期'].max()}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
