# GDSI Research Execution Log

> Started: 2026-07-28 KST
> Mode: append-only decision and evidence trace
> Scope: J1 relevance baseline -> J2 grounded action verifier -> J3 verified
> consolidation -> J4 shadow wake A/B

## Recording Protocol

This log records reproducible decision traces, not hidden chain-of-thought.
Every entry must separate:

1. user-approved objective;
2. current repository evidence and immutable input hashes;
3. hypotheses and alternatives considered;
4. actions actually executed;
5. observed success, failure, or blocked status;
6. claim limits and unresolved risks;
7. the next action and whether user approval is required.

Evidence labels:

- `CONFIRMED`: reproduced from code, artifact validation, or direct measurement.
- `FAILED`: an explicit metric or gate failed.
- `BLOCKED`: execution was not allowed or a prerequisite was absent.
- `EXPLORATORY`: useful diagnostic evidence, never a performance claim.
- `AGENT_HYPOTHESIS`: a new proposal from the coding/research agent, not evidence.
- `USER_DECISION_REQUIRED`: no execution beyond this point without user approval.

Anti-hallucination and anti-override rules:

- Never rewrite a sealed artifact. Add a successor artifact that binds the prior
  SHA-256.
- Never convert a missing value, unreviewed concept, or unavailable result into a
  negative observation.
- Keep DB write, learning, calibration, held-out opening, performance claims, and
  production promotion as independent false-by-default gates.
- Report paper title, identifier, year, venue, citation count, and verification
  date separately. A preprint is never promoted to peer-reviewed evidence by
  inference.
- Record measured values and agent interpretations in different fields or
  paragraphs.
- Do not treat code completion, graph growth, log count, or loss reduction alone
  as evidence that Baby improved future behavior.
- User approval of a design does not authorize DB writes, GPU training, model
  download, lockbox opening, or production integration unless stated explicitly.
- Do not commit or push unless the user explicitly requests it.

## Entry E000 - Starting State

### Objective

Develop Baby as a source-aware Grounded Developmental Self-Improvement system:
select low-risk epistemic actions, predict external outcomes before acting,
consolidate only verified experience, and improve future behavior without
forgetting.

### Confirmed State

- Branch: `DB_Renewal`.
- HEAD: `167265f`.
- J1-R2 rolling development: 12/12 questions user reviewed and materialized.
- J1-R2 lockbox: generator distribution frozen; exact questions and hidden seed
  are not materialized.
- Readiness: lexical baseline execution is allowed; held-out, performance, and
  production gates remain false.
- Current Local-Core causal replay is not a valid question-to-concept relevance
  learner.
- Current live curiosity plumbing records prediction error and learning progress,
  but the idle `explore_batch` path does not perform grounded exploration.
- `LOCAL_CORE_DISTILL` remains off.

### Existing Failures

- Graph external-outcome predictor failed to beat the frequency baseline.
- Local-Core outputs were weakly conditioned on the question.
- Adapter-disabled base inference did not recover a reliable relevance predictor.
- Existing Phase 2 gains are not sufficient evidence of leakage-safe future
  generalization.

### Decision

Finish the already-approved J1 lexical baseline as one bounded measurement.
Do not add another governance layer before obtaining an actual result.

### Next Action

Implement and execute `lexical_char_ngram_tfidf_v1` on the reviewed rolling
development cohort. This action performs no DB write, model download, GPU
training, calibration, lockbox materialization, or production integration.

## Entry E001 - J1-R2 Lexical Baseline

### Immutable Inputs

- Candidate vocabulary count: `1,069`.
- Reviewed rolling-development question count: `12`.
- Development manifest SHA-256:
  `f93e8c1e975763c8b06d045d905e15a777d95ae1948247e1196ffd8d3a27a982`.
- Frozen lockbox-generator manifest SHA-256:
  `0b5bc0cf40edb8826e1ef4f2cc705c243a02de458f182c93d153ad79a471b46f`.
- The exact lockbox questions and hidden seed remain unmaterialized.

### Action

Implemented a deterministic Unicode NFKC, casefolded, character `2..5`-gram
TF-IDF cosine ranker. IDF is fit only on candidate concept names. The scorer
ranks all `1,069` concepts, uses no label as a feature, and reports full-ranking
digests plus metrics over the explicitly reviewed four-concept pools.

