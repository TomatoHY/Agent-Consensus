---
id: task_06_bollinger_squeeze
name: 布林带盘整股票统计
category: statistical_count
grading_type: automated
timeout_seconds: 240
workspace_files: []
---

## Prompt

统计创业板中截至 2024-08-30 的前30个交易日内，有多少只股票的布林带宽度处于盘整状态。

布林带宽度定义为：（上轨 - 下轨）/ 中轨，当该值 < 5% 时认为处于盘整。

将结果写入 `bollinger_count.txt`，格式：
```
符合条件的股票数量: XXX
占创业板比例: X.XX%
```

## Expected Behavior

Agent应该：

1. 获取创业板全部股票列表
2. 对每只股票获取近30个交易日的收盘价
3. 计算布林带：中轨 = 20日SMA，上轨 = 中轨 + 2*20日标准差，下轨 = 中轨 - 2*20日标准差
4. 计算最新一天的布林带宽度 = (上轨 - 下轨) / 中轨
5. 判断是否 < 5%（0.05）
6. 统计满足条件的股票数量和占比
7. 写入 `bollinger_count.txt`

## Grading Criteria

- [ ] 文件 `bollinger_count.txt` 已创建
- [ ] 文件包含数量数值（正整数）
- [ ] 文件包含占比数值（0-100%之间）
- [ ] agent在过程中计算了布林带
- [ ] 数量和占比比例一致（数量/总数 ≈ 占比）

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "bollinger_count.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "count.txt", "bollinger.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["has_count"] = 0.0
        scores["has_ratio"] = 0.0
        scores["bollinger_computed"] = 0.0
        scores["consistency"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text()

    # Extract count (positive integer)
    count_match = re.search(r'(\d+)', content)
    if count_match:
        count = int(count_match.group(1))
        scores["has_count"] = 1.0 if count >= 0 else 0.0
    else:
        count = None
        scores["has_count"] = 0.0

    # Extract ratio
    ratio_match = re.search(r'(\d+\.?\d*)\s*%', content)
    if ratio_match:
        ratio = float(ratio_match.group(1))
        scores["has_ratio"] = 1.0 if 0 <= ratio <= 100 else 0.0
    else:
        ratio = None
        scores["has_ratio"] = 0.0

    # Bollinger computed
    transcript_str = str(transcript).lower()
    scores["bollinger_computed"] = 1.0 if any(kw in transcript_str for kw in ["bollinger", "布林", "boll", "upper.*lower", "std"]) else 0.0

    # Consistency check: count/total_gem ≈ ratio
    # GEM has roughly 1200-1400 stocks
    if count is not None and ratio is not None and count > 0:
        implied_total = count / (ratio / 100) if ratio > 0 else 0
        scores["consistency"] = 1.0 if 800 <= implied_total <= 2000 else 0.5
    else:
        scores["consistency"] = 0.0

    return scores
```
