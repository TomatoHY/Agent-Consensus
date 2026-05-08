#!/usr/bin/env python3
import akshare as ak
import pandas as pd

# 测试获取单只股票数据
stock_code = "300001"
print(f"测试获取股票 {stock_code} 的数据...")

try:
    # 尝试方法1
    print("\n方法1: 使用带横杠的日期格式")
    df1 = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                             start_date="2023-09-01", end_date="2024-11-15", adjust="qfq")
    print(f"成功! 获取到 {len(df1)} 条数据")
    print(f"列名: {df1.columns.tolist()}")
    print(df1.head())
except Exception as e:
    print(f"失败: {e}")

try:
    # 尝试方法2
    print("\n方法2: 使用不带横杠的日期格式")
    df2 = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                             start_date="20230901", end_date="20241115", adjust="qfq")
    print(f"成功! 获取到 {len(df2)} 条数据")
    print(f"列名: {df2.columns.tolist()}")
    print(df2.head())
except Exception as e:
    print(f"失败: {e}")

try:
    # 尝试方法3
    print("\n方法3: 不指定日期")
    df3 = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="qfq")
    print(f"成功! 获取到 {len(df3)} 条数据")
    print(f"列名: {df3.columns.tolist()}")
    print(df3.tail())
except Exception as e:
    print(f"失败: {e}")
