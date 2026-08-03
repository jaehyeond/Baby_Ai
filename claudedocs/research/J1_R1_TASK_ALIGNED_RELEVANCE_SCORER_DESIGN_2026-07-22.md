# J1-R1 Task-Aligned Relevance Scorer Design

Date: 2026-07-22  
Status: contract defined; future data, baselines, training, and claims blocked

## 1. Why this component exists

The current Local Core was trained by causal-LM replay over shuffled graph-neighbor
concept names. J1 asks a different question: given a natural-language question,
which graph concepts are directly relevant to its answer? The adapter-disabled
comparison showed that removing LoRA increased output diversity but did not recover
meaningful exact targets. The new scorer must therefore be a separate task-aligned
component, not another interpretation of the replay adapter score.

This stage defines data and evaluation contracts only. It does not train a model,
download an embedding model, write Neo4j, change runtime behavior, or create a
performance claim.

## 2. Component boundary

```text
question text
    -> deterministic text normalization
    -> relevance scorer
    -> score every concept in the same sealed graph vocabulary
    -> deterministic rank
    -> top-k retrieval for downstream graph/curiosity use

relevance scorer ladder
    1. lexical char-ngram TF-IDF
    2. frozen local embedding cosine
    3. task-aligned learned projection head
```

The scorer returns ranking scores only. Graph spreading activation, memory writes,
curiosity updates, answer generation, and Local Core replay remain separate systems.

## 3. Positive and negative contract

The training unit is one `(question_id, concept_id)` pair.

| Reviewed decision | Target | Use |
|---|---:|---|
| `approved` | 1 | positive |
| `rejected` | 0 | explicit negative |
| `uncertain` | none | excluded from fit and metrics |
| no label | none | never treated as negative |

A positive must be a direct or answer-bearing concept under the reviewed answer.
Mere topical association is insufficient. A negative must have been explicitly
reviewed against the same answer. Random graph concepts and omitted candidates are
not negatives because the current label pool is incomplete.

The old reviewed pack remains `legacy_exploratory_train_only`:

- 6 questions
- 95 reviewed rows
- 23 positive, 56 negative, 16 uncertain
- 48 unique labeled concepts
- 17 concepts repeated across multiple questions

These rows can support prototype fitting. They cannot support held-out or performance
claims.

## 4. Graph vocabulary split

The sealed 1,069-concept vocabulary is assigned before labels and model scores with:

```text
bucket = first32bits(sha256("j1-r1-graph-vocabulary-v1\0" + concept_id)) mod 100
```

| Partition | Buckets | Concepts | Purpose |
|---|---:|---:|---|
| `fit_pool` | 0-79 | 856 | supervised fit identities |
| `development_challenge_pool` | 80-89 | 117 | unseen-concept development stratum |
| `lockbox_challenge_pool` | 90-99 | 96 | unseen-concept final stratum |

All systems still rank the complete 1,069-concept candidate vocabulary. Partitions
are used to restrict supervised labels and stratify metrics, not to make inference
easier by shrinking the candidate set.

Of the 79 binary legacy rows, 58 belong to `fit_pool` and may be used for supervised
prototype fitting: 15 positive and 43 negative. The 21 binary rows in reserved
partitions are excluded from fit.

Exact concept-ID separation is enforced. Semantic alias separation is not yet proven;
therefore no semantic-disjoint claim is allowed until aliases and near-duplicates are
audited.

## 5. Two independent evaluation axes

Question generalization and concept generalization answer different questions and
must not be collapsed.

1. **Primary: future question/time split**
   Measures whether the scorer handles questions that did not exist during model
   development. Random row split is forbidden.
2. **Secondary: concept partition stratum**
   Reports whether each relevant target belongs to fit, development challenge, or
   lockbox challenge vocabulary. This tests transfer to concept identities whose
   labels were not used for supervised fitting.