The first CLI attempt was blocked by the execution sandbox when Python tried to
read its standard library from the local Python installation. The same command
was rerun after local-read authorization and completed. This was an environment
permission incident, not a model or metric failure.

### CONFIRMED

- Artifact:
  `claudedocs/research/j1_r2_lexical_baseline_development_20260728.json`.
- Artifact self SHA-256:
  `3fe59de88762142c37650b4e6c10ab2a420ad9c9725fec5562b8f1c8f9e3888f`.
- Independent `audit-existing` recomputation returned the same self hash.
- Focused tests: `46 passed`.
- Canonical tests: `363 passed`.
- Protected `conversation_handler.py` SHA-256 remained
  `054d974095be7425692860909181fafd54f97a33`.
- DB writes, API calls, model downloads, GPU use, gradients, optimizer steps,
  weight saves, calibration, lockbox materialization, and production changes:
  `0`.

### FAILED

- Macro Recall@8: `0.0`.
- Macro nDCG@8: `0.0`.
- Macro MRR: `0.012469448422`.
- Positive concept in top 8: `0/12`.
- Positive concept with nonzero lexical score: `1/12`.
- The sole nonzero positive ranked `10`, so it still missed top 8.

The reviewed-pool AP of `0.576388888889` is not evidence of useful retrieval:
it is calculated only over one positive and three explicit negatives per
question, while the production-shaped task ranks all `1,069` concepts.

### Interpretation

`CONFIRMED`: the J1 evaluation instrument executes reproducibly.

`FAILED`: surface-form overlap is not a useful question-to-concept relevance
scorer for this cohort.

`EXPLORATORY`: the result is consistent with a semantic relation gap because
11/12 positives share no measured character n-gram signal with their question.
It does not prove that a particular embedding model will solve the task.

The reviewed questions, labels, and candidate partitions must not be changed in
response to this result.

### Next Action

Select and pin one frozen local multilingual embedding encoder before running
Stage 2. A model download is a separate user-approval boundary.

## Entry E002 - Stage 2 Encoder Survey

### Search And Cross-Verification

Search date: `2026-07-28 KST`.

Sources consulted:

- arXiv search for multilingual-E5, BGE-M3, Qwen3-Embedding, and a 2026
  conversational-retrieval robustness study;
- Semantic Scholar paper lookup for venue/year cross-verification;
- Hugging Face model repository metadata for parameter count, language tags,
  license, task, and current repository availability;
- local Hugging Face cache inspection.

Semantic Scholar returned paper title, year, and venue but omitted requested
`citationCount` and `influentialCitationCount`; its direct API returned HTTP
429. Those counts are therefore recorded as `unavailable`, not guessed.

### Candidates

1. `intfloat/multilingual-e5-small`
   - Paper: *Multilingual E5 Text Embeddings: A Technical Report*,
     arXiv `2402.05672`, 2024.
   - Semantic Scholar venue: `arXiv.org`; citation counts: unavailable.
   - Credibility: technical-report preprint, not peer-reviewed evidence.
   - Repository: `117.7M` parameters, Korean included, MIT license.
   - Reproducible retrieval contract: `query:` and `passage:` prefixes,
     attention-mask mean pooling, L2 normalization, cosine.

2. `BAAI/bge-m3`
   - Paper: *M3-Embedding: Multi-Linguality, Multi-Functionality,
     Multi-Granularity Text Embeddings Through Self-Knowledge Distillation*,
     arXiv `2402.03216`, Findings of ACL 2024.
   - Semantic Scholar venue: Annual Meeting of the Association for
     Computational Linguistics; citation counts: unavailable.
   - Credibility: peer-reviewed, but the model supports dense, sparse, and
     multi-vector retrieval beyond this baseline's required scope.
   - Repository: more than 100 languages, 1024-dimensional embeddings, up to
     8192 tokens, MIT license.

