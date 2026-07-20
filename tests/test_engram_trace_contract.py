import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

from neural.baby.engram_trace_contract import (
    ALL_REQUIRED_FALSE_GATES,
    CANONICAL_REQUIRED_FALSE_GATES,
    ENGRAM_BLOCK_REASONS,
    ENGRAM_OWN_GATE,
    ENGRAM_REQUIRED_FALSE_GATES,
    PRESERVED_NEXT_STEP,
    REQUIRED_UPSTREAM_KEYS,
    build_engram_trace_contract,
    build_hash_bindings,
    validate_engram_trace_contract,
)
from neural.baby.pending_question_semantics import canonical_json_sha256


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUTS = PROJECT_ROOT / "scripts" / "research" / "inputs"
DOCS = PROJECT_ROOT / "claudedocs" / "research"

UPSTREAM_PATHS = {
    "fresh_shadow_question_selection": (
        INPUTS / "j1_1_fresh_shadow_question_selection_20260718.json"
    ),
    "fresh_pre_question_shadow_probability_snapshot": (
        INPUTS / "j1_1_fresh_pre_question_shadow_probability_snapshot_20260718.json"
    ),
    "fresh_pre_question_input_pack": (
        INPUTS / "j1_1_fresh_pre_question_shadow_input_pack_20260718.json"
    ),
    "fresh_pre_question_snapshot_input_contract": (
        INPUTS / "j1_1_fresh_pre_question_snapshot_input_contract_20260718.json"
    ),
    "train_only_calibrator_fit": (
        INPUTS / "j1_1_candidate_universe_v2_train_only_calibrator_fit_20260718.json"
    ),
    "calibrator_design_audit": (
        DOCS / "j1_1_candidate_universe_v2_calibrator_design_audit_20260718.json"
    ),
    "calibrator_probability_snapshot": (
        INPUTS / "j1_1_candidate_universe_v2_probability_snapshot_20260718.json"
    ),
    "question_selection_contract": (
        INPUTS / "j1_1_question_selection_contract_20260718.json"
    ),
    "independent_score_capture": (
        INPUTS / "j1_1_candidate_universe_v2_raw_scores_20260716.json"
    ),
    "candidate_vocabulary": INPUTS / "j1_1_candidate_vocabulary_v2_20260716.json",
    "union_label_pack": (
        INPUTS / "j1_1_candidate_universe_v2_labels_reviewed_20260718.json"
    ),
    "answer_source_amendment": INPUTS / "j1_1_answer_source_amendment_20260716.json",
}

SEALED_CONTRACT = INPUTS / "j1_2_engram_trace_contract_20260719.json"


def _reseal(payload: dict) -> dict:
    resealed = copy.deepcopy(payload)
    resealed.pop("engram_trace_contract_sha256", None)
    resealed["engram_trace_contract_sha256"] = canonical_json_sha256(resealed)
    return resealed


@pytest.fixture(scope="module")
def upstream() -> dict:
    missing = [key for key, path in UPSTREAM_PATHS.items() if not path.exists()]
    if missing:
        pytest.skip(f"sealed upstream artifacts unavailable: {sorted(missing)}")
    return {
        key: json.loads(path.read_text(encoding="utf-8"))
        for key, path in UPSTREAM_PATHS.items()
    }


@pytest.fixture(scope="module")
def contract(upstream: dict) -> dict:
    return build_engram_trace_contract(upstream)


# --------------------------------------------------------------------------
# positive
# --------------------------------------------------------------------------


def test_contract_is_definition_only_and_self_validating(contract, upstream):
    assert contract["phase"] == "J1.2"
    assert contract["status"] == (
        "engram_trace_contract_defined_measurement_blocked_not_runtime"
    )
    assert contract[ENGRAM_OWN_GATE] is True
    # The sealed artifact must pass its own validator, with and without upstream.
    assert validate_engram_trace_contract(contract) == contract
    assert validate_engram_trace_contract(contract, upstream) == contract


