# CHANGELOG.md - 일별 작업 기록

> 매일 작업 내용, 성공/실패, 배운 점을 기록합니다.
> 새 세션 시작 시 이 파일을 확인하여 컨텍스트를 복구합니다.

---

## 2026-07-16 (Phase 3 [B-5.4-A] minimal train gate and early stop)

> 상세: `claudedocs/research/PHASE3_CURIOSITY_LOOP_2026-07-14.md`의 `[B-5.4-A]` 절.

### plan/goal cross-check
- **push 기준점**: 시작 시 `DB_Renewal` local/remote HEAD가 사용자 push `7f0d48e`(B5.3)로 일치하고 worktree clean이었다. `AGENTS.md`/`CHANGELOG.md`의 “B5.3 미푸시” 문구만 stale해 이번 기록에서 교정했다.
- B5.1의 외부 outcome 전환, B5.2의 frequency baseline 반증, B5.3의 명시적 sequence 경계는 모두 Phase 3의 “예측오차가 행동에 영향을 주는가”를 정직하게 재는 데 필요했다. 다만 B5.3 이후 추가 계약·락·반복 전체검증은 연구 병목이 될 수 있어, B5.4를 **새 train 1개(7 turn) 뒤 신호가 없으면 즉시 중단**하는 비용 gate로 축소했다.

### 실행과 결과
- **manifest 사전등록**: `scripts/research/manifests/b5_4_train_a_20260716.json`, hash `3486eff0e169f3c4bf1420e924f85427d6747fa4405943dabe35dcace6911b6c`. 예측 이름을 보지 않는 첫 preflight에서 일반 cue `관계`를 발견해 live 전 문장을 `설명해줘` 형식으로 바꿨다. B2 speech-act 필터가 이를 제거해 매 turn 핵심 cue 2개만 남았고, 6/6 scorable pair·고유 preexisting outcome 6개·prediction count 8을 확인했다.
- **live train 7 turn**: 모든 turn이 `external_deferred`, sequence index `0..6`, audit error 없음. Experience 7개와 `NEXT_EXTERNAL_TURN` 6개가 저장됐고 Concept curiosity state는 전후 동일했다. 임시 FastAPI는 수집 후 종료해 port 8000 DOWN.
- **새 sequence 단독**: graph/frequency mean error=`1.0/1.0`, hit=`0/0`, data gate만 true, promotion=false.
- **합친 train 2 sequence/12 pair**: 최선 historical co-occurrence와 multi-cue cosine mean error `0.875`, hit `2`; frequency `0.75`, random `0.992371`; frequency 대비 개선/동률/악화=`1/9/2`. exploratory gate=false, production gate=false. target input·미래 history·mutable relationship strength는 ranking에 사용하지 않았다.
- **조기중단**: candidate signal이 없으므로 두 번째 신규 train, predictor/hyperparameter freeze, sealed held-out 수집, threshold/production 변경, multi-writer unique constraint를 실행하지 않았다. 현 단계에서 held-out를 추가하면 성능 확인보다 검증 절차가 병목이 된다.
- **검증/보고 교정**: canonical `tests/` suite `74 passed`, `pip check`, py_compile, `git diff --check` 통과. 이번 변경은 테스트 3개만 추가했으므로 B5.3 시점의 동일 suite는 71개다. 기존 문서의 “전체 81 passed”는 중복/상이 범위 실행 수를 섞은 부정확한 보고라 71로 교정했다. 보호 handler blob `054d974095be7425692860909181fafd54f97a33` 무변경, 비밀 패턴 0건, port 8000 DOWN.
- artifacts: `claudedocs/research/b5_4_train_a_20260716.json`, `claudedocs/research/b5_4_train_ablation_20260716.json`.

### 다음 판단
- **[B-5.5] target validity gate**: 사용자가 임의로 다음 주제로 이동하는 것을 graph가 맞히게 하는 현재 target이 Phase 3 행동 루프와 정합한지 재검토한다. 우선 후보는 아기가 선택한 질문/행동에 조건부인 다음 사용자 반응 또는 action-conditioned sensor outcome이다. 이 판단 전 추가 live data와 held-out를 금지한다.

---

## 2026-07-16 (Phase 3 [B-5.3] sequence-grounded external outcome contract)

> 상세: `claudedocs/research/PHASE3_CURIOSITY_LOOP_2026-07-14.md`의 `[B-5.3]` 절.

### 완료 ✅ (offline/unit + real read-only Cypher preflight) / live 수집 보류
- **push 기준점**: 시작 시 `DB_Renewal` local/remote HEAD가 사용자 push `5b74663`으로 일치하고 worktree clean이었다. 이 커밋에 B5.2 script/test/artifact/docs가 포함됨을 확인했다.
- **필수 계약** (`neural/baby/external_sequence.py`): `external_sequence_id`, 0-based `external_turn_index`, `external_sequence_split=train|heldout`, `external_sequence_contract_sha256` 네 필드를 정규화한다. ID/turn/split/hash 형식이 하나라도 잘못되면 handler 전에 422로 거부한다.
- **endpoint fail-closed**: research flag는 JSON boolean만 허용한다. 평가 env가 꺼짐, sequence metadata만 단독 전달, DB expected turn 불일치, prediction snapshot 없음에서는 normal same-turn scorer로 fallback하지 않고 handler 전 중단한다. 연구 metadata는 보호 handler context에 전달하지 않는다.
- **DB 이중검사·순서 연결**: endpoint read-only preflight 뒤 `defer_curiosity_outcome_scoring()`의 managed write transaction에서 동일 상태를 다시 검사한다. 성공 시 Experience에 sequence/split/hash/turn을 저장하고 이전 turn과 `NEXT_EXTERNAL_TURN`으로 연결한다. rejected state는 snapshot/sequence 속성을 쓰지 않는다.
- **격리 규칙**: duplicate turn, gap, 기존 sequence 손상, split 변경, manifest hash 변경, 같은 manifest hash의 train/heldout 교차 재사용을 모두 거부한다. B5.1 live pilot도 새 계약과 audit 필드를 보내도록 호환 갱신했으며 기존 artifact read-only 재평가는 같은 수치를 유지했다.
- **offline 증거**: `b5_3_sequence_contract.py` matrix 8/8 통과. artifact는 `database_writes=false`, `live_collection_started=false`, `production_promotion_gate=false`를 명시한다. 실제 Neo4j에서 새 sequence turn 0 state query=`valid`, 저장 Cypher는 `EXPLAIN valid`; 실행 write는 하지 않았다.
- **정직한 한계**: 현재 contract는 순차 단일 프로세스 pilot용 single-writer다. multi-writer production에서는 `(sequence_id, turn_index)` 중복을 원천 차단하는 DB unique constraint/lock이 추가로 필요하다.
- **검증**: canonical `tests/` suite `71 passed`; py_compile, `pip check`, `git diff --check` 통과. Gemini/FastAPI live 호출과 Neo4j write 없음, 8000 DOWN. `conversation_handler.py` current/HEAD blob `054d974095be7425692860909181fafd54f97a33` 동일. (기존 “전체 81”은 후속 B5.4 cross-check에서 중복/상이 범위 실행 수가 섞인 부정확한 집계로 확인돼 교정.)

### 다음 작업
- **[B-5.4-A] train manifest**: 서로 다른 여러 train sequence의 전체 문장·순서·hash를 먼저 고정하고 single-writer로 수집한다. train만으로 후보 predictor와 모든 hyperparameter를 결정·freeze한다.
- **[B-5.4-B] sealed held-out**: held-out 내용은 모델 선택 과정에 노출하지 않고 SHA-256만 먼저 등록한다. predictor/code hash를 freeze한 후 held-out를 한 번만 수집·평가한다.
- held-out가 frequency/random 및 B5 robustness gate를 모두 이길 때만 production 검토를 재개한다. B5.3 변경은 사용자 push `7f0d48e`에 반영됐다.

---

## 2026-07-15 (Phase 3 [B-5.2] graph predictor read-only ablation)

> 상세: `claudedocs/research/PHASE3_CURIOSITY_LOOP_2026-07-14.md`의 `[B-5.2]` 절.

### 완료 ✅ (원인 분해·시간누출 없는 비교) / 승격 ❌
- **B5.1 재감사**: 사용자 push 후 `DB_Renewal` local/remote HEAD `42268bf` 일치, worktree clean을 확인했다. v2.1 artifact와 Neo4j read-only 재평가가 data gate `true`, graph/frequency/random error `0.833333/0.5/0.992315`, hit `1/3`, `promotion_gate=false`를 그대로 재현했다. 기존 보고는 정확했고, 체크포인트의 “7b4862e/B5.1 미푸시” 문구만 stale해 현재 문서에서 교정했다.
- **current predictor root cause**: 모든 cue의 `RELATES_TO` 이웃을 합치고 cue별 지지 수나 후보 degree 벌점 없이 `max(coalesce(hebb_strength,strength))` 한 값으로 전역 top-8을 고른다. 관계 strength는 이후 계속 바뀌지만 역사 버전은 없어 현재 그래프로 과거 rank를 재생하면 future leakage가 생긴다.
- **시간누출 방지 계약**: `scripts/research/b5_2_graph_predictor_ablation.py`는 source Experience보다 엄격히 이전의 conversation Experience와 불변 `INVOLVES` 링크만 사용한다. target input, source 이후 history, 현재 mutable edge strength를 ranking에 쓰지 않으며 모든 Cypher는 read-only다.
- **exploratory 후보**: historical co-occurrence 합, global hub 빈도를 나누는 cosine association, 여러 cue의 공동 지지를 먼저 보는 multi-cue cosine을 동일 top-8로 비교했다. 같은 B5.1 6쌍으로 후보를 선택했으므로 후보가 gate를 통과해도 새 preregistered held-out 전에는 production promotion을 항상 차단한다.
- **결과**: stored live graph=`0.833333`/hit `1`; co-occurrence=`0.75`/hit `2`; cosine=`0.916667`/hit `1`; multi-cue cosine=`0.75`/hit `2`; frequency=`0.5`/hit `3`. 최고 후보도 frequency보다 좋은 pair `1`, tie `3`, worse `2`라 baseline/robustness/exploratory gate 모두 실패했다. 개선은 기존 `비비` 외 `개발자` 부분 hit 하나뿐이고 `도시·사람·이름` 전이는 모두 놓쳤다.
- **transition route 차단 근거**: conversation Experience `1,496`; session_id `0`, speaker_id `0`, user_id `0`, NEXT_TURN link `0`. 전역 timestamp 인접 turn을 연결하면 서로 다른 대화 스트림을 섞으므로 transition-aware predictor를 만들지 않았다.
- **검증**: 신규 6 unit을 포함한 전체 `64 passed`; py_compile, `pip check`, `git diff --check` 통과. Neo4j write/Gemini/live server 호출 없음, FastAPI 8000 DOWN. `conversation_handler.py` current/HEAD blob `054d974095be7425692860909181fafd54f97a33` 동일.

### 다음 작업
- **[B-5.3] sequence-grounded 데이터 계약**: 보호 handler 밖 endpoint/DB층에서 research opt-in `external_sequence_id`와 `external_turn_index`를 Experience에 저장하고 잘못된 순서·중복·stream 교차를 unit에서 fail-closed 검증한다.
- 후보 선택용 여러 train sequence와 완전히 별도의 preregistered held-out sequence를 확보한다. B5.2 후보는 held-out에서 frequency/random과 robustness gate를 이길 때만 다음 live production 검토 대상으로 삼는다.
- threshold 0.02, min observations 3, production predictor/scorer는 유지한다. B5.2 범위는 이후 사용자 push `5b74663`에 반영됐다.

---

## 2026-07-15 (Phase 3 [B-5.1] preregistered external outcome live pilot)

> 상세: `claudedocs/research/PHASE3_CURIOSITY_LOOP_2026-07-14.md`의 `[B-5.1]` 절.

### 완료 ✅ (외부 데이터 확보) / 승격 ❌ (graph가 frequency에 패배)
- **push 상태 재확인**: 시작 시 `DB_Renewal` local/remote HEAD가 사용자 push `7b4862e`로 일치하고 worktree clean이었다. B5 코드·테스트·문서가 이 커밋에 포함됨을 확인했다.
- **route 선택**: predictor 정의와 pre-frame snapshot이 없는 vision route 대신, 최소 요건을 직접 검증할 수 있는 다음 사용자 입력 route를 선택했다. 메시지는 live 결과를 보기 전에 고정하고 SHA-256 계약으로 기록했다.
- **same-turn 오염 차단**: 서버 env `CURIOSITY_EXTERNAL_OUTCOME_EVAL=1`과 request context `external_outcome_evaluation=true`가 모두 있을 때만 `external_deferred`가 활성화된다. 이 모드는 새 Experience에 cue/prediction snapshot만 저장하고 Concept/BrainRegion learning-progress, CuriosityLog, integration priority를 건드리지 않는다. 기본 production 경로는 기존 same-turn scoring을 유지한다.
- **v1 실시간 검토로 false pass 차단**: 최초 7-turn pilot은 겉보기에는 graph가 baseline을 이겼지만, handler stem `어떻`이 cue와 outcome에 남았고 실질 graph hit는 1개뿐이었다. `어떻게/어떻`을 일반 기능어로 제외하고 contaminated pair 제외, 최소 graph hit 3개, frequency를 이긴 pair 최소 3개 및 개선 pair>악화 pair의 robustness gate를 추가했다. 원본과 read-only 재평가 artifact는 실패 증거로 보존했다.
- **v2.1 사전등록·수집**: `하늘→날씨→도시→사람→이름→비비→개발자→프로그램` 연결을 담은 7개 문장을 고정했다. preflight는 6/6 scorable pair, 고유 preexisting outcome 7개, 각 source prediction 8개로 통과했다. 7/7 live turn이 `external_deferred` audit를 통과했고, 사전 cue Concept 9개의 curiosity state는 전후 동일했다.
- **최종 성능**: data gate `true`, contaminated `0`, graph mean error `0.833333` / hit `1`, frequency mean error `0.5` / hit `3`, random expected error `0.992315`. pairwise graph better/tie/worse=`0/4/2`; baseline gate와 robustness gate가 모두 `false`, verdict=`graph_did_not_beat_baselines`, `promotion_gate=false`.
- **쓰기 범위**: 두 live pilot이 총 14개 conversation Experience와 handler의 통상 Concept/관계를 Neo4j에 남겼다. 이를 삭제하지 않고 음성·감사 증거로 보존한다. evaluator와 재평가는 read-only이며, deferred layer는 curiosity state를 변경하지 않았다.
- **검증**: 저장 v2.1 artifact의 별도 read-only 재계산이 동일 수치를 재현했다. 전체 `pytest tests neural/test_neural.py -q`는 `58 passed`; py_compile, `pip check`, `git diff --check` 통과. FastAPI 종료 후 port 8000 listener 없음. `conversation_handler.py` current/HEAD blob 모두 `054d974095be7425692860909181fafd54f97a33`.

