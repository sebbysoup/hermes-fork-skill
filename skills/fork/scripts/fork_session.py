#!/usr/bin/env python3
import argparse
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

CONTROL_MARKER = "__HERMES_FORK_CONTROL_MESSAGE_DO_NOT_CLONE__"
MAX_TITLE_LENGTH = 100


def now_session_id() -> str:
    return f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


def squash_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def sanitize_title(title: str | None) -> str | None:
    if not title:
        return None
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', title)
    cleaned = re.sub(r'[\u200b-\u200f\u2028-\u202e\u2060-\u2069\ufeff\ufffc\ufff9-\ufffb]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if not cleaned:
        return None
    if len(cleaned) > MAX_TITLE_LENGTH:
        cleaned = cleaned[:MAX_TITLE_LENGTH].rstrip()
    return cleaned


def default_hermes_home() -> Path:
    env_home = os.environ.get("HERMES_HOME")
    if env_home:
        return Path(env_home).expanduser()
    return Path.home() / ".hermes"


def connect_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def available_methods() -> dict:
    gui = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    in_tmux = bool(os.environ.get("TMUX")) and shutil.which("tmux") is not None
    methods = {
        "tmux-window": in_tmux,
        "tmux-pane": in_tmux,
        "gnome-terminal": gui and shutil.which("gnome-terminal") is not None,
        "x-terminal-emulator": gui and shutil.which("x-terminal-emulator") is not None,
        "kitty-window": gui and shutil.which("kitty") is not None,
        "print": True,
    }
    return methods


def choose_method(requested: str) -> str:
    methods = available_methods()
    if requested and requested != "auto":
        if requested not in methods:
            raise ValueError(f"Unknown method: {requested}")
        if not methods[requested]:
            raise RuntimeError(f"Requested launcher is unavailable: {requested}")
        return requested
    if methods["tmux-window"]:
        return "tmux-window"
    if methods["gnome-terminal"]:
        return "gnome-terminal"
    if methods["x-terminal-emulator"]:
        return "x-terminal-emulator"
    if methods["kitty-window"]:
        return "kitty-window"
    return "print"


def resolve_session(conn: sqlite3.Connection, source: str | None) -> sqlite3.Row:
    source = (source or "auto").strip()
    if source in {"", "auto", "current"}:
        row = conn.execute(
            """
            SELECT s.*, COALESCE((SELECT MAX(m.timestamp) FROM messages m WHERE m.session_id = s.id), s.started_at) AS last_active
            FROM sessions s
            WHERE s.source = 'cli'
            ORDER BY (s.ended_at IS NULL) DESC, last_active DESC, s.started_at DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            raise RuntimeError("No Hermes CLI sessions found in state.db")
        return row

    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (source,)).fetchone()
    if row is not None:
        return row

    exact = conn.execute("SELECT * FROM sessions WHERE title = ? ORDER BY started_at DESC LIMIT 1", (source,)).fetchone()
    escaped = source.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    numbered = conn.execute(
        "SELECT * FROM sessions WHERE title LIKE ? ESCAPE '\\' ORDER BY started_at DESC LIMIT 1",
        (f"{escaped} #%",),
    ).fetchone()
    if numbered is not None:
        return numbered
    if exact is not None:
        return exact
    raise RuntimeError(f"Could not resolve source session: {source}")


def load_messages(conn: sqlite3.Connection, session_id: str) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp, id",
            (session_id,),
        ).fetchall()
    )


def trim_control_turn(messages: list[sqlite3.Row]) -> tuple[list[sqlite3.Row], bool]:
    last_user_idx = None
    for idx, msg in enumerate(messages):
        if msg["role"] == "user":
            last_user_idx = idx
    if last_user_idx is None:
        return messages, False
    content = messages[last_user_idx]["content"] or ""
    if CONTROL_MARKER in content:
        return messages[:last_user_idx], True
    return messages, False


def compute_tool_call_count(messages: list[sqlite3.Row]) -> int:
    total = 0
    for msg in messages:
        raw = msg["tool_calls"]
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        if isinstance(parsed, list):
            total += len(parsed)
        else:
            total += 1
    return total


def first_user_preview(messages: list[sqlite3.Row]) -> str | None:
    for msg in messages:
        if msg["role"] == "user" and msg["content"]:
            text = squash_ws(msg["content"])
            if text:
                return text[:80]
    return None


def next_lineage_title(conn: sqlite3.Connection, base_title: str | None) -> str | None:
    base_title = sanitize_title(base_title)
    if not base_title:
        return None
    match = re.match(r'^(.*?) #(\d+)$', base_title)
    base = match.group(1) if match else base_title
    escaped = base.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = conn.execute(
        "SELECT title FROM sessions WHERE title = ? OR title LIKE ? ESCAPE '\\'",
        (base, f"{escaped} #%"),
    ).fetchall()
    existing = [row["title"] for row in rows if row["title"]]
    if not existing:
        return base
    max_num = 1
    for title in existing:
        m = re.match(r'^.* #(\d+)$', title)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"{base} #{max_num + 1}"


def determine_title(conn: sqlite3.Connection, source_row: sqlite3.Row, copied_messages: list[sqlite3.Row], requested_name: str | None) -> str | None:
    base = requested_name
    if not base:
        base = source_row["title"]
    if not base:
        base = first_user_preview(copied_messages)
    if not base:
        base = f"Fork of {source_row['id']}"
    return next_lineage_title(conn, base)


def hermes_binary() -> str:
    binary = shutil.which("hermes")
    if binary:
        return binary
    return f"{shlex.quote(sys.executable)} -m hermes_cli.main"


def build_resume_command(session_id: str, launch_cwd: Path, hermes_home: Path) -> str:
    hermes_cmd = hermes_binary()
    parts = [f"cd {shlex.quote(str(launch_cwd))} &&"]
    if os.environ.get("HERMES_HOME") or hermes_home != Path.home() / ".hermes":
        parts.append(f"HERMES_HOME={shlex.quote(str(hermes_home))}")
    parts.append(f"{hermes_cmd} --resume {shlex.quote(session_id)}")
    return " ".join(parts)


def launch_session(method: str, title: str | None, command: str) -> bool:
    if method == "print":
        return False
    if method == "tmux-window":
        window_name = sanitize_title(title or "fork") or "fork"
        subprocess.run(["tmux", "new-window", "-n", window_name[:32], command], check=True)
        return True
    if method == "tmux-pane":
        subprocess.run(["tmux", "split-window", "-v", command], check=True)
        return True
    if method == "gnome-terminal":
        subprocess.run(["gnome-terminal", "--", "bash", "-lc", f"{command}; exec bash"], check=True)
        return True
    if method == "x-terminal-emulator":
        subprocess.run(["x-terminal-emulator", "-e", "bash", "-lc", f"{command}; exec bash"], check=True)
        return True
    if method == "kitty-window":
        subprocess.run(["kitty", "--detach", "bash", "-lc", f"{command}; exec bash"], check=True)
        return True
    raise ValueError(f"Unsupported method: {method}")


def create_fork(conn: sqlite3.Connection, source_row: sqlite3.Row, copied_messages: list[sqlite3.Row], new_session_id: str, new_title: str | None) -> None:
    tool_call_count = compute_tool_call_count(copied_messages)
    with conn:
        conn.execute(
            """
            INSERT INTO sessions (
                id, source, user_id, model, model_config, system_prompt,
                parent_session_id, started_at, ended_at, end_reason,
                message_count, tool_call_count,
                input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens,
                billing_provider, billing_base_url, billing_mode,
                estimated_cost_usd, actual_cost_usd, cost_status, cost_source, pricing_version,
                title
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_session_id,
                source_row["source"],
                source_row["user_id"],
                source_row["model"],
                source_row["model_config"],
                source_row["system_prompt"],
                source_row["id"],
                time.time(),
                None,
                None,
                len(copied_messages),
                tool_call_count,
                source_row["input_tokens"],
                source_row["output_tokens"],
                source_row["cache_read_tokens"],
                source_row["cache_write_tokens"],
                source_row["reasoning_tokens"],
                source_row["billing_provider"],
                source_row["billing_base_url"],
                source_row["billing_mode"],
                source_row["estimated_cost_usd"],
                source_row["actual_cost_usd"],
                source_row["cost_status"],
                source_row["cost_source"],
                source_row["pricing_version"],
                new_title,
            ),
        )
        for msg in copied_messages:
            conn.execute(
                """
                INSERT INTO messages (
                    session_id, role, content, tool_call_id, tool_calls, tool_name,
                    timestamp, token_count, finish_reason, reasoning, reasoning_details, codex_reasoning_items
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_session_id,
                    msg["role"],
                    msg["content"],
                    msg["tool_call_id"],
                    msg["tool_calls"],
                    msg["tool_name"],
                    msg["timestamp"],
                    msg["token_count"],
                    msg["finish_reason"],
                    msg["reasoning"],
                    msg["reasoning_details"],
                    msg["codex_reasoning_items"],
                ),
            )


def result_payload(**kwargs):
    payload = {"status": "ok"}
    payload.update(kwargs)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Fork a Hermes CLI session into a child session and launch it elsewhere.")
    parser.add_argument("--source", default="auto", help="Source session id or title. Default: auto")
    parser.add_argument("--method", default="auto", help="Launcher method: auto, tmux-window, tmux-pane, gnome-terminal, x-terminal-emulator, kitty-window, print")
    parser.add_argument("--name", default=None, help="Optional base title for the forked session")
    parser.add_argument("--hermes-home", default=None, help="Override HERMES_HOME")
    parser.add_argument("--launch-cwd", default=None, help="Working directory to use in the spawned terminal")
    parser.add_argument("--list-methods", action="store_true", help="List available launcher methods and exit")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would happen without creating or launching a fork")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument("--output", choices=["text", "json"], default="text", help="Output format alias for agent-friendly CLI use")
    args = parser.parse_args()

    want_json = bool(args.json or args.output == "json")

    try:
        hermes_home = Path(args.hermes_home).expanduser() if args.hermes_home else default_hermes_home()
        db_path = hermes_home / "state.db"
        if not db_path.exists():
            raise RuntimeError(f"Hermes state.db not found: {db_path}")

        methods = available_methods()
        default_method = choose_method("auto")
        if args.list_methods:
            payload = result_payload(available_methods=methods, default_method=default_method)
            if want_json:
                print(json.dumps(payload, indent=2))
            else:
                print("Available launcher methods:")
                for name, available in methods.items():
                    status = "yes" if available else "no"
                    print(f"- {name}: {status}")
                print(f"Default auto method: {default_method}")
            return 0

        conn = connect_db(db_path)
        source_row = resolve_session(conn, args.source)
        source_messages = load_messages(conn, source_row["id"])
        copied_messages, trimmed_control_turn = trim_control_turn(source_messages)
        launch_cwd = Path(args.launch_cwd).expanduser().resolve() if args.launch_cwd else Path.cwd().resolve()
        chosen_method = choose_method(args.method)
        new_title = determine_title(conn, source_row, copied_messages, args.name)

        if args.dry_run:
            preview_session_id = now_session_id()
            preview_command = build_resume_command(preview_session_id, launch_cwd, hermes_home)
            payload = result_payload(
                dry_run=True,
                source_session_id=source_row["id"],
                source_title=source_row["title"],
                copied_messages=len(copied_messages),
                trimmed_control_turn=trimmed_control_turn,
                suggested_new_session_id=preview_session_id,
                suggested_title=new_title,
                method_requested=args.method,
                method_used=chosen_method,
                launch_command=preview_command,
                hermes_home=str(hermes_home),
                db_path=str(db_path),
            )
            print(json.dumps(payload, indent=2) if want_json else payload)
            return 0

        new_session_id = now_session_id()
        create_fork(conn, source_row, copied_messages, new_session_id, new_title)
        launch_command = build_resume_command(new_session_id, launch_cwd, hermes_home)
        launched = launch_session(chosen_method, new_title, launch_command)
        payload = result_payload(
            source_session_id=source_row["id"],
            source_title=source_row["title"],
            new_session_id=new_session_id,
            new_title=new_title,
            copied_messages=len(copied_messages),
            trimmed_control_turn=trimmed_control_turn,
            method_requested=args.method,
            method_used=chosen_method,
            launched=launched,
            launch_command=launch_command,
            hermes_home=str(hermes_home),
            db_path=str(db_path),
        )
        if want_json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Forked session {source_row['id']} -> {new_session_id}")
            if new_title:
                print(f"Title: {new_title}")
            print(f"Method: {chosen_method}")
            if launched:
                print("Launched a new terminal surface.")
            else:
                print("No terminal surface launched automatically.")
                print(f"Run this command manually:\n{launch_command}")
        return 0
    except Exception as exc:
        payload = {"status": "error", "error": str(exc)}
        if "args" in locals() and want_json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