def test_every_required_gate_is_false(contract):
    assert len(CANONICAL_REQUIRED_FALSE_GATES) == 8
    assert len(ENGRAM_REQUIRED_FALSE_GATES) == 12
    assert len(ALL_REQUIRED_FALSE_GATES) == 21
    for gate in ALL_REQUIRED_FALSE_GATES:
        assert contract[gate] is False, gate
    assert contract["engram_measurement_executed_gate"] is False
    assert contract["statistical_power_gate"] is False


def test_block_reasons_are_non_empty(contract):
    assert contract["block_reasons"]
    assert contract["block_reasons"] == list(ENGRAM_BLOCK_REASONS)
    assert len(contract["block_reasons"]) == 14


def test_trunk_next_step_is_preserved_verbatim(contract, upstream):
    assert contract["next_step"] == PRESERVED_NEXT_STEP
    assert contract["discipline"]["preserves_declared_next_step"] == PRESERVED_NEXT_STEP
    tip = upstream["fresh_shadow_question_selection"]
    assert contract["next_step"] == tip["next_step"]


def test_chain_tip_selection_is_bound(contract, upstream):
    preview = upstream["fresh_shadow_question_selection"]["offline_selection_preview"]
    assert contract["selected_question_id_at_chain_tip"] == preview[
        "selected_question_id"
    ]
    assert contract["selected_order_at_chain_tip"] == preview["selected_order"]


def test_no_cell_is_executed_or_inferential(contract):
    assert len(contract["criteria_mappings"]) == 16
    for cell in contract["criteria_mappings"]:
        assert cell["execution_status"] == "asserted_not_executed"
        assert cell["inferential_claim_supported"] is False
        assert cell["min_n_for_inference"] is None


def test_graph_necessity_requires_confound_controls(contract):
    cell = next(
        item
        for item in contract["criteria_mappings"]
        if item["criterion"] == "necessity" and item["layer"] == "graph_memory"
    )
    assert cell["permutation_null_baseline_required"] is True
    assert cell["degree_normalization_required"] is True
    assert cell["multipath_counting_required"] is True


def test_graph_sufficiency_is_renamed_away_from_gain_of_function(contract):
    cell = next(
        item
        for item in contract["criteria_mappings"]
        if item["criterion"] == "sufficiency" and item["layer"] == "graph_memory"
    )
    assert cell["mapping_kind"] == "pattern_completion_analog_not_gain_of_function"


def test_local_core_identity_declares_digest_scope(contract):
    identity = contract["local_core_identity"]
    assert identity["adapter_sha256_scope"] == (
        "directory_digest_over_models_local_core_adapter_not_single_file_hash"
    )
    assert "_sha256_directory" in identity["adapter_digest_algorithm"]
    assert identity["trainable_parameter_count"] == 0
    # The sealed definition must not assert on-disk state it never checked.
    assert "reproducible_on_disk" not in identity
    assert identity["on_disk_recheck_is_reported_not_sealed"] is True


def test_sample_scale_is_derived_from_sealed_upstream(contract, upstream):
    scale = contract["sample_scale"]
    fit_metrics = upstream["train_only_calibrator_fit"]["cross_validation_metrics"]
    assert scale["train_only_auc_roc"] == fit_metrics["auc_roc"]
    assert scale["binary_label_row_count"] == fit_metrics["row_count"]
    assert scale["positive_label_count"] == fit_metrics["positive_count"]
    assert scale["negative_label_count"] == fit_metrics["negative_count"]
    assert scale["uncertain_label_count"] == upstream["train_only_calibrator_fit"][
        "excluded_uncertain_count"
    ]
    assert scale["reviewed_label_total"] == upstream["union_label_pack"]["label_count"]
    assert scale["question_count"] == upstream[
        "fresh_pre_question_shadow_probability_snapshot"
    ]["question_count"]
    assert scale["min_n_for_inference_status"] == "undefined_pending_power_analysis"
    # every number must name the sealed field it came from
    assert set(scale["sample_scale_source_fields"]) == {
        "question_count",
        "binary_label_row_count",
        "positive_label_count",
        "negative_label_count",
        "uncertain_label_count",
        "reviewed_label_total",
        "train_only_auc_roc",
    }