3. `Qwen/Qwen3-Embedding-0.6B`
   - Paper: *Qwen3 Embedding: Advancing Text Embedding and Reranking Through
     Foundation Models*, arXiv `2506.05176`, 2025.
   - Semantic Scholar venue: `arXiv.org`; citation counts: unavailable.
   - Credibility: preprint, not peer-reviewed evidence.
   - Repository: `595.8M` parameters, Apache-2.0 license.
   - A separate 2026 arXiv preprint (`2604.06176`) reports conversational
     retrieval noise sensitivity without query prompting. This is an
     unverified risk report, not a reproduced result in Baby.

### Local State

None of the three repositories is present in the local Hugging Face cache.
`transformers` and `torch` are installed; `sentence-transformers` is not.

### AGENT_HYPOTHESIS

Use `intfloat/multilingual-e5-small` as the first frozen semantic lower bound.
It is the smallest candidate, explicitly supports Korean, has a fixed
query/passage prompt contract, and can be implemented with the already-installed
`transformers` and `torch` packages. This choice prioritizes a clean,
deployment-relevant diagnostic rather than the strongest available benchmark
model.

### Alternatives Rejected For Stage 2

- Do not compare all three on the 12 reviewed questions and pick the winner;
  that would use the development cohort for model shopping.
- Do not fit a projection head before a frozen semantic baseline exists.
- Do not add graph features to the embedding baseline; graph fusion is a later
  ablation and would hide which component produced the signal.
- Do not open or materialize the lockbox.

### USER_DECISION_REQUIRED

Approve or reject downloading and pinning
`intfloat/multilingual-e5-small` for one frozen Stage 2 development run.
Approval authorizes only the model download, local inference, artifact write,
and validation. It does not authorize training, DB writes, lockbox opening,
performance claims, or production integration.

## Entry E003 - Verification Corrections

### CORRECTION

E001 described `054d974095be7425692860909181fafd54f97a33` as a SHA-256.
That is incorrect: it is the Git blob SHA-1 returned by `git hash-object` for
`neural/baby/conversation_handler.py`.

The independently computed file SHA-256 is
`00a592f043e128523ba89d4be9015a78c520481e62c6cdb821b53877e4a02f84`.
Both values were recorded without modifying the protected file. The protection
check therefore passes; only the algorithm label in E001 was wrong.

### Operator Incident

The final artifact audit was first invoked with a nonexistent `--artifact`
option. The CLI rejected the command before reading or writing an artifact.
It was immediately rerun with the implemented `--output` option and returned
the expected self SHA-256
`3fe59de88762142c37650b4e6c10ab2a420ad9c9725fec5562b8f1c8f9e3888f`.

This incident did not change code, inputs, labels, the artifact, or any research
metric. It is recorded to distinguish an operator invocation failure from an
implementation or scientific failure.

## Entry E004 - Stage 2 Frozen Embedding Implementation

### Objective

Prepare the complete local-only Stage 2 execution path while preserving the
explicit user-approval boundary for model download and inference.

### Read-Only Model Verification

- Model ID: `intfloat/multilingual-e5-small`.
- Immutable revision:
  `614241f622f53c4eeff9890bdc4f31cfecc418b3`.
- Model contract SHA-256:
  `cb71059d69d2a93a7b2cf33468bee46d2b2a43014f2c6e33e700ce8215c664ba`.
- Required local snapshot: nine files, `492,800,290` bytes.
- `model.safetensors`: `470,641,600` bytes, LFS SHA-256
  `1a55775f53449dac10a2bcbc312469fac40b96d53198c407081a831f81c98477`.
- Official configuration checked read-only: 384-dimensional mean pooling,
  512-token maximum, `query: ` and `passage: ` prefixes, L2 normalization.

The remote revision and file metadata were read without downloading model
weights. Hugging Face and Transformers documentation was checked for the
current `snapshot_download`, `local_dir`, `allow_patterns`, and
`local_files_only=True` behavior.

### Implementation

- `neural/baby/relevance_embedding_baseline.py`
  - exact-scope user-decision validator;
  - pinned file size, Git-blob SHA-1, and LFS SHA-256 verification;
  - local snapshot manifest sealer and directory re-audit;
  - label-free query/candidate encoding interface;
  - full-vocabulary cosine ranking and metric recomputation;
  - self-hashed development artifact validator.
