---
id: task_03_volatility_ranking
name: 创业板波动率排名
category: ranking
grading_type: automated
timeout_seconds: 240
workspace_files: []
---

## Prompt

在创业板中找出以 2024-05-31 为截止交易日的前10个交易日内波动率最大的5只股票。

波动率定义为：截至 2024-05-31 的前10日收盘价的标准差除以均值（变异系数）。

将结果写入 `volatility_top5.txt`，格式如下（按波动率从大到小排序）：
```
股票代码,波动率(%)
300XXX,X.XX
300XXX,X.XX
...
```

## Expected Behavior

Agent应该：

1. 获取创业板全部或大量股票列表
2. 对每只股票拉取近10个交易日的收盘价
3. 计算每只股票的波动率 = std(收盘价) / mean(收盘价) * 100%
4. 对所有股票按波动率降序排序
5. 取前5名，写入 `volatility_top5.txt`
6. 波动率保留2位小数

## Grading Criteria

- [ ] 文件 `volatility_top5.txt` 已创建
- [ ] 文件包含恰好5条记录
- [ ] 所有股票代码为合法创业板代码（300开头）
- [ ] 波动率数值为正数且格式合理（0-100之间的百分比）
- [ ] 记录按波动率降序排列

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "volatility_top5.txt"
    if not result_file.exists():
        for alt in ["top5.txt", "result.txt", "output.txt", "volatility.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["five_records"] = 0.0
        scores["valid_codes"] = 0.0
        scores["valid_values"] = 0.0
        scores["sorted_desc"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()
    lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#") and not l.startswith("股票")]

    scores["five_records"] = 1.0 if len(lines) == 5 else (0.5 if 3 <= len(lines) <= 7 else 0.0)

    # Extract codes and values
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

    # Valid GEM codes
    valid = [r for r in records if re.match(r'^3\d{5}$', r[0])]
    scores["valid_codes"] = 1.0 if len(valid) >= 3 else (0.5 if len(valid) >= 1 else 0.0)

    # Valid volatility values (0-100)
    valid_vals = [r for r in records if 0 < r[1] < 100]
    scores["valid_values"] = 1.0 if len(valid_vals) >= 3 else (0.5 if len(valid_vals) >= 1 else 0.0)

    # Check descending order
    if len(records) >= 2:
        vals = [r[1] for r in records]
        scores["sorted_desc"] = 1.0 if all(vals[i] >= vals[i+1] for i in range(len(vals)-1)) else 0.0
    else:
        scores["sorted_desc"] = 0.0

    return scores
```
