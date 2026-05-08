# YFD Agent Consensus 数据集构建说明

本文说明 `/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus` 中两件事：

1. 如何构建用于测试 agent memory 的 `task.md`。
2. 如何用四 agent consensus 框架构建标准答案。

当前标准答案主目录为：

```text
/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run
```

`task.md` 的格式参考了：

```text
/Users/tomato/Documents/potato/project/pinbench-skill/tasks
```

尤其是 `TASK_TEMPLATE.md` 中的 YAML frontmatter + `Prompt` + `Expected Behavior` + `Grading Criteria` + `Automated Checks` + `LLM Judge Rubric` 结构。

## 1. 项目在数据集构建中的角色

`yfd-agent-consensus` 不是普通单 agent 评测器，而是一个“标准答案生成/筛选框架”：

1. 多个 agent 独立解同一道 YFD 金融任务。
2. 每个 agent 阅读其他 agent 的结果并做 cross-review。
3. 每个 agent 基于 review 和 peer summaries 修订自己的答案。
4. 多个 agent 对修订结果投票。
5. 框架按投票、置信度、输出文件完整性、是否命中输出契约等因素选择一个 winner。
6. winner 的 revised workspace 被复制为 `final_workspace`，作为该题的标准答案目录。

所以标准答案不是某个手写 `answer.txt`，而是每题目录下的：

```text
results/agent_consensus_batch/default_run/<task_id>/final_workspace/
```

其中真正要给下游评测使用的答案文件，是 `task.md` 中要求写入的输出文件，例如：

```text
result.txt
volatility_top5.txt
ultimate_filter.txt
correlation_report.txt
```

`final_workspace` 中的 `summary.json`、`stage_output.json`、`stdout.txt`、`stderr.txt`、`command.json` 等是证据和审计材料，不是最终答案本身。

## 2. task.md 的构建原则

一个 YFD task 文件本质上是 PinBench 风格任务规范，服务三个对象：

1. **Agent**：读 `Prompt` 完成任务。
2. **Consensus 框架**：通过反引号中的文件名识别输出契约。
3. **后续评测器/人工复核者**：通过 `Expected Behavior`、`Automated Checks`、`LLM Judge Rubric` 判断答案质量。

当前任务通常存放在：

```text
/Users/tomato/Documents/potato/project/YFD/tasks-v1
/Users/tomato/Documents/potato/project/YFD/tasks-v2
```

批量运行时 `run.sh` 默认使用：

```text
TASKS_DIR="$ROOT/tasks-v1"
```

但已有 `default_run` 中有些 `consensus_report.json` 的 `task_file` 指向 `tasks-v2`，有些指向 `tasks-v1`。因此复核某个标准答案时，应优先查看该题自己的：

```text
<task_id>/consensus_report.json -> task_file
<task_id>/final_workspace/task.md
```

不要只凭当前 `run.sh` 推断它来自哪个任务版本。

## 3. task.md 推荐结构

每个任务文件建议保持以下结构。

```markdown
---
id: task_XX_short_name
name: 中文任务名
category: category_name
grading_type: automated | hybrid | llm_judge
timeout_seconds: 300
grading_weights:
  automated: 0.5
  llm_judge: 0.5
workspace_files: []
---

## Prompt

给 agent 的真实用户任务。必须明确：
- 固定时间基准
- 股票池或行业范围
- 数据窗口
- 指标定义
- 输出文件名
- 输出格式

## Expected Behavior

Agent 应该如何做。写成可复核步骤。

## Grading Criteria

- [ ] 原子检查点 1
- [ ] 原子检查点 2
- [ ] 原子检查点 3

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    ...
```

---

## LLM Judge Rubric

### Criterion 1: xxx（Weight: xx%）

