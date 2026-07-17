"""Prepare or audit external-teacher semantic labels for J1.1B unions.

The draft is generated only from the sealed independent unions and the six
user-reviewed reference answers.  It remains unfit for calibration until an
explicit batch user review creates a separate reviewed successor.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.answer_source import (  # noqa: E402
    validate_answer_source_amendment,
    validate_reference_answer_pack,
)
from neural.baby.candidate_universe import (  # noqa: E402
    UNION_LABEL_PACK_VERSION,
    build_union_label_readiness_report,
    seal_union_label_pack,
    validate_candidate_vocabulary,
    validate_independent_score_capture,
    validate_union_label_pack,
)
from neural.baby.question_calibration import validate_preregistered_manifest  # noqa: E402


DEFAULT_MANIFEST = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_1_train_calibration_a_20260716.json"
)
DEFAULT_RAW_PACK = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_train_calibration_a_20260716_raw_scores_sealed.json"
)
DEFAULT_AMENDMENT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_answer_source_amendment_20260716.json"
)
DEFAULT_ANSWERS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_teacher_answers_reviewed_20260716.json"
)
DEFAULT_VOCABULARY = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_vocabulary_v2_20260716.json"
)
DEFAULT_CAPTURE = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_raw_scores_20260716.json"
)
DEFAULT_LABELS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_labels_draft_20260716.json"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_candidate_universe_v2_labels_draft_20260716.json"
)


LABEL_RULES: dict[int, dict[str, dict[str, str]]] = {
    0: {
        "approved": {
            "정보": "기억이 저장하고 학습이 갱신하는 핵심 대상이다.",
            "관계": "기억과 학습이 서로를 갱신하는 순환 연결을 직접 나타낸다.",
            "상호작용": "기억이 학습을 안내하고 학습이 기억을 수정하는 상호 영향을 나타낸다.",
        },
        "uncertain": {},
    },
    1: {
        "approved": {
            "로보틱스": "컴퓨터 제어와 물리적 로봇을 함께 다루는 직접 관련 분야다.",
            "프로그램": "컴퓨터의 정보 처리와 로봇 제어를 연결하는 핵심 수단이다.",
            "상호작용": "로봇이 물리적 환경을 감지하고 행동한다는 차이를 직접 나타낸다.",
            "알고리즘": "컴퓨터의 계산과 로봇의 제어 절차를 구성하는 공통 요소다.",
        },
        "uncertain": {
            "AI": "컴퓨터와 로봇에 사용될 수 있지만 둘의 필수 정의 요소는 아니다.",
            "사용자": "일부 컴퓨터와 로봇이 사용자와 상호작용하지만 일반적 구조 차이의 핵심은 아니다.",
            "사용": "두 장치의 활용과 연결될 수 있으나 의미가 지나치게 일반적이다.",
        },
    },
    2: {
        "approved": {
            "1시간 뒤": "시간 경과와 이후 맥락이라는 질문 축을 직접 나타낸다.",
            "배움": "새로 배운 지식이 과거 경험을 해석하는 맥락을 바꾼다.",
            "학습": "후속 학습이 기억과 경험의 의미를 수정하는 요인이다.",
            "감정": "감정 변화가 같은 경험의 의미와 영향을 달라지게 할 수 있다.",
        },
        "uncertain": {
            "세상": "후속 사건이 생기는 외부 맥락으로 연결되지만 직접 메커니즘은 아니다.",
            "상호작용": "새 사건과 환경 접촉을 포괄할 수 있지만 기준답변보다 의미가 넓다.",
            "감정 표현": "감정 변화와 관련될 수 있으나 표현 자체가 경험 재해석의 원인은 아니다.",
        },
    },
    3: {
        "approved": {
            "검색": "질문을 바탕으로 답과 증거를 얻는 대표 행동이다.",
            "모르는 것": "궁금증과 질문이 드러내는 지식의 빈틈이다.",
            "답": "질문으로 얻어 기존 지식과 비교하는 핵심 결과다.",
            "새로운": "질문과 증거 연결을 통해 형성되는 새 지식을 직접 나타낸다.",
            "응답": "대화나 탐구에서 질문에 대한 정보를 제공하는 결과다.",
        },
        "uncertain": {
            "비밀 질문": "질문의 한 종류지만 새로운 지식 형성의 일반 메커니즘은 아니다.",
            "사용자": "질문 주체가 될 수 있으나 지식 형성 과정의 핵심 개념은 아니다.",
        },
    },
    4: {
        "approved": {
            "관계": "이야기와 상상이 서로 확장하는 상호 연결을 직접 나타낸다.",
            "학습": "이야기에서 얻은 새 구조와 요소가 다음 상상을 넓히는 과정과 연결된다.",
            "기억": "상상이 재조합하고 이야기가 구조화하는 경험 요소의 원천이다.",
            "상호작용": "상상이 이야기를 만들고 이야기가 다시 상상을 자극하는 순환을 나타낸다.",
        },
        "uncertain": {
            "하늘을 나는 것": "상상의 예시는 될 수 있지만 상호 발전 메커니즘 자체는 아니다.",
            "신기한": "상상의 정서적 결과일 수 있지만 핵심 관계는 아니다.",
            "감정": "이야기와 상상을 자극할 수 있지만 기준답변의 직접 축은 아니다.",
        },
    },
    5: {
        "approved": {
            "관계": "사람의 행동과 세상의 피드백이라는 상호 연결을 직접 나타낸다.",
            "상호작용": "사람이 환경을 바꾸고 환경이 다시 사람을 바꾸는 과정을 나타낸다.",
            "인터넷": "사람이 만들고 사용하면서 다시 행동과 기회를 바꾸는 기술 환경의 예다.",
        },
        "uncertain": {
            "딥러닝": "사람과 세상이 주고받는 기술 영향의 예지만 범위가 좁다.",
            "웹 서치": "기술 환경과 사람 행동의 접점이지만 일반 피드백 관계의 일부 사례다.",
            "사용자": "디지털 환경 속 사람을 가리키지만 사람 전체를 대표하기에는 좁다.",
            "감정": "환경이 사람에게 미치는 영향과 연결될 수 있으나 기준답변에 직접 명시되지는 않았다.",
            "긍정적 감정": "세상의 영향 결과일 수 있지만 일반 상호작용 메커니즘은 아니다.",
        },
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite J1.1B label artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _validated_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], ...]:
    manifest = validate_preregistered_manifest(_load_json(args.manifest))
    raw_pack = _load_json(args.raw_pack)
    amendment = validate_answer_source_amendment(
        manifest, raw_pack, _load_json(args.amendment)
    )
    answers = validate_reference_answer_pack(
        manifest, raw_pack, amendment, _load_json(args.answers)
    )
    vocabulary = validate_candidate_vocabulary(_load_json(args.vocabulary))
    capture = validate_independent_score_capture(
        vocabulary, _load_json(args.capture)
    )
    return manifest, answers, vocabulary, capture


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    if args.labels.exists() or args.report.exists():
        raise FileExistsError("refusing to overwrite existing J1.1B label artifacts")
    _, answers, vocabulary, capture = _validated_inputs(args)
    answer_by_order = {
        int(item["order"]): item for item in answers["answers"]
    }
    entries = []
    for question in capture["questions"]:
        order = int(question["order"])
        rules = LABEL_RULES[order]
        approved = rules["approved"]
        uncertain = rules["uncertain"]
        if set(approved) & set(uncertain):
            raise ValueError(f"overlapping label rules at order {order}")
        labels = []
        union_names = {
            item["concept_name"] for item in question["independent_union"]["union"]
        }
        unknown_rules = (set(approved) | set(uncertain)) - union_names
        if unknown_rules:
            raise ValueError(f"label rules outside union at order {order}: {unknown_rules}")
        for concept in question["independent_union"]["union"]:
            name = concept["concept_name"]
            if name in approved:
                decision = "proposed_approved"
                rationale = approved[name]
            elif name in uncertain:
                decision = "proposed_uncertain"
                rationale = uncertain[name]
            else:
                decision = "proposed_rejected"
                rationale = (
                    f"{name}은(는) 이 기준답변의 핵심 메커니즘을 직접 나타내지 않는다."
                )
            labels.append({
                "concept_id": concept["concept_id"],
                "concept_name": name,
                "decision": decision,
                "rationale": rationale,
            })
        entries.append({
            "order": order,
            "question_id": question["question_id"],
            "question_sha256": question["question_sha256"],
            "answer_sha256": answer_by_order[order]["answer_sha256"],
            "labels": labels,
        })

    created_at = _now_iso()
    labels = seal_union_label_pack({
        "union_label_pack_version": UNION_LABEL_PACK_VERSION,
        "phase": "J1.1B",
        "created_at": created_at,
        "candidate_vocabulary_sha256": vocabulary["candidate_vocabulary_sha256"],
        "independent_score_capture_sha256": capture[
            "independent_score_capture_sha256"
        ],
        "reviewed_reference_answer_pack_sha256": answers[
            "reference_answer_pack_sha256"
        ],
        "semantic_label_source": (
            "external_teacher_drafted_against_user_reviewed_reference_answers"
        ),
        "review_status": "awaiting_user_review",
        "reviewer_role": "assistant_draft",
        "reviewed_at": None,
        "label_count": sum(len(item["labels"]) for item in entries),
        "entries": entries,
        "user_direct_answers": False,
        "database_writes": False,
        "learning_enabled": False,
        "probabilities_computed": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    })
    labels = validate_union_label_pack(capture, answers, labels)
    report = build_union_label_readiness_report(capture, answers, labels)
    report.update({
        "created_at": created_at,
        "candidate_vocabulary_sha256": vocabulary["candidate_vocabulary_sha256"],
        "independent_score_capture_sha256": capture[
            "independent_score_capture_sha256"
        ],
        "union_label_pack_sha256": labels["union_label_pack_sha256"],
        "conversation_handler_changed": False,
        "live_predictor_changed": False,
    })
    _write_json_new(args.labels, labels)
    _write_json_new(args.report, report)
    return report


def audit(args: argparse.Namespace) -> dict[str, Any]:
    _, answers, _, capture = _validated_inputs(args)
    labels = validate_union_label_pack(
        capture, answers, _load_json(args.labels)
    )
    return build_union_label_readiness_report(capture, answers, labels)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "audit"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-pack", type=Path, default=DEFAULT_RAW_PACK)
    parser.add_argument("--amendment", type=Path, default=DEFAULT_AMENDMENT)
    parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS)
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    report = prepare(args) if args.action == "prepare" else audit(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
