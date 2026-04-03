# hermes-fork-skill

A publishable skill-only implementation of Codex-style `/fork` for Hermes.

This repo keeps the phase distinction as an implementation detail only:
- first real `/fork` use localizes the installed skill by writing a machine guide into the installed skill dir
- later `/fork` invocations reuse or refresh that local guide as needed

What `/fork` does:
- clones the current Hermes CLI session from `state.db`
- creates a child session with `parent_session_id`
- strips the synthetic `/fork` control-turn from the copied transcript
- opens the fork in another terminal surface by launching `hermes --resume <new-session-id>`
- falls back to printing the exact resume command if no launcher is available

## Install via skills.sh

```bash
npx skills add sebbysoup/hermes-fork-skill --skill fork
```

## Install via Hermes skills hub

```bash
hermes skills tap add sebbysoup/hermes-fork-skill
hermes skills install sebbysoup/hermes-fork-skill/skills/fork -y --force
```

`--force` is currently needed because Hermes marks this community skill as `CAUTION` during security scanning: it intentionally inspects `HERMES_HOME`/terminal environment and launches terminal subprocesses.

## Generated local guide

On first activation, `/fork` should create:
- `references/local-machine-guide.md`

That file is intentionally machine-specific and should stay local to the installed skill on the owner's computer.
It is not part of the published generic skill definition.

Localization is now handled by `scripts/generate_local_machine_guide.py`, which prefers the active installed skill path and, if needed, falls back only to `<active HERMES_HOME>/skills/...` lookups instead of broad workspace searches. It also treats staged preload copies like `.agents/skills/...` as read-only prompt sources and writes the generated guide into the active installed skill under `HERMES_HOME`. That avoids accidentally writing the guide into a different Hermes home, repo checkout, or temp preload copy.

## Included files

- `skills/fork/SKILL.md`
- `skills/fork/scripts/fork_session.py`
- `skills/fork/scripts/collect_fork_facts.py`
- `skills/fork/scripts/generate_local_machine_guide.py`
- `skills/fork/templates/local-machine-guide.template.md`
