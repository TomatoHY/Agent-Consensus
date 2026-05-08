import akshare as ak
import pandas as pd

# Check what columns are returned
try:
    df = ak.stock_zh_a_spot_em()
    df = df[df['代码'].str.startswith('300')].copy()
    print("Columns:", df.columns.tolist())
    print(f"\nTotal ChiNext stocks: {len(df)}")
    print("\nFirst few rows:")
    print(df.head())
except Exception as e:
    print(f"Error: {e}")