**Score 1.0**: ...
**Score 0.75**: ...
**Score 0.5**: ...
**Score 0.25**: ...
**Score 0.0**: ...
```

### 3.1 YAML frontmatter

必填字段：

| 字段 | 含义 |
| --- | --- |
| `id` | 唯一任务 ID，通常与文件名一致，如 `task_01_macd_rsi_filter`。 |
| `name` | 中文可读任务名。 |
| `category` | 任务类别，用于分组和后续分析。 |
| `grading_type` | `automated`、`hybrid` 或 `llm_judge`。 |
| `timeout_seconds` | 建议执行超时。复杂金融任务一般 300-600 秒。 |
| `grading_weights` | hybrid 任务中 automated 和 llm_judge 的权重。 |
| `workspace_files` | 预置文件说明。当前 consensus runner 只复制 `task.md`，不会自动展开这些文件。 |

注意：`workspace_files` 是从 PinBench 模板继承来的字段，但当前 `yfd-agent-consensus` 的 `_prepare_workspace(...)` 只会写入 `task.md`，不会根据 `workspace_files` 自动复制资产。如果未来任务真的依赖输入文件，需要同步改 runner，或在任务 Prompt 中明确可读路径。

### 3.2 Prompt

`Prompt` 是 agent 实际要完成的任务，必须完整、具体、无歧义。

YFD 金融任务建议固定包含：

- **统一时间基准**：例如“分析截止日统一设为 2026-03-31”。
- **窗口定义**：5/10/20/60/252 个交易日如何回看，停牌如何处理。
- **股票池**：创业板、沪深 A 股、ETF 成分股、行业样本等。
- **指标定义**：MACD、RSI、均线、成交量、PE、行业涨幅等的计算口径。
- **条件关系**：窗口级条件与同日共振条件要分清。
- **输出文件名**：必须用反引号写清楚，例如 `result.txt`。
- **输出格式**：每行一个代码、CSV 表头、字段顺序、最多返回多少行等。

输出文件名一定要放在反引号里，因为 `io_utils.infer_output_contract(...)` 会通过正则扫描 Markdown 中的：

```text
`*.txt`
`*.csv`
`*.json`
`*.jsonl`
`*.md`
`*.py`
```

这些文件名会进入 agent summaries 的 `output_contract` 和 `contract_hits`，影响最终 winner 的 artifact score。

### 3.3 Expected Behavior

`Expected Behavior` 是任务作者对“正确解法路径”的描述，不直接给最终答案。

好的 Expected Behavior 应该：

- 拆成编号步骤。
- 说明完整遍历范围，而不是抽样。
- 写清楚指标公式和边界情况。
- 写清楚哪些条件必须同一天满足，哪些条件只要求窗口内出现。
- 写清楚空结果时如何输出。

示例：`task_01_macd_rsi_filter.md` 中把 RSI 状态机写得很细：

- RSI14 跌破 30 后标记周期起点。
- 从该起点开始首次由 `<=50` 严格上穿到 `>50` 才算有效信号。
- 上穿前再次跌破 30 要重置周期。
- 触发后只有再次跌破 30 才能开启新周期。

这类细节很重要，因为它会直接影响 agent memory 是否能沉淀出“可复用做题规则”。

### 3.4 Grading Criteria

`Grading Criteria` 用 checklist 写，每条尽量原子化：

```markdown
- [ ] 文件 `result.txt` 已创建
- [ ] 文件内容为合法的创业板股票代码格式
- [ ] 代码数量不超过10个
- [ ] agent计算了MACD指标
- [ ] agent计算了RSI指标
```

不要把多个条件压成一句，例如“文件存在且格式正确且数量正确”。这样不利于自动评分和人工复核。

### 3.5 Automated Checks

`Automated Checks` 中的 `grade(transcript, workspace_path)` 是后续评测用的自动评分函数。

当前 `yfd-agent-consensus` 本身不会执行这段代码；它主要把 task 交给 agent 做，并根据输出文件和 consensus 选择答案。但这段代码仍然应该认真写，因为：

- 后续 memory eval 可以直接复用。
- agent 会读到这些检查点，知道需要满足哪些硬约束。
- LLM judge 和人工复核可以用它理解最低通过标准。

自动检查建议：

- 只用标准库和 `pathlib`，避免外部依赖。
- 对结果文件做存在性、格式、数量、字段检查。
- 对 transcript 做关键词或工具调用检查。
- 对缺失文件优雅返回 0 分，不抛异常。
- 对“无符合条件”的合法空结果给出明确处理。

### 3.6 LLM Judge Rubric

LLM Judge Rubric 用于评价自动检查覆盖不到的质量问题，例如：

- 是否完整遍历股票池。
- 指标公式是否正确。
- 任务条件理解是否准确。
- 多跳行业/板块逻辑是否合理。
- 输出是否有解释和可追溯性。

Rubric 建议每个 criterion 都给出 `1.0 / 0.75 / 0.5 / 0.25 / 0.0` 五档描述，并注明权重。

## 4. 标准答案如何构建

标准答案由 `main.py run-task` 或 `main.py run-batch` 生成。

单题：

```bash
python3 /Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/main.py run-task \
  --task-file /Users/tomato/Documents/potato/project/YFD/tasks-v1/category_type_01_technical_indicators_and_signals/task_01_macd_rsi_filter.md \
  --agents-config /Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/config/agents.json \
  --output-dir /Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus/task_01_macd_rsi_filter
