#!/usr/bin/env python3
import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


def default_hermes_home() -> Path:
    env_home = os.environ.get("HERMES_HOME")
    if env_home:
        return Path(env_home).expanduser()
    return Path.home() / ".hermes"


def hermes_binary() -> str:
    binary = shutil.which("hermes")
    if binary:
        return binary
    return f"{shutil.which('python3') or 'python3'} -m hermes_cli.main"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect machine facts for the Hermes /fork skill setup.")
    parser.add_argument("--json", action="store_true", help="Print JSON (default behavior).")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    skill_dir = script_path.parent.parent
    hermes_home = default_hermes_home()
    display = os.environ.get("DISPLAY")
    wayland = os.environ.get("WAYLAND_DISPLAY")
    in_tmux = bool(os.environ.get("TMUX"))

    launchers = {
        "tmux_binary": shutil.which("tmux"),
        "gnome_terminal": shutil.which("gnome-terminal"),
        "x_terminal_emulator": shutil.which("x-terminal-emulator"),
        "kitty": shutil.which("kitty"),
        "wezterm": shutil.which("wezterm"),
        "alacritty": shutil.which("alacritty"),
    }

    available_now = []
    conditional = []
    if in_tmux and launchers["tmux_binary"]:
        available_now.extend(["tmux-window", "tmux-pane"])
    elif launchers["tmux_binary"]:
        conditional.extend(["tmux-window (when invoked inside tmux)", "tmux-pane (when invoked inside tmux)"])

    if (display or wayland) and launchers["gnome_terminal"]:
        available_now.append("gnome-terminal")
    if (display or wayland) and launchers["x_terminal_emulator"]:
        available_now.append("x-terminal-emulator")
    if (display or wayland) and launchers["kitty"]:
        available_now.append("kitty-window")
    available_now.append("print")

    if in_tmux and launchers["tmux_binary"]:
        recommended_now = "tmux-window"
    elif (display or wayland) and launchers["gnome_terminal"]:
        recommended_now = "gnome-terminal"
    elif (display or wayland) and launchers["x_terminal_emulator"]:
        recommended_now = "x-terminal-emulator"
    elif (display or wayland) and launchers["kitty"]:
        recommended_now = "kitty-window"
    else:
        recommended_now = "print"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "skill_dir": str(skill_dir),
        "fork_helper": str(skill_dir / "scripts" / "fork_session.py"),
        "fact_collector": str(script_path),
        "hermes_home": str(hermes_home),
        "state_db": str(hermes_home / "state.db"),
        "state_db_exists": (hermes_home / "state.db").exists(),
        "hermes_binary": hermes_binary(),
        "python3": shutil.which("python3") or "python3",
        "pwd": str(Path.cwd().resolve()),
        "env": {
            "DISPLAY": display,
            "WAYLAND_DISPLAY": wayland,
            "TMUX": os.environ.get("TMUX"),
        },
        "launchers": launchers,
        "available_now": available_now,
        "conditional_methods": conditional,
        "recommended_method_now": recommended_now,
        "notes": [
            "fork_session.py already handles session cloning, parent_session_id, and launcher fallback",
            "HERMES_HOME is respected when set, so profile-scoped Hermes homes fork within that profile automatically",
        ],
    }

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
