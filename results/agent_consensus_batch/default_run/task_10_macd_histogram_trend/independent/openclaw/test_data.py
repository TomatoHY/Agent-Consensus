#!/usr/bin/env python3
"""测试单只股票数据获取"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

# 测试获取一只创业板股票
stock_code = "300750"  # 宁德时代
end_date = "20241231"

print(f"测试获取股票 {stock_code} 的数据...")

try:
    end_dt = datetime.strptime(end_date, '%Y%m%d')
    start_dt = end_dt - timedelta(days=180)
    start_date = start_dt.strftime('%Y%m%d')
    
    print(f"开始日期: {start_date}")
    print(f"结束日期: {end_date}")
    
    df = ak.stock_zh_a_hist(
        symbol=stock_code,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"
    )
    
    print(f"\n获取到 {len(df)} 条数据")
    print(f"\n列名: {df.columns.tolist()}")
    print(f"\n前5行数据:")
    print(df.head())
    print(f"\n数据类型:")
    print(df.dtypes)
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
