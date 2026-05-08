---
id: task_39_interest_rate_sector_rotation
name: 利率敏感型行业轮动策略
category: macro_interest_rate_strategy
grading_type: hybrid
timeout_seconds: 480
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files: []
---

## Prompt

分析利率敏感型行业轮动，完成以下任务：

**第一步（利率趋势判断）**：
获取截至 2024-11-22 的近60日十年期国债收益率（代码可尝试：SHIBOR利率、国债期货数据；若无法获取则用债券ETF如511010的价格反推，说明替代方法）。
计算20日移动平均斜率（用线性回归得到截至 2024-11-22 的最近20天利率序列斜率），判断利率方向：
- 斜率 < -0.002：利率下行
- 斜率 > 0.002：利率上行
- 其他：中性

**第二步（策略选股）**：

当**利率下行**时：筛选创业板中高股息率股票（股息率>3%）且近20日上涨的股票（类债券资产受益于利率下行）。

当**利率上行**时：筛选低PB成长股（PB<3，近20日涨幅>10%，ROE>15%），这类股票在利率上行环境中更具竞争力。

**第三步**：输出截至 2024-11-22 的利率趋势和符合策略的股票。

将结果写入 `rate_strategy.txt`，格式：
```
当前利率趋势: 下行/上行/中性
利率20日斜率: X.XXXX

策略: 高股息/低PB成长
股票代码,股息率(%)/PB,ROE(%),近20日涨幅(%)
300XXX,4.2,12.5,8.3
```

## Expected Behavior

Agent应该：
1. 获取利率数据（国债收益率或替代品）
2. 计算线性回归斜率
3. 判断利率方向并选择对应策略
4. 获取相应的基本面数据（股息率或PB/ROE）
5. 筛选符合策略的创业板股票
6. 输出格式化报告

## Grading Criteria

- [ ] 文件 `rate_strategy.txt` 已创建
- [ ] 文件包含利率趋势判断字段（下行/上行/中性）
- [ ] 文件包含利率斜率数值
- [ ] 文件包含策略类型（高股息或低PB成长）
- [ ] agent尝试了利率数据获取
- [ ] agent使用了线性回归计算斜率

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "rate_strategy.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "strategy.txt", "rate.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["trend_identified"] = 0.0
        scores["slope_present"] = 0.0
        scores["strategy_type"] = 0.0
        scores["rate_data_attempted"] = 0.0
        scores["regression_used"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text()

    trend_kws = ["下行", "上行", "中性", "declining", "rising", "neutral"]
    scores["trend_identified"] = 1.0 if any(kw in content for kw in trend_kws) else 0.0

    scores["slope_present"] = 1.0 if bool(re.search(r'[-+]?\d+\.\d{3,}', content)) else 0.0

    strategy_kws = ["高股息", "低pb", "low.*pb", "高股息率", "成长股", "dividend", "pb.*3"]
    scores["strategy_type"] = 1.0 if any(kw.lower() in content.lower() for kw in strategy_kws) else 0.0

    transcript_str = str(transcript).lower()
    rate_kws = ["国债", "shibor", "利率", "interest.*rate", "bond.*yield", "511010", "treasury"]
    scores["rate_data_attempted"] = 1.0 if any(kw in transcript_str for kw in rate_kws) else 0.0
    scores["regression_used"] = 1.0 if any(kw in transcript_str for kw in
        ["linear.*regress", "线性回归", "polyfit", "linregress", "slope", "斜率"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 利率数据获取与斜率计算（Weight: 30%）

**Score 1.0**: 成功获取了利率数据（国债收益率或合理替代品），线性回归斜率计算正确（用时间序号作x轴，利率值作y轴），阈值±0.002的判断逻辑清晰合理。
**Score 0.75**: 利率数据获取正确，斜率计算略有偏差（如用手动计算首尾差代替线性回归），判断方向正确。
**Score 0.5**: 利率数据用了不够准确的替代品（如直接用股票涨跌近似），但斜率判断方向有合理依据。
**Score 0.25**: 利率数据获取有严重问题，斜率计算方法有根本性错误。
**Score 0.0**: 未获取任何利率数据。

### Criterion 2: 策略选股逻辑（Weight: 40%）

**Score 1.0**: 根据利率方向正确切换策略（下行→高股息，上行→低PB成长），各策略的筛选条件完全正确（股息率>3%、PB<3且涨幅>10%且ROE>15%），策略的经济逻辑合理。
**Score 0.75**: 策略切换正确，某一策略的筛选条件有轻微偏差（如股息率阈值用了2.5%）。
**Score 0.5**: 策略方向正确（选对了哪种策略），但筛选条件有多处偏差。
**Score 0.25**: 策略方向有误（如利率下行却选了成长股）。
**Score 0.0**: 未实现利率敏感策略选股。

### Criterion 3: 基本面数据与结果输出（Weight: 30%）

**Score 1.0**: 正确获取了股息率（下行策略）或PB/ROE（上行策略），相应的基本面筛选准确，输出格式完整（包含利率趋势、斜率、策略类型和个股数据）。
**Score 0.75**: 基本面数据获取基本正确，输出格式略有不规范（缺少部分字段）。
**Score 0.5**: 基本面数据有问题（如股息率数据不准确），但输出框架正确。
**Score 0.25**: 基本面数据严重缺失。
**Score 0.0**: 未创建结果文件。
