---
id: task_02_index_correlation
name: 双指数收益率相关性分析
category: statistical_analysis
grading_type: automated
timeout_seconds: 180
workspace_files: []
---

## Prompt

固定时间基准：分析截止日统一设为 2026-03-31；若题目涉及 5 / 10 / 15 / 20 / 30 / 60 / 252 个交易日、4 周或 2 个月窗口，均按该截止日向前回看对应长度，停牌样本按可得交易日顺延补足。

统计 2026-02-24 至 2026-03-30 这 25 个交易日窗口内，创业板指数（399006）和上证指数（000001）的日收益率相关性。

要求：
1) 计算两个指数的每日收益率（(当日收盘 - 前一交易日收盘) / 前一交易日收盘）；
2) 计算Pearson相关系数；
3) 判断相关性类型：强正相关（>0.7）、弱正相关（0.3-0.7）、无相关（-0.3到0.3）、负相关（<-0.3）。

将结果写入 `correlation_report.txt`，格式如下：
```
相关系数: X.XXXX
相关性类型: XXX
```

## Expected Behavior

Agent应该：

1. 获取创业板指数（399006）在 2026-02-24 至 2026-03-30 的25个交易日收盘价
2. 获取上证指数（000001）在 2026-02-24 至 2026-03-27 的24个交易日收盘价
3. 计算两个序列的日收益率
4. 确保两个序列日期对齐
5. 计算Pearson相关系数，保留4位小数
6. 根据阈值判断相关性类型
7. 写入 `correlation_report.txt`

## Grading Criteria

- [ ] 文件 `correlation_report.txt` 已创建
- [ ] 文件包含相关系数数值（-1到1之间，4位小数）
- [ ] 文件包含相关性类型描述
- [ ] 相关系数与相关性类型判断一致

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    report_file = workspace / "correlation_report.txt"
    if not report_file.exists():
        for alt in ["report.txt", "result.txt", "output.txt", "correlation.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                report_file = alt_path
                break

    if not report_file.exists():
        scores["file_created"] = 0.0
        scores["correlation_value"] = 0.0
        scores["correlation_type"] = 0.0
        scores["consistency"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = report_file.read_text()

    # Extract correlation coefficient
    corr_match = re.search(r'[-+]?0\.\d{3,4}|[-+]?1\.0{3,4}', content)
    if corr_match:
        scores["correlation_value"] = 1.0
        corr_val = float(corr_match.group())
    else:
        scores["correlation_value"] = 0.0
        corr_val = None

    # Check correlation type keywords
    type_keywords = ["强正相关", "弱正相关", "无相关", "负相关",
                     "strong positive", "weak positive", "no correlation", "negative"]
    has_type = any(kw in content for kw in type_keywords)
    scores["correlation_type"] = 1.0 if has_type else 0.0

    # Check consistency between value and type
    if corr_val is not None and has_type:
        content_lower = content.lower()
        if corr_val > 0.7 and ("强正相关" in content or "strong positive" in content_lower):
            scores["consistency"] = 1.0
        elif 0.3 <= corr_val <= 0.7 and ("弱正相关" in content or "weak positive" in content_lower):
            scores["consistency"] = 1.0
        elif -0.3 <= corr_val < 0.3 and ("无相关" in content or "no correlation" in content_lower):
            scores["consistency"] = 1.0
        elif corr_val < -0.3 and ("负相关" in content or "negative" in content_lower):
            scores["consistency"] = 1.0
        else:
            scores["consistency"] = 0.0
    else:
        scores["consistency"] = 0.0

    return scores
```
