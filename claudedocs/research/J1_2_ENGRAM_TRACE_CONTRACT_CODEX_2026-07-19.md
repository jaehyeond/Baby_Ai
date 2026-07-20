# J1.2 Engram Trace Contract — 구현 지시문 + 구현 결과 (self-contained)

> 작성: 2026-07-19 (Claude Code). **rev2 정정본** — §11 정정 이력을 먼저 읽을 것.
> **✅ 구현 완료 (2026-07-20). 구현 중 rev2 대비 2건을 상향 수정했다 — §12 참조.**
> 봉인 계약 sha256 = `1112d9ef7b592076d57cce71f466201154b8f859920d69363c010f1dc8983eed`
> 이 문서는 **구현 지시문**이지 current truth가 아니다. current truth = `AGENTS.md` 체크포인트 + 실제 봉인 artifact JSON.
> `HANDOFF.md` / `TASKS.md`는 current truth로 사용 금지.

---

## 1. 목적

J1 offline contract chain(Question-as-Experiment)에 **정의 전용(definition-only) J1.2 "Engram Trace Contract"** artifact 한 개를 추가한다.

이 계약은 AI Engram 논문(arXiv 2606.14997, "AI Engram: In Search of Memory Traces in Artificial Intelligence", Kwon·Kim·Kim·Kim·Kook·Cha; arXiv상 **ICML 2026 Oral 자기보고**, Semantic Scholar venue/citation **미반영 = 초기 단계 연구**)의 4 criteria(specificity / reactivation / sufficiency / necessity)를 Baby의 4개 층(graph memory / local-core predictor / question-selection probability / source provenance)에 대한 **offline audit 분류표(taxonomy)**로 봉인한다.

**핵심 제약: 어떤 engram 수치도 측정·생성하지 않는다.** 정의·게이트·금지목록·provenance만 봉인하고, 모든 runtime/DB/learning/weight-editing gate는 fail-closed로 false다. 봉인된 chain tip(`eb874fe9…`)이 선언한 `next_step`(capture)은 **보존**되며, J1.2는 그것을 소비·대체·재정렬하지 않는 **병렬 사이드카**다.

산출물은 순수 파일 read + sha256 + JSON write이므로 **GPU 불필요, Neo4j 불필요**하다.

---

## 2. PROTECTED BOUNDARIES (절대 준수 — 위반 시 작업 무효)

1. `neural/baby/conversation_handler.py`(v30)는 **수정 금지**. blob 무변경이 완료 조건에 포함된다.
2. DB write / learning / runtime / production promotion gate는 사용자 명시 승인 전까지 **전부 false**. 새 artifact도 fail-closed로 이 gate들을 false 선언한다.
3. 기존 sealed artifact(`claudedocs/research/*.json`, `scripts/research/inputs/*.json` 중 **기존 파일**)는 **수정 금지**. 새 파일만 추가.
4. `HANDOFF.md` / `TASKS.md`는 current truth 아님.
5. git commit / push는 **사용자 명시 요청 시에만**.
6. weight editing / unlearning / knowledge editing **실행 금지**. Engram 아이디어는 offline 측정/audit 계약으로만 도입한다.
7. offline audit는 **api_server route/hook 등록 0건, HTTP endpoint 호출 0건, Neo4j는 read-only(MATCH / OPTIONAL MATCH / RETURN)만**.

---

## 3. 현재 chain 상태 (2026-07-19 실측)

- 봉인 fresh-shadow chain tip: `scripts/research/inputs/j1_1_fresh_shadow_question_selection_20260718.json`, self-hash `eb874fe9ee5ca53f24f816308c390a1c469f99d2fbf12211735d656e8ec97af9`.
- 선택된 질문 = **order 5, `j1-1-cal-a-05`** (mean_binary_entropy 0.8375901271152193, runner-up order 2 = `j1-1-cal-a-02`).
- tip의 declared `next_step` = `capture_real_fresh_pre_question_shadow_inputs_read_only_before_runtime_selection`.
- **이 next_step은 immutable.** J1.2는 자기 `next_step` 필드에 이 문자열을 **verbatim 재선언**한다.
  - 근거: append-only + sha256 임베드 chain에서 하위 leaf는 상위 hash를 바꿀 수 없다. 정의 사이드카는 트렁크를 선행·차단하지 않는다.
