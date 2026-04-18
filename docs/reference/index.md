# Reference

The **living** reference for jellycell. Topic-scoped docs that evolve
with the codebase — no frozen "v1 spec / v2 spec / …" sprawl. Everything
here is the authoritative statement of how jellycell is built and what
it promises; if a behavior disagrees with the reference, either the
code or the reference is wrong, and we open an issue.

Not sure what you're looking for?

- **Using jellycell day-to-day** — start with
  [Getting started](../getting-started.md) or the
  [User guide](../project-layout.md) instead. This is the reference,
  not the tutorial.
- **Building jellycell or writing a PR** — read
  [architecture](architecture.md) for how the pieces fit together, then
  [contracts](contracts.md) for the three things that bump major versions.

## In this reference

```{toctree}
:maxdepth: 1

architecture
contracts
```

- **[Architecture](architecture.md)** — the piggyback map (what we
  depend on and what we own), the 8-layer dependency order, and where
  each subpackage sits. Update when you add a new dep or shift a
  subpackage's responsibilities.
- **[Contracts](contracts.md)** — the three §10 invariants
  (`--json` schemas, cache key algorithm, agent guide content). The
  ceremony for changing each is documented alongside.

## Other authoritative docs

These live at the top level of `docs/` because they're both user-facing
and reference-quality — no need to duplicate them here:

- [File format](../file-format.md) — notebook layout, tags, PEP-723
  blocks, round-trip guarantees, cache-key inputs.
- [Project layout](../project-layout.md) — `jellycell.toml` schema,
  every config option, directory conventions.
- [CLI reference](../cli-reference.md) — auto-generated from Typer.
- [Agent guide](../agent-guide.md) — what `jellycell prompt` emits;
  stable across patch versions (§10.3).

## Historical

The [v0 spec](../spec/v0.md) is the **frozen record** of what was
promised for the initial `1.0.0` cut — phase budgets, the original
piggyback map, the first statement of the §10 contracts. Useful for
understanding *how* the project got here; everything that evolves
going forward lives in this reference tree instead.
