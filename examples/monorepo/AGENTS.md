# AGENTS.md

This is a placeholder shipped with the `examples/monorepo/` fixture so
`jellycell init showcase-*` detects outer coverage correctly.
**Regenerate the real canonical agent guide** with:

```bash
# from this monorepo root
uv run jellycell prompt --write --force
```

That writes the full §10.3 agent guide here and keeps the matching
`CLAUDE.md` stub alongside it. Native readers: Cursor, Codex, GitHub
Copilot, Aider, Zed, Warp, Windsurf, Gemini CLI. Claude Code reads
`CLAUDE.md` directly, which points back at this file.

## Layout notes for agents working in this monorepo

- One `pyproject.toml` + `.venv` at the root — every showcase runs
  against the same environment. `uv sync` once, run any showcase.
- Each `showcase-*/jellycell.toml` anchors its own `notebooks/`,
  `artifacts/`, `site/`, `manuscripts/`, and `.jellycell/cache/`. No
  cross-leak; editing one showcase's notebook never invalidates the
  other's cache.
- From the monorepo root, run a specific showcase with
  `jellycell --project <showcase> <command>`. Or `cd <showcase>` first
  and let `jellycell.toml` discovery pick the right root.
