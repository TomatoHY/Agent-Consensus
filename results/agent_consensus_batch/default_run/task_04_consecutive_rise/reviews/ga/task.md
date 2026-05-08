---
id: task_04_consecutive_rise
name: 连续稳健上涨股票识别
category: pattern_detection
grading_type: automated
timeout_seconds: 240
workspace_files: []
---

## Prompt

找出创业板中以 2024-06-28 为截止交易日的前5个交易日内连续上涨且每天涨幅都在2%-7%之间的股票。

要求：
1) 连续5天收盘价递增（每日收盘价均高于前一日）；
2) 每天涨幅 = (t日收盘 - t-1日收盘) / t-1日收盘 * 100，在2%-7%区间内；
3) 将符合条件的股票代码和5天累计涨幅（保留2位小数）写入 `steady_rise.txt`。

格式：
```
股票代码,5日累计涨幅(%)
300XXX,XX.XX
```

## Expected Behavior

Agent应该：

1. 获取创业板全部股票列表
2. 对每只股票拉取近6个交易日的收盘价（需要前一日作为基准）
3. 计算每日涨幅并判断是否在2%-7%区间
4. 检查5日连续递增
5. 计算5日累计涨幅 = (第5日收盘 / 第0日收盘 - 1) * 100
6. 写入 `steady_rise.txt`，如无符合股票则写入"无符合条件的股票"

## Grading Criteria

- [ ] 文件 `steady_rise.txt` 已创建
- [ ] 文件内容格式正确（代码+涨幅，或明确说明无结果）
- [ ] 股票代码为合法创业板代码（300开头）
- [ ] 累计涨幅数值合理（5天每天2%-7%，累计应在约10%-42%区间）
- [ ] agent在过程中正确计算了逐日涨幅

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "steady_rise.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "rise.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["valid_codes"] = 0.0
        scores["reasonable_values"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    # Allow empty result (no qualifying stocks)
    no_result_phrases = ["无符合", "没有", "no stock", "none", "0只"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
        scores["valid_codes"] = 1.0
        scores["reasonable_values"] = 1.0
        return scores

    lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#") and "代码" not in l]

    records = []
    for line in lines:
        parts = re.split(r'[,\s\t]+', line)
        if len(parts) >= 2:
            code = parts[0].strip()
            try:
                val = float(parts[1].replace('%', ''))
                records.append((code, val))
            except:
                pass

    scores["valid_format"] = 1.0 if len(records) > 0 else 0.0

    valid_codes = [r for r in records if re.match(r'^3\d{5}$', r[0])]
    scores["valid_codes"] = 1.0 if len(valid_codes) == len(records) and len(records) > 0 else (0.5 if len(valid_codes) > 0 else 0.0)

    # Cumulative 5-day return for 2%-7% daily should be roughly 10.4%-40.3%
    valid_vals = [r for r in records if 8.0 <= r[1] <= 45.0]
    scores["reasonable_values"] = 1.0 if len(valid_vals) == len(records) and len(records) > 0 else (0.5 if len(valid_vals) > 0 else 0.0)

    return scores
```
