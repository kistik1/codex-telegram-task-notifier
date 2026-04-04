#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "telegram-task-notifier"
DEFAULT_CODEX_HOME = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()


def paths(codex_home: Path) -> dict[str, Path]:
    return {
        "repo_root": REPO_ROOT,
        "codex_home": codex_home,
        "skill_dir": codex_home / "skills" / SKILL_NAME,
        "hooks_dir": codex_home / "hooks",
        "config": codex_home / "config.toml",
        "env": codex_home / "hooks" / "telegram.env",
        "state_dir": codex_home / "hooks" / "state",
        "service_dir": Path.home() / ".config" / "systemd" / "user",
        "service_file": Path.home() / ".config" / "systemd" / "user" / "codex-telegram-bot.service",
    }


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def copy_file(src: Path, dst: Path, *, executable: bool = False) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if executable:
        mode = dst.stat().st_mode
        dst.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def ensure_notify_config(config_path: Path, hook_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    desired = str(hook_path)
    if config_path.exists():
        text = config_path.read_text(encoding="utf-8")
    else:
        text = ""

    notify_line_match = re.search(r"(?m)^notify\s*=\s*\[(?P<items>[^\]]*)\]\s*$", text)
    if notify_line_match:
        items = re.findall(r'"([^"]+)"', notify_line_match.group("items"))
        if desired not in items:
            items.append(desired)
        new_line = 'notify = [' + ", ".join(f'"{item}"' for item in items) + "]"
        text = text[: notify_line_match.start()] + new_line + text[notify_line_match.end() :]
    elif re.search(r"(?m)^notify\s*=", text):
        raise RuntimeError(f"Unable to rewrite complex notify setting in {config_path}")
    else:
        prefix = f'notify = ["{desired}"]\n'
        text = prefix + text

    config_path.write_text(text, encoding="utf-8")


def remove_notify_config(config_path: Path, hook_path: Path) -> None:
    if not config_path.exists():
        return
    text = config_path.read_text(encoding="utf-8")
    desired = str(hook_path)
    notify_line_match = re.search(r"(?m)^notify\s*=\s*\[(?P<items>[^\]]*)\]\s*$", text)
    if not notify_line_match:
        return
    items = [item for item in re.findall(r'"([^"]+)"', notify_line_match.group("items")) if item != desired]
    if items:
        new_line = 'notify = [' + ", ".join(f'"{item}"' for item in items) + "]"
    else:
        new_line = ""
    text = text[: notify_line_match.start()] + new_line + text[notify_line_match.end() :]
    config_path.write_text(text, encoding="utf-8")


def write_service_file(service_file: Path, hook_py: Path) -> None:
    template = (REPO_ROOT / "systemd" / "codex-telegram-bot.service.template").read_text(encoding="utf-8")
    body = template.replace("__PYTHON_BIN__", sys.executable).replace("__HOOK_PY__", str(hook_py))
    service_file.parent.mkdir(parents=True, exist_ok=True)
    service_file.write_text(body, encoding="utf-8")


def load_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def systemctl_available() -> bool:
    try:
        run(["systemctl", "--user", "--version"])
        return True
    except Exception:
        return False


def maybe_enable_service(service_file: Path, env_path: Path) -> None:
    if not systemctl_available():
        return
    run(["systemctl", "--user", "daemon-reload"])
    run(["systemctl", "--user", "enable", "codex-telegram-bot.service"], check=False)
    env = load_env_file(env_path)
    if env.get("TELEGRAM_BOT_TOKEN") and env.get("TELEGRAM_CHAT_ID"):
        run(["systemctl", "--user", "restart", "codex-telegram-bot.service"], check=False)
        run(["systemctl", "--user", "start", "codex-telegram-bot.service"], check=False)


def install(codex_home: Path) -> None:
    p = paths(codex_home)
    p["skill_dir"].parent.mkdir(parents=True, exist_ok=True)
    copy_tree(REPO_ROOT, p["skill_dir"])

    for name in ("telegram-notify.sh", "setup-telegram-notify.sh", "codex_telegram.py"):
        copy_file(
            REPO_ROOT / "hooks" / name,
            p["hooks_dir"] / name,
            executable=True,
        )

    p["state_dir"].mkdir(parents=True, exist_ok=True)
    ensure_notify_config(p["config"], p["hooks_dir"] / "telegram-notify.sh")
    write_service_file(p["service_file"], p["hooks_dir"] / "codex_telegram.py")
    maybe_enable_service(p["service_file"], p["env"])


def verify(codex_home: Path) -> int:
    p = paths(codex_home)
    env = load_env_file(p["env"])
    hook_path = p["hooks_dir"] / "telegram-notify.sh"
    results: list[dict[str, str]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        results.append({"name": name, "ok": "true" if ok else "false", "detail": detail})

    add("skill_dir", p["skill_dir"].exists(), str(p["skill_dir"]))
    add("hook_script", hook_path.exists(), str(hook_path))
    add("hook_bridge", (p["hooks_dir"] / "codex_telegram.py").exists(), str(p["hooks_dir"] / "codex_telegram.py"))
    add("config_file", p["config"].exists(), str(p["config"]))

    config_text = p["config"].read_text(encoding="utf-8") if p["config"].exists() else ""
    add("notify_config", str(hook_path) in config_text, "notify hook configured")

    add("env_file", p["env"].exists(), str(p["env"]))
    add("env_token", bool(env.get("TELEGRAM_BOT_TOKEN")), "TELEGRAM_BOT_TOKEN present")
    add("env_chat_id", bool(env.get("TELEGRAM_CHAT_ID")), "TELEGRAM_CHAT_ID present")
    add("service_file", p["service_file"].exists(), str(p["service_file"]))

    if systemctl_available():
        status = run(["systemctl", "--user", "is-active", "codex-telegram-bot.service"], check=False)
        add("service_active", status.returncode == 0, status.stdout.strip() or status.stderr.strip())
    else:
        add("service_active", False, "systemctl --user unavailable")

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(item["ok"] == "true" for item in results) else 1


def send_test(codex_home: Path, label: str) -> int:
    bridge = paths(codex_home)["hooks_dir"] / "codex_telegram.py"
    result = subprocess.run([sys.executable, str(bridge), "send-test", label], text=True)
    return result.returncode


def uninstall(codex_home: Path) -> None:
    p = paths(codex_home)
    remove_notify_config(p["config"], p["hooks_dir"] / "telegram-notify.sh")
    for name in ("telegram-notify.sh", "setup-telegram-notify.sh", "codex_telegram.py"):
        target = p["hooks_dir"] / name
        if target.exists():
            target.unlink()
    if p["skill_dir"].exists():
        shutil.rmtree(p["skill_dir"])
    if p["service_file"].exists():
        if systemctl_available():
            run(["systemctl", "--user", "disable", "--now", "codex-telegram-bot.service"], check=False)
            run(["systemctl", "--user", "daemon-reload"], check=False)
        p["service_file"].unlink()


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    codex_home = DEFAULT_CODEX_HOME
    if command == "install":
        install(codex_home)
        return 0
    if command == "repair":
        install(codex_home)
        return verify(codex_home)
    if command == "verify":
        return verify(codex_home)
    if command == "send-test":
        label = sys.argv[2] if len(sys.argv) > 2 else "manual"
        return send_test(codex_home, label)
    if command == "uninstall":
        uninstall(codex_home)
        return 0
    print("Usage: manage.py [install|repair|verify|send-test|uninstall] [label]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
