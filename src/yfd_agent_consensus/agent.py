import json
import os
import re
import shlex
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


YFD_ROOT = Path("/Users/tomato/Documents/potato/project/YFD")
GENERICAGENT_ROOT = Path("/Users/tomato/Documents/potato/project/GenericAgent")
GENERICAGENT_CONFIG_NAME = "claude_config_yfd"
CLAUDE_MODEL = "claude-sonnet-4-6"
OPENCLAW_MODEL = "ccvibe/claude-sonnet-4-6"
OPENCLAW_AGENT_ID = "main"
OPENCLAW_AGENTS_ROOT = Path.home() / ".openclaw" / "agents"
OPENCLAW_PROMPT_FILENAME = "openclaw_prompt.txt"


@dataclass
class AgentSpec:
    name: str
    cmd: Optional[str] = None
    kind: Optional[str] = None
    model: Optional[str] = None


def load_agents_config(path: Path) -> List[AgentSpec]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        AgentSpec(
            name=item["name"],
            cmd=item.get("cmd"),
            kind=item.get("kind"),
            model=item.get("model"),
        )
        for item in payload
    ]


def _parse_json_from_text(text: str) -> Dict[str, Any]:
    text = text.strip()
    if not text:
        return {}
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {"raw_output": obj}
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            obj = json.loads(match.group(0))
            return obj if isinstance(obj, dict) else {"raw_output": obj}
        except json.JSONDecodeError:
            pass
    return {"raw_output": text}


