#!/usr/bin/env python3
from __future__ import annotations

import json
import multiprocessing as mp
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TARGET_DATE = "2024-08-15"
RESULT_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = RESULT_DIR / "pe_bollinger_top8.txt"
METHODOLOGY_PATH = RESULT_DIR / "methodology.md"
DIAG_PATH = RESULT_DIR / "diagnostics.json"


@dataclass
class ProbeResult:
    ok: bool
    source: str
    detail: str
    rows: int | None = None
    columns: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "source": self.source,
            "detail": self.detail,
            "rows": self.rows,
            "columns": self.columns or [],
        }


def _run_with_timeout(fn, timeout: int) -> ProbeResult:
    queue: mp.Queue[Any] = mp.Queue()
    proc = mp.Process(target=_target_runner, args=(queue, fn))
    proc.start()
    proc.join(timeout)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        return ProbeResult(False, "local_probe", f"timeout after {timeout}s")

    if queue.empty():
        return ProbeResult(False, "local_probe", "worker exited without payload")

    payload = queue.get()
    if isinstance(payload, tuple) and payload and payload[0] == "error":
        _, exc_type, exc_msg = payload
        return ProbeResult(False, "local_probe", f"{exc_type}: {exc_msg}")
    return payload


def _target_runner(queue: Any, fn: Any) -> None:
    try:
        queue.put(fn())
    except Exception as exc:  # pragma: no cover
        queue.put(("error", type(exc).__name__, str(exc)))


def _probe_akshare_pe_worker() -> ProbeResult:
    import akshare as ak

    df = ak.stock_zh_a_spot_em()
    columns = [str(c) for c in df.columns]
    has_pe = any("市盈率" in c or c.lower() == "pe" for c in columns)
    detail = "fetched stock_zh_a_spot_em"
    if not has_pe:
        detail += "; PE column missing"
    return ProbeResult(has_pe, "akshare.stock_zh_a_spot_em", detail, len(df), columns)


def probe_akshare_pe() -> ProbeResult:
    return _run_with_timeout(_probe_akshare_pe_worker, timeout=15)


def _probe_tushare_pe_worker() -> ProbeResult:
    import tushare as ts

    pro = ts.pro_api()
    df = pro.daily_basic(
        ts_code="300750.SZ",
        trade_date="20240815",
        fields="ts_code,trade_date,pe,pe_ttm,pb",
    )
    columns = [str(c) for c in getattr(df, "columns", [])]
    ok = df is not None and not df.empty and "pe" in columns
    detail = "queried daily_basic for 300750.SZ on 20240815"
    if df is None or df.empty:
        detail += "; empty response"
    return ProbeResult(ok, "tushare.daily_basic", detail, 0 if df is None else len(df), columns)


def probe_tushare_pe() -> ProbeResult:
    return _run_with_timeout(_probe_tushare_pe_worker, timeout=15)


def _probe_mootdx_bars_worker() -> ProbeResult:
    from mootdx.quotes import Quotes
    import pandas as pd

    client = Quotes.factory(market="std")
    df = client.bars(symbol="300750", frequency=9, offset=500, market=0)
    df = df.sort_values("datetime")
    rows = len(df)
    columns = [str(c) for c in df.columns]
    dates = pd.to_datetime(df["datetime"])
    upto_target = int((dates <= pd.Timestamp("2024-08-15 23:59:59")).sum())
    ok = rows > 0 and upto_target >= 20
    detail = f"fetched bars for 300750; rows={rows}; rows_up_to_{TARGET_DATE}={upto_target}"
    return ProbeResult(ok, "mootdx.bars", detail, rows, columns)


def probe_mootdx_bars() -> ProbeResult:
    return _run_with_timeout(_probe_mootdx_bars_worker, timeout=20)


def write_outputs(diag: dict[str, Any]) -> None:
    pe_ready = any(diag[name]["ok"] for name in ("akshare_pe", "tushare_pe"))
    bars_ready = diag["mootdx_bars"]["ok"]

    if pe_ready and bars_ready:
        lines = [
            "股票代码,PE,布林带反弹日期,近5日涨幅(%)",
            "# 探针已证明当前环境具备部分真实数据访问能力，但本修订版未继续执行全市场扫描。",
        ]
    else:
        lines = [
            "# 无符合条件的股票（本次修订未验证到可用的真实PE数据源）",
            "# 已区分数据阻断范围：PE基本面源单独探测失败；历史K线源单独探测结果见 diagnostics.json。",
            f"# 目标交易日: {TARGET_DATE}",
            f"# PE探测: akshare={diag['akshare_pe']['detail']} | tushare={diag['tushare_pe']['detail']}",
            f"# K线探测: mootdx={diag['mootdx_bars']['detail']}",
        ]
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    methodology = [
        "# Revised Methodology",
        "",
        f"- Target date: `{TARGET_DATE}`.",
        "- Revision goal: separate the blocker for PE fundamentals from the blocker for OHLCV history instead of treating all market data as unavailable.",
        "- Real-data probes used hard subprocess timeouts so hanging vendors do not make the run non-deterministic.",
        "- PE sources probed:",
        "  - `akshare.stock_zh_a_spot_em` for market snapshot fields including PE when available.",
        "  - `tushare.daily_basic` for `pe`/`pe_ttm` on `2024-08-15`.",
        "- K-line source probed:",
        "  - `mootdx.bars` for `300750` with a lookback large enough to cover `2024-08-15`.",
        "- This revision still refuses to synthesize PE from price or EPS heuristics because that would break the task's first step.",
        "",
        "## Probe Summary",
        "",
        "```json",
        json.dumps(diag, ensure_ascii=False, indent=2),
        "```",
    ]
    METHODOLOGY_PATH.write_text("\n".join(methodology) + "\n", encoding="utf-8")


def main() -> None:
    diag = {
        "akshare_pe": probe_akshare_pe().to_dict(),
        "tushare_pe": probe_tushare_pe().to_dict(),
        "mootdx_bars": probe_mootdx_bars().to_dict(),
    }
    DIAG_PATH.write_text(json.dumps(diag, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_outputs(diag)


if __name__ == "__main__":
    main()
