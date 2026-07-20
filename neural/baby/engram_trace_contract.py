"""Definition-only J1.2 engram trace contract.

This module seals an offline audit taxonomy that maps the four engram criteria
(specificity, reactivation, sufficiency, necessity) onto four Baby layers:
graph memory, local-core predictor, question-selection probability, and source
provenance.

It measures nothing.  It computes no engram quantity, opens no database, loads
no model, registers no endpoint, and edits no weights.  Every runtime, learning,
database, intervention, and promotion gate is sealed false, and ``block_reasons``
is required to stay non-empty so that the single true gate on this artifact can
never be read as "engram measurement completed".

The criteria names predate the AI Engram preprint and are attributed to the
Josselyn/Tonegawa engram literature.  Only the local-core layer could ever hold
the preprint's weight-space object; the other three layers are analogs.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from neural.baby.calibrator_design import (
    CALIBRATOR_DESIGN_FEATURE_NAMES,
    validate_calibrator_design_audit,
)
from neural.baby.calibrator_fit import validate_train_only_calibrator_fit
from neural.baby.calibrator_snapshot import validate_calibrator_probability_snapshot
from neural.baby.candidate_universe import (
    validate_candidate_vocabulary,
    validate_independent_score_capture,
)
from neural.baby.fresh_shadow_probability import (
    validate_fresh_pre_question_shadow_probability_snapshot,
)
from neural.baby.fresh_shadow_selection import validate_fresh_shadow_question_selection
from neural.baby.fresh_snapshot_contract import (
    FORBIDDEN_FRESH_INPUT_FIELDS,
    validate_fresh_pre_question_snapshot_input_contract,
    validate_fresh_pre_question_snapshot_input_pack,
)
from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.question_selection_contract import (
    SELECTION_POLICY,
    validate_question_selection_contract,
)


ENGRAM_TRACE_CONTRACT_VERSION = 1
ENGRAM_TRACE_CONTRACT_PHASE = "J1.2"
ENGRAM_TRACE_CONTRACT_STATUS = (
    "engram_trace_contract_defined_measurement_blocked_not_runtime"
)
ENGRAM_TRACE_CONTRACT_SCOPE = "graph_local_core_engram_offline_audit_definition"
ENGRAM_CRITERIA_POLICY = (
    "specificity_reactivation_sufficiency_necessity_offline_audit_only"
)
ENGRAM_OWN_GATE_SEMANTICS = (
    "definition_wellformed_and_sealed_no_engram_measured"
)

# The declared next step of the sealed chain tip.  J1.2 is a parallel sidecar and
# re-declares this string verbatim; it never consumes or reorders the trunk.
PRESERVED_NEXT_STEP = (
    "capture_real_fresh_pre_question_shadow_inputs_read_only_"
    "before_runtime_selection"
)
ENGRAM_TRACK_NEXT_STEP = (
    "define_read_only_graph_engram_measurement_harness_offline_before_runtime"
)

ENGRAM_OBJECT_LOCUS = (
    "Only the local-core layer holds the paper's weight-space engram object "
    "(W+); the graph, probability, and provenance layers contain NO paper-engram "
    "object - they are cognitive-neuroscience analogs (Josselyn/Tonegawa "
    "framing) and are NOT the estimator's W+."
)
ESTIMATOR_VERIFICATION_STATUS = (
    "closed_form_estimator_W+=W.Sigma+(Sigma+ + Sigma-)dagger_and_case2_collapse_"
    "0.818_to_0.446_are_self_reported_unverified_preprint"
)
ENGRAM_CRITERIA_ATTRIBUTION = (
    "specificity_reactivation_sufficiency_necessity_are_josselyn_tonegawa_engram_"
    "criteria_predating_arxiv_2606.14997_not_originated_by_it"
)

CANONICAL_REQUIRED_FALSE_GATES = (
    "fresh_snapshot_runtime_gate",
    "question_selection_runtime_gate",
    "runtime_probability_snapshot_gate",
    "database_writes",
    "learning_enabled",
    "heldout_gate",
    "performance_claim_gate",
    "production_promotion_gate",
)
ENGRAM_REQUIRED_FALSE_GATES = (
    "weight_editing_gate",
    "unlearning_gate",
    "knowledge_editing_gate",
    "engram_injection_gate",
    "engram_ablation_gate",
    "local_core_intervention_gate",
    "lora_delta_estimator_gate",
    "graph_lesion_write_gate",
    "activation_write_gate",
    "covariance_capture_gate",
    "engram_measurement_executed_gate",
    "statistical_power_gate",
)
ENGRAM_INTERPRETATION_GATE = "local_core_engram_interpretation_gate"
ALL_REQUIRED_FALSE_GATES = (
    CANONICAL_REQUIRED_FALSE_GATES
    + ENGRAM_REQUIRED_FALSE_GATES
    + (ENGRAM_INTERPRETATION_GATE,)
)
ENGRAM_OWN_GATE = "engram_trace_contract_gate"

ACTIVATION_WRITE_GATE_SEMANTICS = (
    "forbids_any_CREATE_or_DELETE_of_Activation_nodes_in_audit_context_"
    "ephemeral_included"
)

ENGRAM_BLOCK_REASONS = (
    "fresh_never_labeled_capture_not_yet_produced",
    "behavioral_sufficiency_necessity_core_not_wired_to_wake_conversation_handler_"
    "v30_protected",
    "causal_sufficiency_necessity_require_weight_editing_forbidden",
    "local_core_numbers_leakage_contaminated_pending_pair_disjoint_3seed_rerun_and_"
    "sealed_canary",
    "lora_delta_estimator_is_paper_case2_collapse_only_merged_full_weight_"
    "localization_read_only_permitted",
    "durable_reactivation_log_absent_activation_nodes_deleted_30s",
    "per_example_gradient_and_perstep_loss_not_stored",
    "probability_layer_is_outcome_instrument_not_engram_locus",
    "provenance_layer_is_audit_substrate_not_engram_measurement",
    "graph_measurements_require_degree_normalization_and_multipath_controls_before_"
    "valid",
    "sample_6_questions_79_rows_23_positives_auc_0.675_below_inference_threshold_"
    "descriptive_only",
    "reviewed_79plus16_labels_are_calibrator_train_split_reuse_is_in_sample_and_"
    "post_hoc_future_info",
    "graph_necessity_edge_masking_near_tautological_degree_dominated_requires_"
    "permutation_null",
    "local_core_growth_runs_show_rising_training_loss_mrr_gain_not_clean_lm_learning",
)

ENGRAM_FORBIDDEN_OPERATIONS = (
    "apply_engram",
    "edit_llm",
    "EngramEditor.apply",
    "W_new=W-alpha*W_engram",
    "W+W_engram_injection",
    "lora_delta_substitution_into_estimator",
    "merged_weight_save_to_disk",
    "models_local_core_adapter_overwrite",
    "record_curiosity_outcome_invocation",
    "cleanup_old_activations_invocation",
    "decay_connections_live_write",
    "durable_or_ephemeral_Activation_node_write",
    "ANSWER_EVIDENCES_CONCEPT_db_write",
    "conversation_handler_v30_edit",
    "api_server_route_or_hook_registration",
    "any_weight_or_knowledge_editing_or_unlearning",
)

READ_ONLY_CITABLE_GRAPH_FUNCTIONS = (
    "prepare_curiosity_prediction",
    "get_spreading_activation",
)

LOCAL_CORE_IDENTITY = {
    "base_model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "base_model_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
    "adapter_sha256": (
        "dd60ed3cd31b82098522ea7b2efff104efe86cb0aeb10b98cb591259fe3cdb8b"
    ),
    "adapter_sha256_scope": (
        "directory_digest_over_models_local_core_adapter_not_single_file_hash"
    ),
    "adapter_digest_algorithm": (
        "sorted_rglob_files_then_len_prefixed_relpath_plus_size_plus_content_see_"
        "j1_1_capture_raw_scores._sha256_directory"
    ),
    "trainable_parameter_count": 0,
    "single_file_hash_is_not_comparable_to_this_digest": True,
    # Whether the digest still recomputes from disk is an observation about the
    # filesystem at run time, not a property of this sealed definition.  The
    # script reports it; this artifact deliberately does not assert it.
    "on_disk_recheck_is_reported_not_sealed": True,
}

LOCAL_CORE_GROWTH_LOG_PATH = "claudedocs/monitoring/local_core_growth.jsonl"

# No minimum-n threshold is asserted: the power analysis that would define one
# has not been done, and inventing a threshold here would manufacture a metric.
MIN_N_FOR_INFERENCE_STATUS = "undefined_pending_power_analysis"

# Every sample-scale number is read from a sealed upstream artifact rather than
# hardcoded, so it cannot drift into a stale performance claim.
SAMPLE_SCALE_SOURCES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "question_count",
        "fresh_pre_question_shadow_probability_snapshot",
        ("question_count",),
    ),
    (
        "binary_label_row_count",
        "train_only_calibrator_fit",
        ("cross_validation_metrics", "row_count"),
    ),
    (
        "positive_label_count",
        "train_only_calibrator_fit",
        ("cross_validation_metrics", "positive_count"),
    ),
    (
        "negative_label_count",
        "train_only_calibrator_fit",
        ("cross_validation_metrics", "negative_count"),
    ),
    (
        "uncertain_label_count",
        "train_only_calibrator_fit",
        ("excluded_uncertain_count",),
    ),
    ("reviewed_label_total", "union_label_pack", ("label_count",)),
    (
        "train_only_auc_roc",
        "train_only_calibrator_fit",
        ("cross_validation_metrics", "auc_roc"),
    ),
)


def _dig(artifact: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = artifact
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            raise ValueError(f"missing upstream sample-scale field: {'.'.join(path)}")
        value = value[key]
    return value


def derive_sample_scale(
    upstream: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Read every sample-scale number straight out of sealed upstream artifacts."""

    _require_upstream(upstream)
    scale: dict[str, Any] = {
        field: _dig(upstream[key], path)
        for field, key, path in SAMPLE_SCALE_SOURCES
    }
    scale["min_n_for_inference_status"] = MIN_N_FOR_INFERENCE_STATUS
    scale["sample_scale_source_fields"] = {
        field: f"{key}.{'.'.join(path)}" for field, key, path in SAMPLE_SCALE_SOURCES
    }
    if scale["positive_label_count"] + scale["negative_label_count"] != (
        scale["binary_label_row_count"]
    ):
        raise ValueError("sample scale positive/negative counts do not sum to rows")
    if scale["binary_label_row_count"] + scale["uncertain_label_count"] != (
        scale["reviewed_label_total"]
    ):
        raise ValueError("sample scale binary/uncertain counts do not sum to reviewed")
    return scale