- `scripts/research/j1_r2_embedding_baseline.py`
  - `readiness`, `acquire-model`, `seal-existing-model`, `run`,
    `audit-existing`, and `audit-with-model`;
  - pinned `snapshot_download` with an E-drive default destination;
  - strict local-only `AutoTokenizer`/`AutoModel`, no remote code,
    safetensors only, CPU float32, evaluation mode, zero trainable parameters,
    deterministic algorithms, attention-mask mean pooling.
- `tests/test_relevance_embedding_baseline.py`
  - model-contract pinning;
  - exact user-approval scope;
  - LFS substitution rejection;
  - missing-snapshot fail-closed behavior;
  - prompt-only feature surface;
  - full-vocabulary and metric recomputation;
  - artifact tamper and non-frozen runtime rejection.

### CONFIRMED

- Focused tests: `9 passed`.
- Canonical tests: `372 passed`.
- Python compilation: passed.
- Lexical predecessor re-audit: self SHA-256 remains
  `3fe59de88762142c37650b4e6c10ab2a420ad9c9725fec5562b8f1c8f9e3888f`.
- Readiness reports `lexical_predecessor_chain_gate=true`.
- Calling `acquire-model` without the user decision fails before importing the
  download client or creating the model directory.
- Expected model directory remains absent.

### BLOCKED

- `model_download_authorized_gate=false`.
- `local_snapshot_validation_gate=false`.
- `embedding_execution_ready_gate=false`.
- No embedding score or metric has been produced.

The first readiness command was blocked before script startup by the same local
Python standard-library sandbox restriction seen in E001. It succeeded after
read-only local Python access was authorized. This is an environment incident,
not a Stage 2 code or model result.

### Claim Limits

This entry proves implementation and approval-boundary behavior only. It does
not prove semantic retrieval improvement, model suitability, Baby learning,
held-out performance, or production readiness.

### USER_DECISION_REQUIRED

Approve or reject the exact Stage 2 scope already listed in E002:

1. download only the nine required files at the immutable revision;
2. verify and seal the local snapshot;
3. run one CPU, frozen, development-only inference over the same 12 questions
   and 1,069 concepts;
4. rerun the model once to audit reproducibility.

Training, DB writes, lockbox materialization, held-out evaluation, performance
claims, and production integration remain forbidden.

## Entry E005 - Stage 2 Byte-Count Correction

### CORRECTION

E004 states that the nine required files total `492,800,290` bytes. That value
is incorrect. The sum recomputed directly from the immutable model contract is
`492,795,290` bytes.

The per-file sizes, revision, LFS SHA-256 values, and model-contract SHA-256 in
E004 are unchanged. This was a documentation transcription error and did not
affect code, tests, a downloaded snapshot, or any research metric.

## Entry E006 - Approved Frozen Embedding Run and Exact Rerun Audit

### USER_DECISION

The user explicitly approved only:

1. downloading the pinned `intfloat/multilingual-e5-small` snapshot;
2. verifying and sealing its integrity;
3. one frozen inference run over the existing 12-question development cohort;
4. one same-model rerun audit.

The decision artifact is
`scripts/research/inputs/j1_r2_embedding_model_review_decision_20260728.json`,
self SHA-256
`48a7710f23834fa0b087eca68c8d7f078026489c72785e6b28b7008a5dbe0de9`.
It does not authorize training, DB writes, exact lockbox question
materialization, held-out evaluation, performance claims, or production
integration.

### CONFIRMED - Snapshot Acquisition and Seal

- Model ID: `intfloat/multilingual-e5-small`.
- Immutable revision:
  `614241f622f53c4eeff9890bdc4f31cfecc418b3`.
- Exactly nine allowlisted files were downloaded to the E-drive model cache.
- Recomputed total size: `492,795,290` bytes.
- `model.safetensors` SHA-256:
  `1a55775f53449dac10a2bcbc312469fac40b96d53198c407081a831f81c98477`.
- Snapshot manifest:
  `scripts/research/manifests/j1_r2_multilingual_e5_small_snapshot_20260728.json`.
- Snapshot manifest self SHA-256:
  `52db8de09fb58cda4d231d306a53d401cceeed0e34e0bde96dc50d7d3263ca59`.