### 다음 작업
- **[B-5.2] predictor 진단을 offline에서 먼저 수행**: 현재 예측에 `문장`, `세상`, `말해줘` 같은 hub/general concept가 상위권을 차지하는 원인을 query/ranking 수준에서 분해한다.
- 저장된 external sequence에 대해 per-cue top-k, transition-aware ranking, generic/hub penalty 같은 최소 후보를 ablation하고, 같은 future-leak 없는 frequency/random baseline보다 반복적으로 좋아질 때만 다음 live pilot을 허용한다.
- threshold 0.02, min observations 3, production scorer는 유지한다. B5.1 범위는 이후 사용자 push `42268bf`에 반영됐다.

---

## 2026-07-15 (Phase 3 [B-5] valid external outcome offline evaluation)

> 상세: `claudedocs/research/PHASE3_CURIOSITY_LOOP_2026-07-14.md`의 `[B-5]` 절.

### 완료 ✅ (평가기 구현·데이터 gate 판정)
- **push 상태 재확인**: `DB_Renewal` local/remote HEAD가 사용자 push `2e9cafb`로 일치하고 시작 worktree clean. 이 커밋에 B3/B4 코드·테스트·문서가 포함됨을 diff로 확인했다.
- **B5 read-only evaluator 추가** (`scripts/research/b5_external_outcome_evaluation.py`): 보존 12 turn을 `서울/컴퓨터 초기/학습/컴퓨터 필터 후`의 4개 독립 시퀀스로 고정하고, 시퀀스 내부의 8개 `t→t+1` pair만 만든다. turn `t`의 저장된 graph prediction을 turn `t+1` 사용자 입력의 비-cue 의미 concept와 비교한다.
- **공정성·baseline**: speech-act와 반복 cue를 제외하고, source turn 시점에 이미 존재한 concept만 scorable로 분리한다. 과거 사용자 입력만 사용하는 frequency baseline과 같은 top-k 크기의 uniform random 기대오차를 함께 계산한다. 미래 Experience/Concept 누출을 막았다.
- **다음 사용자 입력 route 결과**: Experience 누락 `0`, pair `8`. 다음 문장은 모두 `서울/컴퓨터/학습` cue를 말투만 바꿔 반복했고, 이를 제외한 external outcome은 preexisting `0`, novel `0`, scorable pair `0/8`. 따라서 graph/frequency/random mean error는 모두 `null`; `data_gate=false`, `promotion_gate=false`, verdict=`insufficient_external_outcome_data`.
- **다음 센서 route coverage**: vision Experience `45`, observed concepts가 있는 vision `45`, NEXT_FRAME `36`. 그러나 `predicted_concept_ids` snapshot이 있는 vision Experience는 `0`이라 pre-frame prediction과 next-frame observation 비교가 아직 불가능하다.
- **판정**: B5는 모델 패배가 아니라 **valid external evaluation 데이터 부족**으로 종료한다. 같은-turn LLM outcome, canonical scorer, threshold 0.02, min observations 3, production scoring은 변경하지 않는다. 추가 Gemini/live 대화도 실행하지 않았고 Neo4j는 읽기만 했다.
- **검증**: B5 focused unit `11 passed`. 시퀀스 경계, parser/speech-act, cue 제외, concept 생성시각, B4 canonical match 재사용, future-leak 없는 frequency, random 기대값, sparse/pass gate 양쪽, sensor eligibility, Cypher read-only를 검사했다. 전체 suite와 보호 hash 검증은 세션 종료 전에 수행한다.

### 다음 작업
- **[B-5.1] 사용자 입력 route**: 최소 6개의 연속 pair와 최소 4개의 고유 비-cue external outcome이 생기도록, 같은 질문 반복이 아닌 다양한 후속 입력을 수집한다. 예: 현재 cue `컴퓨터` 다음에 사용자가 `로봇과 연결해서 설명해줘`처럼 새 외부 concept를 실제로 제공한다.
- **[B-5.1] 센서 route 대안**: vision Experience 학습 전에 prediction snapshot을 남기는 설계를 offline/unit에서 먼저 검증한 뒤, 다음 NEXT_FRAME의 관측 concept와 비교한다. 보호된 conversation handler와는 분리한다.
- 어느 route든 graph error가 frequency와 random baseline을 모두 이길 때만 production promotion을 재검토한다.

---

## 2026-07-14 (Phase 3 [B] 예측오차 루프 검증·라이브 배선 + 실 대화 운영 확인)

> 상세: `claudedocs/research/PHASE3_CURIOSITY_LOOP_2026-07-14.md`, auto-memory `program_roadmap`(Phase 3)·`db_migration_status`.

### 완료 ✅ (검증됨)
- **[B-4] canonical scoring offline/unit gate — production 연결 안 함** (`scripts/research/b4_canonical_scoring.py`, `tests/test_b4_canonical_scoring.py`): Unicode/case/공백, 보수적 한국어 조사, 길이 제한 `-하/-한`, cue-only 종결형을 분리했다. positive 변형은 허용하면서 `비비/비빔밥`, `형/형광등`, `컴퓨터/컴퓨터공학`, `카메/카메라`, `오디/오디오`, `은하/은한`, `북하/북한`은 불일치로 고정했다. 12 Experience read-only replay 결과 exact mean `1.0`, canonical mean `0.983333`, 개선 1/12(`신기한↔신기하`)뿐이라 **canonicalization-only 가설 기각**.
- **B4 pre-turn predictability 감사**: scored actual 53개 중 40개(75.5%)가 해당 Experience 이후 생성된 신규 Concept, 사전 존재는 13개였다. 신규를 제외해도 scorable 9턴 mean error `0.888889`, hit는 같은 1개뿐. 주원인은 형태가 아니라 **그래프 prediction을 입력받지 않은 LLM의 same-turn 자기생성 응답을 outcome으로 점수화한 target mismatch**다. production `compute_prediction_error()`는 변경하지 않았다.
- **[B-3] 12-turn 운영 표본 결론**: fresh `서울/컴퓨터/학습` 각 3턴(9턴)과 수정 후 `컴퓨터` 3턴을 실행했다. 전부 prediction error=`1.0`, learning progress=`0`, gate=`false`, CuriosityLog 없음. 이는 threshold 실패가 아니라 **graph prediction ID와 handler outcome ID의 표현 불일치**다. 마지막 3턴에서 예측 `신기한`이 다음 응답의 `신기하`와 의미상 같아도 ID가 달라 miss가 됐고, `컴퓨터요/컴퓨터라/컴퓨터에`도 분리됐다. 추가 표본·threshold 조정은 중단하고 [B-4] canonical scoring을 offline/unit부터 진행한다.
- **Gemini 응답 잘림 root cause 분리·복구** (`llm_client.py`, `pyproject.toml`): 동일 프롬프트 SDK A/B에서 구형·신형 모두 `MAX_TOKENS`; 신형 메타데이터로 512 예산 중 thinking 487, 실제 답변 21토큰임을 확인했다. SDK 자체가 원인이 아니었다. 다만 구형 `google-generativeai`는 지원 종료 상태라 공식 `google-genai>=1.10`을 의존성에 추가했다. 가변 `gemini-flash-latest`를 기존 단가와 일치하는 stable `gemini-2.5-flash-lite`로 고정하고 thinking budget 0을 명시했다. probe에서 `STOP`, thinking 0, 완전 응답 160토큰; 실제 후속 3턴도 잘림·메타 누출 없이 완전 응답이었다.
- **B3 cue/outcome 오염 차단** (`live_curiosity.py`, `neo4j_db.py`): `설명해줘/궁금해/무엇이` 등 speech-act terms는 cue에서 제외하되 input audit에는 보존한다. handler가 사용자 메시지까지 outcome Concept로 저장하므로, snapshot input terms와 일치하는 비-cue actual은 점수에서 제외하고 `curiosity_excluded_input_concept_ids`에 별도 기록한다. 실제 세 메시지 모두 cue=`컴퓨터`만 선택했고 각각 `무엇이/설명해줘/궁금해`가 score 제외 목록에 남았다.
- **B3 관측·도구**: Experience에 actual IDs, primary cue/EMA/observations, 전체 cue state JSON을 저장. read-only 후보 선택(`b3_curiosity_candidates.py`), endpoint-mirror snapshot(`b3_curiosity_snapshot.py`), auditable live pilot(`b3_curiosity_live_pilot.py`), SDK response metadata probe(`b3_gemini_sdk_probe.py`) 추가. 모든 live Experience는 삭제하지 않고 음성 증거로 보존했다.
- **Phase 3 [B] 예측오차 루프 첫 조각** (`scripts/research/curiosity_loop.py`): 합성 노이즈-지배 세계서 3정책(random/surprise/progress) 비교. **① learning-progress 호기심이 random보다 학습 가속**(AUC 0.752>0.733, 초반 뚜렷). **② raw surprise는 noisy-TV에 95% 갇힘**(파국). **결정적 설계규칙: 루프는 learning-progress(예측오차 감소율)로 닫아야 함, raw surprise 금지.** 이득 modest·regime 의존(균등환경선 이득 없었음=정직).
- **[B] 라이브 배선 완료** (`neural/baby/live_curiosity.py`, `neo4j_db.py`, `api_server.py`): 대화 handler 호출 전 알려진 cue의 그래프 연관개념을 snapshot하고, 호출 후 `Experience-[:INVOLVES]->Concept` 실제값과 비교. concept/BrainRegion별 error EMA와 learning-progress를 저장하고 **progress만** `integration_priority` 및 기존 `CuriosityLog` 큐에 연결(raw surprise는 관측값만). 최소 3관측+threshold 0.02 gate, deterministic CuriosityLog id로 동시/반복 중복 방지. `conversation_handler.py` v30 변경 없음.
- **검증**: `tests/test_live_curiosity.py` **7 passed**(순수 수학+endpoint prepare→handle→record 호출순서). 실제 Baby_Robotics에 rollback synthetic 노드로 error `1.0→0→0`, progress `0→0.4→0.24`, gate `false→false→true`, integration priority `0.546`, `source=learning_progress` 로그 생성 검증; 동일 타깃 2회 기록에도 로그 1개. synthetic 데이터 전부 삭제.
- **실 대화 운영검증**: push된 `DB_Renewal`의 local/remote HEAD가 `e46af26`으로 일치하고 worktree clean인 상태에서 FastAPI를 기동했다. 동일 실제 Gemini 대화 3턴에서 Experience error `1.0→0.667→0.5`, progress `0→0.133→0.147`, integration priority `0.748→0.801→0.807`, gate `false→false→true`를 관찰했고, 3턴째 `CuriosityLog(source=learning_progress)`가 생성되어 `/api/curiosity?limit=200&status=pending`에 노출됨을 확인했다.
- **초기 부분 통과 판정**: FastAPI→Gemini→Neo4j→learning-progress 호기심 경로는 실제로 닫혔다. 그러나 당시 `.env`의 Upstash Redis 호스트가 더 이상 해석되지 않아 publish/SSE는 guarded failure였다. 또한 단일 반복 문장만 검증했고 첫 질문이 `관계↔세상`으로 일반적이었다. `비비`는 handler stopword, `형의`는 1글자 어간 제한 때문에 identity cue가 되지 않은 것이 원인 후보다. threshold는 변경하지 않았다.
- **Redis v4 신규 구축·전체 이벤트 경로 복구**: `baby_ai_robot_v4`(Upstash Free, GCP Tokyo, TLS)의 새 `rediss://` URL을 `.env`에만 설정. 비밀값을 출력하지 않은 상태로 PING, 임시 키 SET/GET/DELETE, Pub/Sub 왕복 모두 통과. FastAPI `/health`=`healthy`, `/api/events` HTTP 200+`text/event-stream`, 시험 이벤트 payload 일치. 이어 실제 Gemini 대화 1회에서 Neo4j Experience 생성과 SSE `neuron_activation→baby_state→experience` 수신, Experience ID 일치까지 확인했다. 서버 로그 Redis 오류 0건. 테스트 키는 삭제하고 서버·임시 파일은 종료 시 정리.
- **[B-2] cue 품질 개선 완료** (`live_curiosity.py`, `api_server.py`, `neo4j_db.py`): handler의 concept 생성 규칙은 유지하면서 endpoint 전용 `build_curiosity_cue_terms()`로 `비비와→비비`, `형의→형`을 기존 Concept 정확일치 후보로 복원. 조사 제거 전 표면형(`형의`)은 후보에서 제외하고, 한 글자 cue는 explicit list에서만 허용해 broad substring 회귀를 차단했다. 추가로 기존 단일 Cypher 결과의 전역 LIMIT 때문에 고차수 `비비` 이웃만 남고 다른 cue가 사라지는 결함을 발견해, **cue 확정 쿼리와 고유 이웃 예측 쿼리를 분리**했다. strength 우선 상위 cue를 고른다.
- **[B-2] 검증**: handler 원출력 `형의,관계,문장,말해줘` → endpoint 후보 `비비,형,관계,문장,말해줘` → 라이브 Neo4j cue `비비,형,관계,말해줘`. 실제 Gemini 1턴 Experience에도 동일 cue 저장, `형의` 제외 확인. 첫 관측 error `1.0`, progress `0`, gate `false`는 설계 일치. 정규화/오탐/endpoint 실전달/다중-cue 보존을 포함해 `pytest tests neural/test_neural.py -q` **21 passed**, py_compile 통과. `conversation_handler.py` hash `054d974…` 무변경.
- **Neo4j 인스턴스 복구·데이터 무결성 확인**: 세션 내 "다운"은 Desktop 2.x 인스턴스 STOP이 원인(데이터 문제 X). Start 후 **991 Concept·비비 자아허브 181연결·NEXT_FRAME 등 온전** 확인. 뇌 시각화 경로 확립(`http://localhost:7474/browser/` + path 쿼리). db_migration_status에 운영 gotcha 기록.
- **Vercel/프론트 판단**: baby-dashboard는 로컬 백엔드(localhost:8000) 의존 → Vercel 클라우드 프론트가 접근 불가 → **Vercel 지금 불필요**, dev는 프론트 로컬 실행. 공개 데모 시점에만 (백엔드 터널 필요).