- **로컬 코어 어댑터는 봉인 시점 그대로 무결하다** (§11 정정). `models/local_core_adapter/`의 디렉토리 다이제스트가 봉인된 `dd60ed3c…`와 **정확히 일치**함을 2026-07-19 재현 확인. 따라서 capture 트렁크는 **원래의 sealed model identity 그대로 실행 가능**하며, 새 lineage 분기가 필요 없다.
- fresh shadow 체인 4단계 + 관련 모듈/테스트는 현재 **untracked 미커밋**(branch `DB_Renewal`, 16개 파일). J1.2도 커밋하지 않는다.

---

## 4. 생성할 파일 (5개, 전부 신규)

| 역할 | 경로 |
|---|---|
| 봉인 full artifact | `scripts/research/inputs/j1_2_engram_trace_contract_20260719.json` |
| 요약 report | `claudedocs/research/j1_2_engram_trace_contract_20260719.json` |
| 순수 라이브러리 | `neural/baby/engram_trace_contract.py` |
| argparse 스크립트 | `scripts/research/j1_2_engram_trace_contract.py` |
| 테스트 | `tests/test_engram_trace_contract.py` |

기존 fresh-shadow 4단계와 동일한 구조(순수 라이브러리 + 얇은 스크립트 + 테스트 + inputs/claudedocs 이중 산출)를 따른다.

---

## 5. STEP-BY-STEP 구현

### STEP 0 — 무결성 게이트 (쓰기 전 필수)

4개 fresh artifact의 canonical sha256을 재계산해 각 self-hash 필드와 `==` assert. 불일치 시 **abort**. 쓰기 없음.

canonical 규칙: own-hash 필드 pop → `json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))` → UTF-8 인코딩 → sha256.

### STEP 1 — read-only 재검증 (enforced 12개 hash, unenforced 0개)

아래 12개 전부에 대해 `declared == recomputed == stored-in-upstream` 삼중대조를 적용한다. **12개 모두 재계산 소스 파일과 stored 위치가 2026-07-19에 실측 확인됐다.**

직접 enforced 10개 (fresh/계약 chain에 직접 stored):
```
eb874fe9ee5ca53f24f816308c390a1c469f99d2fbf12211735d656e8ec97af9  fresh_shadow_question_selection
494cdd41845ac4f50ae4825db47fcaad63745f0c332bc9bc0ebac7a31209a491  fresh_pre_question_shadow_probability_snapshot
3369c1202d080920ccca9a3b097b3617d6b3d7c0d821c1385f28a585f36416c7  fresh_pre_question_input_pack
6ef040e24c9c74c62f6dbf7e15d7e186f0187bf1c4c45e691b990d09d153fa13  fresh_pre_question_snapshot_input_contract
fd3965f02616b55d7ff9c01785050fd3dcc211bccfde542621a67e61dcedf049  train_only_calibrator_fit
1b11df5ac8c62cc249c59bcb262cf96ded57da7d44c8c62694f07d492644f58b  calibrator_design_audit
2c4ad22d558653e1438a0dc9fa47bf1f8ab37bf02225706a50d5dc0d9a6d1c12  calibrator_probability_snapshot
200421ce2c88956b0328770a2217250343f9f4af2257406beafbc0fe36666c7a  question_selection_contract
69bbe4d302fe152cb80bf6eaa1f5a39ffb2acbc62bc05dc3c4867a30f663cd15  feature_schema
afebaaf55942a27dcdbba91559e5a456cc9fd93855317845e37ce0211be46d15  independent_score_capture
```

추가 enforced 2개 (초안에서 "dangling"으로 오판했던 것 — 소스와 경로 확정됨):

**`518e5e6adb50d6abcfecf3b6bdbb3241c4129f7c106eb4be7aa2113f2110e21d` (union_label_pack)**
- recompute 소스: `scripts/research/inputs/j1_1_candidate_universe_v2_labels_reviewed_20260718.json`에서 `union_label_pack_sha256` 키를 pop 후 canonical hash → 정확히 일치 (실측).
- stored-in-upstream: `j1_1_candidate_universe_v2_train_only_calibrator_fit_20260718.json` (= 이미 enforced인 `fd3965f0`)에 stored.
- → 1-hop, 파일 1개 추가 로드로 삼중대조 완성.