- Post-acquisition readiness had no block reasons. Local snapshot validation,
  lexical predecessor chain, approval, and execution-readiness gates were true;
  all held-out, learning, DB-write, performance, and production gates remained
  false.

### CONFIRMED - Development Inference

The frozen CPU model ranked all `1,069` graph concepts for each of the existing
12 reviewed development questions. It did not consume labels as encoder
features and did not update model weights or the graph.

- Artifact:
  `claudedocs/research/j1_r2_embedding_baseline_development_20260728.json`.
- Artifact self SHA-256:
  `8a7b8fbfb24014ca356160c530789b7eb468d475c579f8c77bbb946e9c55d8e4`.
- Macro Recall@8: `0.5`.
- Macro nDCG@8: `0.291023572476`.
- Macro MRR: `0.238188745977`.
- Reviewed-pool AP: `1.0`.
- Full-vocabulary positive top-1/top-3/top-8/top-20:
  `1/12`, `4/12`, `6/12`, `8/12`.
- Mean positive rank: embedding `53.583333`, lexical `377.583333`.
- Median positive rank: embedding `8`, lexical `313`.
- Compared with the lexical predecessor, the positive rank improved in
  `11/12` questions, tied in `0/12`, and worsened in `1/12`.

### CONFIRMED - Same-Model Rerun

The complete encoding, ranking, and metric computation was run again from the
same sealed snapshot. The rerun reproduced the exact artifact self-hash and all
aggregate metrics. `model_rerun_verified=true`.

### FAILURE_ANALYSIS

The positive-rank results by question were:

| Target | Embedding rank | Lexical rank |
|---|---:|---:|
| 서울 | 4 | 127 |
| 달 | 67 | 547 |
| 구름 | 4 | 71 |
| 최단 경로 | 227 | 10 |
| 청각 | 3 | 134 |
| 중력 | 76 | 168 |
| 카메라 | 1 | 677 |
| 알고리즘 | 230 | 730 |
| 계산기 | 3 | 461 |
| 음악 | 2 | 322 |
| 로봇 | 14 | 304 |
| 프로그램 | 12 | 980 |

The reviewed-pool AP of `1.0` does not establish successful graph-vocabulary
retrieval. Each question has only three explicit reviewed negatives, and those
negatives were easy for this model, while six positives still fell outside the
top eight among all 1,069 candidates.

Two distinct failure sources are visible:

1. concept-name-only embeddings do not reliably solve relational definitions,
   such as natural-satellite-to-moon or force-to-gravity;
2. graph vocabulary contains fragment or surface-form nodes such as
   `그래프에서.`, `알고리즘으로.`, and `사용.` that can outrank canonical
   targets.

The result is therefore a reproducible development semantic signal, not a
held-out performance result, not evidence that Baby learned, and not permission
to train a relevance head.

### OPERATOR_INCIDENT

An initial ad hoc PowerShell rank-comparison command used an invalid
`Where-Object Embed -lt Lexical` expression. It emitted errors and incorrectly
printed zero comparison counts. No artifact or source file was modified. The
comparison was rerun with the explicit script block
`Where-Object { $_.Embed -lt $_.Lexical }`, yielding the confirmed
`11 improved / 0 tied / 1 worsened` counts above.

### AGENT_HYPOTHESIS

Training the projection head now would mostly learn from easy negatives and
could produce an optimistic in-sample result. The next bounded research step
should first create a successor diagnostic for:

1. reviewed hard negatives sampled from the frozen embedding top ranks;
2. canonical target aliases and graph vocabulary fragment quality;
3. error buckets separating lexical form, relational reasoning, and graph-node
   quality.

Any candidate-text enrichment must be provenance-safe, fixed before scoring,
and evaluated as a new successor baseline rather than silently modifying this
sealed result.

### USER_DECISION_REQUIRED

Approve or reject the proposed hard-negative and graph-vocabulary-quality
diagnostic. Such approval would authorize read-only analysis and reviewed input
preparation only. It would not authorize learned-head training, graph cleanup,
DB writes, lockbox opening, held-out evaluation, or production integration.

## Entry E007 - Post-Run Regression and Boundary Audit