def test_sample_scale_drift_from_upstream_is_rejected(contract, upstream):
    tampered = copy.deepcopy(contract)
    tampered["sample_scale"]["train_only_auc_roc"] = 0.99
    with pytest.raises(ValueError, match="sample scale does not match sealed upstream"):
        validate_engram_trace_contract(_reseal(tampered), upstream)


def test_asserting_on_disk_reproducibility_is_rejected(contract):
    tampered = copy.deepcopy(contract)
    tampered["local_core_identity"]["reproducible_on_disk"] = True
    with pytest.raises(ValueError, match="must not assert on-disk reproducibility"):
        validate_engram_trace_contract(_reseal(tampered))


def test_minimum_n_threshold_cannot_be_asserted(contract):
    tampered = copy.deepcopy(contract)
    tampered["sample_scale"]["min_n_for_inference_status"] = "satisfied_n_30"
    with pytest.raises(ValueError, match="must not assert a minimum-n threshold"):
        validate_engram_trace_contract(_reseal(tampered))


def test_all_twelve_hashes_are_bound_and_corroborated(contract):
    bindings = contract["hash_bindings"]
    assert len(bindings) == 12
    assert len(REQUIRED_UPSTREAM_KEYS) == 12
    for binding in bindings:
        assert contract[binding["hash_key"]] == binding["sha256"]
        if binding["source_artifact"] == "fresh_shadow_question_selection":
            # chain tip: nothing upstream references it by construction
            assert binding["stored_in"] == []
            assert binding["no_stored_in_reason"]
        else:
            assert binding["stored_in_count"] >= 1
            assert binding["enforcement"] == (
                "declared_equals_recomputed_equals_stored_in_upstream"
            )


def test_previously_dangling_hashes_are_now_enforced(contract):
    bindings = {item["hash_key"]: item for item in contract["hash_bindings"]}
    union = bindings["union_label_pack_sha256"]
    amendment = bindings["answer_source_amendment_sha256"]
    assert union["source_artifact"] == "union_label_pack"
    assert union["stored_in_count"] >= 1
    assert amendment["source_artifact"] == "answer_source_amendment"
    assert amendment["source_self_hash_field"] == "amendment_sha256"
    assert amendment["stored_in_count"] >= 1


def test_upstream_validators_were_rerun(contract):
    names = contract["revalidated_upstream_artifacts"]
    assert len(names) == 10
    for expected in (
        "validate_fresh_shadow_question_selection",
        "validate_fresh_pre_question_shadow_probability_snapshot",
        "validate_fresh_pre_question_snapshot_input_pack",
        "validate_fresh_pre_question_snapshot_input_contract",
        "validate_question_selection_contract",
        "validate_calibrator_probability_snapshot",
        "validate_train_only_calibrator_fit",
        "validate_calibrator_design_audit",
        "validate_independent_score_capture",
        "validate_candidate_vocabulary",
    ):
        assert expected in names


def test_forbidden_operations_cover_the_known_write_paths(contract):
    ops = contract["forbidden_operations"]
    for expected in (
        "record_curiosity_outcome_invocation",
        "cleanup_old_activations_invocation",
        "durable_or_ephemeral_Activation_node_write",
        "merged_weight_save_to_disk",
        "models_local_core_adapter_overwrite",
        "conversation_handler_v30_edit",
        "api_server_route_or_hook_registration",
    ):
        assert expected in ops


def test_sealed_artifact_on_disk_validates(upstream):
    if not SEALED_CONTRACT.exists():
        pytest.skip("sealed J1.2 contract has not been created yet")
    payload = json.loads(SEALED_CONTRACT.read_text(encoding="utf-8"))
    assert validate_engram_trace_contract(payload, upstream) == payload


