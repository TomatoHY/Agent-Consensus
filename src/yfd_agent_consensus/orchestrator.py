from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Callable, Dict, List, Optional, Tuple

from .agent import AgentSpec, run_agent
from .io_utils import append_text, copy_tree, infer_output_contract, list_workspace_files, read_preview, write_json, write_text
from .prompts import consensus_prompt, independent_prompt, review_prompt, revise_prompt
from .selection import choose_final_agent


_LOG_LOCK = Lock()


def _collect_artifact_details(workspace: Path, task_file: Path) -> Dict:
    workspace_files = list_workspace_files(workspace)
    result_files = [f for f in workspace_files if f.lower().endswith((".txt", ".csv", ".json", ".jsonl")) and "stage_output.json" not in f]
    code_files = [f for f in workspace_files if f.lower().endswith((".py", ".ipynb", ".sh"))]
    contract = infer_output_contract(task_file.read_text(encoding="utf-8"))
    contract_hits = [f for f in workspace_files if Path(f).name in contract]
    result_preview = read_preview(workspace / result_files[0]) if result_files else ""
    code_preview = read_preview(workspace / code_files[0]) if code_files else ""
    return {
        "workspace_files": workspace_files,
        "result_files": result_files,
        "code_files": code_files,
        "contract_hits": contract_hits,
        "output_contract": contract,
        "result_preview": result_preview,
        "code_preview": code_preview,
    }


def _summary_from_stage_output(stage_output: Dict, workspace: Path, task_file: Path) -> Dict:
    parsed = stage_output.get("parsed", {})
    summary = {
        "agent": stage_output["agent"],
        "answer": parsed.get("answer", parsed.get("raw_output", "")),
        "confidence": parsed.get("confidence", 0.0),
        "approach": parsed.get("approach", parsed.get("final_method", "")),
        "artifacts": parsed.get("artifacts", []),
        "assumptions": parsed.get("assumptions", []),
    }
    summary.update(_collect_artifact_details(workspace, task_file))
    return summary


def _prepare_workspace(base_dir: Path, stage: str, agent_name: str, task_file: Path) -> Path:
    workspace = base_dir / stage / agent_name
    workspace.mkdir(parents=True, exist_ok=True)
    write_text(workspace / "task.md", task_file.read_text(encoding="utf-8"))
    return workspace


def _prepare_review_inputs(workspace: Path, own_result: Dict, peer_summaries: List[Dict]) -> None:
    write_json(workspace / "own_result.json", own_result)
    write_json(workspace / "peer_summaries.json", peer_summaries)


def _prepare_revise_inputs(workspace: Path, own_result: Dict, review_result: Dict, peer_summaries: List[Dict]) -> None:
    write_json(workspace / "own_result.json", own_result)
    write_json(workspace / "review_result.json", review_result)
    write_json(workspace / "peer_summaries.json", peer_summaries)


def _prepare_consensus_inputs(workspace: Path, revised_summaries: List[Dict]) -> None:
    write_json(workspace / "revised_summaries.json", revised_summaries)


def _write_agent_logs(workspace: Path, prompt: str, result: Dict) -> None:
    write_text(workspace / "prompt.txt", prompt)
    write_text(workspace / "stdout.txt", result.get("stdout", ""))
    write_text(workspace / "stderr.txt", result.get("stderr", ""))
    if result.get("openclaw_transcript"):
        write_json(workspace / "openclaw_transcript.json", result["openclaw_transcript"])
    write_json(
        workspace / "command.json",
        {
            "agent": result.get("agent"),
            "kind": result.get("kind"),
            "command": result.get("command"),
            "returncode": result.get("returncode"),
            "token_stats": result.get("token_stats", {}),
        },
    )
    parsed = result.get("parsed", {})
    write_json(
        workspace / "summary.json",
        {
            "agent": result.get("agent"),
            "kind": result.get("kind"),
            "returncode": result.get("returncode"),
            "token_stats": result.get("token_stats", {}),
            "answer": parsed.get("answer", parsed.get("raw_output", "")),
            "confidence": parsed.get("confidence", 0.0),
            "approach": parsed.get("approach", parsed.get("final_method", "")),
            "artifacts": parsed.get("artifacts", []),
            "assumptions": parsed.get("assumptions", []),
            "openclaw_transcript_usage": result.get("openclaw_transcript_usage", {}),
            "log_files": {
                "prompt": str(workspace / "prompt.txt"),
                "stdout": str(workspace / "stdout.txt"),
                "stderr": str(workspace / "stderr.txt"),
                "command": str(workspace / "command.json"),
                "stage_output": str(workspace / "stage_output.json"),
                "transcript": str(workspace / "openclaw_transcript.json") if result.get("openclaw_transcript") else "",
            },
        },
    )


