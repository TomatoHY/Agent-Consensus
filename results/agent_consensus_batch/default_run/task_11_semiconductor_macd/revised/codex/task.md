---
id: task_11_semiconductor_macd
name: 半导体板块MACD金叉选股
category: multi_hop_sector_technical
grading_type: hybrid
timeout_seconds: 480
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files: []
---

## Prompt

完成以下多步骤选股任务：

**第一步**：获取创业板指数（399006）的成分股列表。

**第二步**：从成分股中筛选属于半导体或芯片行业的股票（通过股票名称包含"半导体"、"芯片"、"微电子"、"集成电路"等关键词，或行业分类属于半导体）。

**第三步**：对筛选出的半导体股票，计算截至 2024-03-15 的前20个交易日MACD指标，找出MACD金叉（DIFF上穿DEA）发生在其中最后5个交易日内的股票。

**第四步**：对满足第三步条件的股票，按截至 2024-03-15 的20日累计涨幅（(截止日收盘 - 20日前收盘) / 20日前收盘 * 100）从大到小排序，取前5只。

将结果写入 `semiconductor_top5.txt`，格式：
```
股票代码,股票名称,金叉日期,近20日涨幅(%)
300XXX,XXX半导体,2024-01-10,15.23
```

## Expected Behavior

Agent应该按照四步流程依次执行，每步结果作为下一步输入：
1. 调用工具获取399006的成分股列表
2. 用关键词或行业分类过滤半导体相关股票
3. 批量计算MACD，检测近5日内金叉
4. 计算20日涨幅并排序取前5

## Grading Criteria

- [ ] 文件 `semiconductor_top5.txt` 已创建
- [ ] 记录不超过5条
- [ ] 包含股票代码、名称、金叉日期、涨幅四个字段
- [ ] agent进行了指数成分股查询
- [ ] agent进行了行业/关键词筛选
- [ ] agent计算了MACD并检测金叉日期
- [ ] 金叉日期在最近5个交易日内

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re
    from datetime import datetime, timedelta

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "semiconductor_top5.txt"
    if not result_file.exists():
        for alt in ["top5.txt", "result.txt", "output.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["index_queried"] = 0.0
        scores["sector_filtered"] = 0.0
        scores["macd_computed"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "no stock", "none", "0只"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
    else:
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l]
        has_code = any(re.search(r'3\d{5}', l) for l in lines)
        has_date = any(re.search(r'\d{4}-\d{2}-\d{2}', l) for l in lines)
        has_pct = any(re.search(r'\d+\.\d+', l) for l in lines)
        scores["valid_format"] = 1.0 if (has_code and has_date and has_pct) else (0.5 if has_code else 0.0)

    transcript_str = str(transcript).lower()
    scores["index_queried"] = 1.0 if any(kw in transcript_str for kw in ["399006", "成分股", "constituent", "index"]) else 0.0
    scores["sector_filtered"] = 1.0 if any(kw in transcript_str for kw in ["半导体", "芯片", "semiconductor", "chip", "集成电路"]) else 0.0
    scores["macd_computed"] = 1.0 if "macd" in transcript_str else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 多步骤执行逻辑与依赖性（Weight: 35%）

**Score 1.0**: 严格按四步顺序执行，每步结果正确传递给下一步，无跳步或步骤颠倒，整体流程完整。
**Score 0.75**: 四步基本完整，但某一步的输出传递略有问题，如未完整使用上步的筛选结果。
**Score 0.5**: 完成了3步，缺失了某一步（如跳过了排序步骤）。
**Score 0.25**: 仅完成了1-2步，流程未完整执行。
**Score 0.0**: 未按多步骤逻辑执行。

### Criterion 2: 行业筛选准确性（Weight: 25%）

**Score 1.0**: 正确识别了半导体/芯片相关股票，筛选方法合理（名称关键词或行业分类），无明显的行业误判（如把医疗电子误认为芯片）。
**Score 0.75**: 行业筛选基本正确，可能遗漏少量相关股票或误纳入少量无关股票。
**Score 0.5**: 筛选方法过于宽泛或严格，导致结果偏差明显。
**Score 0.25**: 行业筛选逻辑混乱，大量误分类。
**Score 0.0**: 未进行行业筛选。

### Criterion 3: MACD金叉检测与涨幅排序（Weight: 40%）

**Score 1.0**: MACD金叉正确检测（包括具体发生日期），仅保留近5日内金叉，涨幅计算公式正确，前5名排序准确。
**Score 0.75**: 金叉检测正确但日期精度略差，或涨幅计算基准日有1-2天偏差。
**Score 0.5**: 金叉检测有误（如误用收盘价判断），或排序未按涨幅排序。
**Score 0.25**: MACD计算有多处错误，结果可信度低。
**Score 0.0**: 未计算MACD或未进行排序。