**`89c9f71d63ec6e3b040479c32892826747247db6addccaa06e5c38da82d62ac2` (answer_source_amendment)**
- recompute 소스: `scripts/research/inputs/j1_1_answer_source_amendment_20260716.json`에서 `amendment_sha256` pop 후 canonical hash → 정확히 일치 (실측).
- stored-in-upstream 경로 (2-hop, 전 구간 실측):
  `afebaaf5`(enforced raw_scores) → stores `candidate_vocabulary_sha256: bc06ed54f24420eecdaa0be156f6041d882e80648bc64030baf5ac00bd2abd82`
  → `j1_1_candidate_vocabulary_v2_20260716.json`에서 `candidate_vocabulary_sha256` pop 후 재계산 시 `bc06ed54…` 일치
  → 같은 vocabulary 파일이 `answer_source_amendment_sha256: 89c9f71d…`를 stored.
- → 파일 2개 추가 로드로 삼중대조 완성.

`unenforced_provenance` 블록은 **불필요하다.** 넣지 말 것.

### STEP 2 — 라이브러리 `neural/baby/engram_trace_contract.py`

순수 함수(Mapping → dict). dataclass·파일 I/O 없음. `canonical_json_sha256`은 기존 모듈에서 import 재사용.

함수 3개: `build_engram_trace_contract(*upstream)` (입력검증 → seal → **자기 출력 재검증**), `_seal_engram_trace_contract(payload)`, `validate_engram_trace_contract(payload, *upstream)`.

validator 규칙:
- `engram_trace_contract_version == 1`; `phase == "J1.2"` (다른 값 hard-reject); status/scope/policy 정확 일치.
- own gate `engram_trace_contract_gate is True`.
- **required-false 20개 + `local_core_engram_interpretation_gate`**를 `is not False`로 검사. 특히 `engram_measurement_executed_gate is not False` → `ValueError`.
- `block_reasons`가 비면 `ValueError("must enumerate measurement blockers")`.
- **recursive forbidden-field guard는 fresh 체인의 KEY 기반 15-이름 exact-match를 그대로 유지.** ⚠️ **substring/값 매칭으로 확장 금지** — J1.2 payload는 `forbidden_operations` / `block_reasons` / `criteria_mappings`에서 개입 마커를 정당하게 *열거*하므로 값 매칭 시 self-trip한다.
- upstream 인자가 주어지면 **실명 validator 재실행** (실제 함수명은 각 모듈에서 확인 후 import):
  `validate_fresh_shadow_question_selection`, `validate_fresh_pre_question_shadow_probability_snapshot`, `validate_fresh_pre_question_input_pack`(contract 인자 필요), `validate_fresh_pre_question_snapshot_input_contract`, `validate_question_selection_contract`, `validate_calibrator_probability_snapshot`, `validate_train_only_calibrator_fit`, `validate_calibrator_design_audit`, `validate_independent_score_capture`.
  ⚠️ 이 배선(각 validator의 인자 의존성 엮기)이 **이 작업의 최대 비용 항목**이다. fresh_shadow_selection 템플릿은 upstream 1개만 스레드하므로 그대로 복사하면 부족하다.
- self-hash pop/recompute mismatch → `ValueError`.

### STEP 3 — 테스트 `tests/test_engram_trace_contract.py`

plain pytest, inline self-sealed 합성 upstream.

Positive: own gate `True`; required-false 20개 + 부가 gate 전부 `False`; `block_reasons` 비어있지 않음; `next_step` == capture 문자열 verbatim; `phase == "J1.2"`; **봉인된 실제 J1.2 artifact가 자기 validator를 통과**(self-trip 회귀 방지 — 필수).

Negative (`pytest.raises(ValueError, match=...)`): gate flip(canonical 8 각각), 임의 engram-intervention gate `true`, empty `block_reasons`, forbidden-field 깊이별 주입, sha tamper, upstream binding mismatch, phase drift(`"J1.1B"` 주입), `lora_delta_estimator_gate: true`.

### STEP 4 — 스크립트 `scripts/research/j1_2_engram_trace_contract.py`

- `PROJECT_ROOT = Path(__file__).resolve().parents[2]` + `sys.path.insert`
- positional `action`, choices `create | audit-existing`
- `_write_json_new`: 파일 존재 시 `FileExistsError("refusing to overwrite existing artifact")`
- `create`: upstream JSON 로드 → `build_engram_trace_contract(...)` → 봉인본을 `scripts/research/inputs/`에, report(`indent=2, sort_keys=True`)를 `claudedocs/research/`에
- `audit-existing`: 라이브 봉인 chain에 대해 full 재검증
- `main()`은 `sys.stdout.reconfigure(encoding="utf-8")`

### STEP 5 — 검증 명령

