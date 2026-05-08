---
id: task_20_ultimate_multi_condition
name: 五维度综合评分超级选股
category: ultimate_multi_condition_multi_hop
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files: []
---

## Prompt

在创业板中找出同时满足以下**所有条件**的股票（五维度综合筛选）：

**维度1（行业趋势）**：所属行业（医药/新能源/半导体/消费电子之一）截至 2024-12-13 的近20日行业等权指数涨幅 > 5%。

**维度2（个股超越行业）**：个股近20日涨幅 > 所属行业指数涨幅 × 1.3倍。

**维度3（技术指标三项）**：
- 价格在20日和60日均线上方；
- MACD柱状图（histogram）近5日持续为正且递增；
- RSI在50-70之间。

**维度4（量能与K线质量）**：
- 近10日中至少6日收盘价高于开盘价（阳线为主）；
- 近10日成交量均值 > 60日成交量均值。

**维度5（基本面）**：PE > 0 且 PE < 100。

对每只满足条件的股票，计算综合得分 = 各条件满足程度的加权分（自行设计合理的评分逻辑），将结果按综合得分从高到低排序，写入 `ultimate_filter.txt`，格式：
```
股票代码,所属行业,行业涨幅(%),个股涨幅(%),RSI,阳线天数,量能比,PE,综合得分
300XXX,新能源,8.5,12.3,62.1,7,1.35,45.2,88.5
```

## Expected Behavior

Agent应该：
1. 行业分类并计算各行业指数涨幅
2. 对每个强势行业内的个股分别验证五个维度
3. 设计并实现综合评分模型
4. 按得分排序输出全部满足条件的股票

## Grading Criteria

- [ ] 文件 `ultimate_filter.txt` 已创建
- [ ] 包含行业名称字段
- [ ] 包含RSI值（且在50-70范围内）
- [ ] 包含综合得分字段
- [ ] agent完成了MACD、RSI等多个技术指标计算
- [ ] agent检查了PE基本面条件
- [ ] agent设计了综合评分逻辑

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "ultimate_filter.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "filter.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["has_sector"] = 0.0
        scores["valid_rsi"] = 0.0
        scores["has_score"] = 0.0
        scores["multi_indicator"] = 0.0
        scores["pe_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none", "0只"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["has_sector"] = 1.0
        scores["valid_rsi"] = 1.0
        scores["has_score"] = 1.0
    else:
        sector_kws = ["医药", "新能源", "半导体", "消费电子"]
        scores["has_sector"] = 1.0 if any(kw in content for kw in sector_kws) else 0.0

        rsi_matches = re.findall(r'\b([4-7]\d\.\d)\b', content)
        valid_rsi = [float(v) for v in rsi_matches if 50 <= float(v) <= 70]
        scores["valid_rsi"] = 1.0 if len(valid_rsi) > 0 else 0.0

        scores["has_score"] = 1.0 if bool(re.search(r'得分|score|综合', content, re.IGNORECASE)) else 0.0

    transcript_str = str(transcript).lower()
    indicator_count = sum(1 for kw in ["macd", "rsi", "均线", "bollinger", "kdj", "ma60", "ma20"]
                          if kw in transcript_str)
    scores["multi_indicator"] = 1.0 if indicator_count >= 3 else (0.5 if indicator_count >= 2 else 0.0)
    scores["pe_checked"] = 1.0 if any(kw in transcript_str for kw in ["pe", "市盈率", "price.*earn"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 五个维度的完整实现（Weight: 35%）

**Score 1.0**: 所有5个维度条件均正确实现，无遗漏：行业趋势判断、个股超越行业、三项技术指标、量能K线条件、PE基本面。
**Score 0.75**: 实现了4个维度，1个维度有轻微遗漏（如MACD柱状图递增未检查，只检查了正值）。
**Score 0.5**: 实现了3个维度，缺失或有明显错误。
**Score 0.25**: 仅实现了1-2个维度。
**Score 0.0**: 未实现多维度筛选。

### Criterion 2: 行业维度处理准确性（Weight: 20%）

**Score 1.0**: 正确将股票分到医药/新能源/半导体/消费电子四个行业，计算了等权行业涨幅（不是市值加权），只对涨幅>5%的行业内股票进行后续筛选。
**Score 0.75**: 行业分类基本正确，行业涨幅计算方法略有差异（如用少量样本代表）。
**Score 0.5**: 行业分类过于粗糙，或行业涨幅用了非等权方法。
**Score 0.25**: 行业维度有重大错误。
**Score 0.0**: 未进行行业维度处理。

### Criterion 3: 综合评分模型设计（Weight: 25%）

**Score 1.0**: 设计了合理的综合评分模型（各维度赋予不同权重，或用各条件满足程度打分），评分逻辑有合理的经济含义，结果按分数正确排序。
**Score 0.75**: 评分模型有合理设计，但权重设置略显随意，排序正确。
**Score 0.5**: 设计了简单的评分（如满足条件数计数），逻辑简单但有效。
**Score 0.25**: 评分模型设计有明显缺陷（如所有条件等权但某些条件明显更重要）。
**Score 0.0**: 未设计评分模型，仅做了二元筛选。

### Criterion 4: 结果输出完整性（Weight: 20%）

**Score 1.0**: 输出包含所有9个字段，格式清晰，数值在合理范围内，综合得分与各指标一致。
**Score 0.75**: 缺少1-2个字段，但核心字段（代码、行业、得分）存在。
**Score 0.5**: 只有部分字段，可读性差。
**Score 0.25**: 文件存在但内容残缺。
**Score 0.0**: 未创建结果文件。
