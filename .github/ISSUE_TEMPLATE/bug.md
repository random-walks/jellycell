---
name: Bug report
about: Something isn't working as documented
title: "[bug] "
labels: bug
---

## Summary

<!-- One sentence: what went wrong. -->

## Environment

- jellycell version: <!-- `jellycell --version` -->
- Python version: <!-- `python --version` -->
- OS: <!-- macOS 14.x / Ubuntu 22.04 / Windows WSL / ... -->
- Installed via: <!-- pip / uv / editable / ... -->

## Reproduction

<!-- Minimal. The smallest notebook + command that triggers the bug. -->

```python
# notebooks/repro.py
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# %% tags=["jc.step"]
...
```

```bash
jellycell run notebooks/repro.py
```

## Expected

<!-- What should have happened. -->

## Actual

<!-- What actually happened. Paste the full command output and any tracebacks. -->

```
<output>
```

## Notes

<!-- Anything else useful: related issues, workarounds, hypotheses. -->