### CONFIRMED

- Canonical test suite: `372 passed`.
- Stage 2 Python compilation: passed.
- No-model `audit-existing` recomputed the artifact self-hash as
  `8a7b8fbfb24014ca356160c530789b7eb468d475c579f8c77bbb946e9c55d8e4`
  and reproduced the stored aggregate and partition metrics.
- Post-run readiness revalidated the pinned local snapshot and approval
  decision. Its only block reason is
  `embedding_output_already_exists_refuse_overwrite`, which is the intended
  sealed-output overwrite guard.
- `audit-existing` reports `model_rerun_verified=false` by design because that
  command does not load or rerun the model. The earlier `audit-with-model`
  command performed the approved rerun and reported `true`; these outputs have
  different scopes and are not contradictory.
- Protected `neural/baby/conversation_handler.py` Git blob remains
  `054d974095be7425692860909181fafd54f97a33`.
- `git diff --check` found no whitespace error; its only messages were the
  existing Windows LF-to-CRLF conversion warnings for three tracked Markdown
  files.
- A direct trailing-whitespace scan over the Stage 2 code, tests, decision,
  manifests, artifacts, and updated current-truth documents found no matches.

### Claim Limits

This audit establishes deterministic execution, artifact integrity, regression
safety, and protected-boundary preservation. It does not upgrade the
development metrics into held-out evidence or authorize the next research
stage.

## Entry E008 - J1-R2-E3 Hard-Negative and Vocabulary Diagnostic

### USER_DECISION

The user's instruction to proceed with the next step is applied to the exact
scope proposed in E006: read-only hard-negative analysis and reviewed-input
preparation. It does not authorize automatic labels, learned-head fitting,
graph cleanup, DB writes, lockbox materialization, held-out evaluation, or
production integration.

### Contract

The diagnostic consumes the sealed E2 embedding artifact, the same 1,069
candidate vocabulary, the same 12 development questions, and the same reviewed
label pack. It does not rerun the embedding model.

For each question it selects:

1. the five highest-ranked currently unjudged concepts;
2. only when the positive is outside top-8, unjudged concepts within rank
   distance two of the positive.

Existing reviewed positives and negatives are references, not new candidates.
Unjudged never means negative.

Human review is split into independent dimensions:

- relevance:
  `positive/context/hard_negative/unrelated_negative/uncertain`;
- vocabulary:
  `canonical/alias/fragment/malformed/uncertain`.

This separation prevents a semantically related context concept or a malformed
surface form from being collapsed into the same binary label.

### Implementation and Verification

- Pure module:
  `neural/baby/relevance_hard_negative_vocabulary_audit.py`.
- CLI:
  `scripts/research/j1_r2_hard_negative_vocabulary_audit.py`.
- Focused tests:
  `tests/test_relevance_hard_negative_vocabulary_audit.py`.
- Focused result: `9 passed`.
- Python compilation: passed.
- Actual sealed-input readiness: no block reasons; diagnostic generation true;
  all automatic-label, training, DB, head-fit, lockbox, held-out, performance,
  and production gates false.
- Canonical result after generation: `381 passed`.

The first readiness invocation was blocked during Python site initialization by
the local filesystem sandbox denying reads of the installed Python standard
library. The same command passed after the already-scoped local Python access
was authorized. This was an environment incident, not an input-chain or
diagnostic failure.

### Generated Artifacts

- Pending review packet:
  `scripts/research/inputs/j1_r2_embedding_hard_negative_review_packet_20260728.json`.
- Packet self SHA-256:
  `aec20a9d0c714e768c560d8eb4d517edf604ca6c03cd7fc01ed8830fbf2339e4`.
- Read-only audit:
  `claudedocs/research/j1_r2_embedding_hard_negative_vocabulary_audit_20260728.json`.
- Audit self SHA-256:
  `696fe080b26bbb40af6e433394956b8cf6649ca1aff40d843d11288b2f3a04b4`.
- Immediate independent `audit-existing`: exact match.

### Results