```

批量：

```bash
python3 /Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/main.py run-batch \
  --tasks-dir /Users/tomato/Documents/potato/project/YFD/tasks-v1 \
  --agents-config /Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/config/agents.json \
  --output-root /Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run \
  --limit 40
```

项目也提供 `run.sh`：

```bash
cd /Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus
./run.sh task
./run.sh batch
```

默认 agents 配置：

```json
[
  {"name": "ga", "kind": "genericagent"},
  {"name": "codex", "kind": "codex"},
  {"name": "claudecode", "kind": "claude", "model": "claude-sonnet-4-6"},
  {"name": "openclaw", "kind": "openclaw", "model": "ccvibe/claude-sonnet-4-6"}
]
```

## 5. 圆桌会议如何让 agent 讨论出正确答案

这个项目的核心不是“让 4 个 agent 各跑一遍，然后随机选一个”，而是把多 agent 解题组织成一个结构化圆桌会议。

代码入口在：

```text
src/yfd_agent_consensus/orchestrator.py
```

圆桌会议由 `run_consensus_task(...)` 串起，完整顺序是：

```text
independent -> reviews -> revised -> consensus -> selection -> final_workspace
```

每个阶段都让所有 agent 并行执行。`_run_stage_parallel(...)` 使用 `ThreadPoolExecutor(max_workers=len(agents))` 同时启动 `ga`、`codex`、`claudecode`、`openclaw`，每个 agent 都有独立 workspace：

```text
<task_id>/<stage>/<agent_name>/
```

每个 workspace 都会写入一份 `task.md` 快照。随后 runner 把该阶段需要阅读的材料写成 JSON 文件，再由 prompt 告诉 agent 应该读哪些路径、输出哪些结构化字段。

这套设计把“讨论”拆成四轮：

1. **独立作答**：避免一开始互相污染。
2. **交叉审阅**：让每个 agent 看见别人的证据、文件和输出契约命中情况。
3. **修订答案**：允许 agent 吸收 peer 的更强做法或修正自己的错误。
4. **圆桌投票**：只比较修订后的方案，并让 agent 说明支持谁和为什么。

最后系统不盲信单票，而是用投票 + 置信度 + artifact 完整度 + 输出契约命中度打分，选择最终标准答案。

### 5.1 会议材料是如何被压缩和传递的

每个 agent 一轮执行后，`_write_agent_logs(...)` 会保存完整日志：

```text
prompt.txt
stdout.txt
stderr.txt
command.json
summary.json
stage_output.json
openclaw_transcript.json   # 仅 OpenClaw 有 transcript 时出现
```

真正传给其他 agent 的不是完整 stdout，而是 `_summary_from_stage_output(...)` 生成的 summary。summary 包含：

```json
{
  "agent": "ga",
  "answer": "...",
  "confidence": 0.8,
  "approach": "...",
  "artifacts": ["result.txt", "solve.py"],
  "assumptions": [],
  "workspace_files": [],
  "result_files": [],
  "code_files": [],
  "contract_hits": [],
  "output_contract": [],
  "result_preview": "...",
  "code_preview": "..."
}
```

其中 `workspace_files/result_files/code_files` 来自实际文件扫描；`result_preview/code_preview` 是文件前若干字符预览；`output_contract` 是从 `task.md` 中反引号包住的文件名自动提取的；`contract_hits` 表示该 agent 实际生成了哪些任务要求的输出文件。

这一步很关键：圆桌会议不是只看 agent 自己声称“我完成了”，而是把它的实际产物也结构化给其他 agent 看。比如一个 agent 声称写了 `ultimate_filter.txt`，但 `contract_hits` 为空，后续 review 和 selection 都会受到影响。

### 5.2 第一轮：independent 独立发言

代码位置：

```text
orchestrator.py -> run_consensus_task(...) -> stage="independent"
prompts.py -> independent_prompt(...)
```

每个 agent 只收到自己的：

```text
task.md
```

prompt 的核心要求是：

```text
Read the task file and solve it independently in the current directory.
Write all generated code, txt, csv, json, and other result files into result_dir only.
Do not save outputs to external temp folders or tool-specific temp directories.
Return strict JSON with keys: answer, confidence, approach, assumptions, preferred_output, artifacts.
```

这一轮的目的：

- 让不同 agent 独立探索不同路径。
- 暴露各自的数据源选择、指标实现、边界理解。
- 为后续圆桌讨论提供多个候选答案。

输出目录示例：

```text
<task_id>/independent/ga/
<task_id>/independent/codex/
<task_id>/independent/claudecode/
<task_id>/independent/openclaw/
```

这一轮会生成 `independent_summaries`，写入最终的 `consensus_report.json`。

### 5.3 第二轮：reviews 交叉审阅

代码位置：

```text
orchestrator.py -> _prepare_review_inputs(...)
prompts.py -> review_prompt(...)
```

在 review 阶段，每个 agent 会收到两份额外文件：

```text
own_result.json
peer_summaries.json
```

`own_result.json` 是该 agent 第一轮自己的 parsed 输出；`peer_summaries.json` 是其他 agent 的 independent summaries，不包含自己。

也就是说，圆桌会议的第二轮不是让 agent 再做一遍题，而是让它站在审稿人位置比较：

- 自己方案是否满足 task output contract。
- peer 是否生成了明确结果文件。
- peer 是否有可执行代码。
- peer 的 result preview 是否可信。
- peer 的假设是否比自己更合理。
- 是否有人使用模拟数据、放宽条件、漏掉指标、写错输出文件。

prompt 的核心要求是：

```text
Read the task and review files. Do not solve from scratch.
Use peer artifact previews and output-contract coverage when comparing solutions.
Return strict JSON with keys: self_reflection, stronger_peers, suspected_issues, update_plan.
```

这一轮产物是每个 agent 的 `review_result.json`。它让 agent 明确回答：

- 我的方案哪里可能错了？
- 哪些 peer 更强？
- peer 的疑点是什么？
- 我下一轮应该怎么改？

这就是“圆桌讨论”的第一次显式发生：每个 agent 不只是看答案，还要指出错误和改进计划。

### 5.4 第三轮：revised 吸收讨论后修订

代码位置：

```text
orchestrator.py -> _prepare_revise_inputs(...)
prompts.py -> revise_prompt(...)
```

在 revised 阶段，每个 agent 会收到：

```text
own_result.json
review_result.json
peer_summaries.json
```

也就是：

1. 自己第一轮答案。
2. 自己第二轮写下的复盘和 update plan。
3. 其他 agent 的第一轮摘要、文件、预览和 contract 命中情况。

prompt 的核心要求是：

```text
Revise your previous solution after reading the review and peer summary files.
Work in the current directory and update files if needed.
Write all generated code, txt, csv, json, and other result files into result_dir only.
Return strict JSON with keys: answer, confidence, what_changed, final_method, preferred_output, artifacts.
```

这一轮是标准答案质量提升的关键：

- 如果某 agent 第一轮输出了模拟数据，review 后可以改成保守空结果并记录数据源失败证据。
- 如果某 agent 第一轮漏掉同日共振条件，review 后可以修正为日级条件。
- 如果某 agent 第一轮写错文件名，review 后可以补写正确输出文件。
- 如果某 agent 第一轮没有代码，review 后可以补可执行脚本。

项目最终通常从 revised 阶段选答案，而不是 independent 阶段选答案，因为 revised 已经吸收了圆桌讨论的信息。

这一轮会生成 `revised_summaries`，进入最终 `consensus_report.json`。

### 5.5 第四轮：consensus 圆桌投票

代码位置：

```text
orchestrator.py -> _prepare_consensus_inputs(...)
prompts.py -> consensus_prompt(...)
```

在 consensus 阶段，每个 agent 会收到：

```text
revised_summaries.json
```

它包含所有 agent 修订后的摘要、输出文件、代码文件、contract hits、预览等信息。每个 agent 要在这些 revised 方案中选择一个最佳 final scheme。

prompt 的核心要求是：

```text
Read the revised summaries file and choose the best final scheme.
Prefer solutions that satisfy output contract, contain executable artifacts or explicit result files, and provide concrete evidence.
Return strict JSON with keys: preferred_agent, confidence, reasons, merge_notes.
```

这一步是“圆桌会议”的投票环节。每个 agent 不再改自己的结果，而是作为评委选择：

- 哪个 revised 方案最满足任务输出契约。
- 哪个方案有明确结果文件。
- 哪个方案有可执行代码或足够证据。
- 哪个方案的假设最少、最可复现。
- 哪个方案没有采用模拟数据或放宽规则。

输出字段：

```json
{
  "preferred_agent": "ga",
  "confidence": 0.85,
  "reasons": "...",
  "merge_notes": "..."
}
```

### 5.6 系统选择：不是简单多数票

代码位置：

```text
selection.py -> choose_final_agent(...)
```

系统把 consensus votes 和 revised artifacts 结合起来打分。

第一部分：投票分。

每张有效票会给被支持 agent：

```text
1.0 + vote_confidence
```

如果某个投票结果的 `preferred_agent` 不在 revised results 中，这张票会被忽略。

第二部分：被支持方案自身分。

每个 revised 方案都会额外获得：

```text
方案自己的 confidence
+ artifact_score
```

`artifact_score` 的规则：

| 条件 | 加分 |
| --- | --- |
| 有结果文件 `.txt/.csv/.json/.jsonl` | +1.5 |
| 有代码文件 `.py/.ipynb/.sh` | +1.0 |
| 命中 task 输出契约 `contract_hits` | 每个 +0.5，最多 3 个 |
| workspace 中有文件 | 最多 +0.25 |
| answer 非空 | +0.2 |
| 有 result preview | +0.4 |

所以 winner 不是“谁票多谁赢”那么简单。一个方案即使被投票支持，如果没有结果文件、没有命中 `task.md` 要求的输出文件，也会处于劣势。相反，一个方案如果文件完整、命中输出契约、有代码证据，即使票数不是压倒性，也可能被选中。

最终：

```text
winner = max(scores)
```

然后：

```text
copy_tree(output_dir / "revised" / winning_agent, output_dir / "final_workspace")
```

也就是把 winning agent 的 revised workspace 整体复制成标准答案目录。

### 5.7 为什么这套圆桌机制能提升标准答案质量

相比单 agent 直接生成标准答案，这套流程有几个实际收益：

1. **独立性**：第一轮互相不可见，减少从众和 prompt 污染。
2. **多样性**：不同 agent 可能使用不同数据源、代码结构、边界处理。
3. **审稿机制**：review 阶段强迫 agent 看 peer 的文件和预览，而不是只相信自己的答案。
4. **自我修复**：revised 阶段允许 agent 根据 review 修正错误。
5. **证据优先**：consensus prompt 明确偏好满足 output contract、有可执行 artifact、有具体证据的方案。
6. **选择规则可解释**：`selection_scores` 记录每个 agent 的得分，`consensus_report.json` 记录投票、摘要和日志路径。
7. **provenance 完整**：最终答案不是孤立文件，而有 `run.log`、各阶段 workspace、stdout/stderr、stage_output、summary、peer_summaries 支撑。

对 agent memory 测试数据集来说，这很重要：标准答案应该不仅是“某一次 agent 的输出”，而是经过多 agent 互审和修订后的相对稳定答案，并且能追溯为什么选它。

### 5.8 如何人工复核一场圆桌会议

如果某题答案可疑，建议按这个顺序看：

1. 看 `<task_id>/consensus_report.json` 的 `winning_agent` 和 `selection_scores`。
2. 看 `revised_summaries`，确认 winner 是否有 `contract_hits`、`result_files`、`code_files`。
3. 看 `consensus/*/stage_output.json`，确认其他 agent 为什么投它。
4. 看 `reviews/*/review_result.json`，确认有没有指出关键错误。
5. 看 `final_workspace/summary.json` 和 `stdout.txt`，确认 winner 的解法和执行证据。
6. 看 `final_workspace/task.md` 中要求的输出文件，确认格式符合 Prompt。

如果发现 winner 使用了模拟数据、放宽条件、错文件名或证据不足，应重跑该题或人工修订标准答案，并保留新的 run 名称。

## 6. Consensus 生成答案的阶段

每道题会产生如下目录：

```text
<task_id>/
  run.log
  consensus_report.json
  independent/
    ga/
    codex/
    claudecode/
    openclaw/
  reviews/
    ga/
    codex/
    claudecode/
    openclaw/
  revised/
    ga/
    codex/
    claudecode/
    openclaw/
  consensus/
    ga/
    codex/
    claudecode/
    openclaw/
  final_workspace/