```
pytest tests/test_engram_trace_contract.py -q
pytest -q                                             # 전체 스위트 green
python scripts/research/j1_2_engram_trace_contract.py create
python scripts/research/j1_2_engram_trace_contract.py audit-existing
```

전체 스위트 통과 수를 report에 기록할 것 — AGENTS.md의 146 vs 136 불일치가 미해결이므로 이번 실측값으로 확정한다.

---

## 6. 봉인 스키마

### identity
```
engram_trace_contract_version: 1
phase: "J1.2"
status: "engram_trace_contract_defined_measurement_blocked_not_runtime"
engram_trace_contract_scope: "graph_local_core_engram_offline_audit_definition"
engram_criteria_policy: "specificity_reactivation_sufficiency_necessity_offline_audit_only"
own_gate_semantics: "definition_wellformed_and_sealed_no_engram_measured"
```

⚠️ status에 `..._ready_...`를 쓰지 말 것. **`_measurement_blocked_` 프레이밍이 의도적**이다 — own gate `true`가 "측정 완료"로 오독되는 것을 막는다.

### 정직성 신규 필드 (전부 필수)
- `engram_object_locus` — **verbatim**:
  > "Only the local-core layer holds the paper's weight-space engram object (W+); the graph, probability, and provenance layers contain NO paper-engram object — they are cognitive-neuroscience analogs (Josselyn/Tonegawa framing) and are NOT the estimator's W+."
- `estimator_verification_status: "closed_form_estimator_W+=W·Sigma+(Sigma+ + Sigma-)†_and_case2_collapse_0.818_to_0.446_are_self_reported_unverified_preprint"`
- `reviewed_labels_are_train_split_not_engram_ground_truth: true`

### gate

own gate (정확히 하나만 true): `engram_trace_contract_gate: true`

canonical required-false 8:
```
fresh_snapshot_runtime_gate, question_selection_runtime_gate, runtime_probability_snapshot_gate,
database_writes, learning_enabled, heldout_gate, performance_claim_gate, production_promotion_gate
```

engram-extension required-false 12:
```
weight_editing_gate, unlearning_gate, knowledge_editing_gate, engram_injection_gate,
engram_ablation_gate, local_core_intervention_gate, lora_delta_estimator_gate,
graph_lesion_write_gate, activation_write_gate, covariance_capture_gate,
engram_measurement_executed_gate, statistical_power_gate
```

부가: `local_core_engram_interpretation_gate: false`

⚠️ `activation_write_gate`의 의미는 **"audit 맥락에서 :Activation 노드의 어떤 CREATE 또는 DELETE도 금지 (ephemeral 포함)"**로 봉인한다. ephemeral CREATE + `cleanup_old_activations` DELETE 쌍도 write이므로 loophole을 막는다.

### block_reasons (14개, 비어있지 않음)
```
fresh_never_labeled_capture_not_yet_produced
behavioral_sufficiency_necessity_core_not_wired_to_wake_conversation_handler_v30_protected
causal_sufficiency_necessity_require_weight_editing_forbidden
local_core_numbers_leakage_contaminated_pending_pair_disjoint_3seed_rerun_and_sealed_canary
lora_delta_estimator_is_paper_case2_collapse_only_merged_full_weight_localization_read_only_permitted
durable_reactivation_log_absent_activation_nodes_deleted_30s
per_example_gradient_and_perstep_loss_not_stored
probability_layer_is_outcome_instrument_not_engram_locus
provenance_layer_is_audit_substrate_not_engram_measurement
graph_measurements_require_degree_normalization_and_multipath_controls_before_valid
sample_6_questions_79_rows_23_positives_auc_0.675_below_inference_threshold_descriptive_only
reviewed_79plus16_labels_are_calibrator_train_split_reuse_is_in_sample_and_post_hoc_future_info
graph_necessity_edge_masking_near_tautological_degree_dominated_requires_permutation_null
local_core_growth_runs_show_rising_training_loss_mrr_gain_not_clean_lm_learning
```

🔴 **초안에 있던 `sealed_capture_adapter_dd60ed3c_not_reproducible_on_disk_current_6901e239`는 삭제됐다. 사실이 아니다** (§11).

