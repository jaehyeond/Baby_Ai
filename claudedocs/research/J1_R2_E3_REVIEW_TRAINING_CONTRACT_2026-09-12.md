# J1-R2-E3 사용자 검토·학습 정책 successor 계약

상태: 사용자 의미 라벨 검토 대기, 학습 데이터 아님

## 목적과 현재 결론

이 successor는 2026-07-28 E3의 agent 제안표를 사용자가 검토할 수 있는
결정 템플릿으로 옮기고, 검토가 끝났을 때 어떤 행이 관련성 head의 fit
후보가 될 수 있는지만 집계한다. 이번 진행 지시는 60개 의미 라벨의
승인이 아니다. 따라서 생성본의 60개 user decision은 모두 null이고,
현재 fit 자격은 0행이다.

이 계약은 다음 고정 입력을 바이트/정본 해시로 묶는다.

- E3 pending packet: aec20a9d0c714e768c560d8eb4d517edf604ca6c03cd7fc01ed8830fbf2339e4
- E3 read-only audit: 696fe080b26bbb40af6e433394956b8cf6649ca1aff40d843d11288b2f3a04b4
- agent recommendation file: e358c84aa3271400241fad6a1117c8375502d0a8a1aee2aeab89dc58b1657708
- candidate vocabulary: bc06ed54f24420eecdaa0be156f6041d882e80648bc64030baf5ac00bd2abd82
- frozen evaluation universe: 1,069 concepts

원본 역할도 유지한다. primary review 대상은 질문당 top_unjudged 5개,
총 60행이다. 그중 기존 질문 partition을 따라 fit pool 40행과
development challenge pool 20행으로 나뉜다. positive가 top-8 밖이었던
문항의 rank 주변 24행은 score-band 진단 전용이며, 결정 템플릿과 fit
후보에서 모두 제외된다.

## 결정과 fit 정책

사용자는 primary 60행 각각에 두 축을 별도로 결정해야 한다.

- 관련성: positive, context, hard_negative, unrelated_negative, uncertain
- vocabulary: canonical, alias, fragment, malformed, uncertain

context는 관련된 의미 이웃이므로 binary negative로 만들지 않는다.
uncertain은 fit에서 제외한다. fit_pool 안의 positive만 target 1,
hard_negative와 unrelated_negative만 target 0 후보가 된다.
development_challenge_pool은 검토가 끝나도 fit에 넣지 않는다.

vocabulary의 alias 검토 결과는 관련성 라벨과 별도 축이다. alias가
확정되면 원본 1,069-concept 평가 universe는 그대로 두고 alias target만
기록한다. 이 결정은 live graph merge/delete/cleanup 권한을 주지 않는다.
fragment/malformed 판정도 같은 이유로 DB 수정으로 자동 전환하지 않는다.

기존 R1의 58 fit 후보는 계보를 위해 readiness에 유지하지만, 그 수를
충분한 학습량이나 성능 근거로 해석하지 않는다. 사용자 검토가 끝나도
fit_data_sufficiency_gate, training_data_materialization_gate,
learned_head_fit_gate는 별도 판단과 승인 전까지 false다. 학습 목표는
질문 + 후보 concept -> 관련성이며 기존 causal-LM graph-neighbor replay를
재사용하지 않는다.

## 생성물과 사용법

- pending template:
  claudedocs/research/j1_r2_e3_pending_review_decisions_20260912.json
- readiness:
  claudedocs/research/j1_r2_e3_review_readiness_20260912.json
- library:
  neural/baby/e3_review_contract.py
- CLI:
  scripts/research/e3_review_contract.py

현재 상태를 다시 생성하고 검증하는 명령은 다음과 같다.

    & 'E:\A2A\our-a2a-project\.venv\Scripts\python.exe' -B scripts\research\e3_review_contract.py generate
    & 'E:\A2A\our-a2a-project\.venv\Scripts\python.exe' -B scripts\research\e3_review_contract.py validate --expect-incomplete

사용자 검토 후 successor decision artifact에는 모든 60행의
user_relevance_decision, user_vocabulary_decision이 정확히 한 번씩
있어야 한다. alias에는 원본 packet에서 확인되는 별도
alias_target_concept_id가 필요하다. 최상위 provenance는 다음을 모두
요구한다.

- status=user_reviewed
- reviewer_role=user
- decision_source=explicit_user_review_of_e3_primary_rows
- timezone이 있는 reviewed_at
- 비어 있지 않은 review_evidence_reference
- review_complete_gate=true

그 뒤 seal_e3_review_decisions로 새 decision을 self-hash하고
validate --require-user-review에 통과시킨다. validator는 누락·중복 ID,
질문/후보/hash 변조, 24개 diagnostic 행 삽입, agent proposal을
user-reviewed로 바꾼 provenance를 거부한다.

이번 산출물은 JSON 생성/검사 외 실행 경로가 없다. DB read/write, model
inference/download, gradient/optimizer, training-row materialization,
lockbox 생성/소비, held-out 평가, graph cleanup, production 승격은 모두
수행하지 않았다.
