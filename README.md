# hermes-fork-skill

A publishable skill-only implementation of Codex-style `/fork` for Hermes.

What it does:
- clones the current Hermes CLI session from `state.db`
- creates a child session with `parent_session_id`
- strips the synthetic `/fork` control-turn from the copied transcript
- opens the fork in another terminal surface by launching `hermes --resume <new-session-id>`
- falls back to printing the exact resume command if no launcher is available

## Install via skills.sh

```bash
npx skills add sebbysoup/hermes-fork-skill
```

## Hermes note

For Hermes itself, the skill should live under the active `~/.hermes/skills/...` tree so it becomes available as `/fork` after a Hermes restart or fresh CLI launch.

## Included files

- `SKILL.md`
- `scripts/fork_session.py`
