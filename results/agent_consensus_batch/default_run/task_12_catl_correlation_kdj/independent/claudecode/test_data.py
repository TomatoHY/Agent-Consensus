import akshare as ak
import pandas as pd

# Test different ways to fetch CATL data
stock_code = "300750"

print("Testing data fetch methods for CATL (300750)...")

# Method 1: stock_zh_a_hist
print("\n1. Testing stock_zh_a_hist...")
try:
    df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                            start_date="20240301", end_date="20240415", adjust="qfq")
    print(f"Success! Got {len(df)} rows")
    print(df.head())
    print(df.tail())
except Exception as e:
    print(f"Failed: {e}")

# Method 2: stock_zh_a_daily
print("\n2. Testing stock_zh_a_daily...")
try:
    df = ak.stock_zh_a_daily(symbol="sz300750", start_date="20240301", end_date="20240415", adjust="qfq")
    print(f"Success! Got {len(df)} rows")
    print(df.head())
except Exception as e:
    print(f"Failed: {e}")

# Method 3: Check stock list
print("\n3. Checking stock list...")
try:
    stock_list = ak.stock_zh_a_spot_em()
    catl = stock_list[stock_list['代码'] == '300750']
    print(f"CATL in list: {len(catl) > 0}")
    if len(catl) > 0:
        print(catl[['代码', '名称', '最新价']])
except Exception as e:
    print(f"Failed: {e}")
