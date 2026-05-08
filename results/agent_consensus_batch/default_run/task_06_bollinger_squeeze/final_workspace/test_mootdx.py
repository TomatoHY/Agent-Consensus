#!/usr/bin/env python3
"""
测试mootdx API以找出正确的参数
"""
from mootdx.quotes import Quotes
import pandas as pd

print("初始化客户端...")
client = Quotes.factory(market='std')

print("\n=== 测试1: 获取创业板股票列表 ===")
stocks = client.stocks(market=0)
print(f"返回类型: {type(stocks)}")
print(f"数据量: {len(stocks)}")
print(f"列名: {list(stocks.columns)}")

# 筛选创业板
chinext = stocks[stocks['code'].str.startswith(('300', '301'))]
print(f"\n创业板股票数量: {len(chinext)}")
print(f"前5只股票:\n{chinext.head()}")

# 测试获取单只股票数据
if len(chinext) > 0:
    test_code = chinext.iloc[0]['code']
    print(f"\n=== 测试2: 获取股票 {test_code} 的K线数据 ===")

    # 尝试不同的参数
    print("\n尝试 frequency=9, offset=50:")
    try:
        bars = client.bars(symbol=test_code, frequency=9, offset=50)
        print(f"  成功! 数据量: {len(bars) if bars is not None else 0}")
        if bars is not None and len(bars) > 0:
            print(f"  列名: {list(bars.columns)}")
            print(f"  前3行:\n{bars.head(3)}")
            print(f"  最后3行:\n{bars.tail(3)}")
    except Exception as e:
        print(f"  失败: {e}")

    print("\n尝试 frequency=9, offset=100:")
    try:
        bars = client.bars(symbol=test_code, frequency=9, offset=100)
        print(f"  成功! 数据量: {len(bars) if bars is not None else 0}")
    except Exception as e:
        print(f"  失败: {e}")

    # 测试多只股票
    print("\n=== 测试3: 测试前10只股票的数据可用性 ===")
    for i in range(min(10, len(chinext))):
        code = chinext.iloc[i]['code']
        try:
            bars = client.bars(symbol=code, frequency=9, offset=50)
            status = f"✓ {len(bars)} 条" if bars is not None and len(bars) > 0 else "✗ 无数据"
            print(f"  {code}: {status}")
        except Exception as e:
            print(f"  {code}: ✗ 错误 - {e}")