def _estimate_token_len(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _estimate_token_breakdown(*, prompt: str = "", stdout: str = "", stderr: str = "", aux_output: str = "") -> Dict[str, int]:
    prompt_token_len = _estimate_token_len(prompt)
    stdout_token_len = _estimate_token_len(stdout)
    stderr_token_len = _estimate_token_len(stderr)
    aux_output_token_len = _estimate_token_len(aux_output)
    token_len = prompt_token_len + stdout_token_len + stderr_token_len + aux_output_token_len
    return {
        "prompt_token_len": prompt_token_len,
        "stdout_token_len": stdout_token_len,
        "stderr_token_len": stderr_token_len,
        "aux_output_token_len": aux_output_token_len,
        "token_len": token_len,
    }


def _parse_genericagent_usage(stdout_text: str) -> Dict[str, int]:
    input_tokens = 0
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0
    output_token_len = 0
    for match in re.finditer(r"\[Cache\]\s+input=(\d+)\s+creation=(\d+)\s+read=(\d+)", stdout_text):
        input_tokens += int(match.group(1))
        cache_creation_input_tokens += int(match.group(2))
        cache_read_input_tokens += int(match.group(3))
    for match in re.finditer(r"\[Output\]\s+tokens=(\d+)\s+stop_reason=([A-Za-z0-9_:-]+)", stdout_text):
        output_token_len += int(match.group(1))
    if not any([input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_token_len]):
        return {}
    input_token_len = input_tokens + cache_creation_input_tokens
    return {
        "input_tokens": input_tokens,
        "cache_creation_input_tokens": cache_creation_input_tokens,
        "cache_read_input_tokens": cache_read_input_tokens,
        "output_tokens": output_token_len,
        "input_token_len": input_token_len,
        "output_token_len": output_token_len,
        "token_len": input_token_len + output_token_len,
    }


def _parse_claude_usage(stdout_text: str) -> Dict[str, int]:
    input_tokens = 0
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0
    output_tokens = 0
    for line in stdout_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = payload.get("usage")
        if usage is None and isinstance(payload.get("message"), dict):
            usage = payload["message"].get("usage")
        if usage is None and isinstance(payload.get("event"), dict):
            usage = payload["event"].get("usage")
        if not isinstance(usage, dict):
            continue
        input_tokens += int(usage.get("input_tokens", 0))
        cache_creation_input_tokens += int(usage.get("cache_creation_input_tokens", 0))
        cache_read_input_tokens += int(usage.get("cache_read_input_tokens", 0))
        output_tokens += int(usage.get("output_tokens", 0))
    if not any([input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens]):
        return {}
    input_token_len = input_tokens + cache_creation_input_tokens
    return {
        "input_tokens": input_tokens,
        "cache_creation_input_tokens": cache_creation_input_tokens,
        "cache_read_input_tokens": cache_read_input_tokens,
        "output_tokens": output_tokens,
        "input_token_len": input_token_len,
        "output_token_len": output_tokens,
        "token_len": input_token_len + output_tokens,
    }


def _parse_openclaw_usage(stdout_text: str) -> Dict[str, int]:
    try:
        payload = json.loads(stdout_text)
    except json.JSONDecodeError:
        return {}
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return {}
    agent_meta = meta.get("agentMeta")
    if not isinstance(agent_meta, dict):
        return {}
    usage = agent_meta.get("lastCallUsage")
    if not isinstance(usage, dict):
        usage = agent_meta.get("usage")
    if not isinstance(usage, dict):
        return {}
    prompt_tokens = int(agent_meta.get("promptTokens", 0) or 0)
    input_tokens = int(usage.get("input", 0))
    output_tokens = int(usage.get("output", 0))
    cache_read_tokens = int(usage.get("cacheRead", 0))
    cache_write_tokens = int(usage.get("cacheWrite", 0))
    provider_total_tokens = int(usage.get("total", 0))
    input_token_len = prompt_tokens or (input_tokens + cache_write_tokens)
    return {
        "prompt_tokens": prompt_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": cache_write_tokens,
        "provider_total_tokens": provider_total_tokens,
        "total_tokens": output_tokens,
        "input_token_len": input_token_len,
        "output_token_len": output_tokens,
        "token_len": output_tokens,
    }


def _usage_has_signal(usage: Optional[Dict[str, int]]) -> bool:
    if not usage:
        return False
    signal_keys = (
        "input_tokens",
        "output_tokens",
        "cache_write_tokens",
        "cache_read_tokens",
        "cache_creation_input_tokens",
        "cached_input_tokens",
        "total_tokens",
        "token_len",
    )
    return any(int(usage.get(key, 0) or 0) > 0 for key in signal_keys)


def _get_openclaw_agent_store_dir(agent_id: str) -> Path:
    normalized_id = agent_id.replace(":", "-").lower()
    direct_dir = OPENCLAW_AGENTS_ROOT / agent_id
    if direct_dir.exists():
        return direct_dir
    normalized_dir = OPENCLAW_AGENTS_ROOT / normalized_id
    if normalized_dir.exists():
        return normalized_dir
    return direct_dir


def _cleanup_openclaw_sessions(agent_id: str) -> None:
    sessions_dir = _get_openclaw_agent_store_dir(agent_id) / "sessions"
    if not sessions_dir.exists():
        return
    for pattern in ("*.jsonl", "*.jsonl.lock", "*.ndjson"):
        for path in sessions_dir.rglob(pattern):
            try:
                path.unlink()
            except OSError:
                pass
    sessions_store = sessions_dir / "sessions.json"
    if sessions_store.exists():
        try:
            sessions_store.unlink()
        except OSError:
            pass


def _resolve_openclaw_session_id_from_store(agent_id: str) -> Optional[str]:
    sessions_store = _get_openclaw_agent_store_dir(agent_id) / "sessions" / "sessions.json"
    if not sessions_store.exists():
        return None
    try:
        payload = json.loads(sessions_store.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    newest_entry = None
    newest_timestamp = -1
    for entry in payload.values():
        if not isinstance(entry, dict):
            continue
        session_id = entry.get("sessionId")
        updated_at = entry.get("updatedAt")
        if not session_id:
            continue
        if isinstance(updated_at, (int, float)) and updated_at > newest_timestamp:
            newest_timestamp = updated_at
            newest_entry = entry
    if newest_entry:
        return str(newest_entry.get("sessionId"))
    return None


def _find_recent_openclaw_session_path(agent_id: str, started_at: float) -> Optional[Path]:
    sessions_dir = _get_openclaw_agent_store_dir(agent_id) / "sessions"
    if not sessions_dir.exists():
        return None
    candidates = list(sessions_dir.rglob("*.jsonl")) + list(sessions_dir.rglob("*.ndjson"))
    if not candidates:
        return None
    tolerance_seconds = 5.0
    recent_candidates = [path for path in candidates if path.stat().st_mtime >= (started_at - tolerance_seconds)]
    pool = recent_candidates or candidates
    return max(pool, key=lambda path: path.stat().st_mtime)


def _load_openclaw_transcript(agent_id: str, started_at: float) -> List[Dict[str, Any]]:
    agent_dir = _get_openclaw_agent_store_dir(agent_id)
    transcript_path = None
    for attempt in range(15):
        resolved_session_id = _resolve_openclaw_session_id_from_store(agent_id)
        if resolved_session_id:
            sessions_dir = agent_dir / "sessions"
            for candidate in (
                sessions_dir / f"{resolved_session_id}.jsonl",
                sessions_dir / f"{resolved_session_id}.ndjson",
                sessions_dir / resolved_session_id / "transcript.jsonl",
                sessions_dir / resolved_session_id / "events.jsonl",
            ):
                if candidate.exists():
                    transcript_path = candidate
                    break
        if transcript_path is not None:
            break
        transcript_path = _find_recent_openclaw_session_path(agent_id, started_at)
        if transcript_path is not None:
            break
        if attempt < 14:
            time.sleep(1.0)
    if transcript_path is None or not transcript_path.exists():
        return []
    transcript = []
    for line in transcript_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            transcript.append(json.loads(line))
        except json.JSONDecodeError:
            transcript.append({"raw": line})
    return transcript


def _extract_openclaw_usage_from_transcript(transcript: List[Dict[str, Any]]) -> Dict[str, int]:
    prompt_tokens = 0
    last_usage: Dict[str, int] = {}
    request_count = 0
    for entry in transcript:
        if entry.get("type") != "message":
            continue
        msg = entry.get("message", {})
        if msg.get("role") != "assistant":
            continue
        usage = msg.get("usage", {})
        if not isinstance(usage, dict):
            continue
        request_count += 1
        last_usage = {
            "input_tokens": int(usage.get("input", 0) or 0),
            "output_tokens": int(usage.get("output", 0) or 0),
            "cache_read_tokens": int(usage.get("cacheRead", 0) or 0),
            "cache_write_tokens": int(usage.get("cacheWrite", 0) or 0),
            "provider_total_tokens": int(usage.get("totalTokens", 0) or 0),
        }
    for entry in transcript:
        if entry.get("type") != "message":
            continue
        msg = entry.get("message", {})
        if msg.get("role") != "assistant":
            continue
        prompt_tokens = int(msg.get("promptTokens", 0) or 0)
        if prompt_tokens > 0:
            break
    if not any(last_usage.values()) and prompt_tokens <= 0 and request_count == 0:
        return {}
    input_token_len = prompt_tokens or (last_usage.get("input_tokens", 0) + last_usage.get("cache_write_tokens", 0))
    return {
        "prompt_tokens": prompt_tokens,
        "input_tokens": last_usage.get("input_tokens", 0),
        "output_tokens": last_usage.get("output_tokens", 0),
        "cache_read_tokens": last_usage.get("cache_read_tokens", 0),
        "cache_write_tokens": last_usage.get("cache_write_tokens", 0),
        "request_count": request_count,
        "provider_total_tokens": last_usage.get("provider_total_tokens", 0),
        "total_tokens": last_usage.get("output_tokens", 0),
        "input_token_len": input_token_len,
        "output_token_len": last_usage.get("output_tokens", 0),
        "token_len": last_usage.get("output_tokens", 0),
    }


def _parse_codex_usage(stdout_text: str) -> Dict[str, int]:
    for line in reversed(stdout_text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("type") != "turn.completed":
            continue
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            continue
        input_tokens = int(usage.get("input_tokens", 0))
        cached_input_tokens = int(usage.get("cached_input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        return {
            "input_tokens": input_tokens,
            "cached_input_tokens": cached_input_tokens,
            "output_tokens": output_tokens,
            "input_token_len": input_tokens + cached_input_tokens,
            "output_token_len": output_tokens,
            "token_len": input_tokens + cached_input_tokens + output_tokens,
        }
    return {}


def _get_agent_token_stats(
    agent_kind: Optional[str],
    *,
    prompt: str,
    stdout: str,
    stderr: str,
    aux_output: str = "",
    openclaw_transcript_usage: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    estimated = _estimate_token_breakdown(prompt=prompt, stdout=stdout, stderr=stderr, aux_output=aux_output)
    parsed: Dict[str, int] = {}
    if agent_kind == "codex":
        parsed = _parse_codex_usage(stdout)
    elif agent_kind == "genericagent":
        parsed = _parse_genericagent_usage(stdout)
    elif agent_kind == "claude":
        parsed = _parse_claude_usage(stdout)
    elif agent_kind == "openclaw":
        transcript_parsed = openclaw_transcript_usage if _usage_has_signal(openclaw_transcript_usage) else {}
        stdout_parsed = _parse_openclaw_usage(stdout)
        parsed = transcript_parsed if _usage_has_signal(transcript_parsed) else stdout_parsed
    if _usage_has_signal(parsed):
        estimated.update(parsed)
        estimated["token_source"] = "reported"
    else:
        estimated["input_token_len"] = estimated["prompt_token_len"]
        estimated["output_token_len"] = estimated["stdout_token_len"] + estimated["stderr_token_len"] + estimated["aux_output_token_len"]
        estimated["token_len"] = estimated["input_token_len"] + estimated["output_token_len"]
        estimated["token_source"] = "estimated"
    return estimated


def _run(
    cmd: List[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    stdin_text: Optional[str] = None,
    live_stdout_path: Optional[Path] = None,
    live_stderr_path: Optional[Path] = None,
) -> subprocess.CompletedProcess[str]:
    if live_stdout_path is not None:
        live_stdout_path.parent.mkdir(parents=True, exist_ok=True)
    if live_stderr_path is not None:
        live_stderr_path.parent.mkdir(parents=True, exist_ok=True)

    stdout_chunks: List[str] = []
    stderr_chunks: List[str] = []

    with subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE if stdin_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(cwd),
        bufsize=1,
    ) as process:
        if stdin_text is not None and process.stdin is not None:
            process.stdin.write(stdin_text)
            process.stdin.close()

        stdout_file = open(live_stdout_path, "w", encoding="utf-8") if live_stdout_path is not None else None
        stderr_file = open(live_stderr_path, "w", encoding="utf-8") if live_stderr_path is not None else None

        def _pump(stream, sink, chunks: List[str], file_handle) -> None:
            try:
                for line in iter(stream.readline, ""):
                    chunks.append(line)
                    sink.write(line)
                    sink.flush()
                    if file_handle is not None and not file_handle.closed:
                        file_handle.write(line)
                        file_handle.flush()
            finally:
                stream.close()

        stdout_thread = threading.Thread(
            target=_pump,
            args=(process.stdout, sys.stdout, stdout_chunks, stdout_file),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_pump,
            args=(process.stderr, sys.stderr, stderr_chunks, stderr_file),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        try:
            returncode = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            returncode = process.wait()
            stdout_thread.join()
            stderr_thread.join()
            if stdout_file is not None:
                stdout_file.close()
            if stderr_file is not None:
                stderr_file.close()
            raise

        stdout_thread.join()
        stderr_thread.join()
        if stdout_file is not None:
            stdout_file.close()
        if stderr_file is not None:
            stderr_file.close()

    return subprocess.CompletedProcess(cmd, returncode, "".join(stdout_chunks), "".join(stderr_chunks))


def _get_genericagent_llm_no(config_name: str = GENERICAGENT_CONFIG_NAME) -> int:
    mykey_path = GENERICAGENT_ROOT / "mykey.py"
    if not mykey_path.exists():
        return 0
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("genericagent_mykey_for_consensus", mykey_path)
    if spec is None or spec.loader is None:
        return 0
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target_cfg = getattr(module, config_name, None)
    if not isinstance(target_cfg, dict):
        return 0

    sys.path.insert(0, str(GENERICAGENT_ROOT))
    from agentmain import GeneraticAgent

    agent = GeneraticAgent()
    target_apibase = target_cfg.get("apibase")
    target_model = target_cfg.get("model")
    target_apikey = target_cfg.get("apikey")

    for idx, client in enumerate(agent.llmclients):
        backend = client.backend
        cfg = getattr(backend, "cfg", None)
        if not isinstance(cfg, dict):
            continue
        if cfg.get("apibase") == target_apibase and cfg.get("model") == target_model and cfg.get("apikey") == target_apikey:
            return idx
    return 0


def _read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _ensure_openclaw_model(model: str) -> None:
    current = subprocess.run(
        ["openclaw", "models", "status", "--plain"],
        check=False,
        text=True,
        capture_output=True,
    )
    current_model = (current.stdout or "").strip()
    if current_model == model:
        return
    subprocess.run(
        ["openclaw", "models", "set", model],
        check=False,
        text=True,
        capture_output=True,
    )


def _prepare_openclaw_message(prompt: str, cwd: Path) -> str:
    prompt_path = cwd / OPENCLAW_PROMPT_FILENAME
    prompt_path.write_text(prompt, encoding="utf-8")
    return (
        "Read the full task prompt from "
        f"{prompt_path}. Follow it exactly. "
        "Treat that file as the full user message. "
        "Return your final answer in the required format from that prompt."
    )


def _run_native_agent(
    agent: AgentSpec,
    prompt: str,
    cwd: Path,
    timeout_seconds: int,
    live_stdout_path: Optional[Path] = None,
    live_stderr_path: Optional[Path] = None,
) -> Any:
    kind = agent.kind
    if kind == "codex":
        final_path = cwd / "codex_final_message.txt"
        cmd = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--full-auto",
            "--json",
            "-C",
            str(cwd),
            "--add-dir",
            str(YFD_ROOT),
            "--add-dir",
            str(GENERICAGENT_ROOT),
            "-o",
            str(final_path),
            "-",
        ]
        completed = _run(
            cmd,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            stdin_text=prompt,
            live_stdout_path=live_stdout_path,
            live_stderr_path=live_stderr_path,
        )
        final_text = _read_text_if_exists(final_path)
        if final_text:
            completed = subprocess.CompletedProcess(completed.args, completed.returncode, completed.stdout + "\n" + final_text, completed.stderr)
        return completed, cmd, final_text

    if kind == "claude":
        cmd = [
            "claude",
            "-p",
            "--permission-mode",
            "bypassPermissions",
            "--verbose",
            "--model",
            agent.model or CLAUDE_MODEL,
            "--output-format",
            "stream-json",
            "--include-partial-messages",
            "--add-dir",
            str(YFD_ROOT),
            str(GENERICAGENT_ROOT),
            "-",
        ]
        return (
            _run(
                cmd,
                cwd=cwd,
                timeout_seconds=timeout_seconds,
                stdin_text=prompt,
                live_stdout_path=live_stdout_path,
                live_stderr_path=live_stderr_path,
            ),
            cmd,
            "",
        )

    if kind == "genericagent":
        run_key = f"consensus_{agent.name}_{cwd.name}_{os.getpid()}"
        llm_no = _get_genericagent_llm_no()
        ga_task_dir = GENERICAGENT_ROOT / "temp" / run_key
        ga_task_dir.mkdir(parents=True, exist_ok=True)
        (ga_task_dir / "input.txt").write_text(prompt, encoding="utf-8")
        cmd = [
            sys.executable,
            str(GENERICAGENT_ROOT / "agentmain.py"),
            "--task",
            run_key,
            "--llm_no",
            str(llm_no),
        ]
        completed = _run(
            cmd,
            cwd=GENERICAGENT_ROOT,
            timeout_seconds=timeout_seconds + 360,
            live_stdout_path=live_stdout_path,
            live_stderr_path=live_stderr_path,
        )
        ga_output = _read_text_if_exists(GENERICAGENT_ROOT / "temp" / run_key / "output.txt")
        if ga_output:
            completed = subprocess.CompletedProcess(completed.args, completed.returncode, completed.stdout + "\n" + ga_output, completed.stderr)
        return completed, cmd, ga_output

    if kind == "openclaw":
        _ensure_openclaw_model(agent.model or OPENCLAW_MODEL)
        started_at = time.time()
        _cleanup_openclaw_sessions(OPENCLAW_AGENT_ID)
        message = _prepare_openclaw_message(prompt, cwd)
        cmd = [
            "openclaw",
            "agent",
            "--local",
            "--agent",
            OPENCLAW_AGENT_ID,
            "--json",
            "--timeout",
            str(timeout_seconds),
            "--message",
            message,
        ]
        completed = _run(
            cmd,
            cwd=cwd,
            timeout_seconds=timeout_seconds + 60,
            live_stdout_path=live_stdout_path,
            live_stderr_path=live_stderr_path,
        )
        transcript = _load_openclaw_transcript(OPENCLAW_AGENT_ID, started_at)
        transcript_usage = _extract_openclaw_usage_from_transcript(transcript)
        transcript_text = json.dumps(transcript, ensure_ascii=False, indent=2) if transcript else ""
        return completed, cmd, "", transcript, transcript_usage, transcript_text

    raise ValueError(f"Unsupported native agent kind: {kind}")


def run_agent(agent: AgentSpec, prompt: str, cwd: Path, timeout_seconds: int = 1200) -> Dict[str, Any]:
    cmd_used: List[str]
    aux_output = ""
    openclaw_transcript: List[Dict[str, Any]] = []
    openclaw_transcript_usage: Dict[str, int] = {}
    transcript_text = ""
    trajectory_dir = cwd / "trajectory"
    live_stdout_path = trajectory_dir / "stdout.txt"
    live_stderr_path = trajectory_dir / "stderr.txt"
    if agent.kind:
        native_result = _run_native_agent(
            agent,
            prompt,
            cwd,
            timeout_seconds,
            live_stdout_path=live_stdout_path,
            live_stderr_path=live_stderr_path,
        )
        if agent.kind == "openclaw":
            completed, cmd_used, aux_output, openclaw_transcript, openclaw_transcript_usage, transcript_text = native_result
        else:
            completed, cmd_used, aux_output = native_result
    elif agent.cmd:
        cmd_used = shlex.split(agent.cmd)
        completed = _run(
            cmd_used,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            stdin_text=prompt,
            live_stdout_path=live_stdout_path,
            live_stderr_path=live_stderr_path,
        )
    else:
        raise ValueError(f"Agent {agent.name} must define either 'kind' or 'cmd'")
    token_stats = _get_agent_token_stats(
        agent.kind,
        prompt=prompt,
        stdout=completed.stdout,
        stderr=completed.stderr,
        aux_output=aux_output or transcript_text,
        openclaw_transcript_usage=openclaw_transcript_usage,
    )
    payload = {
        "agent": agent.name,
        "kind": agent.kind or "custom",
        "command": cmd_used,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "token_stats": token_stats,
    }
    if openclaw_transcript:
        payload["openclaw_transcript"] = openclaw_transcript
    if openclaw_transcript_usage:
        payload["openclaw_transcript_usage"] = openclaw_transcript_usage
    if completed.returncode != 0:
        payload["parsed"] = {"raw_output": completed.stdout.strip(), "error": completed.stderr.strip()}
        return payload
    payload["parsed"] = _parse_json_from_text(completed.stdout)
    return payload
