---
id: task_18_momentum_portfolio
name: 动量组合构建与绩效分析
category: portfolio_performance_analysis
grading_type: hybrid
timeout_seconds: 480
grading_weights:
  automated: 0.5
  llm_judge: 0.5
workspace_files: []
---

## Prompt

完成动量组合构建与绩效分析：

**第一步**：计算创业板所有股票截至 2024-10-15 的20日动量（前20日累计收益率），选出动量最强的15只股票。

**第二步**：获取这15只股票近60个交易日的日收益率数据，构建等权重组合（每只权重1/15），计算组合每日收益率序列。

**第三步**：计算该组合的绩效指标：
- 年化收益率 = 60日累计收益率 * (252/60)
- 年化波动率 = 日收益率标准差 * √252
- 夏普比率 = (年化收益率 - 2.5%) / 年化波动率

**第四步**：获取创业板指数（399006）同期的相同3项指标，并额外计算：
- 超额收益 = 组合年化收益率 - 指数年化收益率
- 信息比率 = 超额收益 / 追踪误差（追踪误差 = 主动收益标准差 * √252）

将结果写入 `portfolio_analysis.txt`，格式：
```
=== 动量组合 ===
成分股: 300XXX, 300XXX, ...（15只）
年化收益率: XX.XX%
年化波动率: XX.XX%
夏普比率: X.XX

=== 创业板指数 ===
年化收益率: XX.XX%
年化波动率: XX.XX%
夏普比率: X.XX

=== 对比分析 ===
超额收益: XX.XX%
信息比率: X.XX
```

## Expected Behavior

Agent应该：
1. 计算全市场动量，筛选TOP15
2. 获取60日收益率序列，构建等权组合
3. 计算年化收益率、波动率、夏普比率
4. 同样计算指数的三项指标
5. 计算超额收益和信息比率
6. 输出格式化报告

## Grading Criteria

- [ ] 文件 `portfolio_analysis.txt` 已创建
- [ ] 包含15只成分股代码
- [ ] 包含年化收益率、波动率、夏普比率数值
- [ ] 包含指数的对比指标
- [ ] 包含超额收益和信息比率
- [ ] 年化波动率数值合理（A股典型范围10%-60%）

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "portfolio_analysis.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "analysis.txt", "portfolio.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["has_15_stocks"] = 0.0
        scores["has_metrics"] = 0.0
        scores["has_index_comparison"] = 0.0
        scores["reasonable_volatility"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text()

    gem_codes = re.findall(r'3\d{5}', content)
    unique_codes = list(set(gem_codes))
    scores["has_15_stocks"] = 1.0 if len(unique_codes) >= 12 else (0.5 if len(unique_codes) >= 5 else 0.0)

    has_sharpe = bool(re.search(r'夏普|sharpe', content, re.IGNORECASE))
    has_return = bool(re.search(r'年化收益|annualized.*return|return.*annualized', content, re.IGNORECASE))
    has_vol = bool(re.search(r'年化波动|annualized.*vol|volatility', content, re.IGNORECASE))
    scores["has_metrics"] = 1.0 if (has_sharpe and has_return and has_vol) else (0.5 if sum([has_sharpe, has_return, has_vol]) >= 2 else 0.0)

    has_index = bool(re.search(r'399006|创业板指|指数', content))
    has_excess = bool(re.search(r'超额|excess|信息比率|information ratio', content, re.IGNORECASE))
    scores["has_index_comparison"] = 1.0 if (has_index and has_excess) else (0.5 if has_index else 0.0)

    vol_matches = re.findall(r'(\d+\.?\d*)\s*%', content)
    valid_vols = [float(v) for v in vol_matches if 5 <= float(v) <= 80]
    scores["reasonable_volatility"] = 1.0 if len(valid_vols) >= 2 else (0.5 if len(valid_vols) >= 1 else 0.0)

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 动量选股与组合构建（Weight: 25%）

**Score 1.0**: 正确计算20日累计收益率，选出前15名动量股（无重复，均为创业板股票），等权组合每日收益率 = 15只股票日收益率的简单平均，方法正确。
**Score 0.75**: 动量选股或等权构建有轻微错误（如选了14或16只）。
**Score 0.5**: 动量定义有偏差（如用价格涨幅而非百分比收益），或权重不等。
**Score 0.25**: 选股方法有根本性错误，组合构建不合理。
**Score 0.0**: 未完成动量选股。

### Criterion 2: 绩效指标计算准确性（Weight: 40%）

**Score 1.0**: 年化收益率（×252/60）、年化波动率（×√252）、夏普比率（使用2.5%无风险利率）三项均按正确公式计算，数值在合理范围内（夏普比率通常-2到5之间）。
**Score 0.75**: 三项指标公式基本正确，有1个指标的年化系数有轻微偏差（如用365而非252）。
**Score 0.5**: 计算了2项，第3项缺失或有明显公式错误。
**Score 0.25**: 公式有多处错误，数值不合理（如夏普比率>10）。
**Score 0.0**: 未计算绩效指标。

### Criterion 3: 基准对比与超额收益（Weight: 35%）

**Score 1.0**: 正确获取399006同期数据，三项指标计算方法与组合一致，超额收益 = 组合-指数年化收益，信息比率 = 超额收益/追踪误差，数值合理。
**Score 0.75**: 基准指标计算正确，但信息比率公式略有偏差（如未年化追踪误差）。
**Score 0.5**: 计算了超额收益但未计算信息比率，或基准期间与组合不一致。
**Score 0.25**: 基准对比有较大错误。
**Score 0.0**: 未进行基准对比。
