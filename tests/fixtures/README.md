# Test fixtures

Shared, read-only sample data. Tests that need to mutate fixtures should copy
them to `tmp_path` first — use the `sample_project` factory fixture from
`conftest.py`.

## Contents

- `sample_project/jellycell.toml` — minimal valid config.
- `sample_notebook.py` — canonical jupytext percent-format notebook with
  PEP-723 block, markdown cell, tagged code cells. Used by format/lint/run tests.
