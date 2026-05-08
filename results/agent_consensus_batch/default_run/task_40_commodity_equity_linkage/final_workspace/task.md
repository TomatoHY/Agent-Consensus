---
id: task_40_commodity_equity_linkage
name: 碳酸锂期货与锂电股联动套利机会
category: commodity_equity_linkage
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files: []
---

## Prompt

识别期货-现货联动套利机会：

**第一步（期货数据）**：获取碳酸锂主力期货合约（LC主力，或使用其他可用的锂相关期货，若无法获取则用碳酸锂现货价格指数）截至 2024-12-23 的近20日价格，计算涨幅。

**第二步（相关个股识别）**：在创业板中筛选锂电池相关股票，识别标准：股票名称或行业分类含"锂"、"锂电"、"电池"、"电解液"、"正极"、"负极"、"隔膜"等关键词。

**第三步（历史相关性计算）**：计算这些股票近60日收益率与期货价格近60日收益率的Pearson相关系数，筛选历史相关系数 > 0.7 的股票。

**第四步（价差识别）**：对高相关性股票，判断是否存在"期货涨幅>10%但股票涨幅<5%"的价差（滞涨机会）。

**第五步（启动信号）**：对存在价差的股票，检查技术面启动信号：MACD金叉（截至 2024-12-23 的最近10日）或成交量放大（近5日均量>20日均量×1.5倍）。

将结果写入 `commodity_linkage.txt`，格式：
```
期货近20日涨幅: XX.XX%

股票代码,历史相关系数,期货涨幅(%),股票涨幅(%),滞涨差(%),启动信号
300XXX,0.82,15.3,3.2,12.1,MACD金叉
```

## Expected Behavior

Agent应该：
1. 获取碳酸锂期货（或替代品）数据
2. 识别创业板中的锂电池相关股票
3. 计算历史相关性并筛选高相关股
4. 判断价差
5. 检测技术启动信号
6. 输出格式化报告

## Grading Criteria

- [ ] 文件 `commodity_linkage.txt` 已创建
- [ ] 文件包含期货涨幅字段
- [ ] 历史相关系数 > 0.7
- [ ] 滞涨差 > 0（期货涨幅 > 股票涨幅）
- [ ] agent尝试了期货或锂价格数据获取
- [ ] agent识别了锂电池相关股票关键词

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "commodity_linkage.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "linkage.txt", "commodity.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["futures_return_present"] = 0.0
        scores["correlation_valid"] = 0.0
        scores["laggard_gap_positive"] = 0.0
        scores["futures_data_attempted"] = 0.0
        scores["lithium_keywords"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text()

    scores["futures_return_present"] = 1.0 if bool(re.search(r'期货.*涨幅|futures.*return', content, re.IGNORECASE)) else 0.0

    corr_matches = re.findall(r'0\.\d{2,}', content)
    valid_corr = [float(c) for c in corr_matches if float(c) > 0.7]
    scores["correlation_valid"] = 1.0 if len(valid_corr) > 0 else 0.0

    no_result_phrases = ["无符合", "没有", "none", "无价差"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["laggard_gap_positive"] = 1.0
    else:
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l and "期货" not in l]
        records = []
        for line in lines:
            parts = re.split(r'[,\s\t]+', line)
            if len(parts) >= 6:
                try:
                    futures_ret = float(parts[2].replace('%', ''))
                    stock_ret = float(parts[3].replace('%', ''))
                    gap = float(parts[4].replace('%', ''))
                    records.append((futures_ret, stock_ret, gap))
                except:
                    pass
        valid_gap = [r for r in records if r[2] > 0 and r[0] > r[1]]
        scores["laggard_gap_positive"] = 1.0 if len(valid_gap) > 0 else (0.5 if len(records) > 0 else 0.0)

    transcript_str = str(transcript).lower()
    scores["futures_data_attempted"] = 1.0 if any(kw in transcript_str for kw in
        ["期货", "futures", "碳酸锂", "lc", "lithium.*carbonate", "现货价格"]) else 0.0
    scores["lithium_keywords"] = 1.0 if any(kw in transcript_str for kw in
        ["锂", "电池", "lithium", "battery", "正极", "负极", "电解液", "隔膜"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 期货数据获取与处理（Weight: 25%）

**Score 1.0**: 成功获取碳酸锂期货或现货价格数据，数据来源合理，20日涨幅计算准确，明确说明了所用数据的来源和代码。
**Score 0.75**: 获取了近似期货数据（如用相关ETF或指数），方法合理但有局限性，有说明。
**Score 0.5**: 未能获取期货数据，但提出了合理的替代方案（如使用供应商价格指数），并说明了替代方案的局限性。
**Score 0.25**: 期货数据获取有明显问题，替代方案不合理。
**Score 0.0**: 完全未获取任何期货或商品价格数据。

### Criterion 2: 锂电板块识别与相关性计算（Weight: 35%）

**Score 1.0**: 关键词筛选覆盖了6类以上的锂电池产业链环节，历史相关性计算方法正确（60日收益率，Pearson相关系数），阈值0.7正确应用，数据对齐处理合理。
**Score 0.75**: 锂电池识别覆盖了3-5类，相关性计算基本正确，但数据对齐有轻微偏差。
**Score 0.5**: 只识别了锂电池核心股（如"锂"关键词），产业链覆盖不全，相关性计算基本正确。
**Score 0.25**: 锂电识别或相关性计算有明显错误。
**Score 0.0**: 未实现锂电识别和相关性计算。

### Criterion 3: 价差识别与启动信号（Weight: 40%）

**Score 1.0**: 价差条件（期货涨幅>10%且股票涨幅<5%）正确应用，MACD金叉和成交量放大两种启动信号均有检测，结果输出格式完整，启动信号字段清晰标注类型。
**Score 0.75**: 价差识别正确，启动信号只检测了其中一种（MACD金叉或成交量），输出基本完整。
**Score 0.5**: 价差识别有偏差（如阈值不同），启动信号检测有错误，但整体思路正确。
**Score 0.25**: 价差识别和启动信号均有明显问题。
**Score 0.0**: 未实现价差识别和启动信号检测。