MAPPING_KINDS = frozenset({
    "genuine_after_leakage_safe_rerun",
    "descriptive_only_underpowered",
    "pattern_completion_analog_not_gain_of_function",
    "forbidden_intervention",
    "not_definable_now",
    "audit_substrate_only",
    "outcome_instrument_only",
    "RO-now_in_sample_label_reuse",
})
ENGRAM_CRITERIA = ("specificity", "reactivation", "sufficiency", "necessity")
ENGRAM_LAYERS = (
    "graph_memory",
    "local_core_predictor",
    "question_selection_probability",
    "source_provenance",
)
EXECUTION_STATUS_NOT_EXECUTED = "asserted_not_executed"


def _cell(
    criterion: str,
    layer: str,
    mapping_kind: str,
    computation: str,
    misread_risk: str,
    *,
    read_only: bool,
    n_available: Any,
    blocked_reason: str | None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    cell = {
        "criterion": criterion,
        "layer": layer,
        "mapping_kind": mapping_kind,
        "computation": computation,
        "execution_status": EXECUTION_STATUS_NOT_EXECUTED,
        "inferential_claim_supported": False,
        "n_available": n_available,
        "min_n_for_inference": None,
        "min_n_for_inference_status": MIN_N_FOR_INFERENCE_STATUS,
        "read_only": read_only,
        "misread_risk": misread_risk,
        "blocked_reason": blocked_reason,
    }
    if extra:
        cell.update(dict(extra))
    return cell


GRAPH_CONTROL_REQUIREMENTS = {
    "degree_normalization_required": True,
    "multipath_counting_required": True,
}
GRAPH_NECESSITY_CONTROLS = dict(
    GRAPH_CONTROL_REQUIREMENTS,
    permutation_null_baseline_required=True,
)


def _criteria_mappings(scale: Mapping[str, Any]) -> list[dict[str, Any]]:
    question_count = scale["question_count"]
    binary_label_row_count = scale["binary_label_row_count"]
    return [
        # ---------------- specificity ----------------
        _cell(
            "specificity",
            "graph_memory",
            "descriptive_only_underpowered",
            "degree-normalized reference-leakage fraction: share of spreading "
            "activation mass from a target cue that reaches reference-cue "
            "concepts, read-only via get_spreading_activation (MATCH-only)",
            "sparsity mistaken for specificity; hub concepts light up for any "
            "cue, so an undnormalized score reflects degree, not a trace",
            read_only=True,
            n_available=None,
            blocked_reason=(
                "graph_measurements_require_degree_normalization_and_multipath_"
                "controls_before_valid"
            ),
            extra=GRAPH_CONTROL_REQUIREMENTS,
        ),
        _cell(
            "specificity",
            "local_core_predictor",
            "genuine_after_leakage_safe_rerun",
            "||W+||/||W|| localization plus residual response on reference "
            "inputs, computed only on merged full weights (W_pt+BA) held in a "
            "throwaway in-memory copy that is never persisted or served",
            "reads as validated localization although the estimator itself is "
            "an unverified preprint result and the current numbers are leakage "
            "contaminated",
            read_only=True,
            n_available=None,
            blocked_reason=(
                "local_core_numbers_leakage_contaminated_pending_pair_disjoint_"
                "3seed_rerun_and_sealed_canary"
            ),
            extra={
                "lora_delta_substitution_forbidden": True,
                "merged_full_weight_only": True,
                "estimator_conditional": True,
            },
        ),
        _cell(
            "specificity",
            "question_selection_probability",
            "outcome_instrument_only",
            "concentration of calibrated per-candidate probabilities per "
            "question (top mass, mean mass)",
            "concentration is calibrator discriminative power, not parameter-"
            "space specificity; it is a readout, not a trace",
            read_only=True,
            n_available=question_count,
            blocked_reason="probability_layer_is_outcome_instrument_not_engram_locus",
        ),
        _cell(
            "specificity",
            "source_provenance",
            "audit_substrate_only",
            "single-source attributability of each reviewed reference answer "
            "under the answer-source route contract",
            "attributability seals reproducibility only; it never measures how "
            "selectively a memory is stored",
            read_only=True,
            n_available=question_count,
            blocked_reason=(
                "provenance_layer_is_audit_substrate_not_engram_measurement"
            ),
        ),
        # ---------------- reactivation ----------------
        _cell(
            "reactivation",
            "graph_memory",
            "descriptive_only_underpowered",
            "overlap between the predicted concept set from "
            "prepare_curiosity_prediction (MATCH-only) and the actual "
            "reactivated set read read-only from already persisted "
            "Experience.curiosity_actual_concept_ids / predicted_concept_ids / "
            "curiosity_cue_ids, or re-derived in memory over "
            "MATCH (e:Experience)-[:INVOLVES]->(c:Concept)",
            "record_curiosity_outcome must never be called to obtain the actual "
            "set: it SETs Concept/BrainRegion/Experience and MERGEs "
            "CuriosityLog/TRIGGERED_BY, which is a database write",
            read_only=True,
            n_available=None,
            blocked_reason="durable_reactivation_log_absent_activation_nodes_deleted_30s",
            extra=dict(
                GRAPH_CONTROL_REQUIREMENTS,
                event_count_must_be_established_before_any_measurable_tag=True,
                read_only_citable_functions=list(READ_ONLY_CITABLE_GRAPH_FUNCTIONS),
            ),
        ),
        _cell(
            "reactivation",
            "local_core_predictor",
            "not_definable_now",
            "no definition available: hidden pre-activation states Z are not "
            "stored, forward hooks are not implemented, and re-running the "
            "scorer reproduces rankings rather than internal states",
            "re-running the predictor looks like reactivation but only replays "
            "an output ranking",
            read_only=True,
            n_available=None,
            blocked_reason="per_example_gradient_and_perstep_loss_not_stored",
        ),
        _cell(
            "reactivation",
            "question_selection_probability",
            "outcome_instrument_only",
            "per-candidate calibrated probability magnitude treated as "
            "reactivation strength",
            "an output probability is not an internal state; calling it "
            "reactivation strength imports a mechanism that was never measured",
            read_only=True,
            n_available=question_count,
            blocked_reason="probability_layer_is_outcome_instrument_not_engram_locus",
        ),
        _cell(
            "reactivation",
            "source_provenance",
            "audit_substrate_only",
            "reactivation ORDER only, from pre-registered NEXT_EXTERNAL_TURN and "
            "NEXT_FRAME sequence links",
            "ordering of small pre-registered sequences is not evidence that a "
            "trace was reactivated",
            read_only=True,
            n_available=None,
            blocked_reason=(
                "provenance_layer_is_audit_substrate_not_engram_measurement"
            ),
        ),
        # ---------------- sufficiency ----------------
        _cell(
            "sufficiency",
            "graph_memory",
            "pattern_completion_analog_not_gain_of_function",
            "recall-from-trace-only on a masked view (1 - prediction_error), "
            "which is pattern completion from a partial cue on a graph that "
            "already holds the memory",
            "the paper's sufficiency injects a trace into a null state so an "
            "ABSENT memory appears; a read-only graph cannot construct that "
            "null state, so this measures a different property entirely",
            read_only=True,
            n_available=None,
            blocked_reason=(
                "causal_sufficiency_necessity_require_weight_editing_forbidden"
            ),
            extra={"gain_of_function_not_constructible_read_only": True},
        ),
        _cell(
            "sufficiency",
            "local_core_predictor",
            "forbidden_intervention",
            "causal form requires injecting W+ into a null-state model, which is "
            "weight editing and is forbidden; the read-only substitute is an "
            "adapter-versus-base ranking comparison",
            "the adapter-versus-base MRR gain is contaminated twice: pair-overlap "
            "leakage, and both growth runs show training loss RISING while MRR "
            "rose, so the gain is not attributable to clean language-model "
            "learning",
            read_only=False,
            n_available=None,
            blocked_reason=(
                "local_core_growth_runs_show_rising_training_loss_mrr_gain_not_"
                "clean_lm_learning"
            ),
            extra={"rising_loss_evidence_path": LOCAL_CORE_GROWTH_LOG_PATH},
        ),
        _cell(
            "sufficiency",
            "question_selection_probability",
            "outcome_instrument_only",
            "calibrated probability of a candidate treated as evidence the "
            "trace suffices to recover it",
            "a calibrated readout cannot establish a gain-of-function claim",
            read_only=True,
            n_available=question_count,
            blocked_reason="probability_layer_is_outcome_instrument_not_engram_locus",
        ),
        _cell(
            "sufficiency",
            "source_provenance",
            "audit_substrate_only",
            "whether a sealed source record alone reproduces the reference "
            "answer",
            "reproducing a record is provenance replay, not memory sufficiency",
            read_only=True,
            n_available=question_count,
            blocked_reason=(
                "provenance_layer_is_audit_substrate_not_engram_measurement"
            ),
        ),
        # ---------------- necessity ----------------
        _cell(
            "necessity",
            "graph_memory",
            "descriptive_only_underpowered",
            "query-masking COUNTERFACTUAL only: recall(full) - recall(trace-"
            "masked) for the target, plus a reference-preservation check; no "
            "edge is ever deleted and decay_connections is never called",
            "masking a target's own edges makes the delta trivially positive, "
            "and a redundant target gives about zero, so the metric is degree "
            "and redundancy dominated; without an edge-shuffle permutation null "
            "no necessity delta can be shown to exceed chance",
            read_only=True,
            n_available=None,
            blocked_reason=(
                "graph_necessity_edge_masking_near_tautological_degree_dominated_"
                "requires_permutation_null"
            ),
            extra=GRAPH_NECESSITY_CONTROLS,
        ),
        _cell(
            "necessity",
            "local_core_predictor",
            "forbidden_intervention",
            "per-concept form requires subtracting alpha*W+ from live weights, "
            "which is weight editing and is forbidden; per-concept necessity is "
            "additionally unmeasured because per-example gradients are discarded "
            "and no lesion harness exists",
            "a coarse whole-adapter base-versus-adapter ablation is read-only but "
            "is concept-nonspecific and leakage contaminated, so it cannot stand "
            "in for per-concept necessity",
            read_only=False,
            n_available=None,
            blocked_reason=(
                "causal_sufficiency_necessity_require_weight_editing_forbidden"
            ),
        ),
        _cell(
            "necessity",
            "question_selection_probability",
            "RO-now_in_sample_label_reuse",
            "feature-family ablation: drop graph_* or local_core_* features and "
            "recompute the calibrated-probability delta",
            "the calibrator was fit on the same 79 reviewed rows it would be "
            "scored against, so this is in-sample; worse, those rows are post-hoc "
            "human approve/reject decisions, which injects information from after "
            "the pre-question snapshot the trace supposedly produced",
            read_only=True,
            n_available=binary_label_row_count,
            blocked_reason=(
                "reviewed_79plus16_labels_are_calibrator_train_split_reuse_is_in_"
                "sample_and_post_hoc_future_info"
            ),
            extra={"is_calibrator_feature_ablation_not_parameter_space_necessity": True},
        ),
        _cell(
            "necessity",
            "source_provenance",
            "audit_substrate_only",
            "leave-one-source-out over the answer-source routes",
            "definable in principle but not exercised: every reviewed answer "
            "currently routes to a single external-teacher source, so the "
            "leave-one-out contrast does not exist",
            read_only=True,
            n_available=None,
            blocked_reason=(
                "provenance_layer_is_audit_substrate_not_engram_measurement"
            ),
        ),
    ]


DISCIPLINE = {
    "offline_audit_registers_no_api_server_routes_or_hooks_calls_no_http_endpoints_"
    "opens_neo4j_read_only_match_return_only": True,
    "does_not_modify_sealed_artifacts": True,
    "preserves_declared_next_step": PRESERVED_NEXT_STEP,
    "measures_nothing_in_this_artifact": True,
    "activation_write_gate_semantics": ACTIVATION_WRITE_GATE_SEMANTICS,
    "read_only_citable_graph_functions": list(READ_ONLY_CITABLE_GRAPH_FUNCTIONS),
    "adapter_digest_recheck_is_advisory_report_field_not_validator_assertion": True,
}


# ---------------------------------------------------------------------------
# upstream binding specification
# ---------------------------------------------------------------------------

# key -> (declared hash field on this contract, self-hash field inside the source
#         artifact)
UPSTREAM_HASH_SPEC: tuple[tuple[str, str, str], ...] = (
    (
        "fresh_shadow_question_selection",
        "fresh_shadow_question_selection_sha256",
        "fresh_shadow_question_selection_sha256",
    ),
    (
        "fresh_pre_question_shadow_probability_snapshot",
        "fresh_pre_question_shadow_probability_snapshot_sha256",
        "fresh_pre_question_shadow_probability_snapshot_sha256",
    ),
    (
        "fresh_pre_question_input_pack",
        "fresh_pre_question_input_pack_sha256",
        "fresh_pre_question_input_pack_sha256",
    ),
    (
        "fresh_pre_question_snapshot_input_contract",
        "fresh_pre_question_snapshot_input_contract_sha256",
        "fresh_pre_question_snapshot_input_contract_sha256",
    ),
    (
        "train_only_calibrator_fit",
        "train_only_calibrator_fit_sha256",
        "train_only_calibrator_fit_sha256",
    ),
    (
        "calibrator_design_audit",
        "calibrator_design_audit_sha256",
        "calibrator_design_audit_sha256",
    ),
    (
        "calibrator_probability_snapshot",
        "calibrator_probability_snapshot_sha256",
        "calibrator_probability_snapshot_sha256",
    ),
    (
        "question_selection_contract",
        "question_selection_contract_sha256",
        "question_selection_contract_sha256",
    ),
    (
        "independent_score_capture",
        "independent_score_capture_sha256",
        "independent_score_capture_sha256",
    ),
    (
        "candidate_vocabulary",
        "candidate_vocabulary_sha256",
        "candidate_vocabulary_sha256",
    ),
    (
        "union_label_pack",
        "union_label_pack_sha256",
        "union_label_pack_sha256",
    ),
    (
        "answer_source_amendment",
        "answer_source_amendment_sha256",
        "amendment_sha256",
    ),
)

REQUIRED_UPSTREAM_KEYS = tuple(key for key, _, _ in UPSTREAM_HASH_SPEC)

# The chain tip has nothing above it, so no other sealed artifact stores its
# hash.  Every other binding must be corroborated by at least one upstream file.
CHAIN_TIP_KEY = "fresh_shadow_question_selection"
CHAIN_TIP_NO_DOWNSTREAM_REASON = (
    "chain_tip_no_upstream_artifact_references_it_by_construction"
)


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _feature_schema_sha256() -> str:
    return canonical_json_sha256({
        "feature_names": list(CALIBRATOR_DESIGN_FEATURE_NAMES),
    })


def _walk_forbidden_fields(value: Any, path: str = "$") -> None:
    """Key-based exact match against the 15 fresh-chain forbidden names.

    Deliberately key-based: this artifact legitimately *enumerates* intervention
    markers inside forbidden_operations, block_reasons, and criteria_mappings.
    Matching on values would make the contract fail its own validator.
    """

    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text in FORBIDDEN_FRESH_INPUT_FIELDS:
                raise ValueError(
                    f"engram trace contract forbidden field present: {path}.{key}"
                )
            _walk_forbidden_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden_fields(child, f"{path}[{index}]")


def _recompute_self_hash(artifact: Mapping[str, Any], self_hash_field: str) -> str:
    unhashed = _clone(artifact)
    unhashed.pop(self_hash_field, None)
    return canonical_json_sha256(unhashed)


def _require_upstream(upstream: Mapping[str, Mapping[str, Any]]) -> None:
    missing = [key for key in REQUIRED_UPSTREAM_KEYS if key not in upstream]
    if missing:
        raise ValueError(
            "engram trace contract requires upstream artifacts: "
            + ",".join(sorted(missing))
        )


def build_hash_bindings(
    upstream: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Recompute every upstream hash and discover where it is stored.

    Each binding records the recomputed value, the artifact and field it was
    recomputed from, and every other sealed artifact field that stores the same
    value.  Nothing is written and no measurement is performed.
    """

    _require_upstream(upstream)
    bindings: list[dict[str, Any]] = []
    for key, declared_field, self_hash_field in UPSTREAM_HASH_SPEC:
        artifact = upstream[key]
        declared_in_source = str(artifact.get(self_hash_field) or "")
        recomputed = _recompute_self_hash(artifact, self_hash_field)
        if declared_in_source != recomputed:
            raise ValueError(
                f"upstream artifact self-hash mismatch: {key}.{self_hash_field}"
            )
        stored_in = []
        for other_key in REQUIRED_UPSTREAM_KEYS:
            other = upstream[other_key]
            for field, value in other.items():
                if not isinstance(value, str) or value != recomputed:
                    continue
                if other_key == key and field == self_hash_field:
                    continue
                stored_in.append({"artifact": other_key, "field": field})
        stored_in.sort(key=lambda item: (item["artifact"], item["field"]))
        if not stored_in and key != CHAIN_TIP_KEY:
            raise ValueError(
                f"upstream hash has no corroborating storage location: {key}"
            )
        bindings.append({
            "hash_key": declared_field,
            "sha256": recomputed,
            "source_artifact": key,
            "source_self_hash_field": self_hash_field,
            "stored_in": stored_in,
            "stored_in_count": len(stored_in),
            "enforcement": (
                "recomputed_and_self_consistent_only"
                if key == CHAIN_TIP_KEY
                else "declared_equals_recomputed_equals_stored_in_upstream"
            ),
            "no_stored_in_reason": (
                CHAIN_TIP_NO_DOWNSTREAM_REASON if key == CHAIN_TIP_KEY else None
            ),
        })
    return bindings


def revalidate_upstream_artifacts(
    upstream: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """Re-run each existing upstream validator with its real dependencies."""

    _require_upstream(upstream)
    design = upstream["calibrator_design_audit"]
    fit = upstream["train_only_calibrator_fit"]
    contract = upstream["fresh_pre_question_snapshot_input_contract"]
    pack = upstream["fresh_pre_question_input_pack"]
    probability = upstream["fresh_pre_question_shadow_probability_snapshot"]
    selection_contract = upstream["question_selection_contract"]
    vocabulary = upstream["candidate_vocabulary"]

    validate_calibrator_design_audit(design)
    validate_train_only_calibrator_fit(fit, design)
    validate_calibrator_probability_snapshot(
        upstream["calibrator_probability_snapshot"], design, fit
    )
    validate_question_selection_contract(selection_contract)
    validate_candidate_vocabulary(vocabulary)
    validate_independent_score_capture(
        vocabulary, upstream["independent_score_capture"]
    )
    validate_fresh_pre_question_snapshot_input_contract(
        contract, selection_contract, design
    )
    validate_fresh_pre_question_snapshot_input_pack(pack, contract)
    validate_fresh_pre_question_shadow_probability_snapshot(
        probability, contract, pack, fit
    )
    validate_fresh_shadow_question_selection(
        upstream[CHAIN_TIP_KEY], probability
    )
    return [
        "validate_calibrator_design_audit",
        "validate_train_only_calibrator_fit",
        "validate_calibrator_probability_snapshot",
        "validate_question_selection_contract",
        "validate_candidate_vocabulary",
        "validate_independent_score_capture",
        "validate_fresh_pre_question_snapshot_input_contract",
        "validate_fresh_pre_question_snapshot_input_pack",
        "validate_fresh_pre_question_shadow_probability_snapshot",
        "validate_fresh_shadow_question_selection",
    ]


def _seal_engram_trace_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop("engram_trace_contract_sha256", None)
    normalized["engram_trace_contract_sha256"] = canonical_json_sha256(normalized)
    return normalized


def build_engram_trace_contract(
    upstream: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Seal the definition-only J1.2 engram trace contract.

    Performs no measurement: it recomputes upstream hashes, re-runs upstream
    validators, and seals a taxonomy plus a fail-closed gate set.
    """

    _require_upstream(upstream)
    revalidated = revalidate_upstream_artifacts(upstream)
    bindings = build_hash_bindings(upstream)
    by_key = {item["hash_key"]: item["sha256"] for item in bindings}
    scale = derive_sample_scale(upstream)

    contract = upstream["fresh_pre_question_snapshot_input_contract"]
    feature_schema_sha256 = _feature_schema_sha256()
    if contract.get("feature_schema_sha256") != feature_schema_sha256:
        raise ValueError("engram trace contract feature schema hash mismatch")

    tip = upstream[CHAIN_TIP_KEY]
    if tip.get("next_step") != PRESERVED_NEXT_STEP:
        raise ValueError("chain tip next_step drifted from the preserved trunk step")
    preview = dict(tip.get("offline_selection_preview") or {})

    payload: dict[str, Any] = {
        "engram_trace_contract_version": ENGRAM_TRACE_CONTRACT_VERSION,
        "phase": ENGRAM_TRACE_CONTRACT_PHASE,
        "status": ENGRAM_TRACE_CONTRACT_STATUS,
        "engram_trace_contract_scope": ENGRAM_TRACE_CONTRACT_SCOPE,
        "engram_criteria_policy": ENGRAM_CRITERIA_POLICY,
        "own_gate_semantics": ENGRAM_OWN_GATE_SEMANTICS,
        "selection_policy": SELECTION_POLICY,
        "engram_object_locus": ENGRAM_OBJECT_LOCUS,
        "estimator_verification_status": ESTIMATOR_VERIFICATION_STATUS,
        "engram_criteria_attribution": ENGRAM_CRITERIA_ATTRIBUTION,
        "reviewed_labels_are_train_split_not_engram_ground_truth": True,
        "engram_source_reference": {
            "arxiv_id": "2606.14997",
            "title": "AI Engram: In Search of Memory Traces in Artificial Intelligence",
            "venue_claim": "icml_2026_oral_self_reported_on_arxiv",
            "independent_index_status": "semantic_scholar_venue_and_citation_empty",
            "verification_status": "unverified_preprint",
            "intervention_class": "destructive_weight_editing_forbidden",
            "lora_supported_by_paper": False,
        },
        "local_core_identity": dict(LOCAL_CORE_IDENTITY),
        "sample_scale": scale,
        "feature_schema_sha256": feature_schema_sha256,
        "feature_names": list(CALIBRATOR_DESIGN_FEATURE_NAMES),
        "selected_question_id_at_chain_tip": preview.get("selected_question_id"),
        "selected_order_at_chain_tip": preview.get("selected_order"),
        "criteria": list(ENGRAM_CRITERIA),
        "layers": list(ENGRAM_LAYERS),
        "criteria_mappings": _criteria_mappings(scale),
        "hash_bindings": bindings,
        "revalidated_upstream_artifacts": revalidated,
        "forbidden_operations": list(ENGRAM_FORBIDDEN_OPERATIONS),
        "discipline": dict(DISCIPLINE),
        ENGRAM_OWN_GATE: True,
        "block_reasons": list(ENGRAM_BLOCK_REASONS),
        "next_step": PRESERVED_NEXT_STEP,
        "engram_track_next_step": ENGRAM_TRACK_NEXT_STEP,
    }
    for hash_key, sha256 in by_key.items():
        payload[hash_key] = sha256
    for gate in ALL_REQUIRED_FALSE_GATES:
        payload[gate] = False

    sealed = _seal_engram_trace_contract(payload)
    return validate_engram_trace_contract(sealed, upstream)


def validate_engram_trace_contract(
    payload: Mapping[str, Any],
    upstream: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized = _clone(payload)
    _walk_forbidden_fields(normalized)

    if normalized.get("engram_trace_contract_version") != (
        ENGRAM_TRACE_CONTRACT_VERSION
    ):
        raise ValueError("unsupported engram trace contract version")
    if normalized.get("phase") != ENGRAM_TRACE_CONTRACT_PHASE:
        raise ValueError("engram trace contract must be J1.2")
    if normalized.get("status") != ENGRAM_TRACE_CONTRACT_STATUS:
        raise ValueError("engram trace contract status mismatch")
    if normalized.get("engram_trace_contract_scope") != ENGRAM_TRACE_CONTRACT_SCOPE:
        raise ValueError("engram trace contract scope mismatch")
    if normalized.get("engram_criteria_policy") != ENGRAM_CRITERIA_POLICY:
        raise ValueError("engram trace contract criteria policy mismatch")
    if normalized.get("own_gate_semantics") != ENGRAM_OWN_GATE_SEMANTICS:
        raise ValueError("engram trace contract own gate semantics mismatch")
    if normalized.get("selection_policy") != SELECTION_POLICY:
        raise ValueError("engram trace contract selection policy mismatch")
    if normalized.get("engram_object_locus") != ENGRAM_OBJECT_LOCUS:
        raise ValueError("engram trace contract object locus mismatch")
    if normalized.get("estimator_verification_status") != (
        ESTIMATOR_VERIFICATION_STATUS
    ):
        raise ValueError("engram trace contract estimator status mismatch")
    if normalized.get(
        "reviewed_labels_are_train_split_not_engram_ground_truth"
    ) is not True:
        raise ValueError("reviewed labels must be declared a train split")

    if normalized.get("next_step") != PRESERVED_NEXT_STEP:
        raise ValueError("engram trace contract must preserve the trunk next_step")
    discipline = dict(normalized.get("discipline") or {})
    if discipline.get("preserves_declared_next_step") != PRESERVED_NEXT_STEP:
        raise ValueError("engram trace contract discipline next_step mismatch")
    if discipline.get("does_not_modify_sealed_artifacts") is not True:
        raise ValueError("engram trace contract must not modify sealed artifacts")
    if discipline.get("measures_nothing_in_this_artifact") is not True:
        raise ValueError("engram trace contract must declare zero measurement")

    # gates ----------------------------------------------------------------
    if normalized.get(ENGRAM_OWN_GATE) is not True:
        raise ValueError("engram trace contract gate must be true")
    offending = [
        gate for gate in ALL_REQUIRED_FALSE_GATES if normalized.get(gate) is not False
    ]
    if offending:
        raise ValueError(
            "engram trace contract cannot enable gates: " + ",".join(sorted(offending))
        )
    if normalized.get("engram_measurement_executed_gate") is not False:
        raise ValueError("engram trace contract must not record executed measurement")

    block_reasons = list(normalized.get("block_reasons") or [])
    if not block_reasons:
        raise ValueError(
            "engram trace contract block_reasons must enumerate measurement blockers"
        )
    if block_reasons != list(ENGRAM_BLOCK_REASONS):
        raise ValueError("engram trace contract block_reasons mismatch")
    if normalized.get("forbidden_operations") != list(ENGRAM_FORBIDDEN_OPERATIONS):
        raise ValueError("engram trace contract forbidden operations mismatch")

    # criteria mappings ----------------------------------------------------
    mappings = list(normalized.get("criteria_mappings") or [])
    if len(mappings) != len(ENGRAM_CRITERIA) * len(ENGRAM_LAYERS):
        raise ValueError("engram trace contract requires one cell per criterion-layer")
    seen_cells: set[tuple[str, str]] = set()
    for cell in mappings:
        criterion = str(cell.get("criterion") or "")
        layer = str(cell.get("layer") or "")
        if criterion not in ENGRAM_CRITERIA or layer not in ENGRAM_LAYERS:
            raise ValueError("engram trace contract unknown criterion or layer")
        if (criterion, layer) in seen_cells:
            raise ValueError("engram trace contract duplicate criterion-layer cell")
        seen_cells.add((criterion, layer))
        if cell.get("mapping_kind") not in MAPPING_KINDS:
            raise ValueError("engram trace contract unknown mapping_kind")
        if cell.get("execution_status") != EXECUTION_STATUS_NOT_EXECUTED:
            raise ValueError("engram trace contract cells must not be executed")
        if cell.get("inferential_claim_supported") is not False:
            raise ValueError("engram trace contract cells cannot support inference")
        if not str(cell.get("computation") or ""):
            raise ValueError("engram trace contract cells require a computation")
        if not str(cell.get("misread_risk") or ""):
            raise ValueError("engram trace contract cells require a misread risk")
    necessity_graph = next(
        cell
        for cell in mappings
        if cell["criterion"] == "necessity" and cell["layer"] == "graph_memory"
    )
    for control in (
        "degree_normalization_required",
        "multipath_counting_required",
        "permutation_null_baseline_required",
    ):
        if necessity_graph.get(control) is not True:
            raise ValueError(f"graph necessity cell requires {control}")

    # local core identity --------------------------------------------------
    identity = dict(normalized.get("local_core_identity") or {})
    if identity.get("adapter_sha256_scope") != LOCAL_CORE_IDENTITY[
        "adapter_sha256_scope"
    ]:
        raise ValueError("local core adapter hash scope must be declared")
    if identity.get("adapter_digest_algorithm") != LOCAL_CORE_IDENTITY[
        "adapter_digest_algorithm"
    ]:
        raise ValueError("local core adapter digest algorithm must be declared")
    if identity.get("trainable_parameter_count") != 0:
        raise ValueError("local core identity must record zero trainable parameters")
    if "reproducible_on_disk" in identity:
        raise ValueError(
            "local core identity must not assert on-disk reproducibility; the "
            "recheck is an advisory report observation, not a sealed claim"
        )

    scale = dict(normalized.get("sample_scale") or {})
    if scale.get("min_n_for_inference_status") != MIN_N_FOR_INFERENCE_STATUS:
        raise ValueError("sample scale must not assert a minimum-n threshold")

    # upstream bindings ----------------------------------------------------
    bindings = list(normalized.get("hash_bindings") or [])
    if len(bindings) != len(UPSTREAM_HASH_SPEC):
        raise ValueError("engram trace contract hash binding count mismatch")
    for binding in bindings:
        hash_key = str(binding.get("hash_key") or "")
        sha256 = str(binding.get("sha256") or "")
        if normalized.get(hash_key) != sha256:
            raise ValueError(f"engram trace contract hash binding mismatch: {hash_key}")
        if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
            raise ValueError(f"engram trace contract hash not lowercase hex: {hash_key}")
        if binding.get("source_artifact") != CHAIN_TIP_KEY and not list(
            binding.get("stored_in") or []
        ):
            raise ValueError(
                f"engram trace contract binding lacks corroboration: {hash_key}"
            )

    if upstream is not None:
        expected_bindings = build_hash_bindings(upstream)
        if bindings != expected_bindings:
            raise ValueError("engram trace contract hash bindings are not reproducible")
        if scale != derive_sample_scale(upstream):
            raise ValueError(
                "engram trace contract sample scale does not match sealed upstream"
            )
        expected_revalidated = revalidate_upstream_artifacts(upstream)
        if list(normalized.get("revalidated_upstream_artifacts") or []) != (
            expected_revalidated
        ):
            raise ValueError("engram trace contract upstream revalidation mismatch")
        tip = upstream[CHAIN_TIP_KEY]
        preview = dict(tip.get("offline_selection_preview") or {})
        if normalized.get("selected_question_id_at_chain_tip") != preview.get(
            "selected_question_id"
        ):
            raise ValueError("engram trace contract chain tip question mismatch")
        if normalized.get("selected_order_at_chain_tip") != preview.get(
            "selected_order"
        ):
            raise ValueError("engram trace contract chain tip order mismatch")

    if normalized.get("feature_schema_sha256") != _feature_schema_sha256():
        raise ValueError("engram trace contract feature schema hash mismatch")
    if normalized.get("feature_names") != list(CALIBRATOR_DESIGN_FEATURE_NAMES):
        raise ValueError("engram trace contract feature schema mismatch")

    supplied_hash = str(normalized.get("engram_trace_contract_sha256") or "")
    unhashed = _clone(normalized)
    unhashed.pop("engram_trace_contract_sha256", None)
    if supplied_hash != canonical_json_sha256(unhashed):
        raise ValueError("engram trace contract sha256 mismatch")
    return normalized
