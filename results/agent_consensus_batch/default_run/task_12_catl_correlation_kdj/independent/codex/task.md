---
id: task_12_catl_correlation_kdj
name: 宁德时代高相关股KDJ金叉筛选
category: multi_hop_correlation_signal
grading_type: hybrid
timeout_seconds: 480
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files: []
---

## Prompt

完成以下两阶段选股任务：

**第一阶段**：
1. 获取宁德时代（300750）截至 2024-04-15 的前30个交易日日收益率序列；
2. 遍历创业板股票，计算每只股票与宁德时代的30日收益率Pearson相关系数（排除300750本身）；
3. 找出相关系数最高的10只股票（要求相关系数 > 0.8）。

**第二阶段**：
4. 对第一阶段找出的10只高相关股票，检查截至 2024-04-15 的最后5个交易日内是否出现KDJ金叉（K线上穿D线）；
5. 返回同时满足：相关系数>0.8 **且** 截至 2024-04-15 的最后5日出现KDJ金叉的股票。

将结果写入 `corr_kdj_result.txt`，格式：
```
股票代码,相关系数,KDJ金叉日期
300XXX,0.8523,2024-01-12
```

## Expected Behavior

Agent应该：
1. 获取300750的30日收益率
2. 批量计算各股与300750的相关系数
3. 筛选出相关系数>0.8的前10只（若不足10只则取全部）
4. 对这些股票单独计算KDJ（参数K=9, D=3, J=3*K-2*D）
5. 检测近5日K上穿D的金叉
6. 输出同时满足两个条件的股票

## Grading Criteria

- [ ] 文件 `corr_kdj_result.txt` 已创建
- [ ] 文件包含代码、相关系数、日期格式
- [ ] 相关系数值在0.8到1.0之间
- [ ] agent先进行了相关性计算再做KDJ计算（两阶段）
- [ ] agent明确筛选了相关系数>0.8的股票

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "corr_kdj_result.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["high_correlation"] = 0.0
        scores["two_stage_logic"] = 0.0
        scores["kdj_computed"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "no stock", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
        scores["high_correlation"] = 1.0
        scores["two_stage_logic"] = 0.5
        transcript_str = str(transcript).lower()
        scores["kdj_computed"] = 1.0 if "kdj" in transcript_str else 0.0
        return scores

    lines = [l.strip() for l in content.splitlines()
             if l.strip() and not l.startswith("#") and "代码" not in l]

    records = []
    for line in lines:
        parts = re.split(r'[,\s\t]+', line)
        if len(parts) >= 3:
            code = parts[0].strip()
            try:
                corr = float(parts[1])
                records.append((code, corr))
            except:
                pass

    has_code = any(re.match(r'^3\d{5}$', r[0]) for r in records)
    has_date = bool(re.search(r'\d{4}-\d{2}-\d{2}', content))
    scores["valid_format"] = 1.0 if (has_code and has_date) else (0.5 if has_code else 0.0)

    high_corr = [r for r in records if r[1] > 0.8]
    scores["high_correlation"] = 1.0 if len(high_corr) == len(records) and len(records) > 0 else (0.5 if len(high_corr) > 0 else 0.0)

    transcript_str = str(transcript).lower()
    has_corr = any(kw in transcript_str for kw in ["correlation", "相关", "pearson", "corr"])
    scores["two_stage_logic"] = 1.0 if (has_corr and "kdj" in transcript_str) else (0.5 if has_corr else 0.0)
    scores["kdj_computed"] = 1.0 if "kdj" in transcript_str else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 相关性计算方法（Weight: 30%）

**Score 1.0**: 正确计算日收益率（对数收益或算术收益均可），使用Pearson相关系数，日期正确对齐（同一交易日），处理了缺失值或停牌情况。
**Score 0.75**: 相关性计算基本正确，但未处理缺失值或日期对齐略有问题。
**Score 0.5**: 用了价格序列而非收益率序列计算相关性（伪相关）。
**Score 0.25**: 相关性计算方法有根本性错误。
**Score 0.0**: 未计算相关性。

### Criterion 2: KDJ指标计算与金叉检测（Weight: 35%）

**Score 1.0**: KDJ按标准随机指标公式计算（RSV→K→D），参数9/3，K上穿D的金叉检测逻辑正确，仅检测近5日内金叉。
**Score 0.75**: KDJ计算基本正确，金叉检测逻辑有小瑕疵（如检测范围略宽/窄）。
**Score 0.5**: KDJ计算有误或未检测具体金叉日期（仅判断K>D）。
**Score 0.25**: KDJ计算存在明显公式错误。
**Score 0.0**: 未计算KDJ。

### Criterion 3: 两阶段流程执行质量（Weight: 35%）

**Score 1.0**: 明确的两阶段执行：先获取相关性TOP10，再对这10只做KDJ，最终取交集，流程清晰且每步都正确使用上步结果。
**Score 0.75**: 两阶段基本执行，但第二阶段可能多做了一些不必要的股票。
**Score 0.5**: 两阶段逻辑存在，但未严格以第一阶段结果作为第二阶段输入（如直接对全市场算KDJ）。
**Score 0.25**: 仅完成了一个阶段。
**Score 0.0**: 未按两阶段逻辑执行。
