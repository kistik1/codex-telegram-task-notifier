#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

HOOK_DIR = Path(__file__).resolve().parent
CODEX_DIR = HOOK_DIR.parent
ENV_FILE = Path(os.environ.get("CODEX_TELEGRAM_ENV_FILE", str(HOOK_DIR / "telegram.env")))
STATE_DIR = HOOK_DIR / "state"
SESSIONS_DIR = CODEX_DIR / "sessions"
SESSION_STATE_DIR = STATE_DIR / "sessions"
OFFSET_FILE = STATE_DIR / "telegram_update_offset"
BOT_STATE_FILE = STATE_DIR / "bot_state.json"
EVENT_LOG_FILE = STATE_DIR / "notify_events.jsonl"
ALLOWED_EVENT_TYPES = {"agent-turn-complete", "approval-requested", "user-input-requested"}


def ensure_dirs() -> None:
    SESSION_STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def post_telegram(token: str, chat_id: str, text: str) -> dict[str, Any]:
    data = urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        method="POST",
    )
    with urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
    if not body:
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"raw": body}


def get_telegram(token: str, offset: int | None) -> list[dict[str, Any]]:
    params = {"timeout": 30}
    if offset is not None:
        params["offset"] = offset
    url = f"https://api.telegram.org/bot{token}/getUpdates?{urlencode(params)}"
    with urlopen(url, timeout=40) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("result", [])


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def short_time_utc() -> str:
    return datetime.now(timezone.utc).strftime("%d/%m %H:%M")


def parse_utc_timestamp(value: str) -> float | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S UTC", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    return None


def key_variants(key: str) -> list[str]:
    variants = {key}
    variants.add(key.replace("_", "-"))
    variants.add(key.replace("-", "_"))
    parts = key.replace("-", "_").split("_")
    if len(parts) > 1:
        camel = parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])
        variants.add(camel)
    return list(variants)