The primary metric is always computed per question and then macro-averaged. Row-level
micro accuracy is not a valid primary claim because negatives dominate.

## 6. Future development and lockbox packs

### Future development

- New question hashes must not overlap legacy questions.
- Questions and answer-source route are fixed before compared predictor outputs are
  revealed.
- A sample-size/precision plan is required before collection.
- This split may be used for model and hyperparameter selection.
- It remains development evidence, not the final performance claim.

### Future lockbox

- Its manifest must exist before the first supervised relevance-head fit.
- Question hashes must not overlap legacy or development questions.
- Answers and labels remain inaccessible until lexical, embedding, and learned models,
  prompt templates, checkpoints, and metric code are frozen.
- It is opened once and cannot be used for model selection.
- Any rerun after seeing results requires a new lockbox cohort.

To remain outside a human-subject study, canonical questions should come from public
knowledge, synthetic system tasks, or instrumented Quest/tool outcomes. Personal user
memory is excluded from benchmark claims unless a separate governance decision is
made.

## 7. Baseline ladder

### Stage 1: lexical char-ngram TF-IDF

- Unicode NFKC normalization, case folding, and whitespace collapse
- character n-grams of length 2-5
- IDF fitted only on the sealed candidate-name corpus, without labels
- no external API and no learned semantic model
- deterministic score/rank with concept ID as the final tie-breaker

Implementation may proceed now, but execution waits until the future-development and
future-lockbox manifests exist. Running it on the legacy six questions is diagnostic
only and establishes whether the task can be solved by surface overlap.

### Stage 2: frozen local embedding cosine

- local model only; paid embedding APIs are not a canonical baseline
- model ID, immutable revision, weight snapshot SHA-256, tokenizer snapshot, pooling,
  normalization, and prompt-template hash must be recorded
- no supervised label fit
- cannot run as the official second baseline until the Stage-1 artifact exists

The model choice is intentionally not embedded in this contract. It must be selected
and pinned in a separate artifact so changing an embedding model cannot silently
rewrite the baseline.

### Stage 3: task-aligned relevance head

The first learned architecture is a frozen local encoder plus a small projection or
similarity head. It trains only on reviewed binary rows in `fit_pool`. Full causal-LM
replay is forbidden for this objective. Checkpoint versioning and rollback are required.

A cross-encoder may later serve as an offline upper bound, but it is not the first
deployment candidate because it would require one forward pass per question-concept
pair and is poorly matched to Quest/on-device latency.

## 8. Metrics

Primary:

- macro question Recall@8
- macro question nDCG@8

Secondary:

- macro question MRR
- Average Precision on the explicitly reviewed candidate pool

Calibration metrics (`Brier`, log loss, ECE) remain disabled until the evaluated pair
set has exhaustive reviewed labels and the model explicitly emits probabilities.

All system comparisons are paired by question. Confidence intervals or randomization
tests must resample questions, not individual rows. Results are reported separately
for fit-pool targets and concept-challenge targets.

## 9. Promotion gates

The learned head cannot be trained until:

1. lexical artifact exists;
2. local embedding model and artifact are pinned;
3. future development manifest exists;
4. future lockbox manifest exists;
5. reviewed fit rows contain both classes;
6. checkpoint versioning and rollback are available.

Held-out, performance, and production gates remain false until the one-time lockbox
evaluation is complete. No scorer is connected to `conversation_handler.py` during
J1-R1.

## 10. Current artifact and next step

Machine-readable contract:
`claudedocs/research/j1_r1_relevance_scorer_contract_20260722.json`

Contract SHA-256:
`918183cbb9450c5f2932ce8d11434937c62210f4ea0b0633a4aa43f529f16a3d`

Immediate next implementation:

1. create separate future-development and future-lockbox manifest contracts;
2. implement and run the deterministic legacy train-only lexical baseline;
3. inspect whether surface overlap explains the existing targets;
4. only after those artifacts exist, select and pin a local embedding model.
