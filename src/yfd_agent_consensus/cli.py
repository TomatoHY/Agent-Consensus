#!/usr/bin/env python3
import argparse
from pathlib import Path

from .agent import load_agents_config
from .orchestrator import run_consensus_task


def _is_task_completed(output_dir: Path) -> bool:
    return output_dir.exists() and (output_dir / "consensus_report.json").exists()


def cmd_run_task(args):
    agents = load_agents_config(Path(args.agents_config))
    task_file = Path(args.task_file)
    output_dir = Path(args.output_dir)
    if _is_task_completed(output_dir) and not args.force:
        print(f"[skip] task_file={task_file} output_dir={output_dir} report={output_dir / 'consensus_report.json'}")
        print(output_dir / "consensus_report.json")
        return
    report = run_consensus_task(
        task_file=task_file,
        agents=agents,
        output_dir=output_dir,
        verify_cmd=args.verify_cmd,
    )
    print(output_dir / "consensus_report.json")


def cmd_run_batch(args):
    agents = load_agents_config(Path(args.agents_config))
    tasks = sorted(Path(args.tasks_dir).glob("task_*.md"))
    if args.limit is not None:
        tasks = tasks[: args.limit]
    for task_file in tasks:
        task_out = Path(args.output_root) / task_file.stem
        if _is_task_completed(task_out) and not args.force:
            print(f"[skip] task_file={task_file} output_dir={task_out} report={task_out / 'consensus_report.json'}")
            print(task_out / "consensus_report.json")
            continue
        run_consensus_task(
            task_file=task_file,
            agents=agents,
            output_dir=task_out,
            verify_cmd=args.verify_cmd,
        )
        print(task_out / "consensus_report.json")


def build_parser():
    p = argparse.ArgumentParser(description="YFD Agent Consensus")
    sub = p.add_subparsers(dest="command", required=True)

    p_task = sub.add_parser("run-task")
    p_task.add_argument("--task-file", required=True)
    p_task.add_argument("--agents-config", required=True)
    p_task.add_argument("--output-dir", required=True)
    p_task.add_argument("--verify-cmd")
    p_task.add_argument("--force", action="store_true")
    p_task.set_defaults(func=cmd_run_task)

    p_batch = sub.add_parser("run-batch")
    p_batch.add_argument("--tasks-dir", required=True)
    p_batch.add_argument("--agents-config", required=True)
    p_batch.add_argument("--output-root", required=True)
    p_batch.add_argument("--limit", type=int)
    p_batch.add_argument("--verify-cmd")
    p_batch.add_argument("--force", action="store_true")
    p_batch.set_defaults(func=cmd_run_batch)
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
