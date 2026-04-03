---
name: fork
description: "Use when the user wants Codex-style /fork behavior in Hermes. Two-phase skill: phase 1 bootstraps a machine-specific runtime guide; phase 2 loads that local guide and executes the fork from it."
version: 2.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, fork, sessions, tui, terminal, branching, slash-command, bootstrap, setup]
---

# fork

This skill is intentionally split into two strict phases.

Phase 1 is this publishable bootstrap.
Phase 2 is a generated local runtime guide.

The point of the design is:
- keep the upstream skill generic
- keep machine-specific facts out of `SKILL.md`
- let first-run setup discover how `/fork` should behave on this exact machine
- make later `/fork` runs fast and deterministic by following the generated local guide

## Core contract

Treat this file as phase 1 only.
Do not turn this file into the runtime guide.
Do not rewrite this file during setup.
Do not store local machine facts here.

The only local persistent artifact this bootstrap should generate is:
- `references/local-machine-guide.md`

That generated file becomes the authoritative phase-2 runtime guide for future `/fork` activations on this machine.

## Activation algorithm

Preferred runtime condition:
- the `skills` toolset is available, so you can use `skill_view`

If the `skills` toolset is unavailable, you may still proceed, but only by anchoring all discovery to the active `HERMES_HOME` skill tree rather than the broader workspace.

On every activation, do this in order:

1. Try to load:
   - `skill_view(name="fork", file_path="references/local-machine-guide.md")`

2. If that file exists and contains:
   - `SETUP_STATUS: ready`

   then stop treating this bootstrap as the active instruction set and switch immediately to phase 2.

3. If the file does not exist, is unreadable, or is missing `SETUP_STATUS: ready`, run phase 1 setup now.

4. After phase 1 setup completes, immediately load `references/local-machine-guide.md` with `skill_view` and follow that guide for the current user request.

If `skill_view` is unavailable, determine the installed skill directory by checking, in order:
- `<active HERMES_HOME>/skills/fork`
- `<active HERMES_HOME>/skills/software-development/fork`
- only then a tightly constrained search under `<active HERMES_HOME>/skills`

Never start with a broad workspace search when the active Hermes home can identify the installed copy.

Do not stop after setup.
The same activation should both:
- bootstrap the local guide if needed
- then execute the current `/fork` request via phase 2

## Phase 1 — bootstrap/setup only

Goal:
- inspect the local machine
- determine the local `/fork` policy
- materialize phase 2 as `references/local-machine-guide.md`

During phase 1, you are not the runtime skill yet.
Do not improvise the final `/fork` behavior until the local guide exists.

### Required setup steps

1. Locate the installed skill directory precisely.
   Do not start with a broad workspace search.
   Preferred path:
   - call `skill_view(name="fork")`

   Use the returned skill `path` to identify the actual installed skill directory for this activation.

   If `skill_view` is unavailable, resolve the installed directory from the active Hermes home first:
   - `<active HERMES_HOME>/skills/fork`
   - `<active HERMES_HOME>/skills/software-development/fork`

   Only if those locations do not exist should you use `search_files`, and then only constrained to `<active HERMES_HOME>/skills` rather than the whole workspace.

   Once found, resolve these files relative to that installed directory:
   - `scripts/fork_session.py`
   - `scripts/collect_fork_facts.py`
   - `templates/local-machine-guide.template.md`

2. Collect local facts.
   Run the fact collector from the installed skill directory, not from an arbitrary source checkout.
   Run:
   - `python3 <installed-skill-dir>/scripts/collect_fork_facts.py --json`

   Use the script output plus any stable relevant persistent memory about this machine.

3. Synthesize the machine-specific `/fork` policy.
   The generated guide must encode concrete answers for:
   - skill directory
   - hermes binary path
   - python3 path
   - `HERMES_HOME` behavior
   - `state.db` path
   - available terminal launch methods
   - preferred behavior inside tmux
   - preferred behavior outside tmux
   - fallback order
   - exact helper command patterns
   - the intended operator UX on this machine

4. Write the generated guide.
   Create, inside the installed skill directory identified in step 1:
   - `references/local-machine-guide.md`

   Use the installed copy of:
   - `templates/local-machine-guide.template.md`

   The generated guide must:
   - include the sentinel line `SETUP_STATUS: ready`
   - be concrete and machine-specific
   - contain absolute or fully resolved paths where practical
   - record the exact helper commands the runtime should use
   - state that it is a local-only artifact, not something to publish upstream by default
   - never be written into an unrelated source checkout when the installed skill lives elsewhere

5. Handoff to phase 2 immediately.
   After writing the guide, load it with `skill_view` and follow it for the rest of the current request.

### Phase-1 constraints

While bootstrapping:
- do not rewrite `SKILL.md`
- do not mutate Hermes core just to implement `/fork`
- do not manually edit Hermes SQLite state as part of setup
- do not bypass `scripts/fork_session.py` by inventing a separate cloning mechanism
- do not ask the user to repeat local machine facts you can inspect directly
- do not leave setup half-finished if the environment is inspectable
- do not choose helper paths from a broad workspace search when `skill_view(name="fork")` or `<active HERMES_HOME>/skills/...` can identify the installed skill path
- do not write `references/local-machine-guide.md` into a repo checkout unless that checkout is the installed skill directory for the active profile
- do not read or write a same-named skill from another Hermes home when the current activation already has an active `HERMES_HOME`

If the machine changed materially later, phase 1 may regenerate the local guide.
Examples:
- launcher availability changed
- Hermes binary path changed
- profile / `HERMES_HOME` behavior changed
- helper script path changed

## Phase 2 — local runtime guide

Once `references/local-machine-guide.md` exists with `SETUP_STATUS: ready`, that file is the runtime skill.
It should be treated as more specific than this bootstrap.

Phase 2 is responsible for actually carrying out the user's `/fork` request.
The local runtime guide should decide the exact launch method and command forms for this machine.

### Default interpretation of `/fork`

Unless the user specifies otherwise, interpret `/fork` as:
- branch the current Hermes CLI conversation
- keep the original chat intact
- create a child session in Hermes session storage
- open that child in a separate terminal surface when possible
- preserve the normal Hermes TUI and input bar rather than inventing a new permanent custom UI

So `/fork` is primarily:
- session branch + launcher

Not primarily:
- a core TUI rewrite

## Runtime invariants

Even after phase 2 exists, keep these invariants:
- preserve the active workspace cwd when launching the fork
- use the bundled `scripts/fork_session.py` helper for session branching
- respect `HERMES_HOME` and profile-scoped Hermes homes
- default to `--method auto` unless the user explicitly asks for a method
- if no launcher is available, fall back to printing the exact resume command
- report the source session id, new session id, title, chosen method, and launch command when relevant

If the user wants a preview or inspection mode, prefer helper-supported flags such as:
- `--dry-run`
- `--list-methods`
- `--source`
- `--name`
- `--method`

Do not improvise custom database mutations or custom terminal behavior when the helper already supports the request.