```

### 6.1 independent

四个 agent 独立读取 `task.md` 并求解。

Prompt 要求返回 JSON：

```json
{
  "answer": "...",
  "confidence": 0.72,
  "approach": "...",
  "assumptions": [],
  "preferred_output": "code",
  "artifacts": ["result.txt", "solve.py"]
}
```

每个 agent 的 workspace 中会保存：

```text
task.md
prompt.txt
stdout.txt
stderr.txt
command.json
summary.json
stage_output.json
trajectory/stdout.txt
trajectory/stderr.txt
```

以及它自己生成的结果文件和代码。

### 6.2 reviews

每个 agent 会收到：

```text
own_result.json
peer_summaries.json
```

然后做 cross-review。这个阶段不要求重新解题，而是比较自己和 peer 的方案，指出更强方案和问题。

### 6.3 revised

每个 agent 会收到：

```text
own_result.json
review_result.json
peer_summaries.json
```

然后修订自己的答案。标准答案通常来自这个阶段，而不是 independent 阶段。

### 6.4 consensus

每个 agent 会收到：

```text
revised_summaries.json
```

然后投票选择最佳 final scheme，返回：

```json
{
  "preferred_agent": "ga",
  "confidence": 0.85,
  "reasons": "...",
  "merge_notes": "..."
}
```

### 6.5 selection

`selection.py` 的 `choose_final_agent(...)` 不是简单多数投票。它综合：

- consensus votes 中支持某 agent 的票数；
- 投票者 confidence；
- 被支持方案自身 confidence；
- 是否生成结果文件；
- 是否生成代码文件；
- 是否命中 task 中反引号声明的输出契约；
- 是否有 result preview。

得分最高者成为 `winning_agent`。

然后 `orchestrator.py` 会把：

```text
revised/<winning_agent>/
```

复制为：

```text
final_workspace/
```

## 7. 标准答案目录如何使用

对下游评测来说，每道题的标准答案目录是：

```text
results/agent_consensus_batch/default_run/<task_id>/final_workspace/
```

其中：

| 文件 | 用途 |
| --- | --- |
| `task.md` | 该标准答案对应的任务文本快照。 |
| 任务要求的输出文件 | 真正的标准答案，如 `result.txt`、`ultimate_filter.txt`。 |
| `solve.py` / 其他代码 | 生成答案的脚本或证据。不是所有任务都有。 |
| `summary.json` | winning agent 的摘要和 token 统计。 |
| `stage_output.json` | winning agent 的原始阶段输出。 |
| `stdout.txt` / `stderr.txt` | 执行日志。 |
| `command.json` | agent 命令和 return code。 |
| `review_result.json` / `peer_summaries.json` | 修订阶段参考证据。 |

判断最终答案文件的优先级：

1. 先看 `final_workspace/task.md` 中 Prompt 要求写入的反引号文件名。
2. 再看 `summary.json` 中的 `contract_hits` 和 `output_contract`。
3. 最后看 `final_workspace` 中是否有 `.txt/.csv/.json` 结果文件。

示例：

```text
task_01_macd_rsi_filter/final_workspace/result.txt
task_20_ultimate_multi_condition/final_workspace/ultimate_filter.txt
```

`consensus_report.json` 是该题标准答案的总索引，关键字段：

| 字段 | 含义 |
| --- | --- |
| `task_file` | 原始任务文件路径。 |
| `winning_agent` | 被选中的 agent。 |
| `selection_scores` | 每个 revised 方案的选择分。 |
| `independent_summaries` | 独立阶段摘要。 |
| `revised_summaries` | 修订阶段摘要。 |
| `stage_token_stats` | 各阶段 token 统计。 |
| `stage_log_files` | 各阶段日志路径。 |
| `verification` | 若传了 `--verify-cmd`，这里记录验证结果。 |

## 8. default_run 的含义

`default_run` 是当前冻结的一批标准答案产物：

```text
results/agent_consensus_batch/default_run
```

它通常包含每题：

```text
<task_id>/consensus_report.json
<task_id>/final_workspace/
```

这批结果可以作为 memory 测试数据集的 reference answer source。使用时建议：

- 以 `final_workspace` 为标准答案工作区。
- 以 `task.md` 中声明的输出文件为 reference result file。
- 保留 `consensus_report.json` 作为 provenance。
- 对关键任务人工抽查，尤其是输出“无符合条件”的任务。

注意：default_run 是 consensus 的产物，不等同于交易所或数据源官方真值。它的价值在于多 agent 交叉审查和可追踪证据链；如果某题需要严格金融事实真值，应额外加人工验算或独立数据校验。

## 9. 构建新 task.md 的检查清单

新增任务前建议逐项检查：

- [ ] 文件名与 `id` 一致，例如 `task_XX_name.md`。
- [ ] YAML frontmatter 完整。
- [ ] `Prompt` 中写明固定截止日和回看窗口。
- [ ] 输出文件名用反引号标出。
- [ ] 输出格式足够具体，可机器解析。
- [ ] `Expected Behavior` 写清数据源、遍历范围、指标公式、边界条件。
- [ ] `Grading Criteria` 是原子 checklist。
- [ ] `Automated Checks` 缺文件时不会抛异常。
- [ ] 对合法空结果有处理方式。
- [ ] `LLM Judge Rubric` 权重合计 100%。
- [ ] 不依赖当前 consensus runner 不会复制的 workspace assets，除非已同步改 runner。

## 10. 构建标准答案的检查清单

跑完 consensus 后建议检查：

- [ ] 每题存在 `consensus_report.json`。
- [ ] 每题存在 `final_workspace/task.md`。
- [ ] `final_workspace` 中存在 Prompt 要求的输出文件。
- [ ] `summary.json` 的 `contract_hits` 命中目标输出文件。
- [ ] `winning_agent` 的 revised 结果不是明显模拟、放宽条件或空跑。
- [ ] `stdout.txt` / `stderr.txt` 能解释关键数据源失败或成功路径。
- [ ] 对多因子、多跳、行业分类任务人工抽查至少一次。
- [ ] 若使用 `--verify-cmd`，检查 `verification.json` 的 returncode。

## 11. 推荐维护约定

建议后续维护时采用以下约定：

1. **任务源文件只改 tasks 目录，不直接改 final_workspace/task.md。** `final_workspace/task.md` 是运行快照。
2. **标准答案只从固定 run 目录取。** 当前固定目录是 `results/agent_consensus_batch/default_run`。
3. **每次重跑标准答案使用新 run 名。** 例如 `run_20260508`，避免覆盖 default_run。
4. **不要只看最终 result 文件。** 同时看 `consensus_report.json`、`summary.json`、`stdout.txt`，确认答案来自可解释路径。
5. **对 agent memory 测试，保留任务细节难点。** 例如同日共振、RSI 状态机、窗口级条件与日级条件区别，这些正是 memory 应该学习的可复用经验。

## 12. 一句话流程

构建数据集时，先按 PinBench 风格写清楚 `task.md`，让它同时具备 agent 可执行性和评测可判定性；再用四 agent consensus 跑出每题的 `final_workspace`，把其中命中输出契约的文件作为标准答案，并保留完整日志和 consensus report 作为 provenance。