### local_core_identity
```
base_model_id: "Qwen/Qwen2.5-0.5B-Instruct"
base_model_revision: "7ae557604adf67be50417f59c2c2f167def9a775"
adapter_sha256: "dd60ed3cd31b82098522ea7b2efff104efe86cb0aeb10b98cb591259fe3cdb8b"
adapter_sha256_scope: "directory_digest_over_models_local_core_adapter_not_single_file_hash"
adapter_digest_algorithm: "sorted_rglob_files_then_len_prefixed_relpath_plus_size_plus_content_see_j1_1_capture_raw_scores._sha256_directory"
trainable_parameter_count: 0
reproducible_on_disk: true
adapter_recomputed_matches_sealed_at_build_time: true
```

🔴 **`adapter_sha256_scope`와 `adapter_digest_algorithm` 필드는 필수다.** 이 두 필드가 없어서 rev1에서 파일 해시와 디렉토리 다이제스트를 혼동하는 오류가 발생했다. 봉인해서 재발을 막는다.

⚠️ 어댑터 재계산은 **`audit-existing` 시점의 advisory report 필드**로만 기록하고, **validator의 hard assertion으로 넣지 말 것.** 이유: 계약은 미래에 distill이 어댑터를 바꾼 뒤에도 *역사적 기록*으로서 유효해야 한다. hard assertion이면 정상적인 후속 학습이 과거 계약을 깨뜨린다.

### criteria_mappings (16 cell = 4 criteria × 4 layer)

각 cell 필드:
```
criterion, layer, mapping_kind, computation,
execution_status: "asserted_not_executed",     # 필수
inferential_claim_supported: false,            # 전 cell 필수
n_available, min_n_for_inference,
read_only, misread_risk, blocked_reason | null
```

`mapping_kind` enum:
```
genuine_after_leakage_safe_rerun | descriptive_only_underpowered |
pattern_completion_analog_not_gain_of_function | forbidden_intervention |
not_definable_now | audit_substrate_only | outcome_instrument_only |
RO-now_in_sample_label_reuse
```

graph-necessity cell 추가 필드: `permutation_null_baseline_required: true`, `degree_normalization_required: true`, `multipath_counting_required: true`.

🔴 **graph reactivation cell의 "실제 재활성 집합"은 반드시 read-only로 유도한다** — 이미 persist된 `Experience.curiosity_actual_concept_ids` / `predicted_concept_ids` / `curiosity_cue_ids`를 MATCH로 읽거나, `MATCH (e:Experience)-[:INVOLVES]->(c:Concept)` 후 in-memory 계산. `record_curiosity_outcome`을 `read_only: true` cell의 computation에 절대 쓰지 말 것 — 이 함수는 Concept/BrainRegion/Experience에 SET하고 CuriosityLog/TRIGGERED_BY를 MERGE한다(= DB write). 인용 가능한 라이브 graph 함수는 `prepare_curiosity_prediction`, `get_spreading_activation` 둘뿐.

### discipline
```
offline_audit_registers_no_api_server_routes_or_hooks_calls_no_http_endpoints_opens_neo4j_read_only_match_return_only: true
preserves_declared_next_step: "capture_real_fresh_pre_question_shadow_inputs_read_only_before_runtime_selection"
next_step: "capture_real_fresh_pre_question_shadow_inputs_read_only_before_runtime_selection"
engram_track_next_step: "define_read_only_graph_engram_measurement_harness_offline_before_runtime"
does_not_modify_sealed_artifacts: true
```

### forbidden_operations
```
apply_engram, edit_llm, EngramEditor.apply,
W_new=W-alpha*W_engram, W+W_engram_injection, lora_delta_substitution_into_estimator,
merged_weight_save_to_disk, models_local_core_adapter_overwrite,
record_curiosity_outcome_invocation, cleanup_old_activations_invocation,
decay_connections_live_write, durable_or_ephemeral_Activation_node_write,
ANSWER_EVIDENCES_CONCEPT_db_write, conversation_handler_v30_edit,
api_server_route_or_hook_registration, any_weight_or_knowledge_editing_or_unlearning
```

### self-seal
`engram_trace_contract_sha256`

---

## 7. 하지 말 것 (DO-NOT)

