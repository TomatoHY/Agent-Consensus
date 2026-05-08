from typing import Dict, List


def _safe_conf(value) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return 0.0


def _artifact_score(summary: Dict) -> float:
    score = 0.0
    workspace_files = summary.get("workspace_files", [])
    result_files = summary.get("result_files", [])
    code_files = summary.get("code_files", [])
    contract_hits = summary.get("contract_hits", [])
    answer = str(summary.get("answer", "")).strip()

    if result_files:
        score += 1.5
    if code_files:
        score += 1.0
    if contract_hits:
        score += min(len(contract_hits), 3) * 0.5
    if workspace_files:
        score += min(len(workspace_files), 5) * 0.05
    if answer:
        score += 0.2
    if summary.get("result_preview"):
        score += 0.4
    return score


def choose_final_agent(revised_results: List[Dict], revised_summaries: List[Dict], consensus_votes: List[Dict]) -> Dict:
    scores = {}
    revised_map = {item["agent"]: item for item in revised_results}
    summary_map = {item["agent"]: item for item in revised_summaries}

    for vote in consensus_votes:
        parsed = vote.get("parsed", {})
        preferred = parsed.get("preferred_agent")
        if preferred not in revised_map:
            continue
        scores.setdefault(preferred, 0.0)
        scores[preferred] += 1.0 + _safe_conf(parsed.get("confidence"))

    for agent_name, item in revised_map.items():
        scores.setdefault(agent_name, 0.0)
        scores[agent_name] += _safe_conf(item.get("parsed", {}).get("confidence"))
        scores[agent_name] += _artifact_score(summary_map.get(agent_name, {}))

    winner = max(scores.items(), key=lambda kv: kv[1])[0]
    return {
        "winner": winner,
        "scores": scores,
        "winning_result": revised_map[winner],
    }