# --------------------------------------------------------------------------
# negative
# --------------------------------------------------------------------------


@pytest.mark.parametrize("gate", ALL_REQUIRED_FALSE_GATES)
def test_flipping_any_required_false_gate_is_rejected(contract, gate):
    tampered = _reseal({**copy.deepcopy(contract), gate: True})
    with pytest.raises(ValueError, match="cannot enable gates"):
        validate_engram_trace_contract(tampered)


def test_own_gate_must_be_true(contract):
    tampered = _reseal({**copy.deepcopy(contract), ENGRAM_OWN_GATE: False})
    with pytest.raises(ValueError, match="gate must be true"):
        validate_engram_trace_contract(tampered)


def test_empty_block_reasons_are_rejected(contract):
    tampered = _reseal({**copy.deepcopy(contract), "block_reasons": []})
    with pytest.raises(ValueError, match="must enumerate measurement blockers"):
        validate_engram_trace_contract(tampered)


def test_phase_drift_is_rejected(contract):
    tampered = _reseal({**copy.deepcopy(contract), "phase": "J1.1B"})
    with pytest.raises(ValueError, match="must be J1.2"):
        validate_engram_trace_contract(tampered)


def test_next_step_replacement_is_rejected(contract):
    tampered = _reseal({
        **copy.deepcopy(contract),
        "next_step": "define_engram_map_ui_before_capture",
    })
    with pytest.raises(ValueError, match="preserve the trunk next_step"):
        validate_engram_trace_contract(tampered)


def test_executed_measurement_is_rejected(contract):
    tampered = copy.deepcopy(contract)
    tampered["criteria_mappings"][0]["execution_status"] = "executed"
    with pytest.raises(ValueError, match="must not be executed"):
        validate_engram_trace_contract(_reseal(tampered))


def test_inferential_claim_is_rejected(contract):
    tampered = copy.deepcopy(contract)
    tampered["criteria_mappings"][0]["inferential_claim_supported"] = True
    with pytest.raises(ValueError, match="cannot support inference"):
        validate_engram_trace_contract(_reseal(tampered))


def test_dropping_graph_necessity_permutation_null_is_rejected(contract):
    tampered = copy.deepcopy(contract)
    for cell in tampered["criteria_mappings"]:
        if cell["criterion"] == "necessity" and cell["layer"] == "graph_memory":
            cell["permutation_null_baseline_required"] = False
    with pytest.raises(ValueError, match="permutation_null_baseline_required"):
        validate_engram_trace_contract(_reseal(tampered))


def test_unknown_mapping_kind_is_rejected(contract):
    tampered = copy.deepcopy(contract)
    tampered["criteria_mappings"][0]["mapping_kind"] = "genuine_engram_measurement"
    with pytest.raises(ValueError, match="unknown mapping_kind"):
        validate_engram_trace_contract(_reseal(tampered))


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda p: p.update({"label": "approved"}), id="top-level"),
        pytest.param(
            lambda p: p["criteria_mappings"][0].update({"probability": 0.5}),
            id="nested-cell",
        ),
        pytest.param(
            lambda p: p["local_core_identity"].update({"user_review": "ok"}),
            id="nested-identity",
        ),
    ],
)
def test_forbidden_field_injection_is_rejected(contract, mutate):
    tampered = copy.deepcopy(contract)
    mutate(tampered)
    with pytest.raises(ValueError, match="forbidden field present"):
        validate_engram_trace_contract(_reseal(tampered))


