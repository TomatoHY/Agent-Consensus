from pathlib import Path
from typing import Optional


def _base_prompt(stage: str, agent_name: str, task_path: Path, extra_paths: Optional[list] = None) -> str:
    lines = [
        f"stage: {stage}",
        f"agent: {agent_name}",
        "",
        "read_paths:",
        f"task_path: {task_path}",
        f"result_dir: {task_path.parent}",
    ]
    if extra_paths:
        for label, path in extra_paths:
            lines.append(f"{label}: {path}")
    lines.extend(["", "instructions:"])
    return "\n".join(lines)


def independent_prompt(task_file: Path, agent_name: str, workspace: Path) -> str:
    return (
        _base_prompt("independent_solve", agent_name, workspace / "task.md")
        + "\n"
        + (
            "Read the task file and solve it independently in the current directory. "
            "Write all generated code, txt, csv, json, and other result files into result_dir only. "
            "Do not save outputs to external temp folders or tool-specific temp directories. "
            "Return strict JSON with keys: answer, confidence, approach, assumptions, preferred_output, artifacts."
        )
    )


def review_prompt(task_file: Path, agent_name: str, workspace: Path) -> str:
    return (
        _base_prompt(
            "cross_review",
            agent_name,
            workspace / "task.md",
            [
                ("own_result_path", workspace / "own_result.json"),
                ("peer_summaries_path", workspace / "peer_summaries.json"),
            ],
        )
        + "\n"
        + (
            "Read the task and review files. Do not solve from scratch. "
            "Use peer artifact previews and output-contract coverage when comparing solutions. "
            "If you create any notes or result files, write them into result_dir only. "
            "Return strict JSON with keys: self_reflection, stronger_peers, suspected_issues, update_plan."
        )
    )


def revise_prompt(task_file: Path, agent_name: str, workspace: Path) -> str:
    return (
        _base_prompt(
            "revise",
            agent_name,
            workspace / "task.md",
            [
                ("own_result_path", workspace / "own_result.json"),
                ("review_result_path", workspace / "review_result.json"),
                ("peer_summaries_path", workspace / "peer_summaries.json"),
            ],
        )
        + "\n"
        + (
            "Revise your previous solution after reading the review and peer summary files. "
            "Work in the current directory and update files if needed. "
            "Write all generated code, txt, csv, json, and other result files into result_dir only. "
            "Do not save outputs to external temp folders or tool-specific temp directories. "
            "Return strict JSON with keys: answer, confidence, what_changed, final_method, preferred_output, artifacts."
        )
    )


def consensus_prompt(task_file: Path, agent_name: str, workspace: Path) -> str:
    return (
        _base_prompt(
            "consensus_vote",
            agent_name,
            workspace / "task.md",
            [("revised_summaries_path", workspace / "revised_summaries.json")],
        )
        + "\n"
        + (
            "Read the revised summaries file and choose the best final scheme. "
            "Prefer solutions that satisfy output contract, contain executable artifacts or explicit result files, "
            "and provide concrete evidence. If you create any notes or merged outputs, write them into result_dir only. "
            "Return strict JSON with keys: preferred_agent, confidence, reasons, merge_notes."
        )
    )
