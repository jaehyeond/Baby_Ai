# W2 runtime implementation — 2026-09-12

## Scope and result

This worktree implements the W2 runtime contract without starting Neo4j, Redis,
an API server, or any paid provider. It does not read or copy `.env`, mutate a
database, download dependencies, or change the protected conversation and DB
modules.

Implemented behavior:

- `redis://` clients receive only non-TLS options. `rediss://` clients require
  certificate validation and hostname checking. Other URL schemes fail before a
  client is created. URL query parameters cannot add TLS settings to `redis://`
  or weaken certificate/hostname validation for `rediss://`.
- `GET /health/live` is process liveness only. `GET /health` is readiness and
  returns HTTP 503 when a required check is unhealthy.
- Readiness performs bounded Neo4j `RETURN 1`, schema registry, and Redis `PING`
  checks. Failures expose stable error codes and component messages, not raw
  exception text or connection strings.
- If Neo4j was unavailable during lifespan startup, readiness makes a bounded,
  concurrency-collapsed driver initialization attempt. A later readiness request
  can recover in the same API process after Neo4j becomes available.
- Required schema constraints and lookup indexes are checked read-only. The
  lookup checks resolve `NODE`/`RANGE` indexes by label/property shape and
  `ONLINE` state, so valid auto-generated names are reported rather than treated
  as missing. Wrong named shapes and offline semantic matches fail separately.
  The required Experience vector index is checked separately for registry name,
  `ONLINE` state, `VECTOR` type, `Experience` label, and `embedding` property.
- The vector registry name is `BABY_EXPERIENCE_VECTOR_INDEX`; its default is
  `experience_embeddings`. The restored database can therefore select its
  existing `index_2bacf740` registry without recreating the index.
- Provider status reports configuration only and never calls a model API.
- API lifespan initializes dependency clients but never runs schema or seed
  mutations. `run_explicit_initialization(...)` keeps the legacy schema/seed
  functions available only to a caller that explicitly selects schema and/or
  seed work, and returns a sanitized success/failure record.
- Curiosity `explore`/`explore_batch` and imagination
  `imagine`/`predict`/`simulate`/`verify` now perform no DB operation. They return
  `success: false`, `status: awaiting_evidence`, independent execution/result/
  evaluation states, null correctness/reward, `persisted: false`, and the legacy
  response shape keys. Curiosity generation, history/stat reads, and the
  explicit prediction verification endpoint remain available.
- Imagination stats retain historical `was_correct` flag counts only under an
  `unverified` diagnostic block. Verified prediction count is zero, measured
  accuracy is unavailable, and performance claims remain disabled until a
  provenance-backed verifier exists; no historical row is relabeled or written.
- SSE subscribes before returning the streaming response, emits an immediate
  connection comment, and polls Redis with a one-second bound so disconnects and
  15-second heartbeats are checked while idle. Subscription/poll failures expose
  only sanitized unavailable states; unsubscribe and close are independent and
  bounded, and a later connection gets fresh Pub/Sub resources.
- A missing conversation handler now returns a sanitized HTTP 503 before any
  endpoint DB access. The former fallback no longer inserts a successful fake
  Experience.

## Files

- `neural/baby/redis_client.py`
- `neural/baby/api_server.py`
- `neural/baby/runtime_readiness.py` (new)
- `neural/baby/runtime_outcomes.py` (new)
- `tests/test_runtime_readiness.py` (new)
- `tests/test_runtime_outcomes.py` (new)
- `claudedocs/deployment/W2_IMPLEMENTATION_2026-09-12.md` (this report)

## Verification

Commands used the existing main-checkout interpreter with this worktree on
`PYTHONPATH`, disabled bytecode and pytest cache, and placed pytest temporary
output under this checkout.

```powershell
$env:PYTHONPATH='E:\A2A\our-a2a-project\.worktrees\bibi-runtime-20260912'
& 'E:\A2A\our-a2a-project\.venv\Scripts\python.exe' -B -m pytest tests\test_runtime_readiness.py tests\test_runtime_outcomes.py -q -p no:cacheprovider --basetemp '.test-tmp\final-targeted'
```

Final result: `42 passed in 1.17s`.

```powershell
$env:PYTHONPATH='E:\A2A\our-a2a-project\.worktrees\bibi-runtime-20260912'
& 'E:\A2A\our-a2a-project\.venv\Scripts\python.exe' -B -m pytest tests\test_live_curiosity.py tests\test_pending_question_outcome.py -q -p no:cacheprovider --basetemp '.test-tmp\sse-conversation-regression-2'
```

Review-fix result: `41 passed in 1.22s`.

```powershell
$env:PYTHONPATH='E:\A2A\our-a2a-project\.worktrees\bibi-runtime-20260912'
& 'E:\A2A\our-a2a-project\.venv\Scripts\python.exe' -B -m pytest tests -q -s -p no:cacheprovider --basetemp '.test-tmp\final-full'
```

Final result: `437 passed, 1 skipped in 8.29s`.

A capture-enabled full-suite rerun failed in pytest's own capture teardown before
test execution with `ValueError: I/O operation on closed file`; changing to
pytest's no-capture mode (`-s`) produced the complete passing run above. Targeted
and regression runs succeeded with normal capture.

## Parent integration requirements

1. Use `BABY_EXPERIENCE_VECTOR_INDEX=index_2bacf740` for the restored database,
   and make the retrieval query resolve the same registry variable.
2. Run `/health/live` and `/health` against the restored Neo4j and Redis. Confirm
   the vector shape/state and all missing-schema arrays, rather than treating a
   successful connection as sufficient readiness.
3. Exercise SSE connect/reconnect against that Redis instance. This worker did
   not start external services, so SSE recovery is not yet live-validated.
4. Keep schema/seed initialization out of ordinary start. If initialization is
   deliberately requested, call `run_explicit_initialization` and propagate its
   returned state into the readiness startup record; follow it with a fresh
   read-only readiness check.
5. The lifecycle `start/stop/status` launcher is parent-owned and is not part of
   this patch.

No commit, push, or merge was performed.