### 다음 작업
- **[B-1] 인프라 복구 ✅**: `baby_ai_robot_v4` 신규 생성, `.env` 갱신, Pub/Sub·`/api/events`·실 대화 SSE 재검증 완료.
- **[B-2] cue 품질 개선 ✅**: endpoint/DB 정확일치 정규화, 다중 cue 보존, 실제 1턴 검증 완료. `conversation_handler.py` v30 미변경.
- **[B-3] 운영 표본 확대 ✅**: 12 live turns로 cue/LLM 문제와 canonical-ID 문제를 분리했다.
- **[B-4] canonical concept scoring ✅ offline 판정 완료**: broad substring 오탐은 막았으나 개선 1/12로 production gate 실패. 배선하지 않음.
- **[B-5] valid external outcome**: same-turn 자기생성 응답 대신 다음 사용자 입력 또는 센서 관측을 outcome으로 삼는 prequential sequence를 offline/unit에서 먼저 비교한다. 통과 전 추가 live 호출·threshold 변경 금지.
- 대안: 살아있는 코어 실가동(`LOCAL_CORE_DISTILL=1`+서버) · Quest 다양장면 수집([A], 데이터 병목).

---

## 2026-07-13 (🔴 보안: secret 제거 + Gap#6 모니터링 상시화)

### 🔴 보안 조치 ✅ (GitHub push protection 계기)
- **원인**: `.env.bak-20260512`(Anthropic+OpenAI 실키)가 `.gitignore` `.env.bak*` 누락으로 커밋 `40ed387`에 딸려 들어감. push 시도 시 GitHub secret scanning 차단.
- **범위 확정(measure-first)**: secret은 **오직 unpushed 커밋 1개(`40ed387`)에만**. 초기 커밋은 `.env.example`(플레이스홀더)만 — **키는 원격 도달 이력 없음**.
- **조치**: `git rm --cached .env.bak-20260512` + `.gitignore` 보강(`.env.bak*`,`.env.*.bak`,`*.bak`) + `git commit --amend`로 tip 재작성(`40ed387`→`5cfe1a5`, unpushed라 안전, 나머지 29파일 보존).
- **검증**: push 범위=secret 없는 단일 커밋 `5cfe1a5` · `.env.bak` 미추적 · gitignore 차단 확인 · HEAD 트리 실키 패턴 0. **이제 push 통과.** (디스크의 .env.bak은 gitignore됨; 삭제/이동 권고. 키는 원격 미도달이라 로테이션은 선택.)

### 합성 스케일링 연구 ✅ (다음 연구 — 데이터 벽 우회)
> `scripts/research/{synth_world,scaling_study}.py`, `claudedocs/research/SCALING_STUDY_2026-07-13.md`.
- 데이터 밀도가 바인딩 제약(3회 확인)이라, 실제 45프레임 통계에 **캘리브레이션(~13% dev)한 합성 embodied world**로 스택 스케일 거동 규명. 기존 `run_arm`/`run_head` 재사용(합성 events 동일 포맷).
- **핵심 발견: RW 자기학습 우위 = 밀도 아니라 다양성 주도** — 다양성 축(N=2048): 단일장면 −0.5%→4장면 +3.7%→16 +4.7%→32 **+9.5%**. 밀도 축(scenes=8): N 256→4096서 6.8%→4.3% 완만 감소. 메커니즘: 장면↑→marginal과 다른 조건부 P(b\|a) 多→보정된 RW가 일반화로 빈도카운터 이김.
- Q2 학습코어(head)는 N≤4096 전부 그래프 못 이김 → **Phase2 로컬코어 시기상조 재확인**. Q3 움직임이 embodied 예측 약하게 도움.
- **→ 데이터 수집 스펙 변경**: "많은 프레임" 아닌 **"많은 다른 장면"**(`QUEST_APK_CONTRACT.md` 반영).

### Head-crossover probe ✅ (Q2 후속 — 결정적 반전)
> `scripts/research/head_crossover_probe.py`, `claudedocs/research/head_crossover_20260713.json`, SCALING_STUDY 문서 Q2 후속.
- 두 병목 해결로 대규모 재측정: **sampled-negative 랭킹**(O(K) 고정) + **degree-cap 그래프**(허브 O(V²) 회피, matched-capacity cap48 vs dim48). 4 arm 동일 스트림 paired, N≤48k.
- **결정적 반전**: 학습 파라미터 코어가 그래프를 **N≈2~4천서 역전**, 우위 단조증가(−0.8%→**+9.5%@48k**; head MRR 0.72→0.94 vs 그래프 0.86 정체 = 용량한계 그래프 vs 분산 임베딩 CLS 구도).
- **원인 = 항상성**: 초기 "코어 열위"(이 probe + `trainable_head_experiment` 모두)는 **임베딩 발산(overflow) 아티팩트**. norm-clip(=synaptic scaling) 넣으면 코어 이김(+2.4~5.8%, clip∈{2,4,8,16} robust), 빼면 짐(−0.8%) — **causal 확인**. = 리서치 mandate(homeostasis 필수) 실증.
- **함의**: **Phase 2 유망성 상향** — "그래프가 근본적으로 낫다"는 틀림(그건 항상성 없는 코어). 규모+다양성+weight-homeostasis면 코어가 이김. 단 크로스오버 N은 matched-capacity 규정·합성 데이터 의존 → 실 Quest 재확인 필요. Phase 2 착수 시 **weight-homeostasis day-1 필수**.

### Phase 2 Sleep-Distill 프로토타입 + adversarial 검증 ✅
> `scripts/research/sleep_distill{_prototype,_v2}.py`, `claudedocs/research/PHASE2_SLEEP_DISTILL_2026-07-13.md`, workflow wf_e658bb65.
- head_crossover 후속. CLS wake-sleep 축소검증: 그래프=해마(wake 흡수, 코어 frozen), 임베딩코어=신피질(sleep에 그래프 replay로만 학습). Phase 2 "가중치만으로 예측오차 하강 + CLS 안티망각" 주장 검증.
- **v1 4-claim workflow 적대검증**(6 ablation + 4 skeptic + synthesis): A 가중치-자기학습(그래프 frozen, held-out MRR 상승) **CONFIRMED**(고정 early_probe control로 확인 — 과대주장 차단); B replay>raw **REFUTED**(정상스트림선 online 우위, 3독립시드 2승); C 안티망각 **too-weak**(v1엔 망각 스트레서 없음); D no-collapse **REFUTED**(mean-norm은 clip으로 자명→effective rank 필요).
- **v2 순차태스크 안티망각**(v1 지적 반영): Task A→B 어휘 disjoint(분포이동), B학습 후 A-test 유지 측정 + frozen negative pool + stable rank + 다중시드. **결과: online 파국적 망각(−0.318) vs sleep_replay 유지(+0.034) vs sleep_off(구조없어 학습X)** = **CLS 안티망각 성립**(3시드, 분리폭 5×std).
- **화해**: replay 이점 = 정상 스트림선 무(B refuted 맞음), **비정상(평생학습)에서 결정적**(McClelland 1995 CLS 일치).
- **결론**: Phase 2 primitive(경험이 가중치 바꿔 예측오차↓) + CLS 안티망각 **둘 다 축소규모 실증**. caveat: stable rank≈2(collapse 감시), 합성데이터, 임베딩 대역(진짜 Phase2=로컬 LLM+LoRA). **weight-homeostasis(norm-clip) 필수** 재확인.

### Phase 2 실물화 — LLM+LoRA 코어 ✅ (장난감 임베딩 → 진짜 로컬 LLM)
> `scripts/research/llm_core_distill.py`, `claudedocs/research/llm_core_distill_20260713.json`, PHASE2_SLEEP_DISTILL 문서 "실물화".
- **환경**: RTX 4070 SUPER 12GB 확인 → `.venv`에 torch 2.6+cu124 · transformers 5.13 · peft 0.19 설치. Qwen2.5-0.5B fp16 = 1GB VRAM.
- **개념정리(사용자 Q "LLM+LoRA가 뭐고 API 대체?")**: 로컬 LLM+LoRA = **학습가능 신피질**(네 GPU, 가중치 네 것, 경험으로 바뀜) = **장난감 임베딩 코어의 실물화**. Gemini API = frozen **언어 입출력 도구**(다른 상자) → **대화 API 대체가 아니라 공존**. LoRA = 495M 통째 대신 어댑터 1.08M(0.22%)만 학습.
- **결과1 자기학습(실 LLM)**: "아기 방들" 실단어 co-occurrence를 LoRA sleep-distill → base link-MRR 0.176 → **0.382**(Δ+0.207, retrieval無, loss 9.95→2.62) = **진짜 LLM 가중치만으로 예측오차↓**.
- **결과2 안티망각**: online(replay無) Task-A 유지(Δ−0.01) = **파국망각 없음**. LoRA는 어댑터만+base frozen이라 **본질적으로 덜 잊음**(vs 장난감 코어 full-train −0.335). → **정직한 수정**: sleep-replay의 안티망각 역할이 실 LLM+LoRA선 **덜 절박**(프로토타입 시사보다 완화). 단 2태스크·소어휘 쉬움 → 재확인 필요.
- **다음**: 실 Neo4j co-occ(비비·엄마)로 재현 → 실 파이프라인(그래프 replay→야간 LoRA) 연결.

### Phase 2 실 데이터 검증 + 살아있는 코어 ✅ (연구 → 살아있는 시스템)
> `scripts/research/{llm_real_distill,sleep_distill_job}.py`, PHASE2_SLEEP_DISTILL 문서.
- **실 데이터 검증**: 합성 실단어(base 0.176=Qwen 이미 앎=사전지식 복구 의심)를 넘어 **실 Neo4j 그래프**(518c/2241e, 비비·엄마·형)로. **base Qwen 아기연상 거의 모름**(link-MRR 0.089~0.095, chance 4배). LoRA sleep-distill 후 **identity 쌍(Qwen 불가지) 0.081→0.176 평균(Δ+0.094≈2.2배, 3시드 견고, 전체 gain의 4배)** = **아기가 자기 정체성·관계를 가중치로 학습 = 실 데이터 자기학습 첫 실측**. 전체 magnitude modest(데이터 희소=병목).
- **살아있는 로컬 코어**: `sleep_distill_job.py` — LoRA 어댑터 디스크 **영속**(`models/local_core_adapter/`, gitignore) → 실행마다 이어학습 누적. **run1 0.089→0.123, run2 학습전 0.123(=run1 학습후 정확일치=기억유지)→0.152.** MRR 야간마다 성장 = **아기 뇌가 매일 밤 조금씩 자람.** 성장 시계열 `claudedocs/monitoring/local_core_growth.jsonl`.
- **⇒ 자기학습 체인 end-to-end 검증 완료**(Phase 1 가소성 → Phase 2 코어 → 실 데이터 특이연상 학습 → 영속 누적). 유일 병목=데이터 밀도.

### Phase 2 (B) 라이브 트리거 연결 ✅ (코어가 밤마다 자동 성장)
> `scripts/research/sleep_distill_job.py` (`--daily-gate`) + `neural/baby/api_server.py` `_spawn_local_core_distill()`. PHASE2_SLEEP_DISTILL 문서 "(B)".
- **consolidate(수면) 훅**: `/api/memory/consolidate`(full) 종료 시 job을 detached 서브프로세스로 spawn = 브레인이 잘 때 코어 자동 통합·성장.
- **안전(무거운 GPU 학습이라 우선)**: **하루 1회 게이팅**(마커 파일)+**원자적 락**(O_EXCL)+**stale-lock TTL 2h**(hard-kill 대비 영구잔존 방지). Neo4j 다운 시 **traceback 없이 clean skip(exit 0)+마커 미기록**(재시도). 성공 시만 "오늘 완료" 마킹. 훅 **기본 OFF**(env `LOCAL_CORE_DISTILL=1` opt-in). 비차단 Popen·실패 격리(consolidate 영향 0).
- **adversarial review**(workflow wf_42f17ed5, 4 dim). default-OFF 안전 확정 + **enable-path 결함 3개 발견→수정**: (1) OOM 미처리(traceback DEVNULL로 숨음)→GPU 학습 try/except+VRAM 프리플라이트로 clean skip. (2) 실패 시 retry-storm(마커 미기록→매 consolidate 재시도)→`.last_attempt` + 30분 backoff. (3) 락이 `--daily-gate`만 보호(수동 실행 충돌→어댑터 손상)→**락 무조건 획득**+release 가드. **테스트 통과**: 같은날 즉시 skip(4.9s)·Neo4j다운 clean exit0·backoff skip(9s<1800)·누적성장 0.089→0.123→0.152·락 정상해제.
- **켜기**: `LOCAL_CORE_DISTILL=1 python -m neural.baby.api_server` (+Neo4j 상시) or `schtasks` 야간. **⇒ 살아있는 로컬 코어 라이브화 완료. 유일 병목=데이터 밀도(Quest 다양장면 수집, 하드웨어).**

