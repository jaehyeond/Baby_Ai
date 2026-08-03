# Project Core

- Source of truth order: `AGENTS.md` current checkpoint, latest `CHANGELOG.md` entry, then the 2026-07 banner in `Task.md`. Much of older `Task.md` is stale Supabase history.
- Runtime architecture: FastAPI + Neo4j + Redis; Quest/PC/robot are clients. Do not infer the current system from legacy Edge Function sections.
- Protected boundary: do not edit `neural/baby/conversation_handler.py` v30 unless the user explicitly overrides this rule.
- Research scripts and artifacts must remain read-only unless a separate user approval explicitly permits DB writes, learning, held-out execution, or production promotion.
- Exact current experiment metrics are intentionally kept out of this memory; re-read the source-of-truth files before continuing.
- Stack and dependency details: `mem:tech_stack`.
- Project-specific implementation rules: `mem:conventions`.
- Commands and completion checks: `mem:suggested_commands` and `mem:task_completion`.
- Long-lived Baby research directions and deferred features: `mem:research/directions`.