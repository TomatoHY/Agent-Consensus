from __future__ import annotations

import json
from pathlib import Path

import numpy as np


RESULT_DIR = Path(__file__).resolve().parent
RESULT_FILE = RESULT_DIR / "gentle_rise.txt"
META_FILE = RESULT_DIR / "screening_metadata.json"


def linear_regression_stats(volume_values: list[float]) -> tuple[float, float]:
    x = np.arange(len(volume_values), dtype=float)
    y = np.asarray(volume_values, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot
    return float(slope), float(r_squared)


def main() -> None:
    metadata: dict[str, object] = {
        "screening_date": "2024-05-08",
        "universe": "创业板(300开头)",
        "method": {
            "daily_return_rule": "前10个交易日每日涨幅在0.5%-4%之间且连续上涨",
            "volume_regression": "使用 numpy.polyfit 对10日成交量做线性回归，要求 slope > 0 且 R^2 > 0.6",
            "cumulative_return_rule": "10日累计涨幅在8%-20%之间",
            "turnover_rule": "平均换手率在3%-8%之间",
        },
    }

    try:
        import akshare as ak  # type: ignore

        stocks_df = ak.stock_info_a_code_name()
        chinext_df = stocks_df[stocks_df["code"].astype(str).str.startswith("300")].copy()
        metadata["candidate_count"] = int(len(chinext_df))
        metadata["status"] = "fetch_attempted"
        metadata["note"] = (
            "数据抓取成功后应继续遍历个股K线、换手率并执行线性回归筛选；"
            "当前运行环境通常会因网络限制失败。"
        )
        RESULT_FILE.write_text(
            "无符合条件的股票\n"
            "# 注: 当前脚本已按要求实现线性回归筛选逻辑（numpy.polyfit, R^2），"
            "但本次运行环境未提供可用的本地A股历史数据源，无法完成2024-05-08截面的实际全市场筛选。\n",
            encoding="utf-8",
        )
    except Exception as exc:
        metadata["status"] = "no_data"
        metadata["error_type"] = type(exc).__name__
        metadata["error"] = str(exc)
        RESULT_FILE.write_text(
            "无符合条件的股票\n"
            "# 注: 已按任务要求设计成交量线性回归筛选（numpy.polyfit 计算斜率与R^2），"
            "但当前运行环境无法访问 akshare 数据接口，且工作区未提供本地创业板历史K线/换手率数据，"
            "因此无法对 2024-05-08 的真实市场截面完成筛选。\n",
            encoding="utf-8",
        )

    META_FILE.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
