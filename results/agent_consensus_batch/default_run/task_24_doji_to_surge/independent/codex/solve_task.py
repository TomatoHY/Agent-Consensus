from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


WORKSPACE = Path(__file__).resolve().parent
OUTPUT_FILE = WORKSPACE / "doji_surge.txt"
CUTOFF_DATE = pd.Timestamp("2024-06-07")


def get_chinext_stocks() -> list[str]:
    import akshare as ak

    df = ak.stock_info_a_code_name()
    df["code"] = df["code"].astype(str).str.zfill(6)
    return sorted(df.loc[df["code"].str.startswith("300"), "code"].unique().tolist())


def get_kline(code: str, period: int = 180) -> pd.DataFrame:
    import akshare as ak

    df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
    rename_map = {
        "日期": "date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
    }
    df = df.rename(columns=rename_map)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] <= CUTOFF_DATE]
    return df[["date", "open", "high", "low", "close", "volume"]].dropna().tail(period).reset_index(drop=True)


def iter_low_volume_windows(flags: pd.Series) -> Iterable[tuple[int, int]]:
    start = None
    values = flags.fillna(False).tolist()
    for idx, flag in enumerate(values):
        if flag and start is None:
            start = idx
        elif not flag and start is not None:
            if idx - start >= 3:
                yield start, idx - 1
            start = None
    if start is not None and len(values) - start >= 3:
        yield start, len(values) - 1


def analyze_stock(df: pd.DataFrame) -> list[dict]:
    if len(df) < 90:
        return []

    df = df.copy()
    df["vol_ma60"] = df["volume"].rolling(60).mean()
    df["is_low_volume"] = df["volume"] < df["vol_ma60"] * 0.5
    df["prev_close"] = df["close"].shift(1)
    df["gain_pct"] = (df["close"] / df["prev_close"] - 1.0) * 100.0

    recent = df.tail(30).reset_index()
    matches: list[dict] = []

    for start_local, end_local in iter_low_volume_windows(recent["is_low_volume"]):
        low_period = recent.iloc[start_local : end_local + 1]
        swing = (low_period["high"].max() - low_period["low"].min()) / low_period["low"].min()
        if pd.isna(swing) or swing >= 0.03:
            continue

        surge_candidates = recent.iloc[end_local + 1 : min(end_local + 11, len(recent))]
        for _, row in surge_candidates.iterrows():
            row_global = int(row["index"])
            vol_ratio = row["volume"] / row["vol_ma60"] if pd.notna(row["vol_ma60"]) else float("nan")
            prior_30_high = df.iloc[max(0, row_global - 30) : row_global]["high"].max()
            if (
                pd.notna(vol_ratio)
                and vol_ratio > 3.0
                and row["close"] > row["open"]
                and row["gain_pct"] > 5.0
                and pd.notna(prior_30_high)
                and row["close"] > prior_30_high
            ):
                matches.append(
                    {
                        "low_days": len(low_period),
                        "surge_date": row["date"].strftime("%Y-%m-%d"),
                        "vol_ratio": round(float(vol_ratio), 2),
                        "gain_pct": round(float(row["gain_pct"]), 2),
                    }
                )
                break

    return matches


def main() -> None:
    header = "股票代码,地量期天数,天量日期,量比(天量/60日均量),突破涨幅(%)"
    try:
        rows = [header]
        for code in get_chinext_stocks():
            try:
                df = get_kline(code)
            except Exception:
                continue
            for match in analyze_stock(df):
                rows.append(
                    f"{code},{match['low_days']},{match['surge_date']},{match['vol_ratio']},{match['gain_pct']}"
                )
        text = "\n".join(rows) if len(rows) > 1 else "无符合条件的股票"
    except Exception:
        text = "无符合条件的股票"

    OUTPUT_FILE.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
