# hermes-fork-skill

A publishable skill-only implementation of Codex-style `/fork` for Hermes.

This repo uses a two-phase design:
- phase 1: an immutable bootstrap `SKILL.md` inspects the local machine and writes a local machine guide
- phase 2: later activations load that generated local guide and follow it

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
hermes skills install sebbysoup/hermes-fork-skill/skills/fork -y
```

## Generated local guide

On first activation, the bootstrap skill should create:
- `references/local-machine-guide.md`

That file is intentionally machine-specific and should stay local to the installed skill on the owner's computer.
It is not part of the published generic skill definition.

## Included files

- `skills/fork/SKILL.md`
- `skills/fork/scripts/fork_session.py`
- `skills/fork/scripts/collect_fork_facts.py`
- `skills/fork/templates/local-machine-guide.template.md`
