---
id: task_15_volume_price_contraction_breakout
name: 缩量整理后放量突破形态识别
category: complex_volume_price_pattern
grading_type: hybrid
timeout_seconds: 480
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files: []
---

## Prompt

在创业板中找出以 2024-07-15 为截止交易日的前60个交易日内出现"缩量整理后放量突破"形态的股票，条件：

1. **缩量期**：存在连续至少8天的缩量期，每天成交量均低于60日均量的70%；
2. **价格整理**：缩量期内价格波动幅度小于5%（(最高价 - 最低价) / 最低价 < 5%）；
3. **放量突破**：缩量期结束后的5个交易日内，出现至少1天成交量超过60日均量的2.5倍；
4. **价格突破**：放量当天收盘价突破缩量期的最高价；
5. **无大幅回调**：放量突破后，未出现单日跌幅超过5%的回调。

将结果写入 `contraction_breakout.txt`，格式：
```
股票代码,缩量期开始日期,缩量期结束日期,放量突破日期,突破涨幅(%)
300XXX,2024-01-02,2024-01-12,2024-01-15,8.5
```

## Expected Behavior

Agent应该：
1. 获取近60个交易日的K线数据（含收盘价、最高价、最低价、成交量）
2. 计算60日均量作为参考基准
3. 用滑动窗口在时间序列中搜索连续≥8天的缩量期
4. 对找到的缩量期验证价格波动幅度 < 5%
5. 在缩量期结束后的5天内寻找放量突破
6. 验证无回调（放量后每日跌幅<5%）
7. 记录所有满足条件的形态

## Grading Criteria

- [ ] 文件 `contraction_breakout.txt` 已创建
- [ ] 文件包含代码、4个日期字段、突破涨幅
- [ ] 缩量期结束日期早于放量突破日期
- [ ] agent在过程中使用了滑动窗口搜索缩量期
- [ ] agent计算了60日均量作为参考基准
- [ ] agent验证了放量后无大幅回调条件

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re
    from datetime import datetime

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "contraction_breakout.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "breakout.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["date_order"] = 0.0
        scores["volume_baseline"] = 0.0
        scores["drawdown_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "no stock", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
        scores["date_order"] = 1.0
    else:
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l]
        has_dates = bool(re.search(r'\d{4}-\d{2}-\d{2}', content))
        has_code = bool(re.search(r'3\d{5}', content))
        scores["valid_format"] = 1.0 if (has_code and has_dates) else (0.5 if has_code else 0.0)

        # Check date order: contraction_end < breakout_date
        date_sets = []
        for line in lines:
            dates = re.findall(r'\d{4}-\d{2}-\d{2}', line)
            if len(dates) >= 3:
                try:
                    d1 = datetime.strptime(dates[0], "%Y-%m-%d")
                    d2 = datetime.strptime(dates[1], "%Y-%m-%d")
                    d3 = datetime.strptime(dates[2], "%Y-%m-%d")
                    date_sets.append(d1 < d2 < d3)
                except:
                    pass
        scores["date_order"] = 1.0 if all(date_sets) and len(date_sets) > 0 else (0.5 if len(date_sets) > 0 else 0.0)

    transcript_str = str(transcript).lower()
    scores["volume_baseline"] = 1.0 if any(kw in transcript_str for kw in
        ["60日均量", "60.*mean.*vol", "volume.*60", "均量", "avg.*vol"]) else 0.0
    scores["drawdown_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["回调", "drawdown", "跌幅", "decline", "5%"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 形态识别算法的完整性（Weight: 40%）

**Score 1.0**: 五个条件全部正确实现：连续缩量期检测（滑动窗口）、价格振幅计算、放量突破检测、价格突破判断、回调验证，算法逻辑严密。
**Score 0.75**: 实现了4个条件，缺少1个或1个条件有轻微错误（如缺少回调验证）。
**Score 0.5**: 实现了3个条件，有2个条件缺失或有明显错误。
**Score 0.25**: 仅实现了1-2个条件。
**Score 0.0**: 未实现形态识别。

### Criterion 2: 滑动窗口搜索实现（Weight: 25%）

**Score 1.0**: 正确在60天时间序列中用动态滑动窗口搜索缩量期（不限定在固定位置），能找到所有可能的缩量期，并对每个缩量期独立验证后续条件。
**Score 0.75**: 滑动窗口实现基本正确，但可能错过部分重叠或连续的缩量期。
**Score 0.5**: 只搜索了固定位置（如只搜索最近8天），未用动态窗口。
**Score 0.25**: 未用滑动窗口，只做了简单的全局平均比较。
**Score 0.0**: 未实现时间序列搜索。

### Criterion 3: 结果输出精确性（Weight: 35%）

**Score 1.0**: 输出包含代码、缩量起止日期、放量突破日期、突破涨幅，日期顺序正确，涨幅计算准确，无结果时明确说明。
**Score 0.75**: 输出基本正确，个别字段格式不规范或精度有偏差。
**Score 0.5**: 只输出了代码和部分日期，缺少涨幅等数值。
**Score 0.25**: 文件存在但内容不完整或格式混乱。
**Score 0.0**: 未创建结果文件。
