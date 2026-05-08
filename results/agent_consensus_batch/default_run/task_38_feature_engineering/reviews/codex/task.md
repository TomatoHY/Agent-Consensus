---
id: task_38_feature_engineering
name: 技术特征向量与Spearman相关性分析
category: feature_engineering
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files: []
---

## Prompt

构建多维技术特征向量并进行预测性分析：

**第一步（特征计算）**：对创业板股票计算以下至少10个技术特征（取截至 2024-10-22 的最近20日末尾值）：
MACD DIFF值、MACD histogram、RSI14、KDJ_K值、KDJ_D值、布林带位置（(收盘-下轨)/(上轨-下轨)）、ATR14、OBV相对强度（截至 2024-10-22 的OBV/20日均值）、威廉指标Williams%R14、CCI14、20日均线偏离度、5日/20日均量比。

**第二步（相关性分析）**：计算近20日时间窗口内，每个特征值（取每日的特征值）与未来5日收益率（以5日后的收盘价计算）的Spearman相关系数。

**第三步（有效特征筛选）**：找出至少10个特征的Spearman相关系数 > 0.3（与未来收益正相关）的股票。

**第四步（综合信号）**：对筛选出的股票，将截至 2024-10-22 的所有特征值标准化（z-score）后求和，得综合信号强度，取信号最强的10只股票。

将结果写入 `feature_signal.txt`，格式：
```
股票代码,有效特征数量,综合信号强度
300XXX,12,8.53
```

## Expected Behavior

Agent应该：
1. 计算至少10个技术特征
2. 对每只股票计算特征序列与未来收益率的Spearman相关系数
3. 筛选有效特征数≥10的股票
4. 对这些股票计算z-score标准化后的综合信号
5. 输出前10名

## Grading Criteria

- [ ] 文件 `feature_signal.txt` 已创建
- [ ] 包含有效特征数量（应≥10）
- [ ] 包含综合信号强度
- [ ] agent计算了至少8个不同的技术指标
- [ ] agent使用了Spearman相关系数
- [ ] agent进行了标准化处理

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "feature_signal.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "signal.txt", "feature.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["feature_count_valid"] = 0.0
        scores["signal_present"] = 0.0
        scores["indicator_coverage"] = 0.0
        scores["spearman_used"] = 0.0
        scores["normalization_used"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["feature_count_valid"] = 1.0
        scores["signal_present"] = 1.0
    else:
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l]
        records = []
        for line in lines:
            parts = re.split(r'[,\s\t]+', line)
            if len(parts) >= 3:
                try:
                    feat_count = int(parts[1])
                    signal = float(parts[2])
                    records.append((feat_count, signal))
                except:
                    pass

        valid_count = [r for r in records if r[0] >= 10]
        scores["feature_count_valid"] = 1.0 if len(valid_count) > 0 else (0.5 if len(records) > 0 else 0.0)
        scores["signal_present"] = 1.0 if len(records) > 0 else 0.0

    transcript_str = str(transcript).lower()
    indicator_kws = ["macd", "rsi", "kdj", "bollinger", "atr", "obv", "williams", "cci", "偏离度", "均量比"]
    indicator_count = sum(1 for kw in indicator_kws if kw in transcript_str)
    scores["indicator_coverage"] = 1.0 if indicator_count >= 7 else (0.5 if indicator_count >= 4 else 0.0)

    scores["spearman_used"] = 1.0 if any(kw in transcript_str for kw in
        ["spearman", "rank.*corr", "斯皮尔曼", "spearmanr"]) else 0.0
    scores["normalization_used"] = 1.0 if any(kw in transcript_str for kw in
        ["zscore", "z-score", "standardize", "标准化", "normalize", "(x-mean)/std"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 技术特征计算完整性（Weight: 30%）

**Score 1.0**: 计算了至少10个不同类型的技术特征，涵盖趋势（MACD/均线偏离）、震荡（RSI/KDJ/Williams/CCI）、波动（布林带位置/ATR）、量能（OBV/均量比）四大类，计算准确。
**Score 0.75**: 计算了8-9个特征，覆盖了3类以上，计算基本正确。
**Score 0.5**: 计算了5-7个特征，以常见指标为主，较少覆盖量能或波动类。
**Score 0.25**: 只计算了3-4个特征，覆盖面极窄。
**Score 0.0**: 未计算技术特征。

### Criterion 2: Spearman相关性分析方法（Weight: 35%）

**Score 1.0**: 正确使用Spearman相关系数（而非Pearson），时间对齐方式正确（特征日期对应未来第5日收益率），20日时间窗口内有足够样本点（至少10-15个观测），相关系数计算库使用正确（如scipy.stats.spearmanr）。
**Score 0.75**: Spearman相关系数使用正确，但时间对齐有轻微偏差（如未来5日用了对数收益而非算术收益），整体思路正确。
**Score 0.5**: 用了Pearson相关系数代替Spearman，但其他流程正确。
**Score 0.25**: 相关性分析方法有根本性错误（如用价格序列而非收益率）。
**Score 0.0**: 未进行相关性分析。

### Criterion 3: 特征筛选与综合评分（Weight: 35%）

**Score 1.0**: 有效特征筛选阈值（Spearman>0.3）正确应用，z-score标准化公式正确（(x-μ)/σ），综合信号为z-score之和（非加权和），前10名按信号强度正确排序。
**Score 0.75**: 筛选和评分基本正确，z-score用了归一化（0-1范围）替代标准化，但思路合理。
**Score 0.5**: 只完成了筛选阶段，综合信号的标准化步骤有缺失或错误。
**Score 0.25**: 有效特征筛选有明显错误，综合信号未正确实现。
**Score 0.0**: 未实现特征筛选和综合评分。