def _print_stage_log(stage: str, agent_name: str, result: Dict) -> None:
    token_stats = result.get("token_stats", {})
    print(
        f"[{stage}] agent={agent_name} rc={result.get('returncode')} "
        f"input_tokens={token_stats.get('input_token_len', 0)} "
        f"output_tokens={token_stats.get('output_token_len', 0)} "
        f"total_tokens={token_stats.get('token_len', 0)}",
        flush=True,
    )


def _append_run_log(output_dir: Path, message: str) -> None:
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}\n"
    with _LOG_LOCK:
        append_text(output_dir / "run.log", line)


def _run_single_stage_agent(
    output_dir: Path,
    stage: str,
    task_file: Path,
    agent: AgentSpec,
    prompt: str,
    prepare_inputs: Optional[Callable[[Path], None]] = None,
) -> Tuple[str, Dict, Dict]:
    workspace = _prepare_workspace(output_dir, stage, agent.name, task_file)
    if prepare_inputs is not None:
        prepare_inputs(workspace)
    _append_run_log(output_dir, f"[{stage}] start agent={agent.name}")
    print(f"[{stage}] start agent={agent.name}", flush=True)
    result = run_agent(agent, prompt, workspace)
    result["agent"] = agent.name
    _write_agent_logs(workspace, prompt, result)
    write_json(output_dir / stage / agent.name / "stage_output.json", result)
    _print_stage_log(stage, agent.name, result)
    token_stats = result.get("token_stats", {})
    _append_run_log(
        output_dir,
        (
            f"[{stage}] done agent={agent.name} rc={result.get('returncode')} "
            f"input_tokens={token_stats.get('input_token_len', 0)} "
            f"output_tokens={token_stats.get('output_token_len', 0)} "
            f"total_tokens={token_stats.get('token_len', 0)}"
        ),
    )
    summary = _summary_from_stage_output(result, workspace, task_file)
    return agent.name, result, summary


def _run_stage_parallel(
    output_dir: Path,
    stage: str,
    task_file: Path,
    agents: List[AgentSpec],
    prompt_builder: Callable[[AgentSpec, Path], str],
    input_preparer: Optional[Callable[[AgentSpec, Path], None]],
    with_summary: bool,
) -> Tuple[List[Dict], List[Dict]]:
    results_by_agent: Dict[str, Dict] = {}
    summaries_by_agent: Dict[str, Dict] = {}
    max_workers = max(1, len(agents))
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=f"consensus-{stage}") as executor:
        future_map = {
            executor.submit(
                _run_single_stage_agent,
                output_dir,
                stage,
                task_file,
                agent,
                prompt_builder(agent, output_dir / stage / agent.name),
                None if input_preparer is None else lambda workspace, agent=agent: input_preparer(agent, workspace),
            ): agent.name
            for agent in agents
        }
        for future in as_completed(future_map):
            agent_name, result, summary = future.result()
            results_by_agent[agent_name] = result
            summaries_by_agent[agent_name] = summary
    ordered_results = [results_by_agent[agent.name] for agent in agents]
    if with_summary:
        ordered_summaries = [summaries_by_agent[agent.name] for agent in agents]
    else:
        ordered_summaries = []
    return ordered_results, ordered_summaries


