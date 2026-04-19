# CLI reference

Every command supports `--json` for machine-readable output with
`schema_version: 1` ([§10.1 contract](reference/contracts.md)).

## Global flags

- `--project PATH` / `-p PATH` — project root override. Default: discover by
  walking up from cwd for `jellycell.toml`.
- `--quiet` / `-q` — reduce output.
- `--verbose` / `-V` — increase output.
- `--json` — emit JSON to stdout (one object per command).
- `--version` — print version and exit.

## Auto-generated reference

```{typer} jellycell.cli.app:app
:prog: jellycell
:width: 100
```

## Command details

### `jellycell init <path>`

Scaffold a new project.

```bash
jellycell init my-analysis --name my-analysis
```

Flags:
- `--name NAME` — project name. Defaults to the target dir name.
- `--force` — overwrite an existing `jellycell.toml`.

JSON output (example structure):

```
{"schema_version": 1, "path": "/abs/path", "name": "my-project", "created": ["jellycell.toml", "notebooks/", ...]}
```

### `jellycell lint [path]`

Check project against lint rules. Returns exit code 1 on violations.

```bash
jellycell lint              # discover project from cwd
jellycell lint --fix        # apply auto-fixes
jellycell --json lint       # JSON report
```

### `jellycell run <notebook>`

Execute a notebook end-to-end with caching.

```bash
jellycell run notebooks/foo.py
jellycell run notebooks/foo.py --force                    # re-execute all cells
jellycell run notebooks/foo.py -m "fixed sign error"      # journal entry message
```

After the run, `jellycell run` warns about any artifact larger than
`[artifacts] max_committed_size_mb` (default 50) with `.gitignore` / Git
LFS guidance. Set the threshold to `0` in `jellycell.toml` to silence.

When `[journal] enabled = true` (the default) a one-section entry is
appended to `manuscripts/journal.md` — timestamp + cell summary +
artifact changes + your `-m` message. Append-only; hand-edits survive.

### `jellycell render [notebook]`

Render HTML reports.

```bash
jellycell render                              # all notebooks + index
jellycell render notebooks/foo.py             # single notebook
jellycell render --standalone                 # inline images (one-file HTML)
```

### `jellycell view`

Serve the live catalogue (requires `[server]` extra).

```bash
jellycell view                                # use [viewer] config
jellycell view --host 0.0.0.0 --port 8080
JELLYCELL_VIEW_NOCACHE=1 jellycell view       # disable response cache
```

The live server is **disk-write-free for HTML pages** — it renders in
memory and never touches `site/`. Image assets land in
`.jellycell/cache/assets/` (content-addressed, git-ignored) and are
served via the `/_assets/` static mount. `jellycell render` remains the
only command that writes a portable static site under `site/`.

Per-notebook HTML is cached in memory by a view-key that combines the
notebook's source bytes + its cell cache keys — any edit or run
invalidates cleanly. Set `JELLYCELL_VIEW_NOCACHE=1` in the environment
when iterating on templates so every request re-renders.

### `jellycell cache ...`

- `cache list` — show cached cell executions.
- `cache prune [--older-than DURATION] [--keep-last N] [--dry-run]` — remove old entries.
- `cache clear [-y]` — wipe the cache.
- `cache rebuild-index` — re-scan manifests to rebuild SQLite index.

### `jellycell export <format> <notebook>`

- `export ipynb` — `.ipynb` with cached outputs reattached.
- `export md` — MyST markdown (full notebook + every cell's outputs).
- `export tearsheet [-o PATH]` — curated markdown tearsheet. Defaults to
  `manuscripts/tearsheets/<stem>.md` so the auto-generated subfolder stays
  separate from hand-authored writeups at the root of `manuscripts/`.
  Includes markdown narration, inlined image artifacts via relative
  paths, JSON summaries flattened as two-column tables, and a header
  link to `site/<stem>.html` when it exists. Safe to commit; GitHub
  renders it inline.

### `jellycell checkpoint ...`

Bundle reproducible project snapshots (self-contained `.tar.gz`).
Default target on `restore` is a **new sibling directory** — the live
project is never touched unless you explicitly pass `--into` + `--force`.

```bash
jellycell checkpoint create                       # auto-timestamped name
jellycell checkpoint create --name v1-draft -m "submitted for review"
jellycell checkpoint list                         # newest first
jellycell checkpoint restore v1-draft             # → <project>-restored-v1-draft/
jellycell checkpoint restore v1-draft --into /tmp/inspect --force
```

The archive includes `notebooks/`, `data/`, `artifacts/`, `site/`,
`manuscripts/`, `jellycell.toml`, and `.jellycell/cache/` — so a
reviewer who unpacks it can re-render HTML without a re-run. Junk
dirs (`__pycache__`, `.venv`, `.git`, etc.) are skipped. Sidecar
`<name>.json` metadata (created_at, message, file count) sits next to
each `.tar.gz` so `list` is fast.

### `jellycell new <name>`

Scaffold a new notebook under `notebooks/`.

```bash
jellycell new analysis        # creates notebooks/analysis.py
```

### `jellycell prompt`

Emit the canonical [agent guide](agent-guide.md) to stdout, or install
it as `AGENTS.md` + `CLAUDE.md` with `--write`.

```bash
jellycell prompt | pbcopy                           # stdout — pipe into your agent
jellycell prompt --write                            # drop AGENTS.md + CLAUDE.md in cwd
jellycell prompt --write /path/to/repo-root         # target a specific directory
jellycell prompt --write --agents-only              # skip the CLAUDE.md stub
jellycell prompt --write --nested                   # intentional inner nesting (polyglot)
jellycell prompt --write --force                    # overwrite existing files
```

Flags:

- `--write` — switch from stdout emission to disk-install mode.
  Without it, the command behaves identically to pre-1.1 (the §10.3
  stability contract preserves the stdout bytes).
- `--nested` — acknowledge an outer `AGENTS.md` detected in an
  ancestor directory and write an intentional inner override to the
  target. Bypasses the outer-detection refuse only; still refuses to
  clobber an existing target file without `--force`. Use this when
  adopting the polyglot Pattern A layout (jellycell's guide at the
  Python subtree root, repo-wide `AGENTS.md` at the git root).
- `--force` — bypass every check: outer-AGENTS-detection refuse *and*
  overwrite an existing `AGENTS.md` / `CLAUDE.md` at the target.
- `--agents-only` — write only `AGENTS.md`, skip the `CLAUDE.md` stub.
  Useful when Claude Code isn't in the mix.

| Target state                                       | Flag needed            |
| -------------------------------------------------- | ---------------------- |
| No outer AGENTS.md, no existing target file        | (none)                 |
| Outer AGENTS.md exists, no existing inner file     | `--nested`             |
| Existing target file (any scope)                   | `--force`              |
| Outer AGENTS.md exists + existing inner target     | `--nested --force`     |

**Monorepo safety**: `--write` walks up the directory tree looking for
an existing `AGENTS.md` (stopping at the first `.git/` directory,
`$HOME`, or filesystem root). If one is found in an ancestor, the
command refuses by default and prints a hint pointing at `--nested`
(for intentional inner scoping) or `--force` (to bypass all checks).
See [project-layout.md](project-layout.md#multi-project--monorepo-pattern)
for the recommended monorepo layouts.

**What's in AGENTS.md**: the same content as `jellycell prompt` stdout,
with the MyST `:::{important}` directive rewritten as a plain-markdown
blockquote so GitHub renders it natively. All other markdown is
preserved verbatim.
