# Task Completion

- Re-read `git status --short --branch` and confirm the active branch.
- Run focused tests for the changed component, then canonical `.\\.venv\\Scripts\\python.exe -m pytest tests\\ -q`.
- Run `py_compile` for touched Python and `git diff --check`.
- For protected-handler tasks, verify the current `conversation_handler.py` blob matches HEAD.
- Re-run artifact validators such as `j1_exploratory_signal_audit.py audit-existing`.
- Update the current checkpoint in `AGENTS.md`, prepend the session result to `CHANGELOG.md`, and refresh the 2026-07 banner in `Task.md`.
- Report uncommitted files and never imply commit/push happened unless verified.