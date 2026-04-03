# /fork local machine guide

SETUP_STATUS: ready
Generated: <timestamp>
Skill dir: <skill_dir>

## Purpose

This is the machine-specific operating guide for the immutable `fork` bootstrap skill.
Future activations should load this file and follow it instead of rebuilding the setup from scratch.

## Machine facts

- HERMES_HOME default when unset: <hermes_home>
- state.db: <state_db>
- hermes binary: <hermes_binary>
- python3: <python3>
- fork helper: <fork_helper>
- fact collector: <fact_collector>

## Launch method policy

- Preferred when invoked inside tmux: <inside_tmux_policy>
- Preferred when invoked outside tmux on this machine: <outside_tmux_policy>
- Fallback order: <fallback_order>
- Available now: <available_now>
- Conditional methods: <conditional_methods>

## Profile / home behavior

<profile_behavior>

## Operator intent assumptions

<intent_assumptions>

## Command patterns

Plain `/fork`:
```bash
python3 <fork_helper> --method auto --json
```

Print-only preview/result:
```bash
python3 <fork_helper> --method print --json
```

Dry run:
```bash
python3 <fork_helper> --dry-run --method auto --json
```

Specific source session:
```bash
python3 <fork_helper> --source <session-id-or-title> --method auto --json
```

Specific title:
```bash
python3 <fork_helper> --name <branch-title> --method auto --json
```

## Execution checklist

1. Run the helper from the user's current workspace cwd.
2. Default to `--method auto` unless the user asked for tmux/kitty/print/etc.
3. Let the helper create the child session and launch `hermes --resume <new-session-id>`.
4. If the helper falls back to print mode, show the exact `launch_command`.
5. Report source/new session ids, title, chosen method, and whether a terminal was launched.

## Refresh guidance

Regenerate this guide if any of these changed:
- terminal launcher availability
- Hermes binary path
- HERMES_HOME/profile conventions
- helper script path
