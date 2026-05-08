import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(text)


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Union[Dict[str, Any], List[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_workspace_files(workspace: Path) -> List[str]:
    files = []
    for path in sorted(workspace.rglob("*")):
        if path.is_file():
            files.append(str(path.relative_to(workspace)))
    return files


def read_preview(path: Path, max_chars: int = 600) -> str:
    if not path.exists() or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:max_chars]


def infer_output_contract(task_markdown: str) -> List[str]:
    matches = re.findall(r"`([^`]+\.(?:txt|csv|json|jsonl|md|py))`", task_markdown)
    seen = set()
    out = []
    for item in matches:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