### Gap#6 brain health 모니터링 상시화 ✅
> `scripts/monitoring/brain_health_monitor.py` + `README.md`. RESEARCH_SYNTHESIS §3 gap#6.
- **4 지표 시계열**(`claudedocs/monitoring/brain_health.jsonl`, append): ① prediction(link-pred lift/MRR) ② collapse(degree Gini·가중치 엔트로피·고립률·최대허브) ③ forgetting(고정 probe 30 recall@10 vs baseline) ④ plasticity(synthetic 연상 주입→회상→rollback, 비파괴). 임계 breach 시 🔴 alert.
- **baseline(2026-07-12)**: 840 concept(518 connected)/2085 edge, lift 7.86, isolated 0.383, gini 0.65, W-entropy 0.867, forgetting recall 0.70, plasticity ✅ → 🟢 전부 정상. 결정론적, 추세(Δ) 표시.
- **상시화 = consolidate(수면) 훅**: `/api/memory/consolidate`(full) 종료 시 `_spawn_health_monitor()`가 모니터를 detached 백그라운드 실행(비차단·guarded). Neo4j 확실히 켜진 시점 + 생물학적 적절. (수동/야간 schtasks는 README.)
- `api_server.py` py_compile OK, 비파괴(consolidate 실패에 영향 없음).

---

## 2026-07-12 (Phase 1 가소성 실험 — 자기학습 신호 발견 + 프런티어 리서치 종합)

> 상세: `claudedocs/baseline/PHASE1_PLASTICITY_FINDINGS.md`, `RESEARCH_SYNTHESIS_2026-07-12.md`.
> Claude auto-memory: `phase1_plasticity_result_2026-07`(정정본), `program_roadmap_2026-07`(Phase 1 갱신).