def payload_value(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        for variant in key_variants(key):
            value = payload.get(variant)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def infer_risk_lines(state: dict[str, Any]) -> list[str]:
    payload = state.get("raw_payload", {}) if isinstance(state.get("raw_payload"), dict) else {}
    text_parts = [
        state.get("message", ""),
        payload_value(payload, "reason", "command", "prompt", "title", "task"),
        json.dumps(payload, ensure_ascii=False),
    ]
    haystack = " ".join(part for part in text_parts if isinstance(part, str)).lower()

    prod_terms = [
        "production", "prod", "systemctl", "service", "restart", "reload",
        "kill ", "pm2", "docker", "compose", "nginx", "caddy", "port ",
        "deploy", "running process", "stop process",
    ]
    prod_high_terms = [
        "production", "prod", "systemctl restart", "systemctl stop",
        "kill ", "stop process", "deploy",
    ]
    system_terms = [
        "rm -", "sudo", "chmod", "chown", "/etc/", "/usr/", "systemd",
        "iptables", "ufw", "mount", "umount", "kill ", "pkill", "reboot",
    ]
    system_high_terms = [
        "rm -rf", "reboot", "iptables", "ufw", "mount", "umount", "/etc/",
        "sudo", "pkill", "systemd",
    ]
    data_terms = [
        "delete", "truncate", "drop ", "database", "db", "migration",
        "overwrite", "write", "mv ", "cp ", "backup", "restore", "secret",
        "token", "credential", "env", ".env",
    ]
    data_high_terms = [
        "drop ", "delete", "truncate", "database", "migration", "overwrite",
        "restore", "secret", "token", "credential", ".env",
    ]

    def classify(base_terms: list[str], high_terms: list[str]) -> str:
        if any(term in haystack for term in high_terms):
            return "high"
        if any(term in haystack for term in base_terms):
            return "medium"
        return "low"

    return [
        f"Prod/running process impact: {classify(prod_terms, prod_high_terms)}",
        f"System risk: {classify(system_terms, system_high_terms)}",
        f"Data risk: {classify(data_terms, data_high_terms)}",
    ]


def session_id_from_payload(payload: dict[str, Any]) -> str:
    return payload_value(payload, "thread_id", "threadId", "session_id", "sessionId", "id") or "unknown"


def update_session_state(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_dirs()
    session_id = session_id_from_payload(payload)
    path = SESSION_STATE_DIR / f"{session_id}.json"
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    event_type = payload_value(payload, "type") or "unknown"
    status = existing.get("status", "active")
    if event_type == "agent-turn-complete":
        status = "completed"
    elif event_type == "approval-requested":
        status = "waiting_on_approval"
    elif event_type == "user-input-requested":
        status = "waiting_on_user_input"
    elif event_type:
        status = "active"

    updated = {
        "session_id": session_id,
        "status": status,
        "event_type": event_type,
        "updated_at": utc_now(),
        "cwd": payload_value(payload, "cwd", "workspace"),
        "turn_id": payload_value(payload, "turn_id", "turnId"),
        "message": payload_value(
            payload,
            "message",
            "reason",
            "prompt",
            "title",
            "task",
            "last_assistant_message",
            "last-assistant-message",
        ),
        "raw_payload": payload,
    }
    merged = {**existing, **{k: v for k, v in updated.items() if v not in ("", None, {})}}
    path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return merged


def append_event_log(payload: dict[str, Any], state: dict[str, Any]) -> None:
    ensure_dirs()
    entry = {
        "logged_at": utc_now(),
        "event_type": state.get("event_type", ""),
        "session_id": state.get("session_id", ""),
        "turn_id": state.get("turn_id", ""),
        "cwd": state.get("cwd", ""),
        "message": state.get("message", ""),
        "raw_payload": payload,
    }
    with EVENT_LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def should_notify(state: dict[str, Any]) -> bool:
    event_type = state.get("event_type")
    turn_id = state.get("turn_id", "")
    dedupe_key = f"{event_type}:{turn_id}"
    if state.get("last_notified_key") == dedupe_key:
        return False
    state["last_notified_key"] = dedupe_key
    path = SESSION_STATE_DIR / f"{state['session_id']}.json"
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return True


def format_notification(state: dict[str, Any]) -> str:
    event_type = state.get("event_type", "unknown")
    cwd = state.get("cwd", "")
    message = state.get("message", "")
    session_id = state.get("session_id", "unknown")
    header_map = {
        "agent-turn-complete": "Codex task complete",
        "approval-requested": "Codex approval needed",
        "user-input-requested": "Codex input needed",
    }
    lines = [f"{header_map.get(event_type, 'Codex event')} {short_time_utc()}"]
    lines.append(f"Session: {session_id}")
    if cwd:
        lines.append(f"Worktree: {cwd}")
    if event_type == "approval-requested":
        lines.extend(infer_risk_lines(state))
    if message:
        lines.append(f"Details: {message[:500]}")
    return "\n".join(lines)


def handle_notify() -> int:
    payload = read_payload()
    if not payload:
        return 0
    env = load_env()
    state = update_session_state(payload)
    append_event_log(payload, state)
    if not should_notify(state):
        return 0
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return 0
    if state.get("event_type") not in ALLOWED_EVENT_TYPES:
        return 0
    try:
        post_telegram(token, chat_id, format_notification(state))
    except Exception:
        return 0
    return 0


def find_live_codex_processes() -> list[dict[str, str]]:
    try:
        output = subprocess.check_output(["ps", "-eo", "pid=,etimes=,cmd="], text=True)
    except Exception:
        return []
    processes = []
    for line in output.splitlines():
        if "codex" not in line or " rg " in line:
            continue
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        pid, etimes, cmd = parts
        if "bin/codex" not in cmd:
            continue
        processes.append({"pid": pid, "age_seconds": etimes, "cmd": cmd})
    return processes


def project_name_from_cwd(cwd: str) -> str:
    if not cwd:
        return ""
    path = Path(cwd)
    try:
        git_root = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if git_root:
            return Path(git_root).name
    except Exception:
        pass
    return path.name if path.name else str(path)


def one_line(text: str, limit: int = 120) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def is_status_meta_text(text: str) -> bool:
    lowered = " ".join(text.split()).lower()
    if not lowered:
        return True
    return (
        lowered.startswith("/codex_status")
        or lowered.startswith("open sessions:")
        or lowered.startswith("live sessions:")
        or lowered == "test"
        or "no open sessions detected" in lowered
        or "no live sessions detected" in lowered
    )


def normalize_summary(text: str) -> str:
    lowered = text.lower()
    if "codex_status" in lowered or ("open sesion" in lowered or "open session" in lowered):
        return "Updating codex_status output and session summaries"
    if "telegram" in lowered and "bot" in lowered:
        return "Working on Telegram bot integration"
    return text


def read_session_meta(path: Path) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "session_id": path.stem.split("-")[-1],
        "cwd": "",
        "last_timestamp": "",
        "last_event_type": "",
        "completed": False,
        "path": str(path),
        "summary": "",
    }
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return meta
    for line in lines[:5]:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "session_meta":
            payload = obj.get("payload", {})
            meta["session_id"] = payload.get("id", meta["session_id"])
            meta["cwd"] = payload.get("cwd", "")
            break
    for line in reversed(lines[-80:]):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = obj.get("payload", {})
        meta["last_timestamp"] = obj.get("timestamp", "")
        if obj.get("type") == "event_msg" and isinstance(payload, dict):
            meta["last_event_type"] = payload.get("type", "")
            if payload.get("type") == "task_complete":
                meta["completed"] = True
            break
        if obj.get("type") == "response_item":
            payload_type = payload.get("type", "")
            if payload_type:
                meta["last_event_type"] = payload_type
                break
    latest_agent_summary = ""
    for line in reversed(lines[-160:]):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = obj.get("payload", {})
        if obj.get("type") == "event_msg" and isinstance(payload, dict):
            if payload.get("type") == "user_message":
                summary = one_line(str(payload.get("message", "")))
                if summary and not is_status_meta_text(summary):
                    meta["summary"] = summary
                    break
            if payload.get("type") == "agent_message" and not latest_agent_summary:
                summary = one_line(str(payload.get("message", "")))
                if summary:
                    latest_agent_summary = summary
        if obj.get("type") == "response_item" and payload.get("type") == "message":
            content = payload.get("content", [])
            if isinstance(content, list):
                for item in content:
                    text = item.get("text", "") if isinstance(item, dict) else ""
                    summary = one_line(str(text))
                    if summary and not latest_agent_summary:
                        latest_agent_summary = summary
                        break
    if not meta["summary"] and latest_agent_summary:
        meta["summary"] = latest_agent_summary
    meta["mtime"] = path.stat().st_mtime
    return meta


def load_state_cache() -> dict[str, dict[str, Any]]:
    ensure_dirs()
    cache: dict[str, dict[str, Any]] = {}
    for file_path in SESSION_STATE_DIR.glob("*.json"):
        try:
            cache[file_path.stem] = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
    return cache


def collect_status() -> list[dict[str, Any]]:
    state_cache = load_state_cache()
    sessions = []
    files = sorted(SESSIONS_DIR.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    now = time.time()
    recent_log_session_ids = set()
    for path in files[:20]:
        meta = read_session_meta(path)
        session_id = meta["session_id"]
        recent_log_session_ids.add(session_id)
        merged = {**meta, **state_cache.get(session_id, {})}
        if "status" not in merged:
            if merged.get("completed"):
                merged["status"] = "completed"
            elif now - merged.get("mtime", now) < 1800:
                merged["status"] = "active"
            else:
                merged["status"] = "recent"
        sessions.append(merged)
    results = []
    seen_ids = set()
    for session in sessions:
        session_id = session.get("session_id")
        if not session_id or session_id in seen_ids:
            continue
        seen_ids.add(session_id)
        if session.get("status") in {"active", "waiting_on_approval", "waiting_on_user_input"}:
            results.append(session)
    for session_id, cached in state_cache.items():
        if session_id in seen_ids:
            continue
        updated_ts = parse_utc_timestamp(str(cached.get("updated_at", "")))
        is_recent = updated_ts is not None and (now - updated_ts) < 900
        if session_id not in recent_log_session_ids and not is_recent:
            continue
        if cached.get("status") in {"active", "waiting_on_approval", "waiting_on_user_input"}:
            results.append(cached)
            seen_ids.add(session_id)
    return results[:10]


def collect_recent_sessions(limit: int = 10) -> list[dict[str, Any]]:
    files = sorted(SESSIONS_DIR.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    sessions = []
    seen_ids = set()
    for path in files:
        meta = read_session_meta(path)
        session_id = meta.get("session_id")
        if not session_id or session_id in seen_ids:
            continue
        seen_ids.add(session_id)
        sessions.append(meta)
        if len(sessions) >= limit:
            break
    return sessions


def summarize_work(session: dict[str, Any]) -> str:
    summary = one_line(normalize_summary(str(session.get("summary", ""))))
    if summary:
        return summary
    message = one_line(normalize_summary(str(session.get("message", ""))))
    if message:
        return message
    project = project_name_from_cwd(session.get("cwd", ""))
    if project:
        return f"Working in {project}"
    return "No recent summary"


def format_status_message() -> str:
    sessions = collect_status()
    live = find_live_codex_processes()
    active_sessions = [s for s in sessions if s.get("status") == "active"]
    if active_sessions:
        live_sessions = active_sessions[: len(live)]
    else:
        live_sessions = collect_recent_sessions(limit=len(live)) if live else []
    live_session_count = len(live)

    lines = [f"Open sessions: {len(sessions)}"]
    if not sessions:
        lines.append("No open sessions detected.")
    else:
        for session in sessions:
            status = session.get("status", "unknown")
            project = project_name_from_cwd(session.get("cwd", "")) or "unknown"
            lines.append(f"- {project} | {status} | {summarize_work(session)}")

    lines.append(f"Live sessions: {live_session_count}")
    if not live_sessions:
        lines.append("No live sessions detected.")
        return "\n".join(lines)
    for session in live_sessions:
        project = project_name_from_cwd(session.get("cwd", "")) or "unknown"
        lines.append(f"- {project} | {summarize_work(session)}")
    return "\n".join(lines)


def read_offset() -> int | None:
    try:
        return int(OFFSET_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def write_offset(offset: int) -> None:
    ensure_dirs()
    OFFSET_FILE.write_text(str(offset), encoding="utf-8")


def save_bot_heartbeat() -> None:
    ensure_dirs()
    BOT_STATE_FILE.write_text(json.dumps({"updated_at": utc_now()}, indent=2), encoding="utf-8")


def handle_command(token: str, allowed_chat_id: str, text: str, chat_id: str) -> None:
    if chat_id != allowed_chat_id:
        post_telegram(token, chat_id, "Unauthorized chat.")
        return
    command_token = text.strip().split()[0].lower()
    command = command_token.split("@", 1)[0]
    if command == "/codex_status":
        post_telegram(token, chat_id, format_status_message())
        return
    if command == "/ping":
        post_telegram(token, chat_id, "Codex Telegram bot is running.")
        return
    post_telegram(token, chat_id, "Commands: /codex_status, /ping")


def run_bot() -> int:
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return 1
    offset = read_offset()
    while True:
        try:
            updates = get_telegram(token, offset)
            for update in updates:
                offset = update.get("update_id", 0) + 1
                message = update.get("message", {})
                text = message.get("text", "")
                source_chat_id = str(message.get("chat", {}).get("id", ""))
                if text.startswith("/"):
                    handle_command(token, chat_id, text, source_chat_id)
            if offset is not None:
                write_offset(offset)
            save_bot_heartbeat()
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(5)
        except KeyboardInterrupt:
            return 0
        except Exception:
            time.sleep(5)


def send_test_message(label: str) -> int:
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID.", file=sys.stderr)
        return 1
    text = "\n".join(
        [
            f"Codex Telegram notifier test {short_time_utc()}",
            f"Label: {label}",
            f"Hook dir: {HOOK_DIR}",
            f"Codex dir: {CODEX_DIR}",
        ]
    )
    try:
        response = post_telegram(token, chat_id, text)
    except Exception as exc:
        print(f"Telegram send failed: {exc}", file=sys.stderr)
        return 1
    ok = bool(response.get("ok", True))
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    command = sys.argv[1]
    if command == "notify":
        return handle_notify()
    if command == "bot":
        return run_bot()
    if command == "status":
        print(format_status_message())
        return 0
    if command == "send-test":
        label = sys.argv[2] if len(sys.argv) > 2 else "manual"
        return send_test_message(label)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
