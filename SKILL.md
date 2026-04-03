---
name: fork
description: Use when the user wants Codex-style /fork behavior in Hermes. This skill branches the current Hermes CLI conversation into a child session and launches it in another terminal surface without modifying Hermes core.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, fork, sessions, tui, terminal, branching, slash-command]
---

FORK_SKILL_CONTROL_MARKER: __HERMES_FORK_CONTROL_MESSAGE_DO_NOT_CLONE__

# Purpose

This skill gives Hermes a Codex-like `/fork` as a pure skill.

It creates a child CLI session in `state.db`, copies the source conversation history, trims this synthetic control-turn out of the copied transcript, and launches the forked session with the regular Hermes TUI by running `hermes --resume <new-session-id>` in another terminal surface.

# What this is approximating

Interpret the user intent as:
- "branch this exact chat where I am right now"
- "open the branch in a separate terminal/pane/window so I can keep the original chat"
- "reuse the normal Hermes chat bar / TUI instead of inventing a new permanent UI substrate in core"

So this skill does **session branching + new terminal launch**, not a deep in-place TUI rewrite.

# Important runtime rules

- Do not modify Hermes core when this skill is enough.
- Do not hand-roll raw SQLite edits inline if the bundled script can be used.
- Always locate and run the bundled `scripts/fork_session.py` helper.
- Preserve the active workspace cwd by running the script from the current terminal cwd.
- Default to `--method auto` unless the user asks for a specific launcher.
- If no launcher is available, fall back to `--method print` and show the exact resume command.

# How to run the skill

1. Locate the installed helper script with `search_files`.
   - Search under `~/.hermes` for `fork_session.py`
   - Prefer the result ending in `/fork/scripts/fork_session.py`

2. Run it with `terminal` using `python3`.

3. Map user intent to script flags:
   - plain `/fork` -> `--method auto`
   - "list methods" -> `--list-methods`
   - "dry run" / "preview" -> `--dry-run --method auto`
   - "tmux" -> `--method tmux-window`
   - "tmux pane" / "split" -> `--method tmux-pane`
   - "gnome terminal" -> `--method gnome-terminal`
   - "x-terminal-emulator" / generic Linux terminal -> `--method x-terminal-emulator`
   - "kitty" -> `--method kitty-window`
   - "just print the command" -> `--method print`
   - explicit source session id/title -> `--source <value>`
   - explicit branch title/name -> `--name <value>`

4. After the script runs, report:
   - source session id
   - new session id
   - resulting title
   - chosen launch method
   - whether a terminal was actually opened
   - exact resume command if it printed instead of launching

# Expected behavior

The helper script:
- reads the current Hermes `state.db`
- resolves the current or requested CLI session
- clones the session into a new child session using `parent_session_id`
- copies message history while trimming the synthetic `/fork` skill control-turn using the marker above
- preserves the regular Hermes TUI by launching `hermes --resume <new-session-id>` in another terminal surface

# Notes and pitfalls

- The copied branch should use the normal Hermes UI, not a bespoke replacement chat bar.
- Because Hermes skill slash commands currently queue a synthetic skill-expanded user message, the helper intentionally strips that control-turn from the forked transcript.
- If the current Hermes process already started before this skill was installed, the user may need to restart Hermes once so `/fork` is discovered in the slash-command scan.
- If multiple active sessions exist and the user wants a specific one, pass `--source <session-id-or-title>`.
