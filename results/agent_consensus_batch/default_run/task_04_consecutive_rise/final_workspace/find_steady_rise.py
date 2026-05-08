#!/usr/bin/env python3
"""Find ChiNext stocks with 5 consecutive daily rises of 2%-7% ending 2024-06-28."""

from datetime import datetime

import akshare as ak
import pandas as pd


END_DATE = datetime(2024, 6, 28)
OUTPUT_FILE = "steady_rise.txt"


def get_chinext_stocks():
    stock_info = ak.stock_info_a_code_name()
    chinext = stock_info[stock_info["code"].astype(str).str.startswith("300")]
    return chinext["code"].tolist()


def get_recent_history(stock_code: str, end_date: datetime, days: int = 6):
    df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="qfq")
    if df is None or df.empty:
        return None
    df["日期"] = pd.to_datetime(df["日期"])
    df = df[df["日期"] <= end_date].tail(days)
    if len(df) < days:
        return None
    return df


def check_steady_rise(df) -> tuple[bool, float]:
    if df is None or len(df) < 6:
        return False, 0.0

    closes = df["收盘"].astype(float).to_list()
    for i in range(1, 6):
        prev_close = closes[i - 1]
        curr_close = closes[i]
        if curr_close <= prev_close:
            return False, 0.0
        daily_gain = (curr_close - prev_close) / prev_close * 100
        if not (2.0 <= daily_gain <= 7.0):
            return False, 0.0

    cumulative_gain = (closes[-1] / closes[0] - 1) * 100
    return True, cumulative_gain


def main():
    qualifying_stocks = []
    for code in get_chinext_stocks():
        df = get_recent_history(code, END_DATE, days=6)
        ok, cumulative_gain = check_steady_rise(df)
        if ok:
            qualifying_stocks.append((code, cumulative_gain))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        if qualifying_stocks:
            f.write("股票代码,5日累计涨幅(%)\n")
            for code, gain in qualifying_stocks:
                f.write(f"{code},{gain:.2f}\n")
        else:
            f.write("无符合条件的股票\n")


if __name__ == "__main__":
    main()