- capture next_step을 재정렬·대체하지 말 것. **verbatim 재선언**만.
- **어떤 engram 수치도 계산·저장하지 말 것**. 모든 cell은 `execution_status: "asserted_not_executed"`.
- `record_curiosity_outcome` / `cleanup_old_activations` / `decay_connections` 호출 금지.
- LoRA delta를 Engram 추정기에 대입 금지.
- 어댑터 재계산을 **validator hard assertion으로 넣지 말 것** (advisory report 필드로만).
- 어댑터 무결성을 **단일 파일 해시로 검증하지 말 것** — 봉인값은 디렉토리 다이제스트다 (§11).
- api_server route/hook 등록, HTTP endpoint 호출, Neo4j write 세션 금지.
- **Track A(graph 실측)를 J1.2 정의에 번들 금지.** 별도 artifact `j1_2a`로 분리, degree-normalization + multi-path counting + permutation(edge-shuffle) null baseline을 hard precondition으로.
- 병합 가중치(W_pt + BA)를 디스크에 저장하거나 `models/local_core_adapter/`를 덮어쓰지 말 것.
- git commit / push 금지.

---

## 8. 완료 기준

1. `scripts/research/inputs/j1_2_engram_trace_contract_20260719.json` 생성, `status == "engram_trace_contract_defined_measurement_blocked_not_runtime"`.
2. `engram_trace_contract_gate: true`, 나머지 20개 gate + `local_core_engram_interpretation_gate` 전부 `false`.
3. `block_reasons` 14개, 비어있지 않음.
4. `next_step` == capture 문자열 verbatim.
5. `claudedocs/research/j1_2_engram_trace_contract_20260719.json` report 생성. report에 다음 3문장이 **사람이 읽는 평문으로** 포함될 것:
   - "engram measurement was not executed."
   - "graph / probability / provenance layers are not the paper's weight-space engrams."
   - "the sealed local-core adapter digest `dd60ed3c…` is a **directory** digest and recomputes exactly as of this build; it is not a single-file hash."
6. `audit-existing`이 라이브 봉인 chain(enforced **12**개 hash 삼중대조)에 대해 통과.
7. `pytest` 전체 스위트 green + self-trip 회귀 테스트 통과. **실측 통과 수를 report에 기록.**
8. `conversation_handler.py` blob 무변경. 기존 sealed artifact 무변경. DB write 0건.

**capture는 여전히 트렁크의 다음 실행 액션으로 남는다.**

---

## 9. 미해결 쟁점 (사용자 결정 필요 — Codex는 임의 결정 금지)

1. **어댑터 체크포인트 보존 정책 (예방 조치, 권장)**: 어댑터는 현재 무결하지만, `LOCAL_CORE_DISTILL` 누적 학습은 `models/local_core_adapter/`를 **제자리에서 덮어쓴다**. `.gitignore:13`이 이 경로를 제외하므로 git 복구 경로도 없다. 다음 distill 실행이 봉인 binding을 파괴하면 복구 불가다. → `models/checkpoints/<digest>/` immutable 저장 또는 봉인 전 tar 스냅샷을 **capture 실행 전에** 도입할 것을 권장. 단 이는 distill 저장 경로를 건드리는 **코드 변경**이므로 J1.2 범위 밖이며 별도 승인 필요.
2. **Track A(`j1_2a`) 승격 여부**: advisory 필드로 둘지, 추적되는 필수 후속으로 승격할지. "정의만 되고 호출 안 됨" 안티패턴(이 프로젝트 5회 반복) 재발 방지 장치.
3. **graph necessity permutation null 사양**: edge-shuffle 반복 수, 통계 임계 미정. `j1_2a` 설계 시 확정.
4. **statistical_power_gate 해제 최소 n**: 미정의. 현재 표본(6질문 / 79행 / 23양성 / AUC 0.675)은 descriptive only.
5. **untracked 16개 파일 처리**: fresh shadow 체인 전체가 미커밋. 커밋은 사용자 명시 시에만 하되, 작업 범위가 커진 상태임을 인지.

> rev1의 미해결 쟁점 #1(`518e5e6a` 강제 여부)과 #2(`dd60ed3c` 복원)는 **둘 다 실측으로 해소**됐다. 전자는 enforced로 승격, 후자는 애초에 손실이 아니었다.

---

## 10. 유지되는 관측 사실

- `local_core_growth.jsonl`: run 1 (`resumed: false`) loss_first 3.891 → loss_last 5.775; run 2 (`resumed: true`) 2.187 → 5.421. **두 run 모두 training loss가 상승하는데 MRR만 올랐다.** MRR 상승을 clean LM 학습으로 귀속할 수 없다는 red flag는 그대로 유효하며, pair-overlap leakage(18/250)와 함께 local-core 해석 금지의 근거다.
- `feature_names` 9개 중 5개(`local_core_raw_score`, `local_core_rank`, `local_core_rank_percentile`, `in_local_core_top_k`, `in_both_top_k`)가 local-core 의존이다. **만약** 장래에 다른 어댑터로 capture하게 된다면, 봉인된 calibrator(`fd3965f0`, `l2_logistic_regression_binary_relevance_v1`)는 그 점수 분포에 적용 불가가 되며 재적합(= 새 라벨 = 새 리뷰 사이클)이 필요하다. 현재는 어댑터가 무결하므로 **해당 없음**.

