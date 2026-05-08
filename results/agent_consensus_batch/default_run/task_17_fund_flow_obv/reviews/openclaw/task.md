---
id: task_17_fund_flow_obv
name: 大单净流入与OBV上升通道筛选
category: fund_flow_technical_multi_hop
grading_type: hybrid
timeout_seconds: 420
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files: []
---

## Prompt

完成以下资金流向+技术分析多维度筛选：

**第一步**：获取创业板截至 2024-09-13 的前5个交易日大单净流入数据（若工具不支持则用成交量代理：大单买入≈当日成交量×0.4），找出连续3天以上大单净流入为正的股票。

**第二步**：对这些股票计算近20日OBV（能量潮）指标：
- OBV计算：当日收盘 > 前日收盘，OBV += 当日成交量；当日收盘 < 前日收盘，OBV -= 当日成交量；持平则不变。
- 筛选OBV处于近20日最高值附近（截至 2024-09-13 的OBV > 近20日OBV均值的1.1倍）。

**第三步**：验证价格处于上升通道：20日均线斜率为正（近5日的20日均线值递增），且收盘价在20日均线上方。

将结果写入 `fund_flow_result.txt`，格式：
```
股票代码,大单净流入天数,OBV相对强度,均线偏离度(%)
300XXX,4,1.25,3.5
```

其中：OBV相对强度 = 截至 2024-09-13 的OBV / 近20日OBV均值，均线偏离度 = (收盘价 - 20日均线) / 20日均线 * 100

## Expected Behavior

Agent应该：
1. 获取大单成交量代理（单笔成交额>100万）
2. 筛选连续3天以上净流入的股票
3. 对筛选结果计算OBV并检验强度
4. 验证均线上升通道条件
5. 计算三个量化指标并输出

## Grading Criteria

- [ ] 文件 `fund_flow_result.txt` 已创建
- [ ] 包含代码、净流入天数、OBV强度、均线偏离度
- [ ] OBV相对强度值 > 1.1（符合条件）
- [ ] agent计算了OBV指标
- [ ] agent检查了均线斜率条件

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "fund_flow_result.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["obv_strength"] = 0.0
        scores["obv_computed"] = 0.0
        scores["ma_slope_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
        scores["obv_strength"] = 1.0
    else:
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l]
        has_code = bool(re.search(r'3\d{5}', content))
        has_numbers = len(re.findall(r'\d+\.?\d*', content)) >= 3
        scores["valid_format"] = 1.0 if (has_code and has_numbers) else (0.5 if has_code else 0.0)

        obv_values = re.findall(r'1\.\d+', content)
        valid_obv = [float(v) for v in obv_values if float(v) > 1.1]
        scores["obv_strength"] = 1.0 if len(valid_obv) > 0 else 0.0

    transcript_str = str(transcript).lower()
    scores["obv_computed"] = 1.0 if "obv" in transcript_str or "能量潮" in transcript_str else 0.0
    scores["ma_slope_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["slope", "斜率", "递增", "ma.*increasing", "均线.*上升"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 资金流向数据处理（Weight: 25%）

**Score 1.0**: 正确获取了大单净流入数据，或明确说明用成交量代理并合理设置代理参数，正确统计连续净流入天数（严格连续，不跳天）。
**Score 0.75**: 资金数据处理基本正确，但连续天数统计有轻微问题（如允许间隔1天）。
**Score 0.5**: 用了不合理的代理方式，或只统计了天数总和而非连续天数。
**Score 0.25**: 资金流向数据处理存在明显错误。
**Score 0.0**: 未处理资金流向数据。

### Criterion 2: OBV计算与强度判断（Weight: 35%）

**Score 1.0**: OBV按标准公式正确累计计算，OBV均值用20日滑动均值，强度阈值1.1倍正确应用，逻辑清晰。
**Score 0.75**: OBV计算基本正确，均值计算有轻微偏差（如用总均值而非滑动均值）。
**Score 0.5**: OBV计算有错误（如每次重置为0），但方向判断逻辑正确。
**Score 0.25**: OBV概念有误，未按涨跌方向累计。
**Score 0.0**: 未计算OBV。

### Criterion 3: 均线通道验证与输出（Weight: 40%）

**Score 1.0**: 正确计算20日SMA序列，斜率判断用近5日均线值是否单调递增，偏离度计算准确，三个输出指标均正确。
**Score 0.75**: 均线通道判断基本正确，输出指标有1个计算偏差。
**Score 0.5**: 斜率判断用了错误方法（如只比较首尾），或偏离度计算有误。
**Score 0.25**: 均线通道判断存在根本性错误。
**Score 0.0**: 未进行均线通道验证。
