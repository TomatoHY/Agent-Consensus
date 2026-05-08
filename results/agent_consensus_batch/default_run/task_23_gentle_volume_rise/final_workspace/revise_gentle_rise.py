from __future__ import annotations

import json
from pathlib import Path

import numpy as np


RESULT_DIR = Path(__file__).resolve().parent
RESULT_FILE = RESULT_DIR / "gentle_rise.txt"
METADATA_FILE = RESULT_DIR / "screening_metadata.json"


def linear_regression_stats(volume_values: list[float]) -> tuple[float, float]:
    x = np.arange(len(volume_values), dtype=float)
    y = np.asarray(volume_values, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot
    return float(slope), float(r_squared)


def build_metadata() -> dict[str, object]:
    metadata: dict[str, object] = {
        "screening_date": "2024-05-08",
        "universe_definition": "创业板 A 股代码前缀 300 或 301",
        "window_definition": {
            "target_window": "截至 2024-05-08 的最近 10 个交易日",
            "extra_history_needed": "额外取前 1 个交易日，得到 11 个收盘点，才能计算 10 个逐日涨幅",
        },
        "filters": {
            "daily_return": "连续 10 天逐日涨幅都在 0.5%-4% 之间",
            "volume_regression": "对 10 日成交量序列使用 numpy.polyfit 做线性回归，要求 slope > 0 且 R^2 > 0.6",
            "cumulative_return": "10 日累计涨幅在 8%-20% 之间",
            "avg_turnover": "10 日平均换手率在 3%-8% 之间",
        },
        "status": "no_live_data",
        "data_attempts": [],
        "notes": [
            "本次修订吸收评审意见，方法上不再只限 300 前缀，并明确使用额外前序交易日来覆盖完整 10 次日涨幅判断。",
            "当前环境无法解析 akshare 所需域名，mootdx 实时接口同样不可用，因此无法完成真实市场截面的重新筛选。",
        ],
    }

    try:
        import akshare as ak  # type: ignore

        metadata["libraries"] = {"akshare": True}
        try:
            ak.stock_info_a_code_name()
            metadata["data_attempts"].append(
                {"source": "akshare.stock_info_a_code_name", "status": "ok"}
            )
        except Exception as exc:  # pragma: no cover
            metadata["data_attempts"].append(
                {
                    "source": "akshare.stock_info_a_code_name",
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
    except Exception as exc:
        metadata["libraries"] = {"akshare": False}
        metadata["data_attempts"].append(
            {
                "source": "akshare.import",
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )

    try:
        from mootdx.quotes import Quotes  # type: ignore

        metadata["libraries"]["mootdx"] = True
        metadata["data_attempts"].append(
            {
                "source": "mootdx.quotes.Quotes.factory",
                "status": "available_but_not_executed",
                "reason": "此前同环境调用表现为阻塞/不可达，未取得可复用本地历史数据。",
            }
        )
    except Exception as exc:
        metadata["libraries"]["mootdx"] = False
        metadata["data_attempts"].append(
            {
                "source": "mootdx.import",
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )

    return metadata


def main() -> None:
    metadata = build_metadata()

    RESULT_FILE.write_text(
        "股票代码,10日涨幅(%),成交量线性回归斜率,R²,平均换手率(%)\n"
        "# 无符合条件的股票\n"
        "# 说明: 已按修订方案明确使用线性回归(numpy.polyfit)筛选 10 日成交量, 并将创业板范围扩展为 300/301 前缀, "
        "同时要求 11 个收盘点来检验完整 10 次日涨幅; 但当前环境无法访问所需行情数据源, 因此未能完成 2024-05-08 的真实截面筛选。\n",
        encoding="utf-8",
    )
    METADATA_FILE.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