- Questions: `12`.
- Review rows: `84`.
- Unique selected concepts: `67`.
- Top-unjudged rows: `60`.
- Positive-rank-neighbor rows: `24`.
- Automatically assigned positive/context/hard-negative/unrelated labels: `0`.
- Vocabulary concepts with at least one deterministic surface flag: `41/1069`.
- Boundary-punctuation concepts: `35/1069`.
- Boundary-punctuation variant groups: `6`, covering `12` concepts.
- NFKC+casefold normalized exact-collision groups: `0`.
- Selected-row boundary-punctuation flags: `12`.
- Selected-row boundary-punctuation-variant flags: `10`.

Examples of verified punctuation variants include:

- `그래프에서` / `그래프에서.`;
- `알고리즘으로` / `알고리즘으로.`;
- `사용` / `사용.`;
- `구현해줘` / `구현해줘.`.

Machine flags are objective review cues only. They are not automatic alias,
fragment, malformed, or negative labels.

### FAILURE_ANALYSIS

The selected top candidates confirm why unjudged-as-negative is unsafe.
For the Seoul question, `수도`, `한국의 수도`, `도시`, and `서울특별시` rank
above or near the reviewed positive `서울`. These include plausible context,
answer paraphrase, or alias cases; converting them all to negatives would
poison the relevance target.

The shortest-path question instead ranks `그래프에서.`, `그래프에서`, `경로.`,
`알고리즘으로.`, and `알고리즘으로` above the positive. This is evidence that
semantic relevance error and graph surface-form quality are separate failure
sources.

A post-generation recheck found that the 24 positive-neighbor rows are mostly
deep-rank score-band samples for failed questions. Examples around the positive
include `네/신기한 것/비 생성 과정/이동시키는` for `달` and
`계획/이유/나무/신기한 것` for `중력`. These rows are useful to diagnose score
compression but are not useful hard-negative candidates.

### CORRECTED_NEXT_RULE

- The `60` top-unjudged rows are the primary semantic review set.
- The `24` positive-neighbor rows are diagnostic-only.
- A future decision materializer must refuse to convert diagnostic-only
  neighbor rows into learned-head negatives.
- Existing E3 artifacts remain unchanged; the distinction is preserved by each
  row's `selection_reasons` and this append-only correction.

### USER_DECISION_REQUIRED

The next bounded step is to present agent recommendations for the 60 primary
rows, then receive user corrections or approval before creating a separate
review-decision artifact. No recommendation or user approval may mutate the
sealed packet. No learned-head training is authorized yet.

## Entry E009 - Primary-Row Agent Recommendations

### Action

Created
`claudedocs/research/J1_R2_E3_PRIMARY_REVIEW_AGENT_RECOMMENDATIONS_2026-07-28.md`
for the 60 `top_unjudged` rows. The document is bound by reference to packet
`aec20a9d...` and audit `696fe080...`.

The 24 diagnostic-only positive-neighbor rows are explicitly excluded.

### Proposal Counts

Relevance:

- positive: `1`;
- context: `52`;
- hard-negative: `4`;
- unrelated-negative: `3`;
- uncertain: `0`.

Vocabulary:

- canonical: `36`;
- alias: `1`;
- fragment: `16`;
- malformed: `7`;
- uncertain: `0`.

An independent regex count over the 60 Markdown table rows reproduced these
counts exactly.

### Critical Interpretation

The proposed hard-negative yield is only `4/60`. Most top-ranked unjudged
concepts are related context, components, hypernyms, or graph extraction
fragments. Therefore:

1. top-ranked unjudged concepts are not a valid negative pool;
2. binary positive-versus-all-other training would suppress useful semantic
   neighborhoods;
3. context must either be excluded from binary loss or modeled as a separate
   target;
4. vocabulary repair decisions must remain independent from relevance labels.

### Claim Limits

These are agent recommendations, not user-reviewed labels and not training
data. They do not change the sealed packet or any existing label pack.

### USER_DECISION_REQUIRED

The user must approve or correct the 60-row proposal before a separate,
self-hashed review-decision artifact can be created. That approval still would
not authorize learned-head fitting; the post-review data contract must be
reviewed separately.

## Entry E010 - Controlled Dream Audit Placement

### Reference Interpretation

