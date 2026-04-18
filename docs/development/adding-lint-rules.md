# Adding a lint rule

Lint rules live in `src/jellycell/lint/rules.py`. Each rule is a function + metadata.

## Pattern

```python
# src/jellycell/lint/rules.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jellycell.paths import Project


@dataclass(frozen=True)
class Violation:
    rule: str
    path: Path
    line: int | None
    message: str
    fixable: bool


def rule_my_rule(project: Project) -> list[Violation]:
    """Check that <thing>. Return a list of violations."""
    violations: list[Violation] = []
    # scan project, append Violation(...) for each problem
    return violations


def fix_my_rule(project: Project, violation: Violation) -> bool:
    """Apply auto-fix for a violation. Return True if applied, False if skipped."""
    # ... mutate files, return True ...
    return True


RULES: dict[str, Callable[[Project], list[Violation]]] = {
    "my-rule": rule_my_rule,
    # ... other rules ...
}

FIXERS: dict[str, Callable[[Project, Violation], bool]] = {
    "my-rule": fix_my_rule,
    # ... other fixers ...
}
```

## Rules

1. **Names are kebab-case.** Match the ruff convention: `pep723-position`, `declared-deps`, `artifact-paths`.
2. **Configurable via `jellycell.toml`.** If the rule can be opt-in/opt-out, check `project.config.lint.<name>` before scanning.
3. **Fixers are optional.** Some rules can't be auto-fixed; those violations are reported with `fixable=False`.
4. **Test both paths.** Unit test: rule detects + ignores correctly. Fix test: fix applies correctly and is idempotent.

## Testing

```python
# tests/unit/test_lint_rules.py
def test_my_rule_detects(sample_project_factory):
    project = sample_project_factory(with_violation=True)
    violations = rule_my_rule(project)
    assert len(violations) == 1
    assert violations[0].rule == "my-rule"


def test_my_rule_fix_is_idempotent(sample_project_factory):
    project = sample_project_factory(with_violation=True)
    violations = rule_my_rule(project)
    assert fix_my_rule(project, violations[0]) is True
    assert rule_my_rule(project) == []  # gone
    # Second fix on a clean project is a no-op
    assert fix_my_rule(project, violations[0]) is False
```
