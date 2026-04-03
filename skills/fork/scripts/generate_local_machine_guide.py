#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from collect_fork_facts import collect_fork_facts, default_hermes_home


def resolve_runtime_skill_dir(prompt_source_dir: Path, hermes_home: Path | None = None) -> Path:
    hermes_home = (hermes_home or default_hermes_home()).expanduser().resolve()
    prompt_source_dir = prompt_source_dir.expanduser().resolve()

    candidates = [
        hermes_home / "skills" / "fork",
        hermes_home / "skills" / "software-development" / "fork",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    try:
        prompt_source_dir.relative_to(hermes_home)
        return prompt_source_dir
    except ValueError:
        return candidates[0]


def _render_template(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(f"<{key}>", value)
    return rendered


def generate_local_machine_guide(
    *,
    runtime_skill_dir: Path,
    hermes_home: Path | None = None,
    facts: dict | None = None,
) -> dict:
    runtime_skill_dir = runtime_skill_dir.expanduser().resolve()
    hermes_home = (hermes_home or default_hermes_home()).expanduser().resolve()
    facts = facts or collect_fork_facts(skill_dir=runtime_skill_dir, hermes_home=hermes_home)

    template_path = runtime_skill_dir / "templates" / "local-machine-guide.template.md"
    guide_path = runtime_skill_dir / "references" / "local-machine-guide.md"
    guide_path.parent.mkdir(parents=True, exist_ok=True)

    available_now = facts.get("available_now") or ["print"]
    conditional_methods = facts.get("conditional_methods") or ["none"]
    recommended = facts.get("recommended_method_now") or "print"
    inside_tmux_policy = "tmux-window" if "tmux-window" in available_now else "tmux-window when available; otherwise auto fallback"
    outside_tmux_policy = recommended
    fallback_order = " -> ".join(available_now)
    profile_behavior = (
        f"HERMES_HOME is set to {hermes_home}. The fork helper respects HERMES_HOME, so all session branching and launches stay in this Hermes home. "
        f"The active state.db is {facts['state_db']}."
    )
    env = facts.get("env") or {}
    display_desc = env.get("DISPLAY") or env.get("WAYLAND_DISPLAY") or "no GUI display detected"
    intent_assumptions = (
        f"The operator is using the active Hermes home {hermes_home}. Current display context: {display_desc}. "
        f"Recommended default launcher right now is {recommended}. `/fork` should preserve the normal Hermes TUI and branch into a resumed child session."
    )

    replacements = {
        "timestamp": str(facts["generated_at"]),
        "skill_dir": str(runtime_skill_dir),
        "hermes_home": str(hermes_home),
        "state_db": str(facts["state_db"]),
        "hermes_binary": str(facts["hermes_binary"]),
        "python3": str(facts["python3"]),
        "fork_helper": str(runtime_skill_dir / "scripts" / "fork_session.py"),
        "fact_collector": str(runtime_skill_dir / "scripts" / "collect_fork_facts.py"),
        "inside_tmux_policy": inside_tmux_policy,
        "outside_tmux_policy": outside_tmux_policy,
        "fallback_order": fallback_order,
        "available_now": json.dumps(available_now),
        "conditional_methods": json.dumps(conditional_methods),
        "profile_behavior": profile_behavior,
        "intent_assumptions": intent_assumptions,
    }

    content = _render_template(template_path.read_text(), replacements)
    guide_path.write_text(content)

    return {
        "status": "ok",
        "runtime_skill_dir": str(runtime_skill_dir),
        "guide_path": str(guide_path),
        "hermes_home": str(hermes_home),
        "recommended_method_now": recommended,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the machine-local guide for the Hermes /fork skill.")
    parser.add_argument("--runtime-skill-dir", default=None, help="Explicit installed skill dir to update")
    parser.add_argument("--hermes-home", default=None, help="Override HERMES_HOME")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    hermes_home = Path(args.hermes_home).expanduser() if args.hermes_home else default_hermes_home()
    prompt_source_dir = Path(__file__).resolve().parent.parent
    runtime_skill_dir = (
        Path(args.runtime_skill_dir).expanduser()
        if args.runtime_skill_dir
        else resolve_runtime_skill_dir(prompt_source_dir, hermes_home=hermes_home)
    )
    result = generate_local_machine_guide(runtime_skill_dir=runtime_skill_dir, hermes_home=hermes_home)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Generated {result['guide_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
