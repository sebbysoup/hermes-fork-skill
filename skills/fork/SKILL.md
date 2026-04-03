---
name: fork
description: "Use when the user wants Codex-style /fork behavior in Hermes. /fork is a self-initializing skill: on first real use it localizes itself inside the installed skill directory, then it forks the current Hermes CLI session into a child session and launches it in another terminal surface when possible."
version: 3.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, fork, sessions, tui, terminal, branching, slash-command, setup]
---

# /fork

FORK_SKILL_CONTROL_MARKER: __HERMES_FORK_CONTROL_MESSAGE_DO_NOT_CLONE__

This is the user-facing `/fork` skill.

The two-phase idea is only an implementation detail.
From the operator perspective there is only one thing:
- run `/fork`
- if needed, it sets itself up inside the installed skill directory
- then it forks the current Hermes CLI conversation

## Product intent

Default `/fork` means:
- branch the current Hermes CLI conversation
- keep the original chat intact
- create a child session with lineage in Hermes session storage
- open that child in another terminal surface when possible
- preserve the normal Hermes TUI/input bar rather than inventing a new permanent UI mode

So `/fork` is primarily:
- session branch + launcher

not:
- a core TUI rewrite

## Non-negotiable runtime rules

1. `/fork` must operate on the active Hermes home only.
   Respect `HERMES_HOME` and never write local artifacts into another Hermes home.

2. `/fork` must localize itself in the installed skill copy.
   Machine-specific data belongs in:
   - `references/local-machine-guide.md`

3. `/fork` must use the bundled helper scripts, not ad-hoc DB edits:
   - `scripts/generate_local_machine_guide.py`
   - `scripts/collect_fork_facts.py`
   - `scripts/fork_session.py`

4. If no terminal launcher is available, `/fork` must fall back to printing the exact resume command.

5. Preserve the active workspace cwd when launching the fork.

## How `/fork` should behave when invoked

Treat the text after `/fork` as optional runtime flags or user instructions.
Examples:
- `/fork`
- `/fork --method print`
- `/fork --dry-run --method auto`
- `/fork --source 20260403_123456_abcd12`
- `/fork --name api-debug-branch`

If the user supplies helper-compatible flags, pass them through to `fork_session.py`.
If the user gives plain-language intent instead, convert it into the closest helper invocation.
Default to `--method auto` unless the user explicitly asks for a method.

## Self-setup / localization contract

`/fork` is allowed to permanently alter its own installed local copy only by maintaining:
- `references/local-machine-guide.md`

Do not rewrite `SKILL.md` during setup.
Do not store machine-specific state anywhere else unless the user explicitly asks.

### Resolve the real runtime install target

Preferred path:
- call `skill_view(name="fork")`

Use the returned `path` only to identify the prompt source.
If it points at a staged preload/temp copy such as `.agents/skills/...`, treat that as read-only prompt source only.

The runtime install target must be resolved from the active Hermes home first:
- `<active HERMES_HOME>/skills/fork`
- `<active HERMES_HOME>/skills/software-development/fork`
- only then a tightly constrained search under `<active HERMES_HOME>/skills`

Never start with a broad workspace search.
Never write local artifacts into a repo checkout or temp preload copy when the active installed skill already exists.

### When setup is required

Before running the fork helper, inspect `references/local-machine-guide.md` in the runtime install target.

If any of these is true, setup is required:
- the file does not exist
- it lacks `SETUP_STATUS: ready`
- it references a different `HERMES_HOME` than the active one
- it references a different runtime skill dir than the active installed copy
- its helper paths do not match the active installed copy

When setup is required, run exactly:
- `python3 <runtime-skill-dir>/scripts/generate_local_machine_guide.py --runtime-skill-dir <runtime-skill-dir> --json`

That script is the authoritative setup path.
Do not hand-roll the machine guide if the script is available.

After setup, load:
- `skill_view(name="fork", file_path="references/local-machine-guide.md")`

and treat it as the local runtime guide for the remainder of the current `/fork` request.

## Execution path

Once the runtime install target is resolved and the local guide is fresh enough:

1. Run the helper from the user's current workspace cwd.
2. Use:
   - `python3 <runtime-skill-dir>/scripts/fork_session.py ...`
3. Default to `--method auto` unless overridden.
4. Pass through any helper-compatible flags from the `/fork` invocation.
5. Prefer JSON output when you need to inspect the result precisely.

Use these helper-supported flags when relevant:
- `--dry-run`
- `--list-methods`
- `--source`
- `--name`
- `--method`
- `--output json`
- `--json`

## Reporting requirements

After invoking the helper, report the important result fields when available:
- source session id
- new or suggested new session id
- title
- chosen method
- whether a terminal was launched
- launch command when relevant
- guide path if setup happened

## Important anti-patterns

Do not:
- mutate Hermes core just to make `/fork` work
- manually edit Hermes SQLite state instead of using `fork_session.py`
- ask the user to repeat machine facts you can inspect directly
- write `local-machine-guide.md` into a different Hermes home
- write `local-machine-guide.md` into `.agents/skills/...` staged preload copies
- ignore stale-guide mismatches caused by switching profiles or `HERMES_HOME`

## Final interpretation

The operator should be able to think of `/fork` as one self-initializing feature.
If setup is needed, do it locally and continue.
Do not stop after setup if the actual fork can still be executed in the same activation.
