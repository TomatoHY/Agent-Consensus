---
id: task_30_composite_scoring
name: 量价综合评分模型选股
category: composite_scoring_model
grading_type: hybrid
timeout_seconds: 480
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files: []
---

## Prompt

设计量价强度综合评分模型，对创业板股票进行打分和筛选：

**评分规则**（总分100分）：

- **价格强度**（40分）：计算截至 2024-12-09 的近20日涨幅，在全创业板中的百分位排名 × 40；
- **量能强度**（30分）：计算（截至 2024-12-09 的近20日换手率均值 / 近60日换手率均值），在全创业板中的百分位排名 × 30；
- **趋势强度**（20分）：计算ADX指标（14日），ADX值/100 × 20；
- **资金强度**（10分）：计算截至 2024-12-09 的近5日大单净流入占成交额比例（若无数据用成交量增减率代理），在全创业板中的百分位排名 × 10。

**筛选条件**：综合得分 > 75，PE < 60 且 PE > 0，排除ST股票。

按综合得分排序，取前15只，写入 `composite_score.txt`，格式：
```
股票代码,价格强度分,量能强度分,趋势强度分,资金强度分,总分,PE
300XXX,36.5,25.2,14.8,8.1,84.6,32.5
```

## Expected Behavior

Agent应该：
1. 计算全市场的20日涨幅分布，对每只股票求百分位排名
2. 计算换手率比值的全市场百分位排名
3. 计算ADX（需要DI+和DI-的计算，参数14日）
4. 计算资金强度（或代理指标）
5. 合并四个维度的得分，筛选总分>75
6. 过滤PE和ST条件后排序取前15

## Grading Criteria

- [ ] 文件 `composite_score.txt` 已创建
- [ ] 最多15条记录
- [ ] 总分值在75-100之间（筛选条件）
- [ ] agent计算了ADX指标（或有明确的趋势强度计算）
- [ ] agent使用了百分位排名归一化
- [ ] agent过滤了PE和ST条件

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "composite_score.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "score.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["count_limit"] = 0.0
        scores["total_score_valid"] = 0.0
        scores["adx_computed"] = 0.0
        scores["percentile_used"] = 0.0
        scores["pe_filtered"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["count_limit"] = 1.0
        scores["total_score_valid"] = 1.0
    else:
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l]
        scores["count_limit"] = 1.0 if len(lines) <= 15 else 0.5

        total_scores = re.findall(r'\b([7-9]\d\.\d|100\.0)\b', content)
        valid_scores = [float(s) for s in total_scores if 75 <= float(s) <= 100]
        scores["total_score_valid"] = 1.0 if len(valid_scores) > 0 else 0.0

    transcript_str = str(transcript).lower()
    scores["adx_computed"] = 1.0 if any(kw in transcript_str for kw in
        ["adx", "average directional", "方向指数", "di+", "di-"]) else 0.0
    scores["percentile_used"] = 1.0 if any(kw in transcript_str for kw in
        ["percentile", "分位", "rank", "百分位", "rankdata"]) else 0.0
    scores["pe_filtered"] = 1.0 if any(kw in transcript_str for kw in
        ["pe", "市盈率", "st"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 评分模型设计合理性（Weight: 30%）

**Score 1.0**: 四个维度的百分位排名归一化方法正确（用全市场分布而非固定区间），权重（40/30/20/10）正确应用，总分0-100的设计合理，ADX计算完整（包含DI+/DI-）。
**Score 0.75**: 模型设计基本正确，ADX计算有简化（如只用ATR近似），或百分位归一化有轻微偏差。
**Score 0.5**: 实现了2-3个维度，其他维度用简化方法，但加权框架正确。
**Score 0.25**: 评分模型设计有根本性错误（如直接用原始值加权而非百分位）。
**Score 0.0**: 未设计综合评分模型。

### Criterion 2: 各维度指标计算技术准确性（Weight: 35%）

**Score 1.0**: 20日涨幅（准确定义）、换手率比值、ADX（Wilder法，包含DI+/DI-）、资金强度（或合理代理）四个指标均正确计算，无明显公式错误。
**Score 0.75**: 3个指标计算准确，ADX有轻微近似。
**Score 0.5**: 2个指标正确，ADX未实现而用其他趋势指标代替（需合理说明）。
**Score 0.25**: 多数指标计算有明显错误。
**Score 0.0**: 指标计算整体不可信。

### Criterion 3: 筛选与排序（Weight: 35%）

**Score 1.0**: 总分>75、PE在0-60之间、排除ST（名称含ST或*ST的股票）三个条件全部正确实现，按总分降序排列，前15名选取准确。
**Score 0.75**: 两个筛选条件正确，ST过滤有遗漏（如只过滤ST不过滤*ST）。
**Score 0.5**: 只实现了总分筛选，PE和ST过滤有缺失。
**Score 0.25**: 筛选条件有多处遗漏或错误。
**Score 0.0**: 未实现筛选和排序。