def test_sha256_tamper_is_rejected(contract):
    tampered = copy.deepcopy(contract)
    tampered["engram_trace_contract_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="sha256 mismatch"):
        validate_engram_trace_contract(tampered)


def test_hash_binding_mismatch_is_rejected(contract):
    tampered = copy.deepcopy(contract)
    tampered["train_only_calibrator_fit_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="hash binding mismatch"):
        validate_engram_trace_contract(_reseal(tampered))


def test_binding_without_corroboration_is_rejected(contract):
    tampered = copy.deepcopy(contract)
    for binding in tampered["hash_bindings"]:
        if binding["source_artifact"] == "union_label_pack":
            binding["stored_in"] = []
            binding["stored_in_count"] = 0
    with pytest.raises(ValueError, match="lacks corroboration"):
        validate_engram_trace_contract(_reseal(tampered))


def test_object_locus_removal_is_rejected(contract):
    tampered = _reseal({
        **copy.deepcopy(contract),
        "engram_object_locus": "graph measures the engram",
    })
    with pytest.raises(ValueError, match="object locus mismatch"):
        validate_engram_trace_contract(tampered)


def test_reviewed_label_train_split_declaration_is_required(contract):
    tampered = _reseal({
        **copy.deepcopy(contract),
        "reviewed_labels_are_train_split_not_engram_ground_truth": False,
    })
    with pytest.raises(ValueError, match="train split"):
        validate_engram_trace_contract(tampered)


def test_adapter_digest_scope_removal_is_rejected(contract):
    tampered = copy.deepcopy(contract)
    tampered["local_core_identity"]["adapter_sha256_scope"] = "single_file"
    with pytest.raises(ValueError, match="adapter hash scope"):
        validate_engram_trace_contract(_reseal(tampered))


def test_upstream_tamper_breaks_binding_reproduction(contract, upstream):
    tampered_upstream = copy.deepcopy(upstream)
    tampered_upstream["candidate_vocabulary"]["status"] = "tampered"
    with pytest.raises(ValueError):
        validate_engram_trace_contract(contract, tampered_upstream)


def test_upstream_self_hash_tamper_is_rejected(upstream):
    tampered = copy.deepcopy(upstream)
    tampered["union_label_pack"]["union_label_pack_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="self-hash mismatch"):
        build_hash_bindings(tampered)


def test_adapter_recheck_recomputes_the_directory_digest_not_a_file_hash():
    """The recheck must reproduce the original computation, not a similar one."""

    sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "research"))
    from j1_2_engram_trace_contract import (  # noqa: E402
        LOCAL_CORE_ADAPTER_DIR,
        adapter_digest_recheck,
        sha256_directory,
    )

    if not LOCAL_CORE_ADAPTER_DIR.is_dir():
        pytest.skip("local core adapter directory unavailable")
    sealed = (
        "dd60ed3cd31b82098522ea7b2efff104efe86cb0aeb10b98cb591259fe3cdb8b"
    )
    recheck = adapter_digest_recheck(sealed)
    assert recheck["is_advisory_not_validator_assertion"] is True
    assert recheck["digest_scope"] == "directory_digest_not_single_file_hash"
    assert recheck["recomputed_digest"] == sha256_directory(LOCAL_CORE_ADAPTER_DIR)
    # a single-file hash of the weights must NOT equal the directory digest;
    # confusing the two is what produced a false "adapter lost" conclusion
    weights = LOCAL_CORE_ADAPTER_DIR / "adapter_model.safetensors"
    if weights.exists():
        file_hash = hashlib.sha256(weights.read_bytes()).hexdigest()
        assert file_hash != recheck["recomputed_digest"]


def test_adapter_recheck_reports_unknown_when_directory_is_absent(tmp_path,
                                                                 monkeypatch):
    sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "research"))
    import j1_2_engram_trace_contract as script  # noqa: E402

    monkeypatch.setattr(script, "LOCAL_CORE_ADAPTER_DIR", tmp_path / "absent")
    recheck = script.adapter_digest_recheck("d" * 64)
    assert recheck["matches_sealed"] is None
    assert recheck["recomputed_digest"] is None
    assert "recheck_error" in recheck
    statements = script.report_statements(recheck)
    assert "could NOT be recomputed" in statements[2]


def test_missing_upstream_artifact_is_rejected(upstream):
    partial = {
        key: value
        for key, value in upstream.items()
        if key != "answer_source_amendment"
    }
    with pytest.raises(ValueError, match="requires upstream artifacts"):
        build_hash_bindings(partial)
