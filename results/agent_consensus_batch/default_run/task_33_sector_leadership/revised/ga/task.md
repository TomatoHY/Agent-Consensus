---
id: task_33_sector_leadership
name: 行业板块龙头股识别
category: sector_leadership
grading_type: hybrid
timeout_seconds: 480
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files: []
---

## Prompt

识别创业板行业板块龙头股，完成以下步骤：

**第一步**：计算创业板各主要行业（医药、半导体、新能源、消费电子、软件、传媒等至少6个行业）的近20日等权平均涨幅，选出涨幅前3的强势行业。

**第二步**：在强势行业内，计算个股相对强度 RS = 个股近20日涨幅 / 所属行业平均涨幅，筛选 RS > 1.5 的领涨个股。

**第三步**：对领涨个股做进一步筛选：
- 流通市值 > 50亿元；
- 近20日换手率均值 > 5%（活跃）；
- MACD金叉（截至 2024-05-22 的最近10日内）且 RSI > 60；
- 收盘价创截至 2024-05-22 的近60日新高。

将结果写入 `sector_leader.txt`，格式：
```
股票代码,所属行业,RS值,流通市值(亿),换手率(%),RSI
300XXX,新能源,2.3,150.5,8.2,68.5
```

## Expected Behavior

Agent应该：
1. 完成6个以上行业的分类
2. 计算各行业等权均值并找前3强势行业
3. 计算RS并初筛>1.5
4. 逐条验证市值、换手率、MACD金叉、RSI、创新高
5. 输出综合满足所有条件的股票

## Grading Criteria

- [ ] 文件 `sector_leader.txt` 已创建
- [ ] 包含行业名称字段
- [ ] RS值 > 1.5
- [ ] 换手率 > 5%
- [ ] RSI值 > 60
- [ ] agent识别了至少3个强势行业
- [ ] agent计算了MACD金叉

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "sector_leader.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "leader.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["rs_valid"] = 0.0
        scores["rsi_valid"] = 0.0
        scores["turnover_valid"] = 0.0
        scores["sector_identified"] = 0.0
        scores["macd_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["rs_valid"] = 1.0
        scores["rsi_valid"] = 1.0
        scores["turnover_valid"] = 1.0
    else:
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l]
        records = []
        for line in lines:
            parts = re.split(r'[,\s\t]+', line)
            if len(parts) >= 6:
                try:
                    rs = float(parts[2])
                    turnover = float(parts[4].replace('%', ''))
                    rsi = float(parts[5])
                    records.append((rs, turnover, rsi))
                except:
                    pass

        valid_rs = [r for r in records if r[0] > 1.5]
        scores["rs_valid"] = 1.0 if len(valid_rs) == len(records) and len(records) > 0 else (0.5 if len(valid_rs) > 0 else 0.0)

        valid_rsi = [r for r in records if r[2] > 60]
        scores["rsi_valid"] = 1.0 if len(valid_rsi) == len(records) and len(records) > 0 else (0.5 if len(valid_rsi) > 0 else 0.0)

        valid_t = [r for r in records if r[1] > 5]
        scores["turnover_valid"] = 1.0 if len(valid_t) == len(records) and len(records) > 0 else (0.5 if len(valid_t) > 0 else 0.0)

    transcript_str = str(transcript).lower()
    sector_kws = ["医药", "半导体", "新能源", "消费电子", "软件", "传媒", "pharma", "semiconductor", "energy", "software"]
    sector_count = sum(1 for kw in sector_kws if kw in transcript_str)
    scores["sector_identified"] = 1.0 if sector_count >= 4 else (0.5 if sector_count >= 2 else 0.0)
    scores["macd_checked"] = 1.0 if "macd" in transcript_str else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 行业分类与强势行业识别（Weight: 30%）

**Score 1.0**: 正确分类至少6个行业，等权均值计算正确（每行业内各股等权），前3强势行业识别准确，行业分类有经济合理性（不把零售误放到科技）。
**Score 0.75**: 分类了5-6个行业，等权均值基本正确，但某些行业的分类边界略模糊。
**Score 0.5**: 分类了3-4个行业，但遗漏了重要行业或分类较粗糙。
**Score 0.25**: 行业分类和强势识别有明显问题。
**Score 0.0**: 未进行行业分类。

### Criterion 2: 相对强度与龙头筛选逻辑（Weight: 35%）

**Score 1.0**: RS = 个股涨幅/行业均值计算正确，RS>1.5筛选准确，四个进一步筛选条件（市值、换手率、MACD金叉、RSI、创新高）全部正确实现。
**Score 0.75**: RS计算正确，4个进一步筛选中有1个未实现或有小错误（如RSI阈值用了65而非60）。
**Score 0.5**: RS筛选正确，但进一步筛选只实现了2-3个条件。
**Score 0.25**: RS计算有误，或进一步筛选大量缺失。
**Score 0.0**: 未实现相对强度筛选。

### Criterion 3: 结果完整性（Weight: 35%）

**Score 1.0**: 所有字段完整（代码、行业、RS、市值、换手率、RSI），数值均满足筛选条件（RS>1.5、换手率>5%、RSI>60），格式规范。
**Score 0.75**: 缺少1个字段（通常是市值），其他字段正确。
**Score 0.5**: 只有代码、行业、RS，缺少技术指标。
**Score 0.25**: 字段严重残缺。
**Score 0.0**: 未创建结果文件。
