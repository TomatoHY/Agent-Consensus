#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/tomato/Documents/potato/project/YFD"
PROJECT_ROOT="$ROOT/yfd-agent-consensus"
MAIN_PY="$PROJECT_ROOT/main.py"
AGENTS_CONFIG="$PROJECT_ROOT/config/agents.json"
TASKS_DIR="$ROOT/tasks-v1"
OUTPUT_ROOT="$ROOT/yfd-agent-consensus/results/agent_consensus_batch"
TASK_FILE="$TASKS_DIR/task_20_ultimate_multi_condition.md"
TASK_OUTPUT_DIR="$ROOT/yfd-agent-consensus/results/agent_consensus/task_20_ultimate_multi_condition"

BATCH_LIMIT="40"
BATCH_OUTPUT_DIR="$OUTPUT_ROOT/default_run"

RUN_MODE="${1:-task}"

echo "[run.sh] project=$PROJECT_ROOT"
echo "[run.sh] mode=$RUN_MODE"
export PYTHONUNBUFFERED=1

if [[ "$RUN_MODE" == "task" ]]; then
  echo "[run.sh] task_file=$TASK_FILE"
  echo "[run.sh] output_dir=$TASK_OUTPUT_DIR"
  python3 "$MAIN_PY" run-task \
    --task-file "$TASK_FILE" \
    --agents-config "$AGENTS_CONFIG" \
    --output-dir "$TASK_OUTPUT_DIR"
elif [[ "$RUN_MODE" == "batch" ]]; then
  echo "[run.sh] tasks_dir=$TASKS_DIR"
  echo "[run.sh] output_root=$BATCH_OUTPUT_DIR"
  echo "[run.sh] limit=$BATCH_LIMIT"
  python3 "$MAIN_PY" run-batch \
    --tasks-dir "$TASKS_DIR" \
    --agents-config "$AGENTS_CONFIG" \
    --output-root "$BATCH_OUTPUT_DIR" \
    --limit "$BATCH_LIMIT"
else
  echo "RUN_MODE must be 'task' or 'batch'"
  exit 1
fi