The reviewed `Inputs -> Wiki -> Outputs -> Dream Sequence` pattern is useful as
an external-memory maintenance architecture, not as evidence that an LLM
updates its own weights or becomes more intelligent automatically. The closest
primary design reference is Andrej Karpathy's LLM Wiki:

- short reviewed: `https://www.youtube.com/shorts/LmFLiXsQ9LI`;
- primary idea file: `https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`.

The primary design separates:

- immutable raw sources remain the source of truth;
- an LLM-maintained wiki is derived, compiled memory;
- `CLAUDE.md` or `AGENTS.md` defines the schema and maintenance rules;
- ingest, query, and lint are distinct operations.

The short's quantitative growth language is not adopted as a research claim.

### Placement Decision

Add `J1-R2-M0 Controlled Dream Audit` as a non-blocking side track:

```text
J1 critical path:
E3 user review
  -> self-hashed review-decision artifact
  -> post-review relevance-learning contract
  -> learned-head development evaluation

Memory-integrity side track:
E3 review-decision artifact
  -> M0 read-only detection
  -> proposal-only artifact
  -> human review
  -> separately approved transactional repair, if justified
```

M0 is not inserted before E3 review because the agent recommendations are not
reviewed truth. M0 also does not replace J3 verified sleep self-compile: J3
trains candidate weights or world-model components from verified J1/J2
records, whereas M0 audits the integrity of the external graph memory.

### Initial Scope

The first M0 contract may consume only:

1. the sealed E3 packet and audit;
2. the future user-reviewed E3 decision artifact;
3. a frozen graph-vocabulary snapshot and its hash;
4. deterministic detector/version hashes.

The first detector family is limited to evidence already exposed by E3:

- aliases and punctuation variants;
- fragments;
- malformed surface forms.

Contradiction, staleness, orphan, and provenance-gap detection are later
extensions because they require additional relation, time, and source
contracts.

### Hard Boundaries

The first M0 iteration must remain:

- read-only against Neo4j;
- proposal-only and reversible by construction;
- independent from relevance labels;
- non-blocking for the J1 learned-head development path;
- unable to auto-label, merge, delete, or write graph state;
- unable to train or modify model/LoRA weights;
- unable to enable `LOCAL_CORE_DISTILL` or a scheduled Dream job.

Any later repair executor requires separate user approval, a transaction,
before/after snapshots, rollback instructions, and preservation of the current
1,069-concept evaluation universe until the current evaluation epoch is
complete.

### Correct Next Action

The immediate next action remains the 60-row E3 user review. After approval or
correction, create the self-hashed E3 review-decision artifact. Then:

1. define the post-review relevance-learning contract on the J1 critical path;
2. in parallel, specify the M0 proposal schema and read-only detector contract;
3. do not implement graph mutation or scheduled maintenance.

## 2026-09-07 — 보호 핸들러 blob 재기준선 (feature/memory-gateway → DB_Renewal merge)
- `neural/baby/conversation_handler.py` 에 두 줄(import `_gateway_augment`, `_build_system_prompt` 직후 호출)을 추가했다. `MEMORY_GATEWAY=1` 이 아니면 반환값이 그대로라 기존 동작은 바뀌지 않는다.
- blob: HEAD ef48297 `054d974095be7425692860909181fafd54f97a33` → 브랜치 `c1922cc61240c75b7446306ed2b57e70d813f27d`.
- 이 브랜치를 합치면 위 "무변경 ✅" 판정의 기준값은 뒤의 값이다. J1 봉인 artifact 는 건드리지 않았다. 새 worktree 체크아웃에서 원시 바이트 sha256 봉인 테스트 3건이 실패하는데, 해당 파일은 미수정이고 blob 은 HEAD 와 같다(줄끝 정규화 차이로 판단, E: 체크아웃에서 재확인 필요).
- 라이브 그래프 쓰기(사용자 지시 "다음 순서 진행"에 따름): :Person 5개(owner 속성 6개 채움 + stranger 4개, created_by=person_hub_seed_2026-09-07), 시나리오 대화 Experience 5개(speaker brother, 2026-09-07 08:26~08:30 UTC), FEELS_ABOUT 12개, access_ts 갱신. 평가 universe 의 Concept 삭제·병합은 없다.