### 완료 ✅ (검증됨)
- **프런티어 리서치 6각 fan-out + 종합** (dynamic workflow, 652K tokens, citation 교차검증): STDP-on-graph, 항상성, 예측오차 게이팅, eval 방법론, 로컬코어 sleep-distill, gap 분석 → `claudedocs/baseline/RESEARCH_SYNTHESIS_2026-07-12.md`.
- **Phase 1 가소성 3-실험 (LLM-free, `scripts/baseline/`)**:
  1. `plasticity_experiment.py` (정적 랜덤분할, 동일후보 채점·20-fold CV·paired): 순진한 가소성(STDP/항상성/양성전용 PE게이팅) 전부 가산빈도 baseline(lift 5.34) **못 이김** — 정적지표가 빈도 보상.
  2. `prequential_experiment.py` (test-then-train + EdgeBank baseline + ECE + time-shuffle 반증): **Rescorla-Wagner 음성증거 규칙**(w_ab→P(b|a) 보정)이 빈도(0.494)·암기(0.426)를 **유의·강건**하게 이김(MRR **0.510**, paired 484/282 p≈0, 다중시드 최악도 초과), ECE 0.038, 우위는 **time-shuffle서 붕괴=진짜 시간적 학습**. → **Phase 1 자기학습 신호 성립.**
  3. `trainable_head_experiment.py` (학습가능 임베딩 head, 온라인 SGD, gap#1 리허설): MRR 0.415 < 규칙, 곡선기울기 음수 → **518노드 규모선 파라미터 코어가 스칼라 못 이김**(리서치 scale caveat 실증).
- **정정**: 초기 "가설 반증"은 틀린 지표(정적)×틀린 규칙(양성전용) 탓 → measure-first + 리서치 교차검증으로 정정. RW 음성증거가 정답 메커니즘.

### 함의 (로드맵 실증 재정렬)
- Phase 1 죽은 길 아님(RW=싸고 진짜, 보정 w_ab=Phase2 예측오차 신호원). 효과 완만(+3.5%).
- **순서 재정렬**: 학습코어(Phase 2)는 현 규모서 손해 → **밀도(Phase 4 embodiment) 먼저/병행 → 그 다음 로컬 코어.**
- **비가역 보류(사용자 확인 후)**: 방향성 엣지 마이그레이션(RELATES_TO 무향→w_fwd/w_bwd, ~4170엣지) + RW 프로덕션 반영. 라이브 그래프·프로덕션 규칙 미변경(오프라인 검증만).

### 산출물
- `scripts/baseline/{plasticity,prequential,trainable_head}_experiment.py` (재사용 A/B 하니스)
- `claudedocs/baseline/{PHASE1_PLASTICITY_FINDINGS,RESEARCH_SYNTHESIS_2026-07-12}.md` + `{plasticity,prequential,trainable}_*_20260712.json`

### 완료 ✅ (오후: Phase 4 embodiment 파이프라인 착수·준비완료)
> 상세: `claudedocs/baseline/EMBODIMENT_PIPELINE_2026-07-12.md`, `docs/QUEST_APK_CONTRACT.md`, auto-memory `embodiment_pipeline_2026-07`.
- **승격 근거**: 3-실험(언어/학습head/embodiment) 전부 "데이터 밀도+다양성+움직임=바인딩 제약" 실증 → **Phase 4를 Phase 2 앞으로 승격**.
- **measure-first**: `quest-concepts`(A4.3) 엔드포인트 이미 작동·올바름. 45 vision 프레임(밀집 5.4객체/프레임, <10s 시퀀스), pose/depth 0, 2026-05-12 이후 스트리밍 없음(제약=수량).
- **`scripts/baseline/embodied_prediction.py`**: embodied next-frame 예측(북극성 지표). 정적 데스크 장면서 graph_spread가 **popularity baseline 못 이김**(R@10_new 0.51 vs 0.55) → 정적·무동작이라 구조 예측 여지 없음 = **pose/depth(움직임) 필요성의 증거 기반 정당화**.
- **파이프라인 확장(비파괴·검증)**: `api_server.py` quest-concepts에 `head_pose`/`depth_bins` 선택캡처(하위호환) + `neo4j_db.link_vision_frame_sequence`로 `(:Experience)-[:NEXT_FRAME {dt_sec,pose_delta}]->` 시퀀스 링크(synthetic 프레임 Cypher end-to-end 검증) + `scripts/maintenance/backfill_frame_sequence.py`(멱등·`--rollback`)로 기존 45프레임→**36 NEXT_FRAME 엣지·9시퀀스** backfill. 두 파일 py_compile OK.
- **막힘(사용자·기기)**: Quest 프레임 생성=하드웨어-인-더-루프. APK가 head_pose/depth 전송(`docs/QUEST_APK_CONTRACT.md`)+다양한 장면 대량 세션 수집 필요. 수집 후 `embodied_prediction.py` 재측정=embodied 자기학습 신호 판정.
- 라이브 그래프 비파괴(신규 엣지·선택속성만), conversation_handler·프로덕션 규칙 미변경.

---

## 2026-07-11 (Identity/Access-Control + LLM 복구 + 자기학습 프로그램 로드맵)

> 전략·로드맵 상세는 Claude auto-memory: `program_roadmap_2026-07`(최상위), `self_learning_architecture_2026-07`(북극성), `beyond_api_llm_strategy_2026-07`, `identity_access_control_2026-07`.

### 완료 ✅ (검증됨)
- **decay_connections 버그 수정** (`neural/baby/neo4j_db.py:1240`): 이전 `cutoff=_now_iso()`+`last_accessed IS NULL`이 매 consolidate마다 미접근 Experience 전체를 감쇠 → `coalesce(last_accessed, created_at) < now-stale_days(14)`로 선택적 감쇠. synthetic node proof로 **런타임 검증**(fresh Experience: OLD=감쇠 / NEW=보호). `timedelta` import.
- **before baseline**: `scripts/baseline/measure_baseline.py --tag before_research_20260710` → `claudedocs/baseline/`. 개념 978, RELATES_TO 1793, 고립 **48.4%**, power-law α **1.15**, modularity Q **0.434**.
- **Identity & Access-Control** (`docs/IDENTITY_ACCESS_CONTROL.md` 신규):
  - STEP1-2: `:Person{owner_pjh, 박재현, role:owner}` 허브 + 별칭 4개(개발자/사용자/형/엄마) `ALIAS_OF` + UserModel(mom/brother) `IDENTIFIED_BY`. `scripts/maintenance/seed_owner_identity.py`(idempotent·비파괴·`--rollback`·dry-run). **mom/brother=테스트 페르소나 확정**.
  - STEP0+4: owner token(`.env OWNER_SECRET`) + **owner 사칭 차단**(endpoint에서 owner speaker_id인데 토큰 없으면 guest 강등, `hmac.compare_digest` 상수시간) + `resolve_speaker_clearance`/`access_tier` 필터(`get_user_context`). **conversation_handler v30 0 수정** — endpoint+db층만. 사칭→guest 로그 + 직접호출 검증.
- **brain LLM 복구**: `gemini-2.0-flash`(404 deprecated)로 브레인 mute였음 → `gemini-flash-latest`(별칭, version-deprecation 재발 방지) `llm_client.py` 3곳. 실 대화 응답 확인.
- **Phase 1 자기학습 계측 착수**: `scripts/baseline/measure_prediction.py` 신규(PPR spreading-activation link-prediction, held-out 엣지). baseline `before_plasticity`: 무작위 대비 예측 lift **7.86×**(MRR 0.156, hit@10 42%, mean_rank 31/487) = "그래프가 실제로 더 잘 예측하게 되는가(=자기학습)"를 재는 척도 확보. 가소성 규칙 개선 전/후 이 값을 비교. + 자기학습 프런티어 서베이는 Bandi 볼트(`강화학습/`)에 저장.

### 변경 파일
- `neural/baby/neo4j_db.py` (decay 수정 · `resolve_speaker_clearance` · `get_user_context` 필터)
- `neural/baby/api_server.py` (owner token 인식/사칭차단 · `import os,hmac`)
- `neural/baby/llm_client.py` (모델 → gemini-flash-latest)
- `.env` (OWNER_SECRET), `scripts/maintenance/seed_owner_identity.py`(신규), `docs/IDENTITY_ACCESS_CONTROL.md`(신규)

### 결정 / 방향
- **"API 탈피 = 자기학습 전환"은 같은 한 수** (frozen API→로컬 trainable 코어). 진짜 자기학습=경험이 코어 파라미터를 바꿈; 현 frozen-LLM+graph는 자기학습 아님(Voyager 천장).
- **최상위 프로그램 로드맵 수립**: 자기성장 아기 뇌 Phase 0~5, **장기 ~1.5~3년**, 마일스톤=예측오차 곡선 하강.
- **다음 진입점: Phase 1** — 진짜 가소성 규칙(STDP+감쇠+항상성+PE게이팅) + 예측오차 계측(LLM-free).

### ⚠️ 미해결
- LLM 톤 변화(신형 flash, 영어·감정값 노출) · OpenAI fallback quota 429 · `last_accessed` 속성 전 Experience 부재(reinforce_memory 미반영 의심) · degraded no-LLM fallback 미구현.

---

## 2026-04-27 (Phase A4.5C — 파서 개선: 공접 + be-copula)

### 핵심 성과 ✅

`concept_binding.py::extract_color_bindings()` 에 두 규칙 추가:
- **공접**: `COLOR1 + "and" + COLOR2 + NOUN` → COLOR1도 NOUN 수식 (예: "blue and gray keys" → blue→keys, gray→keys)
- **be-copula**: `NOUN + (is|are|was|were) + COLOR` → COLOR가 NOUN 수식 (예: "The keyboard is white" → white→keyboard)

### offline 검증 (36 quest_passthrough Experience 재실행)

| 지표 | A4.4 | A4.5C | 변화 |
|---|---|---|---|
| Total pair instances | 35 | **40** | +5 |
| Unique pair types | 13 | **15** | +2 |
| Strict precision | 94.1% | **~95%** | ↑ |
| Recall (추정) | ~86% | **~97.5%** | **+11%p** |

신규 진짜 binding:
- `blue → keys` (exp #4, 공접 규칙)
- `white → keyboard` × 4건 (exp #23/25/27/30, be-copula)

미해결 케이스 1건 (`white → square` FP, exp #29) — POS tagger 도입 없이 해결 불가, MVP 수용.

### Smoke test 검증 (3 POST)

1. **인접**: `"A yellow bottle on the desk."` → yellow→bottle reinforced ✅
2. **공접**: `"white keys and blue and gray keys"` → 3 binding (white/blue/gray → keys), blue+gray 신규 ✅
3. **be-copula**: `"The keyboard is white"` → white→keyboard 신규 ✅

### 변경 파일

- `neural/baby/concept_binding.py::extract_color_bindings()` — 규칙 2 (공접), 규칙 3 (be-copula) 추가, 헬퍼 `_is_valid_object()` 도입

### DB 최종 상태

describes_color 관계 **6개**:
- yellow → bottle (str=0.60, obs=3)
- white → keys (str=0.55, obs=2)
- yellow → liquid (str=0.55, obs=2)
- **white → keyboard (str=0.50, obs=1)** ← be-copula 신규
- **blue → keys (str=0.50, obs=1)** ← 공접 신규
- **gray → keys (str=0.50, obs=1)** ← 공접 신규

### 의도적 보수 (MVP 범위 밖)

- 3단 공접 `red, blue, and green keys` (현재 데이터 0건)
- 형용사 + COLOR `big and yellow ball` (POS tagger 필요)
- 거리-2 binding `bottle of yellow liquid` 의 bottle 추정 (의도적 — VLM 의도 따라 yellow→liquid 만 잡음)
- 문장 분할 (`split('.')`) — 현재 데이터에서 cross-sentence 오류 0건

### 관련 메모리

- `memory/a4.5c_parser_extension.md` (신규)

---

## 2026-04-27 (Phase A4.5α — Hebbian / describes 관계 격리)

### 핵심 성과 ✅

`hebbian_update()` 의 MERGE 패턴에 ``{source: 'hebbian'}`` 속성을 추가하여 다른 의미 관계 (특히 A4.4 의 ``describes_color``) 와의 충돌 위험을 제거. 같은 concept 쌍에 Hebbian 관계와 describes 관계가 별도로 병존 가능.

### 발견 경위 (controlled experiment)

A4.5 우선순위 분석 단계에서 `decay_connections()` 와 `hebbian_update()` 가 A4.4 의 새 binding 관계와 어떻게 상호작용하는지 점검. **decay 는 정상**. 하지만 Hebbian 의 속성 없는 MERGE 가 다음 동작을 보임 (실측):

- 시뮬: `(yellow)-[:RELATES_TO {relation_type:'describes_color'}]->(bottle)` 존재 시
- `MERGE (a)-[r:RELATES_TO]->(b)` 실행
- → 기존 describes_color 관계가 **매치되어** ON MATCH 발동
- → describes_color 관계의 `strength` 가 +0.05 더 증가 (의도 외)
- → describes_color 관계에 `source='hebbian'`, `hebb_strength` 속성이 **덮어씌워짐**
- → 하나의 관계가 "describes 와 Hebbian 둘 다" 라고 주장하는 모순 상태

현재 DB 에는 충돌 0건 (Quest 경로 concept 과 대화 Hebbian 호출 pair 가 우연히 겹치지 않음) 이지만 잠재 폭탄.

### 변경 (1 라인 효과)

`neural/baby/neo4j_db.py` 의 `hebbian_update()`:

```diff
- MERGE (a)-[r:RELATES_TO]->(b)
- ON CREATE SET r.strength = $delta, r.hebb_strength = $delta,
-   r.source = 'hebbian', r.created_at = $now
+ MERGE (a)-[r:RELATES_TO {source: 'hebbian'}]->(b)
+ ON CREATE SET r.strength = $delta, r.hebb_strength = $delta,
+   r.created_at = $now
```

`r.source = 'hebbian'` 의 ON CREATE SET 은 제거 (MERGE 패턴에 이미 포함되어 자동 부여). 멱등성 유지.

### 검증

**Controlled experiment (재수행)**:
- Before: `yellow→bottle` 사이 describes_color 1개 (str=0.55)
- `hebbian_update([(yellow_id, bottle_id)])` 호출
- After: 2개 관계 병존:
  - describes_color: **str=0.55 보존** ✅ (변경 없음)
  - hebbian (rt=NULL, src='hebbian'): str=0.05 신규 ✅
- 격리 성공 — 한 쌍에 의미가 다른 두 관계가 별도 존재

**회귀 테스트**:
- 기존 Hebbian 관계 1087개 중 임의 선택 → `hebbian_update` 재호출
- ON MATCH 정상 발동: strength 0.02 → 0.07 (delta=0.05)
- canonical ordering (min,max) 정상 작동
- **기존 데이터 100% 호환**

### 부가 검증

- `decay_connections()` 는 `MATCH ()-[r:RELATES_TO]->()` 로 모든 RELATES_TO 대상 → describes_color 도 자동 감쇠 ✅
- decay 와 ON MATCH 강화는 Hebbian-style balance 형성 — 반복 관찰되는 binding 만 생존, 일회성은 소멸 (인간 기억 메커니즘과 일치)

### 변경 파일

- `neural/baby/neo4j_db.py` `hebbian_update()` — MERGE 패턴 수정 + 격리 의도 docstring 추가

### 부작용 / 주의

- **frontend 시각화**: 같은 concept 쌍에 Hebbian + describes 두 관계가 보임. 이미 다른 pair 에 multi-edge 존재하므로 (예: AI→사람 6개) 새 행동 아님.
- **spreading activation**: 같은 쌍을 두 번 traverse 가능. 잠재 over-activation. A4.5+ 에서 distinct 처리 검토 필요.
- 기존 describes_color 관계 3개 (yellow→bottle, yellow→liquid, white→keys) **변경 없음**.

---

## 2026-04-24 (Phase A4.4 — Color→Object Descriptor Binding)

### 핵심 성과 ✅

VLM 응답의 "yellow bottle" 같은 색상-객체 인접 패턴을 파싱하여 Neo4j에 `(yellow)-[:RELATES_TO {relation_type:"describes_color"}]->(bottle)` 관계로 저장. Baby AI가 색상과 객체를 분리된 개념으로 유지하면서도 **binding 관계로 연결**하는 뇌과학적 표상(V4 vs IT) 구조 확립.

### 설계 결정 — offline 검증 기반

A4.3에서 누적된 36개 quest_passthrough Experience의 `vlm_response`를 파서로 재처리하여 **구현 전 precision 측정**:
- 34 candidate pair, 12 unique
- Strict precision **94.1%** (32/34), recall ≈ 86%
- FP 1건(`white→square`) — decay로 자연 정리 수용

**제1원칙 정합성 검토**: 색상 concept을 삭제(필터링)하지 않고 **관계로 분리**. V4(색상) ⟷ IT(객체) 분리 표상 + binding problem (Treisman) 해결 방식과 일치.

### 채택한 구조

- **저장 위치**: 기존 `RELATES_TO` 라벨 재사용 + `relation_type="describes_<aspect>"` 속성
- **aspect 필드**: 미래 material/size/shape 확장 준비
- **방향성**: descriptor → object (형용사가 명사를 수식하는 feedforward)
- **ON CREATE/MATCH**: strength 0.5→cap 1.0 (Hebbian-style), evidence_count++, sources 배열 멱등 추가
- frontend 시각화(`/api/brain/concept-relations`)에 자동 포함 — 관찰 가능성 확보

### 변경 파일 (3개)

**PC 측**:
- `neural/baby/concept_binding.py` **신규** (86 LoC) — COLOR 셋(19) + stopword 셋 + `extract_color_bindings(text)` 순수 함수. DB 의존 0, 대화 경로 재사용 가능.
- `neural/baby/neo4j_db.py` — `link_descriptor_to_object()` 메서드 추가 (+70 LoC). RELATES_TO 멱등 MERGE + 방향성 보존 + sources/observation_count/evidence_count 관리.
- `neural/baby/api_server.py` — `post_quest_concepts` 에 2e) 블록 삽입: 파서 호출 → name_to_id 맵 lookup → `link_descriptor_to_object` 호출. `QuestConceptsResponse`에 `bindings_created/reinforced/skipped` 3 필드 추가.

### 검증 (3 POST smoke test)

| POST | 문장 | 결과 |
|---|---|---|
| #1 | "yellow bottle of yellow liquid" | bindings_created=**2** (yellow→bottle, yellow→liquid) |
| #2 | 동일 문장 재시도 | bindings_reinforced=**2**, strength 0.50→0.55, evidence 1→2 ✅ |
| #3 | "white keys and touchpad" | bindings_created=**1** (white→keys) ✅ |

최종 DB 상태: describes_color 관계 3개 (yellow→bottle, yellow→liquid, white→keys). Concept 오염 없음 (969→969). smoke_test source 태그는 Cypher로 정리.

### 파서 규칙 (MVP)

1. COLOR (19종) 토큰 뒤 바로 다음 단어가
2. STOPWORDS_AFTER_COLOR 아니고
3. COLOR 아니고
4. 길이 2+ (acronym `hp` 허용 — A4.3 대비 완화)
이면 `(color, noun, "color")` pair 생성.

**다층 방어**: Kotlin ConceptExtractor 길이 3+ 필터가 payload 단계에서 `hp` 같은 acronym을 차단 → Python 파서가 `white→hp` 후보를 뽑아도 `name_to_id` 맵에 없어 자동 skip. 실질 DB 오염률 FP 2.9%.

### 범위 밖 (A4.5 이후)

- be-copula 구조 (`"keyboard is white"`)
- 공접 처리 (`"blue and gray keys"` — blue 누락)
- material/size/shape 확장 (aspect 필드는 준비됨)
- POS tagger 도입 (연속 형용사 구분 — `white square keys` FP 해결)
- 사용자 ground truth 정정 기능 (VLM 환각 보정, 예: "yellow liquid"는 실제 고체)

### 주의

- 현 VLM(SmolVLM-500M)이 실제 고체(비타민 통)를 "liquid"로 환각 — Baby AI는 VLM 출력 그대로 학습 (철학적 일관성). ground truth 정정은 A4.5+.
- Kotlin ConceptExtractor 길이 필터를 2로 완화할 경우 FP 방어 재평가 필요.

### 관련 메모리

- `memory/a4.4_completed.md` **신규** — 검증 Cypher + 파서 규칙 + smoke test 결과
- `memory/a4.3_completed.md` — baseline (36 exp 실측, 969 concept)

---

## 2026-04-24 (Phase A4.3 — Quest → PC FastAPI → Neo4j E2E)

### 핵심 성과 ✅

Quest 3S APK가 SmolVLM-500M 추론 후 추출한 Concept을 PC FastAPI로 POST → Neo4j에 저장하는 전체 파이프라인이 1+5 rounds E2E로 검증 완료.

**Concept 909 → 925 (+16 신규), Experience 3062 → 3068 (+6 quest_passthrough)**

### 변경 파일

**PC 측** (`neural/baby/api_server.py`):
- 추가: Pydantic 모델 `QuestImageMeta`, `QuestConceptsRequest`, `QuestConceptsResponse`
- 추가: `POST /api/vision/quest-concepts` endpoint
  - `insert_experience(task_type="vision", tags=["quest_passthrough","vision"], extras={...})`
  - `insert_concept(category="visual")` 루프 — 자동으로 occipital region 매핑
  - 후처리 Cypher: `c.sources` 배열 (멱등 추가), `c.quest_observation_count++`, `c.last_quest_seen`
  - `link_experience_concept` (INVOLVES, confidence=0.5)
- emotional_salience=0.4 (수동 관찰 — 대화 0.5~0.6보다 낮음)

**Quest 측** (`quest-passthrough-test/`):
- `app/src/main/AndroidManifest.xml`: `INTERNET`, `ACCESS_NETWORK_STATE` 권한 + `usesCleartextTraffic="true"`
- `app/src/main/java/com/babyai/passthroughtest/QuestUploader.kt` 신규 — HttpURLConnection + org.json (의존성 0)
- `app/src/main/java/com/babyai/passthroughtest/MainActivity.kt`: `pc_url` intent extra + 캡처 메타 추적 + POST 호출

### 핸드오프 계획 → 실제 구현 정정

| 계획 (2026-04-20) | 실제 (2026-04-24) | 사유 |
|---|---|---|
| `upsert_vision_concept()` 신규 메서드 | 추가 안 함, `insert_concept(category="visual")` 재사용 | 기존 메서드가 MERGE+멱등+region mapping 모두 수행 |
| `source` (단수) | `c.sources` (배열) | 같은 Concept이 대화+Quest 양쪽 출처 가능 |
| OkHttp 의존성 | HttpURLConnection 표준 라이브러리 | APK 크기 최소화 |
| 별도 라벨 `:VisionConcept` | 통합 `:Concept` + `c.sources` 필드 (대안 B 채택) | 사용자 결정 — Baby AI 통합 학습 |

### E2E 결과 (5 rounds)

성능: avg 5509ms (min 4525, max 5831, std 493), 배터리 100%→96% (4% drop), 온도 35°C 무변동

누적 학습 (같은 책상+컴퓨터 장면):
- R1: 10 신규
- R2: 0 신규 + 4 매치
- R3: 0 신규 + 5 매치
- R4: 2 신규 + 2 매치
- R5: 0 신규 + 4 매치

가장 많이 본: computer (qcnt 6), monitor (5), text (4), keyboard (3), webpage (3)
모든 Quest concept이 `:MAPPED_TO occipital` (해부학적으로 정확)

### 핵심 결정 — adb reverse over USB

학교망 `sgwlan_secure` (WPA2-Enterprise EAP)에서 Quest 인증 실패 반복 → EAP 디버깅 비효율.

**해결**: `adb reverse tcp:8000 tcp:8000` → Quest는 `http://127.0.0.1:8000` 호출 → USB 터널로 PC localhost 도달.

장점: Wi-Fi/방화벽/NAT 모두 우회. PC 방화벽 인바운드 설정 불필요. 가장 안정.
한계: USB 케이블 길이 한계 (이동 학습은 A4.4 이후 핫스팟 또는 EAP 인증서 필요)

### 검증된 사실 / 새 함정

- `usesCleartextTraffic="true"` 필수 (Android 14 기본 차단)
- APK 재설치 후 권한 재부여 필수 (`pm grant ... CAMERA`, `pm grant ... HEADSET_CAMERA`)
- `usage_count`는 신규 시 0 초기화, ON MATCH에서만 증가 (qcnt 6 / ucnt 5는 정상)
- FastAPI `extras`는 `json.dumps`로 직렬화 — 조회 시 deserialize 필요

### 관련 메모리

- `memory/a4.3_completed.md` — 운영 명령 + 검증 Cypher (재현용)
- `memory/dev_patterns.md` — adb reverse 황금 패턴, 권한 재부여 함정
- `memory/passthrough_api_research.md` — A4.0~A4.3 연속 일지

---

## 2026-03-23~24 (Phase C2 + Step 3 PendingQuestion)

### Phase C2: Hebbian Learning 구현 ✅

**핵심**: 함께 활성화된 개념 쌍의 RELATES_TO 관계를 강화/생성하는 Hebbian 학습

**변경 파일**:
- [x] `neural/baby/neo4j_db.py` — `hebbian_update()`, `get_hebb_stats()` 추가
  - UNWIND pairs, strength + hebb_strength 동시 갱신 (cap 1.0)
  - canonical ordering (min,max)으로 방향성 중복 방지
- [x] `neural/baby/conversation_handler.py` — Step 5.6 Hebbian 블록 삽입
  - 직접 공출현(delta=0.05) + 간접 공활성화(delta=0.02)
  - `activations = []` 초기화 추가 (try 블록 밖 안전 처리)
- [x] `neural/baby/api_server.py` — `GET /api/brain/hebb-stats` 엔드포인트

**설계 결정**: `strength` + `hebb_strength` 둘 다 갱신
- spreading activation에 즉시 반영 (strength)
- Hebbian 기여분 감사 추적 (hebb_strength)
- decay_connections()와 자연스럽게 경쟁 (강화 vs 망각)

### Step 3: PendingQuestion Neo4j 노드 + API ✅

**핵심**: CuriosityLog와 구조적으로 다른 PendingQuestion 노드 신규 생성

**변경 파일**:
- [x] `neural/baby/neo4j_db.py` — 4개 메서드 (insert/get/update/answer)
  - `(:CuriosityLog)-[:GENERATED]->(:PendingQuestion)` 관계 지원
- [x] `neural/baby/api_server.py` — 4개 엔드포인트 + Pydantic 모델
  - `publish_pending_question()` 활성화 (기존 미사용 → 호출 연결)
  - GET/POST /api/pending-questions, PATCH /{id}, POST /{id}/answer

**호출 지점 검증**: 6개 새 메서드 모두 엔드포인트에서 호출 확인 ✅

### Vision Neo4j 마이그레이션 — substrate.py 의존 제거 ✅

**핵심**: api_server.py에서 substrate.py(Supabase) 의존 완전 제거

**변경**:
- [x] `POST /api/vision/process` → Gemini Vision API 직접 호출 + Neo4j Experience 저장
- [x] `GET /api/vision/stats` → Neo4j Experience(task_type='vision') 카운트
- [x] `POST /api/process` → conversation_handler.handle_conversation() 위임
- [x] substrate.py import 0건 확인 (grep 검증 완료)

**검증**: `python -c "from neural.baby.api_server import app"` → Import OK, 46 endpoints

### Phase D1: 내적 시뮬레이션 ✅ + Phase D2: 감정 기반 주의 ✅

**D2 변경**:
- [x] `neural/baby/neo4j_db.py` — `get_spreading_activation()` depth 하드코딩 버그 수정
  - `*1..2` → `*1..{safe_depth}` (f-string, 1~5 범위 제한)
- [x] `neural/baby/conversation_handler.py` — `_get_attention_params()` 함수 추가
  - 호기심 > 0.7 → depth=3, limit=30 / 두려움 > 0.5 → depth=1, limit=10
  - Step 5.5에서 감정 기반 동적 spreading activation 파라미터 사용

**D1 변경**:
- [x] `neural/baby/conversation_handler.py` — Step 5.7 내적 시뮬레이션
  - stage >= 3 + activations >= 3 + 30% 확률 게이트
  - 상위 2개 활성화 개념으로 "만약 X와 Y가 연결된다면?" 자동 Prediction 생성
  - prediction_type="hypothetical", based_on_concepts 포함

### Phase D3: 발달 자동 전이 ✅

**핵심**: 대화 파이프라인 내에서 경험 수 기반 자동 stage 전이

**변경 파일**:
- [x] `neural/baby/conversation_handler.py` — Step 7.5 stage check 블록
  - `_STAGE_THRESHOLDS = {1: 10, 2: 30, 3: 70, 4: 150, 5: 300}`
  - 경험 수 초과 시 `update_baby_state(development_stage=next_stage)` + SSE 알림

**비판적 발견**: world_model.py, substrate.py, development.py, emotions.py의 핵심 로직이
Neo4j 마이그레이션 이후 conversation_handler.py에서 **단절됨** (6번째 "정의만 되고 호출 안 됨" 패턴)
→ D3는 development.py 의존 없이 Neo4j 기반으로 직접 구현

### Phase C3: 기억 재생 (Memory Replay) ✅

**핵심**: 수면 중 고감정 경험의 개념 네트워크를 재활성화 + offline Hebbian learning

**변경 파일**:
- [x] `neural/baby/neo4j_db.py` — `replay_recent_memories()` + `create_sleep_log()`
  - 고감정 경험 → INVOLVES → 개념 수집 → spreading activation → hebbian_update(delta=0.02)
  - SleepLog 노드 생성 (기존에 조회만 있고 생성 없었음 → 해결)
- [x] `neural/baby/api_server.py` — `POST /api/memory/replay` + `ReplayRequest` 모델
  - `publish_neuron_activation()` import 추가 → SSE로 sleep_replay 이벤트 전송
- [x] `frontend/baby-dashboard/src/hooks/useIdleSleep.ts` — Phase 1.5에 replay 호출 추가
  - consolidation 직후, curiosity 생성 전에 실행

**설계 결정**:
- 수면 중 Hebbian delta=0.02 (대화 중 0.05보다 약한 강화)
- `trigger_type: "sleep_replay"`로 대화 중 활성화와 구분
- SleepLog 생성 코드 없음 버그 해결

---

## 2026-03-19 (Phase 3)

### DB Migration Phase 3: SSE + Redis Pub/Sub 프론트엔드 연결 완료 ✅

**완료 항목**:
- [x] `neural/baby/conversation_handler.py` — Spreading Activation 추가 (Step 5.5)
  - `get_spreading_activation(concept_ids)` 호출 후 `publish_neuron_activation()` 발행
  - `saved_concept_ids` 수집 패턴으로 기존 루프 비파괴적 수정
- [x] `neural/baby/api_server.py` — `GET /api/brain/activation-summary` 엔드포인트 추가
  - Neo4j INVOLVES 관계 기반 heatmap + replay 데이터 반환
  - `useNeuronActivations` 초기 로드용
- [x] `frontend/baby-dashboard/src/hooks/SSEContext.tsx` — SSEProvider + Context (신규)
  - 단일 EventSource 앱 전체 공유
  - 지수 백오프 재연결 (3s → 6s → 12s → max 60s)
- [x] `frontend/baby-dashboard/src/hooks/useSSESubscription.ts` — SSE 구독 hook
  - `useSSESubscription(handler)` — SSEContext에서 구독/해제
  - handler ref 패턴으로 불필요한 재구독 방지
- [x] `frontend/baby-dashboard/src/hooks/useNeuronActivations.ts` — Supabase Realtime 제거
  - Supabase `channel('brain-activity')` 구독 → `useSSESubscription` 교체
  - 초기 heatmap: `supabase.rpc(...)` → `GET /api/brain/activation-summary` 교체
- [x] `frontend/baby-dashboard/src/components/Providers.tsx` — SSEProvider 래퍼 (신규)
- [x] `frontend/baby-dashboard/src/app/layout.tsx` — `<Providers>` 추가
- [x] `frontend/baby-dashboard/.env.local` — `NEXT_PUBLIC_FASTAPI_URL=http://localhost:8000` 추가
- [x] `scripts/migration/phase3_realtime/test_sse_stream.py` — 검증 스크립트

**비판적 검토로 수정된 원래 계획**:
- ioredis + Next.js `/api/events/route.ts`: 삭제 (FastAPI CORS로 브라우저 직접 연결 가능)
- pending_question / imagination 채널: Phase 4 이연 (발행자 미이식)
- useNeuronActivations의 concept/region name 조회 (Supabase): Phase 4 이연

**TypeScript 타입 검사**: `npx tsc --noEmit` → 오류 0개 ✅

**Go/No-Go 기준** (서버 실행 후 검증):
- [ ] `GET /api/brain/activation-summary` → heatmap + replay 반환
- [ ] `POST /api/conversation` → Redis `baby-ai:neuron_activation` 채널 발행
- [ ] 브라우저 EventSource → `baby_state` 이벤트 수신

---

## 2026-03-19 (Phase 2)

### DB Migration Phase 2: Neo4j Backend + FastAPI 기본 구조 완료 ✅

**완료 항목**:
- [x] `neural/baby/neo4j_db.py` — db.py BrainDatabase 완전 대체 (40개 async 메서드)
- [x] `neural/baby/redis_client.py` — Redis Pub/Sub + 캐시 래퍼
- [x] `neural/baby/api_server.py` — lifespan 패턴 + 기본 엔드포인트 추가
- [x] `neural/baby/conversation_handler.py` — DB-first 대화 파이프라인 구현
- [x] `scripts/migration/phase2_backend/test_fastapi_endpoints.py` — Phase 2 검증 스크립트

**비판적 검증으로 발견한 수정 사항**:
- Cypher SET에서 `min()` / `max()` 사용 불가 (집계 함수로 인식됨) → `CASE WHEN`으로 대체
- MERGE ON CREATE 시 `id: randomUUID()` 별도 SET 필요 (props 딕셔너리 포함 불가)
- `LLMClient.generate()`는 동기 함수 → `asyncio.to_thread()` 래핑으로 비동기화

**conversation_handler.py 파이프라인**:
1. `get_baby_state()` → 감정/발달 상태
2. Gemini 호출 (`asyncio.to_thread`)
3. `insert_experience()` → Neo4j 저장
4. `insert_concept()` + `link_experience_concept()` → 개념 연결
5. `log_emotion()` → EmotionLog 저장
6. `update_baby_state()` → 상태 업데이트
7. Redis `PUBLISH` → baby_state + experience 이벤트

**검증 결과 (4/4 PASS)**:
| 검증 | 결과 |
|-----|------|
| POST /api/conversation → Neo4j Experience 생성 | PASS |
| GET /api/state → BabyState 반환 | PASS |
| GET /api/brain/concepts → 835개 Concept 반환 | PASS |
| POST /api/memory/consolidate → 2151개 Experience 강화 | PASS |

---

## 2026-03-19 (Phase 1)

### DB Migration Phase 1: Neo4j 스키마 + 데이터 마이그레이션 완료 ✅

**비판적 검증으로 발견한 수정 사항**:
- embedding 차원: 계획의 768 → 실측 **1536** (OpenAI text-embedding-3-small)
- embedding REST 반환 형식: float[] 예상 → 실제 **JSON 문자열** (json.loads 파싱 필수)
- 실제 데이터 규모: MEMORY.md 기록(~3,577행) → 실측 **11,786행** (Baby AI가 성장함)
- `concept_brain_mapping` 테이블: `id` 컬럼 없음 (composite key만 존재)
- HTTP 206 = Partial Content = 정상 (처음에 에러로 오인, 수정)
- MCP Supabase가 다른 프로젝트(사주 앱) 연결 → REST API 직접 사용으로 우회

**완료 항목**:
- [x] `scripts/migration/phase1_schema/neo4j_schema.cypher` — DDL (제약조건 12개 + 인덱스 6개 + 벡터 3개)
- [x] `scripts/migration/phase1_schema/export_supabase.py` — Supabase → JSON (11,786행)
- [x] `scripts/migration/phase1_schema/import_to_neo4j.py` — JSON → Neo4j MERGE
- [x] `scripts/migration/phase1_schema/validate_migration.py` — 정합성 검증
- [x] `.gitignore` — `scripts/migration/migration_data/` 추가
- [x] **Neo4j 스키마 적용**: 20개 인덱스/제약조건 모두 ONLINE
- [x] **데이터 임포트 완료**: 11개 노드 레이블 + 4개 관계 타입
- [x] **벡터 인덱스 3개 ONLINE**: concept_embeddings, experience_embeddings, visual_embeddings

**검증 결과 (5/5 PASS)**:
| 검증 | 결과 |
|-----|------|
| 노드 수 일치 (11개 레이블) | PASS |
| 관계 수 일치 (4개 타입) | PASS |
| 임베딩 무결성 (148개 Concept) | PASS |
| 벡터 인덱스 상태 (3개 ONLINE) | PASS |
| 벡터 검색 동작 (score=1.0000) | PASS |

**Neo4j 최종 상태**:
- Nodes: BrainRegion(9) + Concept(820) + Experience(3039) + EmotionLog(1503) + ... = ~8,313
- Relationships: RELATES_TO(680) + MAPPED_TO(820) + INVOLVES(1060) + CAUSES(3) = 2,563
- Vector indexes: 1536-dim cosine, 148 concepts + 106 experiences embedded

**다음**: Phase 2 — `neo4j_db.py` + FastAPI 백엔드

---

## 2026-03-19

### DB Migration Phase 0: Neo4j AuraDB Free 연결 ✅

- [x] **Neo4j AuraDB Free 인스턴스 생성** — baby-ai (ID: b76cbc85)
- [x] **Python neo4j 드라이버 설치** — v6.1.0
- [x] **연결 문제 진단 및 해결** (3가지 함정 발견)
  1. `neo4j+s://` → AuraDB Free 단일노드에서 라우팅 테이블 조회 실패 (Windows 11 + AuraDB Free 구조적 한계, Community #74376)
  2. `bolt+s://[instance].databases.neo4j.io` → writer 노드로 일관되게 라우팅 안 됨
  3. `database_='b76cbc85'` 직접 지정 → "Database not found" (bolt+s 직접 연결 시)
- [x] **최종 해결책**: system DB → `SHOW DATABASES WHERE writer=true` → writer 주소 동적 조회 → 직접 연결
- [x] **검증 완료**: Neo4j 5.27-aura, Cypher 5, Nodes: 0, Indexes: 2
- [x] **.env 업데이트**: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE 추가
- [x] **scripts/test_neo4j_connection.py** 작성 (연결 패턴 문서화 포함)

### DB Migration Phase 0: Upstash Redis 연결 ✅

- [x] **Upstash Redis 인스턴스 생성** — baby-ai-redis, GCP Tokyo (asia-northeast1)
- [x] **설정**: Eviction OFF, TLS ON, 500K commands/month, 256MB, 50GB bandwidth
- [x] **Python redis-py 설치** — redis[hiredis]
- [x] **연결 검증 완료** (3개 테스트 통과)
  1. SET/GET/DEL: `hello-baby-ai` 정상
  2. Pub/Sub: `baby-ai:test-channel` → 1 listener, 메시지 수신 성공
  3. Server INFO: Redis 8.2.0, standalone mode
- [x] **.env 업데이트**: `REDIS_URL=rediss://...` 추가 (TLS 필수)
- [x] **scripts/test_redis_connection.py** 작성 (asyncio + Pub/Sub 패턴 포함)

### Phase 0 완료 ✅✅

| 항목 | 상태 | 세부 |
|------|------|------|
| Neo4j AuraDB Free | ✅ | b76cbc85, v5.27-aura, Cypher 5 |
| Upstash Redis | ✅ | baby-ai-redis, v8.2.0, GCP Tokyo |

**다음 (Phase 1)**: Neo4j 스키마 생성 (Cypher DDL, vector indexes, constraints)

---

## 2026-02-23

### v30 기억 회상 라이브 테스트 + 전체 진단 ✅
- [x] **v30 테스트 결과**: 기억 회상 파이프라인 작동 확인
  - "날짜에 대해 공부 했어?" → concepts_recalled: 10, experiences_recalled: 5
  - v28 대비: "비비는 잘 몰라요!" → "날짜 박사가 될 거라서 잘 알고 있어요!" (확실한 개선)
  - DB description 직접 인용: "특정한 시점을 가리키는 단위"
  - 이전 대화 참조: "전에 형이랑도 이야기했잖아요!"
- [x] **한계 발견**: 10개 concept 중 2-3개만 피상적 활용 → 프롬프트 강화 필요

### 발견된 버그 3건
1. **useBrainRegions.ts stage 5 미정의** — STAGE_PARAMS에 5 없음 → fallback으로 BABY 표시 (DB는 stage=5)
2. **stage 번호 체계 불일치** — BabyStateCard(1-based) vs useBrainRegions(0-based)
3. **발달 단계 전이 미구현** — `_check_stage_advance()`는 Python에만 존재, EF에서 stage 올리는 로직 없음
   - "정의만 되고 호출 안 됨" 패턴 5번째 발견!

### DB 현재 통계 (2026-02-23)
| 테이블 | 수량 |
|--------|------|
| semantic_concepts | 488 (prod) |
| concept_relations | 616 |
| experiences | 965 |
| baby_state | stage=5, exp=2175 |

---

## 2026-02-20

### conversation-process v29/v30 배포 ✅
- [x] **v29**: Memory Recall Pipeline 구현
  - `extractKeywords()` — 한국어 조사 제거 + 불용어 필터링
  - `loadRelevantConcepts()` — ILIKE 기반 concept 검색
  - `loadRelevantExperiences()` — 과거 대화 경험 검색
  - `formatMemoryContext()` — 프롬프트에 기억 컨텍스트 주입
- [x] **v30 (v29b)**: 프롬프트 강화
  - `[필수 규칙]` 섹션 추가 — "모르겠어요/기억 안 나요/까먹었어요" 금지
  - `[기억 강도: X%]` 표시 추가
  - extras에 `concepts_recalled`, `experiences_recalled` 저장
  - 디버그 로그: keyword 추출, recall 결과 로깅

---

## 2026-02-18

### conversation-process v27 배포 ✅ (CRITICAL BUG FIX)
- [x] **Concept isolation bug 수정**: concept 이름으로 글로벌 검색 → 프로덕션 concept 재사용 문제
  - 수정: concept/relation lookup에 `ablation_run_id` 스코핑 추가
  - `.single()` → `.maybeSingle()` (no-match 시 graceful handling)
- [x] F4 emotion downstream 구현 (v24→v25→v26→v27)

---

## 2026-02-10

### conversation-process v23 배포 ✅
- [x] `maybeImagine()` 400 에러 수정 (jsonb[]/uuid[] 타입 불일치)
  - thoughts: string[] → {type, content, timestamp, connections}[] (jsonb[])
  - connections_discovered: string[] → {content, discovered_at}[] (jsonb[])
  - predictions_made: string[] → [] (uuid[]이므로 텍스트 예측 제외)
- [x] ThoughtProcess 패널 데이터 강화
  - RPC `get_brain_activation_summary()`에 concept_name, concept_category, region_name JOIN 추가
  - Realtime 구독에서 concept/region 조회 추가
  - ThoughtStep 인터페이스: conceptName, conceptCategory, regionName, triggerType, intensity
- [x] `RealisticBrain.tsx` + `brain/page.tsx` ThoughtProcessPanel 구현
  - "파동의 원인" (대화 컨텍스트) + "생각 경로" (direct) + "연상 확산" (spreading) 3섹션
  - 영역별 그룹화 + 접기/펼치기

### 문서 정비 ✅
- [x] MEMORY.md: v23 상태 반영
- [x] Task.md: v23 버전 업데이트
- [x] CLAUDE.md: brain-researcher agent, DB 통계 최신화
- [x] SQL_task.md: Phase B/C1 마이그레이션 기록
- [x] ROADMAP.md: Phase C1 완료 + v23 반영
- [x] PROJECT_VISION.md: Phase C1 완료 반영

---

## 2026-02-09

### Phase C1: 활성화 전파 (Spreading Activation) ✅
- [x] `conversation-process` v21: `spreadActivation()` BFS 함수 (maxDepth=2, decay=0.5)
  - 양방향 전파 (from/to, 역방향 0.7x)
  - trigger_type: 'spreading_activation'
- [x] `useNeuronActivations.ts`: spreadingRegions + waveCount 상태 추가 (5s decay)
- [x] `RealisticBrain.tsx`: SpreadingRipple 컴포넌트 (확장 링 + amber glow)
  - spreading 영역: 느린 맥동, 넓은 glow, amber 발광
  - 활성 영역 범례에 wave count + spreading 표시
- [x] MD 파일 업데이트 (ROADMAP, PROJECT_VISION, Task, CHANGELOG)
- [x] 빌드 성공 (TypeScript 에러 없음)

### Phase C1-A+C: 파동 재생 + 누적 히트맵 ✅
- [x] DB 마이그레이션: `brain_region_id` 인덱스 + `trigger_type, created_at` 복합 인덱스
- [x] RPC 함수 `get_brain_activation_summary()`: replay + heatmap 단일 호출
  - replay: 최근 대화 턴의 활성화 200개 (시간순)
  - heatmap: 영역별 누적 활성화 횟수 + 평균 강도
- [x] `useNeuronActivations.ts`: mount 시 RPC 호출 → 3초 staggered replay + heatmap state
- [x] `RealisticBrain.tsx`: heatmapIntensity → base glow (자주 쓴 영역 은은히 빛남)
  - replay 중 "마지막 대화 파동 재생 중..." UI 표시
  - 누적 활성화 기록 범례 (비활성 시)
- [x] 빌드 성공 (TypeScript 에러 없음)

### Phase C2: 대화 컨텍스트 + 상상 자동화 ✅
- [x] DB 마이그레이션: `neuron_activations`에 `experience_id` 컬럼 추가 + 인덱스
- [x] RPC `get_brain_activation_summary()` 업데이트: replay에 experience context (user_message, ai_response, dominant_emotion) 포함
- [x] `conversation-process` v22:
  - `logNeuronActivations()`에 `experienceId` 파라미터 추가
  - `spreadActivation()`에 `experienceId` 파라미터 추가
  - `maybeImagine()` 함수 추가 (4번째 "호출 안 됨" 패턴 수정!)
    - 조건: stage >= 3, curiosity > 0.6, 40% 확률
    - Gemini가 대화 기반 상상 토픽/thoughts/connections 생성
    - trigger: 'conversation_curiosity'
  - 응답에 `imagination_triggered` 필드 추가
- [x] `useNeuronActivations.ts`: `activationContext` 상태 추가 (experienceId, userMessage, aiResponse, emotion)
  - RPC replay에서 experience context 자동 추출
  - Realtime 구독에서 conversation 활성화 시 experience 조회
- [x] `RealisticBrain.tsx`: "파동의 원인" 패널 추가
  - 활성 영역 + replay 중 하단에 표시
  - 형아의 메시지 + 비비의 응답 + 감정 표시
- [x] 빌드 성공 (TypeScript 에러 없음)

---

## 2026-02-07

### Phase W2: Wake Word 대화 흐름 개선 ✅
- [x] `useWakeWord.ts` 7-state 머신 (OFF/LISTENING/GREETING/CONVERSING/CAPTURING/PROCESSING/SPEAKING)
- [x] "비비야" → 인사 → 연속 대화 (wake word 없이)
- [x] `/api/wake-greeting` API route + `WakeWordIndicator.tsx` 상태 추가
- [x] `sense/page.tsx` 통합

### Phase B: 해부학적 뇌 시각화 ✅
- [x] DB: `brain_regions`(9), `concept_brain_mapping`(452), `neuron_activations`(Realtime)
- [x] `conversation-process` v20: neuron activations 자동 기록
- [x] `RealisticBrain.tsx` + `useNeuronActivations.ts` + `useBrainRegions.ts`
- [x] `brain/page.tsx` 해부학/추상 뷰 토글
- [x] 빌드 + Vercel 배포

---

## 2026-02-06

### Emotion→Goal Pipeline + Self-Evaluation Fix ✅

**문제 발견:**
- `emotion_goal_influences` 테이블이 0건 (방금 만든 테이블인데 호출 안 됨 - 3번째 "정의만 되고 호출 안 됨" 패턴!)
- `self_evaluation_logs` 0건 (Edge Function 존재하지만 아무도 호출하지 않음 - 같은 패턴!)

**구현 내용:**
- [x] `conversation-process` v19 배포 (두 문제 한 번에 해결)
  - 복합 감정 감지 (`detectCompoundEmotion()`) + valence/arousal 계산 추가
  - `saveEmotionLog()` 업데이트: valence, arousal, compound_emotion 컬럼 채움
  - `saveEmotionGoalInfluence()` 함수 추가: 감정→목표 매핑 자동 기록
  - `triggerSelfEvaluation()` 함수 추가: 경험별 자기평가 자동 기록 (LLM 없이, 규칙 기반)
- [x] Frontend: EmotionRadar에 "감정 기반 추천 목표" 섹션 추가
  - GOAL_TYPE_CONFIG (6개 목표 타입 한국어 레이블/아이콘/설명)
  - EMOTION_GOAL_MAP (복합+기본 감정 → 목표 타입 매핑)
  - framer-motion 애니메이션
- [x] 빌드 테스트 통과 (20/20 페이지)
- [x] 실제 대화 테스트로 파이프라인 검증 완료

**검증 결과:**
| 테이블 | 이전 | 이후 |
|--------|------|------|
| emotion_goal_influences | 0 | 1+ (자동 생성) |
| self_evaluation_logs | 0 | 1+ (자동 생성) |
| emotion_logs (새 필드) | null | valence/arousal/compound 채워짐 |

**팀 분배:**
- Lead (Opus): Edge Function 분석 + v19 작성/배포 + 테스트/검증
- Frontend Agent (Sonnet): EmotionRadar.tsx 시각화 추가
- 순차 실행: 분석 → Edge Function → 검증 → Frontend → 빌드

**교훈:**
- "정의만 되고 호출 안 됨" 패턴 3번째 반복 → MEMORY에 "새 테이블/함수 추가 시 호출 지점 반드시 확인" 강화
- 두 개의 독립적 문제가 같은 근본 원인 (conversation-process에서 호출 부재) → 한 번의 업데이트로 동시 해결

**파일 변경 목록:**
| 파일 | 변경 |
|------|------|
| Supabase `conversation-process` | v18 → v19 (compound detect + VA + goal influence + self-eval) |
| `frontend/.../EmotionRadar.tsx` | GOAL_TYPE_CONFIG + EMOTION_GOAL_MAP + 추천 목표 섹션 |

---

### Emotion Engine Upgrade (Phase E) ✅

**작업 내용:**
- [x] DB Migration: emotion_logs에 `valence`, `arousal`, `compound_emotion` 컬럼 추가
- [x] DB Migration: `emotion_goal_influences` 테이블 생성 (감정→목표 영향 기록)
- [x] DB Migration: `recent_emotion_stats`, `daily_emotion_summary` view에 VA/compound 추가
- [x] DB: 기존 211개 emotion_logs 레코드 valence/arousal 백필 완료
- [x] Backend: `emotions.py`에 5개 복합 감정 추가 (pride, anxiety, wonder, melancholy, determination)
- [x] Backend: `COMPOUND_EMOTIONS` dict + `EMOTION_GOAL_MAP` dict 추가
- [x] Backend: `EmotionalState.detect_compound_emotion()` 메서드 추가
- [x] Backend: `EmotionalCore.suggest_goal_from_emotion()` 메서드 추가
- [x] Backend: `EmotionalState.to_dict()` 업데이트 (compound_emotion 필드 추가)
- [x] Frontend: `EmotionRadar.tsx` 탭 시스템 추가 (감정 레이더 / 감정 지도)
- [x] Frontend: Valence-Arousal 2D ScatterChart (Russell's circumplex model)
- [x] Frontend: Compound emotion badge (헤더 우측, framer-motion 애니메이션)
- [x] Frontend: `database.types.ts`에 새 컬럼/테이블 타입 추가
- [x] 빌드 테스트 통과 (TypeScript 에러 1건 수정)

**팀 분배 전략:**
- Lead (Opus): DB migration 직접 + 통합/빌드/검증
- Backend Agent (Sonnet): emotions.py 코드 작성
- Frontend Agent (Sonnet): EmotionRadar.tsx + database.types.ts 코드 작성
- 순차 실행: DB → Backend (검증) → Frontend (Backend 인터페이스 확정 후) → 통합

**파일 변경 목록:**
| 파일 | 변경 |
|------|------|
| `neural/baby/emotions.py` | COMPOUND_EMOTIONS, EMOTION_GOAL_MAP, detect/suggest 메서드 추가 |
| `frontend/.../EmotionRadar.tsx` | 탭 시스템 + VA plot + compound badge |
| `frontend/.../database.types.ts` | emotion_logs 새 컬럼 + emotion_goal_influences 타입 |
| Supabase | 4개 migration (컬럼추가, 테이블생성, 백필, view 재생성) |

---

### MD 파일 재구성 및 최신화 ✅

**작업 내용:**
- [x] `task_baby_brain.md` → `docs/archive/` 아카이브 (2026-01-20 이후 미업데이트, Task.md와 역할 중복)
- [x] `ROADMAP.md` → Phase A/V/W, Causal Discovery, Prediction Auto-Verification 추가
- [x] `PROJECT_VISION.md` → Phase 10/11/W/A/V 및 최신 파이프라인 추가 (v1.4)
- [x] `Task.md` → DB 통계 최신화 (447 뉴런, 519 시냅스, 583 경험)
- [x] `CHANGELOG.md` → 누락된 Prediction Auto-Verification 엔트리 추가

**DB 최신 통계 (2026-02-06):**
| 항목 | 수량 | 변화 |
|------|------|------|
| semantic_concepts | 447 | +34 (from 413) |
| concept_relations | 519 | +90 (from 429) |
| experiences | 583 | +123 (from 460) |
| emotion_logs | 211 | +27 (from 184) |
| visual_experiences | 13 | +5 (from 8) |
| causal_models | 3 | 신규 |
| predictions | 8 (5 verified) | +2 (from 6) |
| pending_questions | 8 (all answered) | 신규 |
| imagination_sessions | 9 | +5 (from 4) |

---

## 2026-02-05

### Prediction Auto-Verification 파이프라인 ✅

**문제 발견:**
- `verify_prediction()` 함수가 정의만 되어있고 호출되지 않음 (Causal Discovery와 동일 패턴)
- 미검증 예측 5개가 `was_correct = null`로 방치

**구현 내용:**
- [x] `world_model.py`에 `auto_verify_predictions()` 함수 추가
  - 미검증 예측 조회 → 관련 경험 확인 → LLM으로 정확성 판단 → DB 업데이트
- [x] `auto_generate_from_experience()`에서 자동 호출 통합
- [x] 5개 예측 자동 검증 완료 (`auto_verified=true`, `was_correct=true`)

---

### Causal Discovery 파이프라인 활성화 ✅

**문제 발견:**
- `causal_models` 테이블이 0건 (인과관계 데이터 없음)
- `discover_causal_relation()` 함수가 정의만 되어있고 호출되지 않음
- CausalGraph UI 컴포넌트는 이미 구현되어 있었지만 데이터 없이 빈 화면

**구현 내용:**
- [x] `world_model.py`에 `extract_causal_relations_from_experience()` 함수 추가
  - 감정 기반 인과관계 추출 (`_extract_emotion_based_causality`)
  - 성공/실패 기반 인과관계 추출 (`_extract_outcome_based_causality`)
  - LLM 기반 개념 인과관계 추출 (`_extract_concept_based_causality`)
- [x] `auto_generate_from_experience()`에 causal discovery 통합
  - 경험 처리 시 자동으로 인과관계 발견
  - `causal_relations` 결과 필드 추가
- [x] `test_world_model.py` 테스트 추가
  - `test_causal_discovery()` 함수
  - DB stats에 causal_models 조회 추가

**테스트 결과:**
```
Causal Models: 3
- 질문 → 호기심 (enables, strength: 0.60)
- 학습 → 이해 (enables, strength: 0.50)
- 질문 → 이해 (enables, strength: 0.50)
```

**파일 변경 목록:**
| 파일 | 변경 |
|------|------|
| `neural/baby/world_model.py` | extract_causal_relations_from_experience() 함수 추가 |
| `scripts/test_world_model.py` | test_causal_discovery() 테스트 추가 |
| `ROADMAP.md` | Causal Discovery 파이프라인 완료 표시 |
| `CHANGELOG.md` | 작업 기록 |

**기대 효과:**
- 대화할 때마다 인과관계 자동 축적
- CausalGraph 탭에서 시각화 가능해짐
- Baby AI의 인과 추론 능력 실제 작동

---

## 2026-02-04

### 작업 내용
- [x] MD 파일 구조 정리
  - Task.md에 "현재 진행 중인 Phase" 섹션 추가
  - CHANGELOG.md 생성 (이 파일)
  - `docs/PHASE_A_PROACTIVE_QUESTIONS.md` 생성

### Phase A Day 1 완료 ✅
- [x] `pending_questions` 테이블 생성
  - 15개 컬럼: question, question_type, context, priority, status, answer 등
  - question_type: personal, preference, experience, relationship
  - status: pending, asked, answered, skipped, expired
- [x] RLS 정책 설정 (Allow all access)
- [x] Supabase Realtime 활성화 (Day 3에서 사용)
- [x] 테스트 데이터로 CRUD 검증 완료

### 마이그레이션 기록
1. `create_pending_questions_table` - 테이블 + 인덱스 + 트리거
2. `add_rls_pending_questions` - RLS + Realtime

### 배운 점 / 메모
- Task.md에 "현재 진행 중인 Phase" 섹션이 없어서 작업 추적이 어려웠음
- CHANGELOG.md로 일별 기록을 분리하면 세션 간 컨텍스트 복구가 쉬움
- 기존 `curiosity_queue`와 일관된 스타일로 테이블 설계함

### Phase A Day 2 완료 ✅
- [x] `generate-curiosity` v3 코드 분석
  - 4가지 호기심 소스: concept_gap, failure, pattern, similarity
  - 모든 호기심 → curiosity_queue → autonomous-exploration (웹 검색)
- [x] 호기심 분류 로직 설계
  - Gemini LLM으로 factual vs personal/preference/experience/relationship 분류
  - 분류 프롬프트 설계 (CLASSIFICATION_PROMPT)
- [x] `generate-curiosity` v4 배포
  - `classifyCuriosity()`: Gemini로 호기심 분류
  - `saveToPendingQuestions()`: 개인적 질문 저장
  - `curiosityToQuestion()`: 개념 → 자연스러운 질문 변환
  - 새 action: `get_pending_questions`
- [x] v4 테스트 검증
  - 30개 호기심 생성 → 29 factual + 1 experience
  - factual → curiosity_queue ✅
  - experience → pending_questions ✅

### v4 변경 요약
```
v3: 호기심 → curiosity_queue → 웹 검색
v4: 호기심 → 분류(Gemini) → factual? → curiosity_queue → 웹 검색
                           → personal? → pending_questions → 사용자에게 질문
```

### Phase A Day 3 완료 ✅
- [x] `pending_questions` 타입 추가 (`database.types.ts`)
  - Row, Insert, Update 타입 정의
  - PendingQuestion, QuestionType, QuestionStatus 헬퍼 타입
- [x] `usePendingQuestions` hook 생성 (`hooks/usePendingQuestions.ts`)
  - Supabase Realtime INSERT 이벤트 구독
  - 질문 목록 fetch (priority 정렬)
  - `markAsAsked()`, `submitAnswer()`, `skipQuestion()` 메서드
  - `newQuestionAlert` 상태로 새 질문 알림
- [x] `QuestionNotification` 컴포넌트 생성 (`components/QuestionNotification.tsx`)
  - 슬라이드-인 토스트 알림 UI
  - 질문 타입별 색상/이모지 (personal, preference, experience, relationship)
  - "답변하기" / "나중에" 버튼
  - 15초 자동 dismiss
- [x] 메인 페이지 통합 (`app/page.tsx`)
  - usePendingQuestions hook 연결
  - QuestionNotification 렌더링
  - 브라우저 알림 연동 (sendNotification)
  - window.prompt로 임시 답변 UI (Day 4에서 모달로 개선)
- [x] 빌드 테스트 통과

### Day 3 파일 변경 목록
| 파일 | 변경 |
|------|------|
| `src/lib/database.types.ts` | pending_questions 타입 추가 |
| `src/hooks/usePendingQuestions.ts` | 새 파일 생성 |
| `src/hooks/index.ts` | usePendingQuestions export 추가 |
| `src/components/QuestionNotification.tsx` | 새 파일 생성 |
| `src/components/index.ts` | QuestionNotification export 추가 |
| `src/app/page.tsx` | Realtime 구독 + 알림 UI 통합 |

### Phase A Day 4 완료 ✅
- [x] `QuestionBubble` 모달 컴포넌트 생성 (`components/QuestionBubble.tsx`)
  - Full-screen 모달 오버레이
  - Textarea로 답변 입력
  - 확신도 선택 (💯확실해요 / 👍대체로 / 🤔잘 모르겠어요)
  - Ctrl+Enter로 빠른 제출
  - "나중에 답변할게요" 스킵 옵션
- [x] 답변 → semantic_concepts 저장 로직 (`usePendingQuestions.ts`)
  - `saveAnswerAsConcept()`: 답변을 semantic_concepts 테이블에 저장
  - 질문 타입별 카테고리 매핑 (personal→user_info, preference→user_preference 등)
  - `extras`에 질문 메타데이터 저장 (source, question_id, question_text 등)
  - `learned_concept_id`로 pending_questions와 연결
- [x] `QuestionList` 컴포넌트 생성 (`components/QuestionList.tsx`)
  - 여러 질문 목록 표시 (priority 정렬)
  - 확장/축소 가능한 카드 UI
  - 첫 번째 질문에 "우선" 뱃지 표시
  - 빈 상태 UI (궁금한 게 없을 때)
- [x] 메인 페이지 통합 (`app/page.tsx`)
  - window.prompt → QuestionBubble 모달로 교체
  - "질문" 탭 추가 (pending questions 개수 뱃지)
  - QuestionList 컴포넌트 렌더링
- [x] 빌드 테스트 통과

### Day 4 파일 변경 목록
| 파일 | 변경 |
|------|------|
| `src/components/QuestionBubble.tsx` | 새 파일 생성 |
| `src/components/QuestionList.tsx` | 새 파일 생성 |
| `src/components/index.ts` | QuestionBubble, QuestionList export 추가 |
| `src/hooks/usePendingQuestions.ts` | saveAnswerAsConcept 로직 추가 |
| `src/app/page.tsx` | QuestionBubble 모달 + questions 탭 통합 |

### Day 4 핵심 변경
```
Day 3: 알림 → window.prompt → 답변 저장
Day 4: 알림 → QuestionBubble 모달 → 답변 저장 + semantic_concepts 연동
       + questions 탭에서 전체 질문 목록 관리
```

### Phase A Day 5 완료 ✅ - E2E 통합 테스트
- [x] 테스트 환경 확인
  - Supabase URL: `https://extbfhoktzozgqddjcps.supabase.co`
  - `generate-curiosity` v4 Edge Function ACTIVE
  - `pending_questions` 테이블 Realtime 활성화 확인
- [x] generate-curiosity 호출 테스트
  - 21개 호기심 생성 → 20 factual + 1 experience
  - 분류 로직 정상 동작 (Gemini 2.0 Flash)
  - factual → curiosity_queue, personal → pending_questions
- [x] pending_questions INSERT 테스트
  - 테스트 질문: "아빠가 제일 좋아하는 노래가 뭐야?" (preference, priority 0.9)
  - Realtime INSERT 이벤트 발생 확인
- [x] 답변 → semantic_concepts 저장 flow 검증
  - 답변: "아빠는 김광석의 서른 즈음에를 제일 좋아해요"
  - semantic_concepts 저장 완료 (category: user_preference)
  - pending_questions.learned_concept_id 연결 확인
  - pending_questions.status → 'answered' 전환 확인

### Day 5 E2E Flow 검증 결과
```
generate-curiosity (v4)
    ↓ Gemini 분류
    ↓ personal/preference/experience/relationship
    ↓
pending_questions INSERT
    ↓ Realtime 이벤트
    ↓
Frontend usePendingQuestions
    ↓ newQuestionAlert
    ↓
QuestionNotification → QuestionBubble
    ↓ 사용자 답변 입력
    ↓
semantic_concepts INSERT (user_preference)
    ↓
pending_questions UPDATE (answered + learned_concept_id)
```

### 테스트 데이터
| 항목 | 값 |
|------|-----|
| question_id | aab0fd73-05fc-44bf-80b6-f79bb7d6466c |
| question | 아빠가 제일 좋아하는 노래가 뭐야? |
| answer | 아빠는 김광석의 "서른 즈음에"를 제일 좋아해요 |
| concept_id | 005f02d3-7290-4c1f-8397-1fc698fd0f9b |
| concept_category | user_preference |
| concept_source | proactive_question |

### Phase A 완료 요약 🎉
**Day 1**: `pending_questions` 테이블 설계 + Realtime 활성화
**Day 2**: `generate-curiosity` v4 - Gemini 분류 로직
**Day 3**: `usePendingQuestions` hook + `QuestionNotification` 알림
**Day 4**: `QuestionBubble` 모달 + `QuestionList` + semantic_concepts 저장
**Day 5**: End-to-end 통합 테스트 완료

### 다음 단계 제안
- [ ] 실제 프론트엔드 배포 후 브라우저에서 라이브 테스트
- [ ] 추가 질문 타입 (personal, relationship) 테스트
- [ ] 질문 만료 로직 구현 (status: expired)
- [ ] 답변 품질에 따른 concept strength 조정 로직

---

## 템플릿

```markdown
## YYYY-MM-DD

### 작업 내용
- [ ] 작업 1
- [ ] 작업 2

### 성공
- 무엇이 잘 됐는지

### 실패 / 문제
- 무엇이 안 됐는지
- **원인**:
- **해결**:

### 배운 점 / 메모
- 기억해야 할 것

### 다음 세션 TODO
- [ ] 다음에 할 것
```