---

## 11. 정정 이력 (rev1 → rev2, 2026-07-19)

**rev1의 오류: "봉인된 어댑터 `dd60ed3c`가 소실됐다"는 주장은 거짓이었다.**

- 오류 경로: `Get-FileHash models/local_core_adapter/adapter_model.safetensors` = `6901e239…`를 봉인된 `adapter_sha256` = `dd60ed3c…`와 비교해 불일치로 판정했다. 그러나 봉인값은 `j1_1_capture_raw_scores.py`의 **`_sha256_directory()`**가 산출한 **디렉토리 다이제스트**다 — `adapter_config.json`, `adapter_model.safetensors`, `README.md` 3개 파일을 정렬해 각각 (길이-접두 상대경로 + 파일크기 + 내용)으로 누적 해시한다. **파일 해시와 디렉토리 다이제스트는 서로 다른 객체이며, 비교 자체가 성립하지 않았다.**
- 실측 반증: 동일 알고리즘을 재현하니 `dd60ed3c…`가 **정확히 일치**. 또한 `adapter_model.safetensors`의 mtime은 `2026-07-13 16:14:10`으로, 봉인 capture 시각(`2026-07-17T11:16:08Z`) **이후 수정된 적이 없다**.
- "야간 distill이 덮어썼다"는 설명은 그럴듯했기 때문에(누적 학습이 실제로 in-place 덮어쓰기를 하고, growth log에 `resumed: true`가 있음) 검증 없이 통과했다. **알려진 실패 양상과 패턴이 일치한다는 것이 원인이 같다는 뜻은 아니다.**
- 교훈: 봉인된 해시를 검증할 때는 **비슷해 보이는 계산이 아니라 원래의 계산을 재현**해야 한다. 그래서 rev2는 `adapter_sha256_scope`와 `adapter_digest_algorithm`을 계약에 봉인해 같은 혼동이 재발하지 않게 한다.

**이 오류로 인해 rev1에서 잘못 파생된 것들 (전부 rev2에서 철회)**:
- block_reason `sealed_capture_adapter_dd60ed3c_not_reproducible_on_disk_current_6901e239` → **삭제**
- `local_core_identity.reproducible_on_disk: false` → **true**
- `current_disk_adapter_sha256` 필드 → **삭제** (파일 해시라 비교 불가, 재혼동 유발)
- "디스크 어댑터 해시 대조 validator 절대 넣지 말 것 — 항상 실패한다" → **반전**. 디렉토리 다이제스트 대조는 통과하며, advisory report 필드로 유용하다.
- "capture 트렁크의 로컬코어 재현이 물리적으로 불가능" → **철회**. 원래 sealed identity 그대로 실행 가능하며 lineage 분기가 불필요하다.
- Local-Core Engram Pilot의 "checkpoint 소실" 차단 사유 → **철회**. 다만 LoRA Case-2, leakage, 개입 금지, 추정기 미검증이라는 나머지 차단 사유는 그대로이므로 **우선순위 C(보류)는 유지**된다.

**rev1에서 그대로 유효한 것**: J1.2 정의 전용 사이드카 결정, next_step verbatim 보존, `_measurement_blocked_` status 프레이밍, `engram_object_locus`, 4-criteria 매핑 강등 표기, `record_curiosity_outcome`은 read-only 아님, rising-loss red flag, 우선순위 A > B > C > D.

---

## 12. 구현 결과 (2026-07-20)

### 생성된 파일 (5개, 전부 신규 · 기존 파일 수정 0건)
| 역할 | 경로 |
|---|---|
| 봉인 계약 | `scripts/research/inputs/j1_2_engram_trace_contract_20260719.json` |
| 요약 report | `claudedocs/research/j1_2_engram_trace_contract_20260719.json` |
| 라이브러리 | `neural/baby/engram_trace_contract.py` |
| 스크립트 | `scripts/research/j1_2_engram_trace_contract.py` |
| 테스트 | `tests/test_engram_trace_contract.py` |

