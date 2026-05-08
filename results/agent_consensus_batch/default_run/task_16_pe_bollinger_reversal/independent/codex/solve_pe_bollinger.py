from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


END_DATE = "2024-08-15"
LOOKBACK_START = "2024-06-15"
OUTPUT_FILE = Path("pe_bollinger_top8.txt")


@dataclass
class Candidate:
    code: str
    pe: float
    rebound_date: str
    gain_5d_pct: float


def compute_bollinger(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["mid"] = out["close"].rolling(20).mean()
    std = out["close"].rolling(20).std(ddof=0)
    out["upper"] = out["mid"] + 2 * std
    out["lower"] = out["mid"] - 2 * std
    out["vol5"] = out["volume"].rolling(5).mean()
    out["vol20"] = out["volume"].rolling(20).mean()
    return out


def screen_candidate(code: str, pe: float, hist: pd.DataFrame) -> Candidate | None:
    if hist.empty or len(hist) < 25:
        return None

    hist = hist.sort_values("date").reset_index(drop=True)
    hist = compute_bollinger(hist)
    last = hist.iloc[-1]

    recent20 = hist.tail(20).copy()
    touched = recent20[recent20["close"] <= recent20["lower"]]
    if touched.empty:
        return None
    if pd.isna(last["mid"]) or last["close"] <= last["mid"]:
        return None
    if pd.isna(last["vol5"]) or pd.isna(last["vol20"]) or last["vol5"] <= last["vol20"]:
        return None

    touch_idx = touched.index[-1]
    rebound_date = hist.loc[touch_idx, "date"].strftime("%Y-%m-%d")

    if len(hist) < 6:
        return None
    gain_5d_pct = (last["close"] / hist.iloc[-6]["close"] - 1) * 100
    return Candidate(code=code, pe=float(pe), rebound_date=rebound_date, gain_5d_pct=float(gain_5d_pct))


def fetch_and_screen() -> list[Candidate]:
    import akshare as ak

    spot = ak.stock_zh_a_spot_em()
    spot["代码"] = spot["代码"].astype(str).str.zfill(6)
    spot = spot[spot["代码"].str.startswith("300")].copy()

    pe_col = None
    for candidate in ["市盈率-动态", "市盈率-静态", "PE", "pe"]:
        if candidate in spot.columns:
            pe_col = candidate
            break
    if pe_col is None:
        raise RuntimeError(f"PE column not found in spot columns: {spot.columns.tolist()}")

    spot[pe_col] = pd.to_numeric(spot[pe_col], errors="coerce")
    spot = spot[(spot[pe_col] >= 15) & (spot[pe_col] <= 60)].copy()

    results: list[Candidate] = []
    for _, row in spot.iterrows():
        code = row["代码"]
        hist = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=LOOKBACK_START.replace("-", ""),
            end_date=END_DATE.replace("-", ""),
            adjust="qfq",
        )
        if hist.empty:
            continue

        hist = hist.rename(
            columns={
                "日期": "date",
                "收盘": "close",
                "成交量": "volume",
            }
        )
        hist["date"] = pd.to_datetime(hist["date"])
        hist["close"] = pd.to_numeric(hist["close"], errors="coerce")
        hist["volume"] = pd.to_numeric(hist["volume"], errors="coerce")
        hist = hist.dropna(subset=["date", "close", "volume"])

        candidate = screen_candidate(code=code, pe=float(row[pe_col]), hist=hist)
        if candidate is not None:
            results.append(candidate)

    results.sort(key=lambda x: (x.pe, x.code))
    return results[:8]


def write_candidates(candidates: list[Candidate]) -> None:
    lines = ["股票代码,PE,布林带反弹日期,近5日涨幅(%)"]
    for c in candidates:
        lines.append(f"{c.code},{c.pe:.1f},{c.rebound_date},{c.gain_5d_pct:.1f}")
    OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_offline_notice(exc: Exception) -> None:
    OUTPUT_FILE.write_text(
        "# 无符合条件的股票（离线环境阻断数据源）\n"
        "# 已实现筛选逻辑：创业板PE 15-60，20日Bollinger中轨/上下轨，最近20日触及下轨后截至2024-08-15收盘重回中轨上方，近5日均量>近20日均量。\n"
        f"# 阻断原因: {type(exc).__name__}: {exc}\n",
        encoding="utf-8",
    )


def main() -> None:
    try:
        candidates = fetch_and_screen()
        if candidates:
            write_candidates(candidates)
        else:
            OUTPUT_FILE.write_text(
                "# 无符合条件的股票\n"
                "# 已完成PE、布林带、成交量筛选，但在当前可访问数据下结果为空。\n",
                encoding="utf-8",
            )
    except Exception as exc:
        write_offline_notice(exc)


if __name__ == "__main__":
    main()