def run_consensus_task(task_file: Path, agents: List[AgentSpec], output_dir: Path, verify_cmd: Optional[str] = None) -> Dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_text(output_dir / "run.log", "")
    print(f"[task] start task_file={task_file}", flush=True)
    _append_run_log(output_dir, f"[task] start task_file={task_file}")

    independent_results, independent_summaries = _run_stage_parallel(
        output_dir=output_dir,
        stage="independent",
        task_file=task_file,
        agents=agents,
        prompt_builder=lambda agent, workspace: independent_prompt(task_file, agent.name, workspace),
        input_preparer=None,
        with_summary=True,
    )

    independent_result_map = {result["agent"]: result for result in independent_results}
    review_results, _ = _run_stage_parallel(
        output_dir=output_dir,
        stage="reviews",
        task_file=task_file,
        agents=agents,
        prompt_builder=lambda agent, workspace: review_prompt(
            task_file,
            agent.name,
            workspace,
        ),
        input_preparer=lambda agent, workspace: _prepare_review_inputs(
            workspace,
            independent_result_map[agent.name].get("parsed", {}),
            [s for s in independent_summaries if s["agent"] != agent.name],
        ),
        with_summary=False,
    )

    review_result_map = {result["agent"]: result for result in review_results}
    revised_results, revised_summaries = _run_stage_parallel(
        output_dir=output_dir,
        stage="revised",
        task_file=task_file,
        agents=agents,
        prompt_builder=lambda agent, workspace: revise_prompt(
            task_file,
            agent.name,
            workspace,
        ),
        input_preparer=lambda agent, workspace: _prepare_revise_inputs(
            workspace,
            independent_result_map[agent.name].get("parsed", {}),
            review_result_map[agent.name].get("parsed", {}),
            [s for s in independent_summaries if s["agent"] != agent.name],
        ),
        with_summary=True,
    )

    consensus_votes, _ = _run_stage_parallel(
        output_dir=output_dir,
        stage="consensus",
        task_file=task_file,
        agents=agents,
        prompt_builder=lambda agent, workspace: consensus_prompt(task_file, agent.name, workspace),
        input_preparer=lambda agent, workspace: _prepare_consensus_inputs(workspace, revised_summaries),
        with_summary=False,
    )

    selection = choose_final_agent(revised_results, revised_summaries, consensus_votes)
    winning_agent = selection["winner"]
    print(f"[selection] winning_agent={winning_agent} scores={selection['scores']}", flush=True)
    _append_run_log(output_dir, f"[selection] winning_agent={winning_agent} scores={selection['scores']}")
    final_workspace = output_dir / "final_workspace"
    copy_tree(output_dir / "revised" / winning_agent, final_workspace)

    verification = {"enabled": False}
    if verify_cmd:
        import shlex
        import subprocess

        completed = subprocess.run(
            shlex.split(verify_cmd),
            cwd=str(final_workspace),
            text=True,
            capture_output=True,
        )
        verification = {
            "enabled": True,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        write_json(output_dir / "verification.json", verification)
        print(f"[verify] rc={completed.returncode}", flush=True)
        _append_run_log(output_dir, f"[verify] rc={completed.returncode}")

    report = {
        "task_file": str(task_file),
        "winning_agent": winning_agent,
        "selection_scores": selection["scores"],
        "independent_summaries": independent_summaries,
        "revised_summaries": revised_summaries,
        "stage_token_stats": {
            "independent": {r["agent"]: r.get("token_stats", {}) for r in independent_results},
            "review": {r["agent"]: r.get("token_stats", {}) for r in review_results},
            "revised": {r["agent"]: r.get("token_stats", {}) for r in revised_results},
            "consensus": {r["agent"]: r.get("token_stats", {}) for r in consensus_votes},
        },
        "stage_log_files": {
            "independent": {
                agent.name: {
                    "prompt": str(output_dir / "independent" / agent.name / "prompt.txt"),
                    "stdout": str(output_dir / "independent" / agent.name / "stdout.txt"),
                    "stderr": str(output_dir / "independent" / agent.name / "stderr.txt"),
                    "command": str(output_dir / "independent" / agent.name / "command.json"),
                    "summary": str(output_dir / "independent" / agent.name / "summary.json"),
                    "transcript": str(output_dir / "independent" / agent.name / "openclaw_transcript.json"),
                }
                for agent in agents
            },
            "review": {
                agent.name: {
                    "prompt": str(output_dir / "reviews" / agent.name / "prompt.txt"),
                    "stdout": str(output_dir / "reviews" / agent.name / "stdout.txt"),
                    "stderr": str(output_dir / "reviews" / agent.name / "stderr.txt"),
                    "command": str(output_dir / "reviews" / agent.name / "command.json"),
                    "summary": str(output_dir / "reviews" / agent.name / "summary.json"),
                    "transcript": str(output_dir / "reviews" / agent.name / "openclaw_transcript.json"),
                }
                for agent in agents
            },
            "revised": {
                agent.name: {
                    "prompt": str(output_dir / "revised" / agent.name / "prompt.txt"),
                    "stdout": str(output_dir / "revised" / agent.name / "stdout.txt"),
                    "stderr": str(output_dir / "revised" / agent.name / "stderr.txt"),
                    "command": str(output_dir / "revised" / agent.name / "command.json"),
                    "summary": str(output_dir / "revised" / agent.name / "summary.json"),
                    "transcript": str(output_dir / "revised" / agent.name / "openclaw_transcript.json"),
                }
                for agent in agents
            },
            "consensus": {
                agent.name: {
                    "prompt": str(output_dir / "consensus" / agent.name / "prompt.txt"),
                    "stdout": str(output_dir / "consensus" / agent.name / "stdout.txt"),
                    "stderr": str(output_dir / "consensus" / agent.name / "stderr.txt"),
                    "command": str(output_dir / "consensus" / agent.name / "command.json"),
                    "summary": str(output_dir / "consensus" / agent.name / "summary.json"),
                    "transcript": str(output_dir / "consensus" / agent.name / "openclaw_transcript.json"),
                }
                for agent in agents
            },
        },
        "verification": verification,
    }
    write_json(output_dir / "consensus_report.json", report)
    print(f"[task] done report={output_dir / 'consensus_report.json'}", flush=True)
    _append_run_log(output_dir, f"[task] done report={output_dir / 'consensus_report.json'}")
    return report
