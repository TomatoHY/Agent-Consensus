import akshare as ak
import pandas as pd

# Try to get ChiNext constituent stocks
print("Trying to get ChiNext Index (399006) constituent stocks...")

try:
    stock_info = ak.stock_info_a_code_name()
    constituents = stock_info[stock_info['code'].str.startswith('300')]
    print(f"\nFound {len(constituents)} stocks starting with 300")
    print(f"\nColumn names: {constituents.columns.tolist()}")
    print(f"\nFirst 10 stocks:")
    print(constituents.head(10))

    # Check for semiconductor keywords
    semiconductor_keywords = ['半导体', '芯片', '微电子', '集成电路', '晶圆', '封测']

    print(f"\n\nSearching for semiconductor stocks...")
    for keyword in semiconductor_keywords:
        matches = constituents[constituents['name'].str.contains(keyword, na=False)]
        if len(matches) > 0:
            print(f"\nStocks containing '{keyword}':")
            print(matches)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
