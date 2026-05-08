from collections import Counter
from pathlib import Path
import re


WORKDIR = Path(__file__).resolve().parent

SOURCE_FILES = [
    Path("/Users/tomato/Documents/potato/project/YFD/results/agent_task_with_memory/openclaw/task_01_macd_rsi_filter/result.txt"),
    Path("/Users/tomato/Documents/potato/project/YFD/results/agent_task_with_memory/claude/task_01_macd_rsi_filter/result.txt"),
    Path("/Users/tomato/Documents/potato/project/YFD/results/agent_task_with_memory/codex/task_01_macd_rsi_filter/result.txt"),
    Path("/Users/tomato/Documents/potato/project/YFD/results/agent_task_with_memory/openclaw_sonnet/task_01_macd_rsi_filter/result.txt"),
    Path("/Users/tomato/Documents/potato/project/YFD/results/agent_task_with_memory/genericagent/task_01_macd_rsi_filter/result.txt"),
    Path("/Users/tomato/Documents/potato/project/YFD/results/agent_task_v2/openclaw/task_01_macd_rsi_filter/result.txt"),
    Path("/Users/tomato/Documents/potato/project/YFD/results/agent_task_v2/claude_opus/task_01_macd_rsi_filter/result.txt"),
    Path("/Users/tomato/Documents/potato/project/YFD/results/agent_task_v2/claude_sonnet/task_01_macd_rsi_filter/result.txt"),
    Path("/Users/tomato/Documents/potato/project/YFD/results/agent_task_v2/codex/task_01_macd_rsi_filter/result.txt"),
    Path("/Users/tomato/Documents/potato/project/YFD/results/agent_task_v2/genericagent/task_01_macd_rsi_filter/result.txt"),
    Path("/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_01_macd_rsi_filter/independent/ga/result.txt"),
]

CODE_RE = re.compile(r"^3\d{5}$")


def load_codes(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return [line.strip() for line in lines if CODE_RE.fullmatch(line.strip())]


def main() -> None:
    counts: Counter[str] = Counter()
    for path in SOURCE_FILES:
        counts.update(load_codes(path))

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    top10 = [code for code, _ in ranked[:10]]
    (WORKDIR / "result.txt").write_text(
        "\n".join(top10) + ("\n" if top10 else ""),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
