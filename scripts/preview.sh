#!/usr/bin/env bash
# Launch the jellycell live viewer against examples/demo.
#
# Runs the demo notebook first (populating the cache) so the viewer has
# something to show, then serves via `jellycell view`. Used by
# .claude/launch.json and `make preview`.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEMO="$ROOT/examples/demo"

cd "$ROOT"

# Populate the cache if empty or stale. Rerun is cheap (cache hit) on subsequent starts.
uv run jellycell run "$DEMO/notebooks/tour.py" || {
  echo "Demo run failed — starting viewer anyway so you can see error state." >&2
}

exec uv run jellycell view "$DEMO"
