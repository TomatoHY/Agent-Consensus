---
id: task_16_pe_bollinger_reversal
name: PE筛选后布林带反弹选股
category: fundamental_technical_combined
grading_type: hybrid
timeout_seconds: 420
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files: []
---

## Prompt

完成以下基本面+技术面联合选股：

**第一步（基本面筛选）**：获取创业板股票的市盈率（PE）数据，筛选出PE在15-60之间的股票（排除亏损股PE<0和高估值PE>60）。

**第二步（技术面筛选）**：对筛选出的股票计算近20日布林带（中轨=20日SMA，上下轨=中轨±2倍标准差），找出"价格从下轨反弹站上中轨"的股票：
- 价格曾触及或跌破下轨（截至 2024-08-15 的最近20天内收盘价 ≤ 下轨）；
- 之后收盘价回到中轨以上（截至 2024-08-15 的收盘价 > 中轨）。

**第三步（量能验证）**：要求近5日成交量均值 > 近20日成交量均值（量能配合）。

按PE从低到高排序，将前8只写入 `pe_bollinger_top8.txt`，格式：
```
股票代码,PE,布林带反弹日期,近5日涨幅(%)
300XXX,28.5,2024-01-12,6.3
```

## Expected Behavior

Agent应该：
1. 获取PE数据并筛选15-60区间
2. 对筛选后的股票批量计算布林带
3. 检测触及下轨后回到中轨的时间点
4. 验证量能条件
5. 计算近5日涨幅
6. 按PE升序排列取前8名

## Grading Criteria

- [ ] 文件 `pe_bollinger_top8.txt` 已创建
- [ ] 记录不超过8条
- [ ] 包含PE值且在15-60之间
- [ ] agent获取了PE数据
- [ ] agent计算了布林带
- [ ] agent验证了量能条件

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "pe_bollinger_top8.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "top8.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["pe_range"] = 0.0
        scores["count_limit"] = 0.0
        scores["pe_data_fetched"] = 0.0
        scores["bollinger_computed"] = 0.0
        scores["volume_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["pe_range"] = 1.0
        scores["count_limit"] = 1.0
    else:
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l]
        scores["count_limit"] = 1.0 if len(lines) <= 8 else 0.5

        pe_values = re.findall(r'\b([1-9]\d?\.\d|\d{2,3})\b', content)
        valid_pe = [float(v) for v in pe_values if 15 <= float(v) <= 60]
        scores["pe_range"] = 1.0 if len(valid_pe) > 0 else 0.0

    transcript_str = str(transcript).lower()
    scores["pe_data_fetched"] = 1.0 if any(kw in transcript_str for kw in
        ["pe", "市盈率", "price.*earning", "p/e"]) else 0.0
    scores["bollinger_computed"] = 1.0 if any(kw in transcript_str for kw in
        ["bollinger", "布林", "upper.*band", "lower.*band", "boll"]) else 0.0
    scores["volume_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["volume", "成交量", "vol", "量能"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 基本面数据获取与筛选（Weight: 25%）

**Score 1.0**: 正确获取了PE数据，明确筛选了PE在15-60之间的股票，排除了亏损股（PE<0）和高估值股（PE>60）。
**Score 0.75**: PE数据获取正确，筛选逻辑基本对，但边界处理略有偏差（如包含了PE=0的股票）。
**Score 0.5**: PE数据获取有问题（如用PB代替PE），或筛选区间错误。
**Score 0.25**: 尝试了PE筛选但有重大错误。
**Score 0.0**: 未获取PE数据。

### Criterion 2: 布林带反弹检测逻辑（Weight: 40%）

**Score 1.0**: 正确计算布林带（20日SMA±2σ），反弹检测分两步：先找到历史触及下轨的时间点，再确认最新收盘价回到中轨以上，逻辑严密不混淆。
**Score 0.75**: 布林带计算正确，反弹检测基本正确，但对"触及下轨"的判断过于宽松或严格。
**Score 0.5**: 布林带计算有误（如只用1σ），或反弹检测逻辑只检查了其中一个条件。
**Score 0.25**: 布林带概念应用有根本性错误。
**Score 0.0**: 未计算布林带。

### Criterion 3: 量能条件与综合排序（Weight: 35%）

**Score 1.0**: 正确计算近5日和近20日均量并比较（5日均量>20日均量），近5日涨幅计算准确，按PE升序排列正确，取前8名。
**Score 0.75**: 量能条件和排序基本正确，有1个小错误（如按PE降序排列）。
**Score 0.5**: 量能条件有计算错误，或排序方向有误。
**Score 0.25**: 量能和排序均有较大错误。
**Score 0.0**: 未实现量能验证和排序。
