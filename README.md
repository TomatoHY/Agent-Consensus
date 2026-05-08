# YFD Agent Consensus

一个精简的四 agent 共识求解框架，面向 `YFD` 任务。

流程：

1. 4 个 agent 独立做题
2. 每个 agent 阅读其他 agent 的结果并反思
3. 每个 agent 基于反思做一次修订
4. 4 个 agent 再投票并给出统一方案
5. 系统选择最终方案，并可选执行验证命令

支持：

- 静态任务：最终答案可以是写死的 `result.txt`
- 实时任务：最终答案可以是可执行代码 + 运行产物

## 目录

```text
yfd-agent-consensus/
  README.md
  main.py
  config/
    example_agents.json
  src/
    yfd_agent_consensus/
      __init__.py
      agent.py
      cli.py
      io_utils.py
      orchestrator.py
      prompts.py
      selection.py
```

## agent 接口约定

每个 agent 命令需要：

- 从 `stdin` 接收 prompt
- 在当前工作目录 `cwd` 内读写文件
- 在 `stdout` 返回 JSON

推荐返回格式：

```json
{
  "answer": "最终答案或摘要",
  "confidence": 0.72,
  "approach": "简短方法说明",
  "artifacts": ["result.txt", "solve.py"],
  "assumptions": ["使用固定截止日 2026-03-31"],
  "preferred_output": "code"
}
```

如果 agent 没返回合法 JSON，框架会保留原始文本并做降级解析。

## agent 配置

见：

- [example_agents.json](/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/config/example_agents.json)

字段：

- `name`: agent 名称
- `kind`: 原生类型，可选 `codex` / `claude` / `genericagent` / `openclaw`
- `model`: 可选，给 `claude` 或 `openclaw`
- `cmd`: 自定义命令。若提供 `cmd`，可不写 `kind`

当前版本已经按 [run_yfd_tasks.py](/Users/tomato/Documents/potato/project/YFD/scripts/run_yfd_tasks.py) 的调用方式兼容了四种原生 agent：

- `codex`
- `claude`
- `genericagent`
- `openclaw`

也就是说，你可以直接使用 `kind` 配置，而不必自己再写 wrapper。

## 单题运行

```bash
python3 /Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/main.py run-task \
  --task-file /Users/tomato/Documents/potato/project/YFD/tasks-v2/task_20_ultimate_multi_condition.md \
  --agents-config /Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/config/example_agents.json \
  --output-dir /Users/tomato/Documents/potato/project/YFD/results/agent_consensus/task_20
```

## 批量运行

```bash
python3 /Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/main.py run-batch \
  --tasks-dir /Users/tomato/Documents/potato/project/YFD/tasks-v2 \
  --agents-config /Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/config/example_agents.json \
  --output-root /Users/tomato/Documents/potato/project/YFD/results/agent_consensus_batch \
  --limit 5
```

## 可选验证

如果你有统一验证脚本，可以传：

```bash
--verify-cmd "python3 /path/to/verify.py"
```

框架会在最终选中的 workspace 里执行这个命令。

## 输出

每题目录下会有：

- `independent/`：四个 agent 的独立 workspace
- `revised/`：四个 agent 的修订 workspace
- `consensus_report.json`
- `final_workspace/`
- `verification.json`（如果启用）

每个阶段的 agent 目录下还会有：

- `trajectory/stdout.txt`：运行中实时写入的标准输出
- `trajectory/stderr.txt`：运行中实时写入的错误输出
- `stdout.txt` / `stderr.txt`：阶段结束后的完整输出归档
- `summary.json`：该阶段的 token 统计、解析结果、日志文件路径
- `openclaw_transcript.json`：如果是 OpenClaw，会额外保存 transcript

## 选择规则

默认不是简单多数投票，而是：

1. 统计每个 agent 在协商阶段支持谁
2. 叠加支持者给出的置信度
3. 参考被支持方案自身置信度
4. 选择总分最高者

这样比单纯投票稳一点。