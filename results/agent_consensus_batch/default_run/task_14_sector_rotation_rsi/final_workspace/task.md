---
id: task_14_sector_rotation_rsi
name: 强势行业超强个股RSI筛选
category: sector_rotation_multi_hop
grading_type: hybrid
timeout_seconds: 480
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files: []
---

## Prompt

完成以下四步行业轮动选股任务：

**第一步**：将创业板股票按行业分组，至少区分：医药、科技/半导体、新能源、消费、其他。

**第二步**：计算截至 2024-06-14 的近20日等权平均涨跌幅，找出涨幅最强的2个行业。

**第三步**：在这2个强势行业内，筛选出个股涨幅超过所在行业均值1.5倍的"超强个股"。

**第四步**：对超强个股计算RSI（14日），返回RSI在40-70之间（未超买但有动量）的股票。

将结果写入 `sector_rotation_result.txt`，格式：
```
强势行业: XXX, XXX
股票代码,行业,个股涨幅(%),RSI
300XXX,新能源,25.3,58.2
```

## Expected Behavior

Agent应该严格按四步执行，每步依赖上一步结果。最终结果需同时满足：
- 所在行业为前2强势行业
- 个股涨幅 > 所在行业均值 * 1.5
- 14日RSI在40-70之间

## Grading Criteria

- [ ] 文件 `sector_rotation_result.txt` 已创建
- [ ] 文件包含强势行业名称（2个）
- [ ] 文件包含代码、行业、涨幅、RSI四个字段
- [ ] RSI值在40-70之间
- [ ] agent进行了行业分类
- [ ] agent计算了行业平均涨幅

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "sector_rotation_result.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["sector_names"] = 0.0
        scores["valid_rsi"] = 0.0
        scores["sector_classified"] = 0.0
        scores["avg_return_computed"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()
    content_lower = content.lower()

    # Check for sector names in output
    sector_keywords = ["医药", "半导体", "科技", "新能源", "消费", "pharma", "semiconductor", "energy", "consumer"]
    has_sectors = sum(1 for kw in sector_keywords if kw in content) >= 2
    scores["sector_names"] = 1.0 if has_sectors else 0.0

    # Check RSI values in range 40-70
    rsi_matches = re.findall(r'\b([3-9]\d\.\d|\d\d\.\d)\b', content)
    valid_rsi = [float(v) for v in rsi_matches if 40 <= float(v) <= 70]
    scores["valid_rsi"] = 1.0 if len(valid_rsi) > 0 else 0.0

    transcript_str = str(transcript).lower()
    scores["sector_classified"] = 1.0 if any(kw in transcript_str for kw in
        ["行业", "sector", "industry", "医药", "新能源", "半导体", "消费"]) else 0.0
    scores["avg_return_computed"] = 1.0 if any(kw in transcript_str for kw in
        ["average", "均值", "mean", "平均涨幅", "行业均值"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 行业分类合理性（Weight: 25%）

**Score 1.0**: 正确将创业板股票分为至少5类（医药、科技/半导体、新能源、消费、其他），分类方法合理（基于行业代码、股票名称或概念板块），覆盖大部分股票。
**Score 0.75**: 分类基本合理，但分类方式较粗糙或某个行业覆盖不准确。
**Score 0.5**: 分类过于简单（只分了2-3类），或有明显误分类。
**Score 0.25**: 分类方法不合理，大量股票被错误分类。
**Score 0.0**: 未进行行业分类。

### Criterion 2: 四步流程的逻辑链条（Weight: 35%）

**Score 1.0**: 四步严格串联执行，强势行业→超强个股→RSI筛选，每步结果正确传入下步，无逻辑断层。
**Score 0.75**: 四步基本完整，但某一步的输出传递有轻微问题（如第三步用了全市场均值而非行业均值）。
**Score 0.5**: 完成了3步，缺少某一个关键步骤或步骤间逻辑有断层。
**Score 0.25**: 仅完成了1-2步，流程大量缺失。
**Score 0.0**: 未按四步逻辑执行。

### Criterion 3: 数值计算准确性（Weight: 25%）

**Score 1.0**: 行业等权均值计算正确（等权=每只股票权重相同），1.5倍阈值应用正确，RSI计算准确（14日Wilder法），40-70区间判断无误。
**Score 0.75**: 大部分计算正确，有1个小错误（如用加权均值替代等权均值）。
**Score 0.5**: 2-3个计算指标有误，但整体思路正确。
**Score 0.25**: 大部分数值计算有错误。
**Score 0.0**: 未进行有效的数值计算。

### Criterion 4: 结果格式与完整性（Weight: 15%）

**Score 1.0**: 结果明确列出2个强势行业名称，股票信息包含代码、行业、涨幅、RSI四个字段，格式清晰可读。
**Score 0.75**: 结果基本完整，缺少1个字段或格式略乱。
**Score 0.5**: 只输出了部分字段。
**Score 0.25**: 文件存在但内容不完整。
**Score 0.0**: 未创建结果文件。
