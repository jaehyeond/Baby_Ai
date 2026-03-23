---
name: project-conventions
description: This skill should be used when creating new functions, tables, API endpoints, or edge functions in the Baby AI project. Also applies when modifying development stage logic, stage gates (can_predict, can_simulate, can_imagine), or any code involving developmental transitions. Prevents the "defined but never called" anti-pattern that has occurred 5 times in this project.
version: 1.0.0
---

# Baby AI Project Conventions

Critical conventions learned from repeated mistakes in this project. Follow these rules strictly when adding or modifying code.

## Anti-Pattern: "Defined But Never Called" (5 Incidents)

This is the most recurring bug in the project. New functions/tables are created but never integrated into the execution flow.

### Past Incidents

| Function/Feature | Where Defined | What Was Missing |
|-----------------|---------------|------------------|
| `verify_prediction()` | Python neural module | No call site in conversation-process |
| `discover_causal_relation()` | Python neural module | No call site in conversation-process |
| `suggest_goal_from_emotion()` | Python neural module | No call site in conversation-process |
| `self-evaluation` EF | Edge Function | Never called from any pipeline |
| `imagination_sessions` table | Database | No trigger — fixed by adding `maybeImagine()` |
| `_check_stage_advance()` | Python `development.py` | Python-only, no Edge Function implementation |

### Mandatory Rule

When creating ANY new function, table, Edge Function, or API endpoint:

1. **Identify the call site** — Where in the existing pipeline will this be invoked?
2. **Implement the call** — Add the actual invocation at that call site
3. **Verify the chain** — Trace from user action → pipeline → new code → result
4. **Test the path** — Confirm the new code executes during a real interaction

If no clear call site exists, the feature should NOT be created yet.

## Development Stage Gates

Baby AI has developmental stages that gate certain capabilities. Respect these gates when implementing features.

### Stage Definitions

| Stage | Name | Number | Key Capabilities |
|-------|------|--------|-----------------|
| NEWBORN | 신생아 | 0 | Basic reactions only |
| INFANT | 영아 | 1 | Pattern recognition begins |
| BABY | 아기 | 2 | `can_predict()` — prediction enabled |
| TODDLER | 유아 | 3 | `can_simulate()`, `can_imagine()` — simulation & imagination |
| CHILD | 아동 | 4 | `can_reason_causally()` — causal reasoning |
| ADOLESCENT | 청소년 | 5+ | Full capabilities (stage 5+ params undefined in useBrainRegions!) |

### Stage Numbering Inconsistency (CRITICAL)

Three different numbering systems exist simultaneously:

| Component | Base | Example |
|-----------|------|---------|
| `BabyStateCard` (Frontend) | **1-based** | Stage 1 = NEWBORN |
| `useBrainRegions` (Frontend) | **0-based** | Stage 0 = NEWBORN |
| Python `development.py` | **0-based** | Stage 0 = NEWBORN |

When working across frontend and backend, always verify which numbering system applies.

### Known Bug: Stage 5+ Undefined

`useBrainRegions` hook has `STAGE_PARAMS` that only define stages 0-4. Stage 5+ falls back to BABY parameters. This needs immediate fixing when working on brain region code.

## Database Type Rules

### Array Types in PostgreSQL/Supabase (Legacy)

| Type | Rule | Example |
|------|------|---------|
| `jsonb[]` | Must be object arrays | `[{"key": "value"}]` — plain strings cause errors |
| `uuid[]` | Empty array = `[]` | Text values not accepted |
| `text[]` | Compatible with `string[]` | Direct mapping |

### Neo4j Property Types

Node properties accept primitive types and arrays of primitives. No nested objects in properties — use relationships instead.

## Multi-Tenant Data Isolation

When writing lookup queries (Neo4j Cypher or any DB query), ALWAYS include tenant scoping. Past incident: a query without tenant filtering returned data from other tenants, causing cross-contamination.

**Rule**: Every query that reads tenant-specific data must include a `WHERE` clause with the tenant identifier.

## Memory Recall Pipeline Limitations (v30)

Current pipeline recalls 10 concepts + 5 experiences, but Gemini typically uses only 2-3 superficially.

**Known causes**:
- Concept descriptions are too brief (1 line)
- Prompt constrains response to "1-3 sentences"
- No current date injection in prompt

When modifying the recall pipeline, consider these limitations and avoid making them worse.
