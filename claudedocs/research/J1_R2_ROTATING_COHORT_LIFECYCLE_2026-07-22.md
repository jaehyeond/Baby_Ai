# J1-R2 Rotating Cohort Lifecycle

## 1. Decision

J1-R2 corrects one interpretation of the sealed J1-R1 relevance-scorer
contract. J1-R1 remains immutable historical evidence. Its graph-vocabulary
partition must not become a permanent ban on what Baby may learn.

The replacement rule is:

> Freeze evaluation evidence for one evaluation epoch. Never freeze Baby's
> live experience, graph growth, curiosity, or memory consolidation.

This is required by the project goal: a source-aware, grounded developmental
AI that can learn from Quest, tool, and environment outcomes while retaining
auditable promotion and rollback. The relevance scorer is one memory-retrieval
instrument, not the complete agent and not the research goal itself.

## 2. Why permanent cohorts are wrong here

A permanent question or concept holdout creates four problems for a growing
system:

1. useful experience may be withheld from the learner indefinitely;
2. graph vocabulary becomes stale as new concepts arrive;
3. repeated evaluation rewards optimization to a fixed benchmark;
4. a fixed split measures one snapshot, not learning progress over time.

The revised design freezes a graph snapshot and evidence assignment only for
the current evaluation epoch. Concepts created after the cutoff enter a
temporal-novelty stratum in the next epoch.

## 3. Four data roles

| Role | Reuse | Model selection | Claim status | Learning status |
|---|---:|---:|---|---|
| Live growth stream | continuous | no | not evaluation evidence | always eligible |
| Anchor regression | reusable | no | known regression data, never held out | already historical |
| Rolling development | within one generation | yes | exploratory/development only | labels release after consumption |
| One-time lockbox | no | no | final evidence only after opening | labels release to next generation |

The six legacy questions are the anchor. They are useful for retention and
regression tracking, but cannot support held-out or performance claims.

## 4. Generator governance

The development and lockbox cohorts must be produced by an independent,
deterministic generator. The subject model cannot generate its own questions
or grade itself. Canonical sources are limited to fixed public references,
deterministic synthetic environments, and instrumented Quest/tool outcomes.
Personal user memory is excluded from this benchmark.

The generator distribution is frozen before baseline output by binding:

- implementation SHA-256;
- specification SHA-256;
- sample-size-plan SHA-256;
- source and grading rules.

Rolling-development questions may then be materialized and reviewed before
the lexical baseline. Lockbox instances are different: the generator is frozen
first, the model snapshot is frozen later, and only then are instances sampled
from a hidden seed. Lockbox plaintext is never stored in the repository.

## 5. Release and renewal

A reserved item means a supervised benchmark label, not a concept that Baby is
forbidden to encounter. Live learning therefore continues while an epoch is
open. After a development or lockbox cohort is consumed, its labels may train
only the next model generation. The current epoch is renewed when its lockbox
is consumed, its graph snapshot is invalidated, or the epoch expires.

Continual evaluation must report more than static retrieval quality:

- pre-update to post-update learning progress;
- forward transfer to temporally new concepts;
- backward retention on the anchor;
- forgetting delta on prior anchor generations.

## 6. Sealed state

The lifecycle artifact is:

`claudedocs/research/j1_r2_relevance_cohort_lifecycle_20260722.json`

SHA-256:
`2ab4cf1edc5a97063d3cf540ff20620f645a7ff494bffb008cef84240577ce32`

The manifest hashes are:

| Role | SHA-256 | Current state |
|---|---|---|
| Anchor | `76355a8953d8dc88b4d427b3e9fb8cf494411cb398ce7bdf80394e463e35fc88` | materialized, active |
| Rolling development | `89595ade911eb996192031b91ec47e1827fc6b1d2142c0f296a3614f8887c4e4` | draft, zero questions |
| One-time lockbox | `6eef5c5e216851fc0e5e33b3d007d5edcbdaa1dbaf54b5f5425184bed921801b` | draft, zero questions |

Bundle readiness is sealed at:
`6beb8b98795cff0387a0980fdf3a4422d138c38d49c0b09da4b427f28a73e1f6`.

Current gates are deliberately:

- anchor manifest: `true`;
- development manifest: `false`;
- lockbox generator manifest: `false`;
- lexical baseline execution: `false`;
- held-out, performance, and production: `false`.

No question data was invented to make the gate pass. The next valid action is
to review and freeze the independent generator specification and sample-size
plan, materialize the rolling-development cohort, and freeze the lockbox
generator. Only then may the lexical baseline run.

## 7. Protected boundaries

This phase performs file reads, validation, and append-only JSON creation only.
It does not import the runtime, access Neo4j, train a model, download an
embedding model, change weights, or modify `conversation_handler.py`.