### 완료 기준 대조
| 기준 | 결과 |
|---|---|
| status | `engram_trace_contract_defined_measurement_blocked_not_runtime` ✅ |
| gate | `engram_trace_contract_gate: true` 단 하나, required-false **21개 전부 false** ✅ |
| block_reasons | 14개, 비어있지 않음 ✅ |
| next_step verbatim | chain tip과 byte 단위 동일 ✅ |
| hash 삼중대조 | **12개 enforced, unenforced 0개** ✅ (tip은 상류가 없어 recompute+self-consistency만) |
| upstream validator 재실행 | 10개 ✅ |
| criteria_mappings | 16 cell, 전부 `asserted_not_executed` · `inferential_claim_supported: false` ✅ |
| `audit-existing` | 라이브 봉인 체인 대조 통과 ✅ |
| 테스트 | J1.2 **61 passed** / 전체 `pytest tests/` **242 passed** ✅ |
| handler blob | `054d974095be7425692860909181fafd54f97a33` 무변경 ✅ |
| 기존 sealed artifact | 수정 0건 (추적 파일 변경 0건) ✅ |
| DB write / 모델 로드 / 네트워크 | 0건 ✅ |

### rev2 대비 상향 수정 2건 (독립 적대적 검증에서 발견)

**(1) `sample_scale`을 하드코딩에서 upstream 유도로 변경.**
rev2 설계는 `question_count: 6`, `train_only_auc_roc: 0.675` 등을 상수로 박았다. 그러면 upstream 재적합 시 stale 성능 수치가 `performance_claim_gate: false` 아래에서 그대로 통과한다. 이제 7개 수치를 전부 봉인 upstream에서 읽고(`SAMPLE_SCALE_SOURCES`), 각 수치가 온 필드 경로를 `sample_scale_source_fields`에 함께 봉인하며, `validate_engram_trace_contract`가 upstream과 대조한다. 합계 정합성(양성+음성=이진행, 이진행+불확실=리뷰총계)도 검사한다. AUC는 반올림 없이 upstream 원값 `0.6746894409937888`을 쓴다.

**(2) 어댑터 다이제스트를 "주장"에서 "실측"으로 변경.**
rev2 설계는 `reproducible_on_disk: true`를 봉인하고 report에 "recomputes exactly as of this build"라고 쓰게 했으나, **실제로 재계산하는 코드가 없었다** — 이번 세션의 원래 오류(파일해시↔디렉토리다이제스트 혼동)와 정확히 같은 종류의 결함이다. 이제:
- 봉인 계약은 `reproducible_on_disk`를 **담지 않는다**. 담으면 validator가 거부한다 (디스크 상태는 봉인된 정의의 속성이 아니다).
- 스크립트가 `_sha256_directory` 알고리즘을 그대로 재현해 **실제로 재계산**하고, 결과를 report의 `local_core_adapter_digest_recheck`에 advisory로 기록한다. 2026-07-20 실행 결과 `matches_sealed: true`, 재계산값 `dd60ed3c…`.
- report의 평문 문장은 실측 결과에 따라 3가지(일치 / 불일치 / 재계산 불가)로 분기한다. 미래 distill이 어댑터를 바꾸면 문장이 자동으로 바뀔 뿐, 계약은 역사적 기록으로서 계속 유효하다.
- 회귀 테스트가 "단일 파일 해시 ≠ 디렉토리 다이제스트"를 명시적으로 assert한다.

### 알려진 사실 (수정 아님, 기록용)
- 맨 `pytest`(인자 없음)는 `.venv`/`node_modules`까지 수집하려다 capture 오류로 죽는다. **기존 문제이며 J1.2와 무관**하다(J1.2 파일을 `--ignore`해도 동일). canonical 실행은 `pytest tests/`다. AGENTS.md의 146 vs 136 불일치는 이 invocation 차이에서 비롯됐을 가능성이 크다. 현재 기준선 181 + J1.2 61 = **242**.
- `neural` 패키지 import는 `neural/__init__.py` → `agents.coder.agent` → `anthropic` + `load_dotenv()`를 끌어온다. 클라이언트 인스턴스화·소켓·파일쓰기는 없으며 **모든 J1.1 모듈이 공유하는 패키지 수준 성질**이지 J1.2 회귀가 아니다.
- J1.2는 미커밋 J1.1 fresh-shadow 모듈 4개에 의존하므로 **독립적으로 커밋·리뷰할 수 없다**. 커밋 범위 결정 시 함께 다뤄야 한다.
