---
name: fork
description: "Use when the user wants Codex-style /fork behavior in Hermes. Immutable bootstrap skill: first run performs local setup and writes a machine-specific usage guide; later runs load that guide and follow it."
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, fork, sessions, tui, terminal, branching, slash-command, setup]
---

# fork bootstrap

This `SKILL.md` is intentionally generic and should stay immutable across machines.
Do not rewrite this file during setup.

Instead, setup writes a machine-specific guide at:
- `references/local-machine-guide.md`

That generated guide becomes the authoritative operating manual for later `/fork` runs on that machine.

# Phase 1 — local setup bootstrap

On every activation, first try to load:
- `skill_view(name="fork", file_path="references/local-machine-guide.md")`

If that file exists and contains `SETUP_STATUS: ready`, skip to Phase 2.

If it does not exist, do setup now before executing the user request:

1. Locate the installed skill directory and helper files.
   - Use `search_files` to find `fork_session.py` and `collect_fork_facts.py` under the installed `fork` skill.

2. Inspect this machine.
   - Run `python3 scripts/collect_fork_facts.py --json` with `terminal`.
   - Use your persistent memory about the owner and this machine in addition to the script output.

3. Write the generated local guide.
   - Create `references/local-machine-guide.md` in the installed skill directory.
   - Use `templates/local-machine-guide.template.md` as the structure.
   - Fill in concrete values for this machine: paths, launch-method policy, profile/HERMES_HOME behavior, and exact helper commands.
   - Include the sentinel line `SETUP_STATUS: ready` near the top.

4. Keep setup local.
   - Do not mutate `SKILL.md`.
   - Do not treat the generated guide as a publishable upstream change unless the user explicitly asks.

5. After writing the guide, immediately load it with `skill_view` and follow it for the current request.

# Phase 2 — execution

If `references/local-machine-guide.md` exists, treat it as the primary machine-specific skill.
Load it and follow it instead of re-interpreting this bootstrap.

The generated guide should tell you exactly how this machine wants `/fork` to behave, but the underlying implementation should still branch the Hermes CLI session and launch:
- `hermes --resume <new-session-id>`

in a new terminal surface when possible.

# Interpretation of user intent

Default interpretation:
- branch the current Hermes CLI conversation
- keep the original chat intact
- open the branch in another terminal/pane/window
- preserve the normal Hermes TUI/input bar rather than inventing a separate permanent UI mode

So `/fork` is primarily:
- session branch + launcher

not:
- a core TUI rewrite

# Generic execution constraints

Even after setup, keep these invariants:
- prefer the generated local guide over generic reasoning
- preserve the active workspace cwd when launching the fork
- use the bundled `scripts/fork_session.py` helper instead of ad-hoc SQLite edits
- if no terminal launcher is available, fall back to printing the exact resume command
- report the source session id, new session id, title, chosen method, and launch command when relevant
