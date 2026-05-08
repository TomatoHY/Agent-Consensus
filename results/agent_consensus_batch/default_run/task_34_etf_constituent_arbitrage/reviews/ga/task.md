---
id: task_34_etf_constituent_arbitrage
name: ETF成分股滞涨套利机会识别
category: etf_constituent_arbitrage
grading_type: hybrid
timeout_seconds: 480
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files: []
---

## Prompt

寻找与行业ETF价格背离的个股套利机会：

**第一步**：获取创业板主要行业ETF截至 2024-06-24 的近20日走势，识别处于上涨趋势的ETF（20日涨幅>8%，且5日均线>20日均线）。可关注的ETF包括：医药ETF（159929）、半导体ETF（159813）、新能源ETF（159642）等，至少检查3个ETF。

**第二步**：获取处于上涨趋势的ETF的主要成分股（可通过工具查询，或用该行业的创业板股票近似代替），计算各成分股近20日涨幅。

**第三步**：找出滞涨股（个股涨幅 < ETF涨幅的50%），验证基本面健康（PE > 0，ROE > 8%）。

**第四步**：检查滞涨股的技术面启动信号：MACD将金叉（DIFF上穿DEA，或两者距离缩小到0.05以内）或刚金叉，且KDJ < 50（低位）。

将结果写入 `etf_arbitrage.txt`，格式：
```
股票代码,对应ETF代码,个股涨幅(%),ETF涨幅(%),滞涨率(%),PE,ROE(%)
300XXX,159929,3.2,12.5,74.4,28.5,12.3
```

滞涨率 = (ETF涨幅 - 个股涨幅) / ETF涨幅 * 100

## Expected Behavior

Agent应该：
1. 获取多个行业ETF数据并筛选上涨ETF
2. 获取对应成分股或行业股票
3. 计算涨幅差异，筛选滞涨股
4. 验证基本面（PE/ROE）
5. 验证技术面启动信号

## Grading Criteria

- [ ] 文件 `etf_arbitrage.txt` 已创建
- [ ] 包含对应ETF代码字段
- [ ] 滞涨率值为正数
- [ ] 个股涨幅 < ETF涨幅
- [ ] agent检查了至少一个行业ETF
- [ ] agent检查了ROE和PE基本面

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "etf_arbitrage.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "arbitrage.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["lag_rate_positive"] = 0.0
        scores["etf_queried"] = 0.0
        scores["fundamentals_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
        scores["lag_rate_positive"] = 1.0
    else:
        has_code = bool(re.search(r'3\d{5}', content))
        has_etf = bool(re.search(r'15\d{4}', content))  # ETF codes start with 15xxxx
        scores["valid_format"] = 1.0 if (has_code and has_etf) else (0.5 if has_code else 0.0)

        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l]
        records = []
        for line in lines:
            parts = re.split(r'[,\s\t]+', line)
            if len(parts) >= 7:
                try:
                    stock_ret = float(parts[2].replace('%', ''))
                    etf_ret = float(parts[3].replace('%', ''))
                    lag_rate = float(parts[4].replace('%', ''))
                    records.append((stock_ret, etf_ret, lag_rate))
                except:
                    pass

        valid_lag = [r for r in records if r[2] > 0 and r[0] < r[1]]
        scores["lag_rate_positive"] = 1.0 if len(valid_lag) == len(records) and len(records) > 0 else (0.5 if len(valid_lag) > 0 else 0.0)

    transcript_str = str(transcript).lower()
    etf_codes = ["159929", "159813", "159642", "etf"]
    scores["etf_queried"] = 1.0 if any(kw in transcript_str for kw in etf_codes) else 0.0
    scores["fundamentals_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["roe", "pe", "净资产收益率", "市盈率"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: ETF数据获取与上涨趋势识别（Weight: 25%）

**Score 1.0**: 正确获取了至少3个行业ETF的数据，涨幅和均线趋势判断正确（20日涨幅>8%且5日>20日均线），筛选出了上涨ETF。
**Score 0.75**: 获取了2-3个ETF，趋势判断基本正确。
**Score 0.5**: 只获取了1个ETF，或ETF代码使用错误但方向正确。
**Score 0.25**: ETF数据获取有明显问题。
**Score 0.0**: 未获取ETF数据。

### Criterion 2: 成分股滞涨识别逻辑（Weight: 35%）

**Score 1.0**: 正确获取或近似成分股，滞涨定义（<ETF涨幅50%）正确实现，滞涨率计算公式准确，正确建立个股与对应ETF的关联。
**Score 0.75**: 滞涨识别基本正确，成分股用行业股票近似但覆盖率不足。
**Score 0.5**: 滞涨阈值有偏差（如<ETF涨幅的70%），或成分股获取有问题。
**Score 0.25**: 滞涨识别逻辑有根本性错误。
**Score 0.0**: 未实现滞涨识别。

### Criterion 3: 基本面与技术面验证（Weight: 40%）

**Score 1.0**: PE>0且ROE>8%的基本面筛选正确，MACD将金叉或刚金叉（含距离缩小判断）且KDJ<50的技术面信号检测准确，两类验证均有合理实现。
**Score 0.75**: 基本面验证正确，技术面验证有简化（如只检查MACD金叉，未检查KDJ）。
**Score 0.5**: 只实现了基本面或技术面其中一类验证。
**Score 0.25**: 两类验证均有实现但有明显错误。
**Score 0.0**: 未实现基本面和技术面验证。
