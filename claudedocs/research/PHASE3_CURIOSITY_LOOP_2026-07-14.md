# Phase 3 [B] 예측오차 루프 닫기 — 검증 보고 (2026-07-14)

> program_roadmap Phase 3 / self_learning_architecture (A)(D). Phase 2 완주 후 뇌는 "배우지만
> 무기력"(코어가 예측오차 계산하나 행동에 영향 X). 루프를 닫는다 = 자기 예측오차(surprise)로
> **무엇을 볼지(주의·탐색·호기심)를 스스로 정한다**(active inference / ICM).
> 스크립트: `scripts/research/curiosity_loop.py`. 원자료: `claudedocs/research/curiosity_loop_20260714.json`.

## 검증 질문 (measure-first, 라이브 배선 전)
**자기 예측오차로 행동을 정하는 뇌가 무작위보다 빨리 배우는가?** = active inference 핵심 주장.
통과해야 conversation 파이프라인 배선이 정당. (시스템 미가동·conversation_handler 수정금지라
합성으로 메커니즘부터 검증 = 세션 measure-first 규율.)

## 방법
- **환경(노이즈-지배, 현실 근사)**: 학습가능 장면 20개(구조 O, 난이도 변주) + **노이즈 장면 40개**
  (매번 무작위=예측불가). 볼 수 있는 것의 2/3가 노이즈 = 호기심의 임무는 학습가능 구조를 **찾는** 것.
- **뇌**: degree-capped co-occurrence 그래프(세션 재사용). 예산 1200스텝(< 노이즈 안 피하면 부족).
- **정책(매 스텝 어느 장면 볼지)**: `random`(기준) · `surprise`(예측오차 최대=raw ICM) ·
  `progress`(예측오차 **감소율** 최대=learning progress, Oudeyer).
- **측정(3시드)**: held-out 예측 MRR vs 스텝(학습곡선·AUC) + 노이즈 장면 방문율.

## 결과 (3 seed, 노이즈-지배 세계)
| policy | final MRR | AUC(학습속도) | 노이즈 방문 |
|---|---:|---:|---:|
| random | 0.840 | 0.733 | 66% |
| **surprise (raw PE)** | 0.641 | 0.566 | **95% (갇힘)** |
| **progress (learning-progress)** | **0.859** | **0.752** | 58% |

학습곡선: progress가 MRR 0.83에 ~480스텝서 도달, random은 ~660스텝. surprise는 0.64서 정체.

## 판정 (둘 다 성립)
1. **✅ 루프를 닫으면(호기심) 학습 가속**: learning-progress 정책이 random을 이김(AUC 0.752>0.733,
   초반 학습 뚜렷히 빠름). = 자기 예측오차로 주의를 정하면 **학습가능 구조를 찾아** 예산을 효율 배분.
2. **✅ 순진한 surprise는 파국(noisy-TV 함정)**: 예측오차 최대화 정책이 **노이즈 장면에 95% 갇힘**
   (항상 오차 높지만 학습 불가). 최악 성능. = **닫는 신호로 raw 예측오차를 쓰면 안 됨.**

## 결정적 설계 규칙 (라이브 배선 시)
**루프는 반드시 learning-progress(예측오차 감소율)로 닫아야 한다 — raw surprise(예측오차 크기)로는
안 된다.** 안 그러면 아기가 TV 화면 잡음을 멍하니 보는 꼴(noisy-TV): 영원히 놀랍지만 못 배움.

## 한계 (정직)
- 이득 폭 modest(AUC +2.6%). 호기심 우위는 **regime 의존**: 노이즈/이질적 학습가능성 + 빠듯한 예산에서
  뚜렷(균등·저예산 환경선 breadth-first random도 충분). 초기 실험(9장면·과예산)선 이득 없었음(정직).
- 합성 데이터. 정책은 greedy-argmax(탐색 미세). 실 wake 스트림선 재확인 필요.

## 다음 (라이브 배선 — 시스템 가동 필요)
검증됐으니 배선 정당. 단 Neo4j 가동 + 실 대화 필요:
1. **surprise 계산**: 각 경험(대화 turn) 학습 전, 그래프/코어로 공동활성 예측→실제와의 예측오차.
   (RW delta = prequential_experiment 이미 계산.) endpoint/db층(conversation_handler v30 미변경).
2. **learning-progress 신호**: 개념/영역별 예측오차 감소율 추적 → **호기심 타깃**(뭘 물을지·탐색할지)
   + **통합 우선순위**(emotional_salience 확장). 기존 curiosity_queue(Phase 8)와 연결.
3. **noisy-TV 가드 필수**: raw surprise 금지, learning-progress로 게이팅.

산출: `scripts/research/curiosity_loop.py`, `claudedocs/research/curiosity_loop_20260714.json`.

## 라이브 배선 결과 (2026-07-14)
- 구현: `neural/baby/live_curiosity.py`(순수 계산), `neo4j_db.py`(pre-turn prediction snapshot +
  post-turn outcome/EMA/CuriosityLog), `api_server.py`(endpoint pre/post 호출 + consolidate priority).
- **noisy-TV guard**: raw `prediction_error`는 Experience 관측 속성으로만 저장. 통합 강도와 호기심 큐에는
  positive EMA 감소량(`learning_progress`)만 반영. 첫 관측은 progress=0, 최소 3관측·threshold 0.02 전 gate 금지.
- cue는 handler의 동일 규칙 기반 개념 추출 결과와 Neo4j Concept 이름 정확 일치로 선택(substring 과포착 방지).
- `conversation_handler.py` v30은 변경하지 않음. 기존 `/api/curiosity`는
  `source=learning_progress`, `query_type=concept_relation` 로그를 그대로 노출.
- 검증: `tests/test_live_curiosity.py` 7 passed. rollback synthetic Neo4j 3턴에서 error `1→0→0`,
  progress `0→0.4→0.24`, gate `false→false→true`, integration priority `0.546`; 동일 타깃 로그 중복 없음.
- 구현 검증 시점에는 Gemini 실 호출을 수행하지 않았으며, 아래 운영검증에서도 threshold는 조정하지 않았다.

## 실 대화 운영검증 (2026-07-14)
- **사전조건 확인**: `DB_Renewal` local/remote HEAD `e46af26` 일치, worktree clean, Neo4j 7687 UP,
  FastAPI 8000은 직접 기동 후 `/health` healthy. 실제 대화 전 Experience count 3069.
- **실험**: `비비와 형의 관계를 한 문장으로 말해줘.`를 동일 guest context에서 실제 Gemini 경로로 3회 반복.
- **결과**:

| turn | prediction error | learning progress | integration priority | gate |
|---:|---:|---:|---:|---|
| 1 | 1.000 | 0.000 | 0.748 | false |
| 2 | 0.667 | 0.133 | 0.801 | false |
| 3 | 0.500 | 0.147 | 0.807 | true |

- 3턴째 `CuriosityLog` `be9e608a-0a17-55e0-af09-2b778d8697a5`가
  `source=learning_progress`, `status=pending`으로 생성됐고 `/api/curiosity?limit=200&status=pending`에서 확인했다.
- **판정**: FastAPI→Gemini→Neo4j→learning-progress→CuriosityLog 루프는 실제 경로에서도 작동한다.
  raw surprise가 아니라 오차 감소량으로 3관측째 gate되는 설계도 관측값과 일치한다.
- **당시 인프라 한계**: 첫 운영검증 때 `.env`의 Upstash Redis 호스트 DNS 해석이 실패해 Redis publish와
  SSE 경로는 검증 실패했다. 예외가 대화를 중단시키지는 않았지만 당시에는 전체 스택 성공이 아니었다.
- **후속 Redis 복구**: 신규 `baby_ai_robot_v4`(GCP Tokyo, TLS)를 생성하고 `.env`에 새 URL을 설정했다.
  PING·임시 키 SET/GET/DELETE·Pub/Sub 왕복, `/health`, `/api/events` 시험 payload, 실제 Gemini 대화의
  `neuron_activation→baby_state→experience` SSE 및 Experience ID 일치를 모두 확인했다. Redis 오류 로그 0건.
- **질 한계**: 생성 질문은 `관계와(과) 세상의 관계를 더 알아보자`로 너무 일반적이었다. 현재 parser에서
  `비비`는 stopword이고 `형의`는 1글자 어간 `형`으로 축약되지 않아 identity cue가 사라진 것이 원인 후보다.
  단일 문장 3회 표본이므로 threshold는 유지한다.

## [B-2] cue 품질 개선 (2026-07-14)
- **보호 경계**: `conversation_handler.py` v30은 변경하지 않았다(blob `054d974…`). handler의 Concept 생성과
  호기심 cue 후보 생성은 목적이 다르므로 endpoint 전용 `build_curiosity_cue_terms()`를 추가했다.
- **정규화**: 사용자 메시지의 한국어 조사 표면형을 기존 Concept 정확일치 후보로만 복원한다.
  `비비와→비비`, `형의→형`; replacement 전 `형의`는 후보에서 제외한다. 한 글자 cue는 explicit 후보일 때만
  허용하고, cue list가 없을 때의 message substring fallback은 기존 2글자 제한을 유지한다.
- **추가 root cause와 수정**: 기존 Cypher는 cue와 이웃을 한 결과셋에 넣고 전역 LIMIT을 적용해 고차수
  `비비`의 이웃이 결과를 독점했다. cue 상위 N개를 먼저 확정한 뒤, 그 ID들의 고유 이웃을 별도 집계하도록
  두 쿼리로 분리했다. explicit 후보에서는 기존 graph strength 우선으로 identity hub를 앞세운다.
- **검증 사다리**:
  1. handler 원출력: `형의, 관계, 문장, 말해줘`
  2. endpoint 후보: `비비, 형, 관계, 문장, 말해줘`
  3. 라이브 read-only snapshot cue: `비비, 형, 관계, 말해줘`
  4. 실제 Gemini 1턴 Experience cue: `비비, 형, 관계, 말해줘` (`형의` 없음)
  5. `pytest tests neural/test_neural.py -q` 21 passed, py_compile 통과
- 실제 outcome Concept에는 보호된 handler 규칙 때문에 `형의/형은/형이`가 여전히 남는다. B-2는 이를 새로
  만들거나 고치지 않고, 호기심 snapshot의 알려진 identity cue만 안전하게 복원한다.
- **다음 [B-3]**: 다양한 관계/사물 문장으로 gate 빈도와 생성 질문 품질을 관찰한 뒤 threshold 조정 여부 판단.

## [B-3] 운영 표본 확대와 실패 분해 (2026-07-14 후속)

### 표본과 1차 결과
- Neo4j에서 observations=0이며 degree가 과도하지 않은 `서울`, `컴퓨터`, `학습`을 fresh stream으로
  골라 각각 3턴씩 실제 FastAPI→Gemini→Neo4j 경로를 실행했다.
- 9턴 모두 prediction error=1.0, learning progress=0, gate=false, CuriosityLog 없음. threshold를
  낮춰 해결할 성질이 아니므로 추가 9-stream 확장은 중단했다.
- Experience IDs(삭제하지 않고 음성 증거로 보존):
  `6d426fe9-2d0f-4ed8-94eb-e6e30db48011`, `3316f5f6-296c-4664-b2cc-cd705e430f02`,
  `0246aef4-38e5-4c13-af1e-34ca79ee9bf7`, `282a9570-4136-4d61-9d6f-301147a43d85`,
  `a00f9758-fda3-4b56-8fca-2d9a83432236`, `50e2e34f-f8e3-49e3-8cb5-a4d841f3e232`,
  `291e1790-d5a9-49c1-aaa0-0996730c2a1c`, `b8e61dce-dfbb-46e7-b7b6-63d1ff2f47e7`,
  `d80c1329-45b6-4fb2-b7f9-d4da08a68a22`.

### 원인 1: LLM 출력 예산을 thinking이 소진
- 동일 프롬프트를 구형 `google-generativeai`와 신형 `google-genai`로 각각 호출했으나 둘 다
  `MAX_TOKENS`. 신형 응답 메타데이터에서 prompt 235, thinking 487, 실제 answer 21,
  total 743을 확인했다. 512 output budget 대부분이 내부 thinking에 사용돼 답변이 잘렸다.
- SDK 자체의 차이는 아니었다. 다만 구형 SDK는 지원 종료 상태이므로 공식 `google-genai>=1.10`을
  정식 의존성으로 추가했다.
- 가변 `gemini-flash-latest` 대신 기존 코드 단가와 일치하는 stable
  `gemini-2.5-flash-lite`를 고정하고 thinking budget=0으로 설정했다. probe는 `STOP`, answer 160,
  thinking 0이었다.

### 원인 2: speech-act cue와 사용자 입력이 outcome을 오염
- 첫 표본이 `설명해줘`, `궁금해`, `무엇이` Concept를 만든 뒤 다음 turn부터 이들이 알려진 cue로
  승격됐다. endpoint/DB층에서 이 speech-act terms를 cue에서 제외했다.
- handler는 `response + user message`에서 Concept를 함께 생성한다. 따라서 user input terms와 정확히
  같은 비-cue actual을 점수에서 제외하고, `curiosity_excluded_input_concept_ids`에는 감사용으로 보존했다.
- read-only snapshot과 실제 후속 3턴 모두 cue는 `컴퓨터` 하나만 남고 각 기능어는 제외 목록에 남았다.

### 수정 후 3-turn 판정: canonical ID가 남은 병목
- 후속 Experience: `ffd88f20-72c5-4973-9de6-7986cb3113c1`,
  `01f4d589-5dd9-438b-86c7-0597067126f9`, `ed7f3ef4-c1f4-486b-aff5-7d3c834f5d5d`.
- 세 응답 모두 잘림 없이 완전했고 cue/input 필터도 작동했다. 그러나 세 턴 모두 error=1.0,
  progress=0, gate=false였다.
- turn 1 실제 `신기한`이 turn 2 predicted에 들어왔지만 turn 2 actual은 `신기하`로 저장돼 exact-ID
  hit가 아니었다. `컴퓨터요`, `컴퓨터라`, `컴퓨터에`도 동일 cue의 형태 변이지만 서로 다른 ID다.
- **결론**: 다음 [B-4]는 handler를 바꾸지 않고 conservative canonical-name scoring을 먼저
  offline/unit에서 검증한다. exact normalized equality만 허용하고 broad substring은 금지하며,
  `비비/비빔밥`, `형/형광등` 같은 false-positive 대조군을 반드시 포함한다. 이 gate를 통과하기 전
  threshold 조정이나 추가 live 표본은 금지한다.

## [B-4] canonical scoring offline gate (2026-07-14)

### 가설과 안전장치
- 가설: `신기한↔신기하`, `컴퓨터↔컴퓨터에` 같은 표면형 분리가 exact-ID error를 과대평가한다.
- production에 연결하기 전에 `scripts/research/b4_canonical_scoring.py`로 12개 보존 Experience를
  read-only replay했다. `conversation_handler.py`, Neo4j state, threshold는 변경하지 않았다.
- 일반 predicted↔actual match는 Unicode/case/공백, 보수적 조사 제거, 2음절 base 이상의 `-하/-한`
  교대만 허용했다. `-요/-라`는 알려진 cue 변형 제외에만 제한했다.
- false-positive gate: `비비/비빔밥`, `형/형광등`, `컴퓨터/컴퓨터공학`, `카메/카메라`,
  `오디/오디오`, `은하/은한`, `북하/북한`은 모두 불일치여야 한다.

### 결과 1: canonicalization-only 가설 기각
| metric | exact | canonical |
|---|---:|---:|
| 12-turn mean error | 1.000000 | 0.983333 |
| 개선 turn | 0 | 1/12 |

- 유일한 회복은 Experience `01f4d589-5dd9-438b-86c7-0597067126f9`의
  predicted `신기한` ↔ actual `신기하`; canonical error는 1.0→0.8이었다.
- 형태 분리는 실재하지만 12턴 실패를 설명하는 주원인은 아니다. canonical scorer는 production에
  연결하지 않는다.

### 결과 2: same-turn outcome 자체가 사전 예측 불가능
- Concept/Experience의 ISO `created_at`으로 actual이 turn 전에 존재했는지 감사했다. Experience가 먼저
  생성되고 응답 Concept가 뒤에 MERGE되는 현재 pipeline 순서를 사용했다.
- scored actual 53개 중 **40개(75.5%)가 그 turn 신규 Concept**, preexisting은 13개였다.
- 신규 actual을 제외해도 scorable 9턴의 preexisting canonical mean error는 `0.888889`; hit는 위 1개뿐.
- 즉 현재 graph predictor는 cue의 기존 이웃을 예측하지만, outcome은 그 prediction을 입력받지 않은
  LLM이 같은 turn에 자유 생성한 단어다. 둘의 불일치는 학습 실패라기보다 **target mismatch**다.

### 판정과 다음 [B-5]
1. canonicalization-only production 배선 금지.
2. threshold 0.02와 min observations 3 유지; 추가 live 표본 금지.
3. 다음 offline 비교 대상:
   - A안: turn `t`의 prediction을 turn `t+1` 사용자 입력 Concept와 비교.
   - B안: 시각/센서 Experience의 다음 외부 관측 Concept와 비교.
   - same-turn LLM output을 계속 쓰려면 graph predictions를 generator에 conditioning해야 하나,
     이는 보호된 `conversation_handler.py` 경계와 행동 생성 의미를 바꾸므로 현재는 배선하지 않는다.
4. A/B sequence에서 random/frequency baseline보다 prequential error가 실제 감소할 때만 live gate로 승격한다.

## [B-5] valid external outcome offline evaluation (2026-07-15)

### 질문과 사전 gate
- 질문: turn `t`에서 저장한 graph prediction이 LLM 자신의 같은-turn 문장이 아니라 **다음 외부 입력**을
  random/frequency baseline보다 잘 예측하는가?
- 사용자 입력 route는 보존 12 turn을 4개 독립 sequence로 나누고 내부의 `t→t+1` 8 pair만 사용했다.
  sequence 경계를 넘어선 임의 timestamp 연결은 금지했다.
- 반복 source cue와 speech-act를 제외하고, source 시점에 존재한 concept만 성능 점수에 포함한다.
- 데이터 gate는 scorable pair 6개 이상, 고유 preexisting external outcome 4개 이상이다. 성능 gate는 graph
  mean error가 과거 사용자 입력 frequency와 uniform random top-k 기대 error보다 모두 낮아야 한다.

### 구현과 단위 검증
- `scripts/research/b5_external_outcome_evaluation.py`: Neo4j read-only sequence/history/concept/sensor coverage.
- `tests/test_b5_external_outcome_evaluation.py`: 11 tests. sequence 경계, generic speech-act와 repeated cue,
  pre-turn availability, B4 conservative match, history future leak, random 기대값, sparse/pass gate,
  sensor eligibility, Cypher mutation 부재를 검증했다.

### 결과 A — 다음 사용자 입력
| 항목 | 결과 |
|---|---:|
| 보존 Experience | 12/12 |
| 올바른 `t→t+1` pair | 8 |
| scorable pair | **0/8** |
| preexisting non-cue outcome | **0** |
| novel non-cue outcome | **0** |
| graph / frequency / random error | 계산 불가(`null`) |

- 모든 target 입력은 `서울을 설명해줘→서울이 궁금해`, `컴퓨터를 설명해줘→컴퓨터가 궁금해`,
  `학습을 설명해줘→학습이 궁금해`처럼 동일 cue를 말투만 바꾼 반복이었다.
- predictor가 source cue 자체를 후보에서 제외하므로 cue 반복을 outcome으로 세는 것은 불공정하다. 이를
  제외하면 새 외부 정보가 하나도 없어 모델과 baseline의 승패를 측정할 수 없다.

### 결과 B — 다음 센서 관측 coverage
| 항목 | 결과 |
|---|---:|
| vision Experience | 45 |
| observed Concept가 있는 vision | 45 |
| NEXT_FRAME link | 36 |
| prediction snapshot이 있는 vision | **0** |

- frame sequence와 관측은 있지만, 각 frame 전에 무엇을 예측했는지가 저장되지 않았다. 현재 데이터로는
  pre-frame prediction과 next-frame outcome을 짝지을 수 없다.

### 판정
1. `data_gate=false`, `baseline_gate=false`, `promotion_gate=false`.
2. verdict는 `insufficient_external_outcome_data`. 이는 graph 성능 실패가 아니라 **평가 데이터 부재**다.
3. production scorer, threshold 0.02, min observations 3, canonical 배선은 그대로 둔다.
4. Neo4j write, Gemini/live 호출, `conversation_handler.py` 수정은 하지 않았다.

### 다음 [B-5.1]
- 사용자 입력 route: 최소 6 pair와 고유 비-cue external outcome 4개 이상을 실제 다양한 후속 입력으로
  수집한다. 같은 topic의 질문형만 바꾸는 반복은 표본으로 세지 않는다.
- 센서 route: vision 처리 전에 prediction snapshot을 남기는 별도 endpoint/DB 설계를 offline/unit에서
  검증한 뒤 NEXT_FRAME 관측과 비교한다.
- 어느 route든 graph error가 frequency와 random baseline을 모두 이길 때만 production 승격을 재검토한다.

## [B-5.1] preregistered external outcome live pilot (2026-07-15)

### 목적과 안전 경계
- B5의 `scorable pair=0`을 해소하되 결과를 본 뒤 문장을 고르는 것을 막기 위해 7개 메시지를 사전등록하고
  SHA-256 계약으로 고정했다. 센서 route는 pre-frame predictor 정의가 아직 없어 사용자 입력 route를 택했다.
- FastAPI env `CURIOSITY_EXTERNAL_OUTCOME_EVAL=1`과 request context
  `external_outcome_evaluation=true`의 double opt-in에서만 `external_deferred` 모드가 작동한다.
- deferred 모드는 Experience에 cue/prediction/input snapshot만 붙이고 same-turn error를 계산하지 않는다.
  Concept/BrainRegion EMA, CuriosityLog, integration priority는 변경하지 않는다. production 기본 동작도 바꾸지 않았다.

### 실시간 검토로 발견한 v1 오염
- 첫 사전등록 7-turn(`컴퓨터→로봇→카메라→기억→학습→경험→감정`)은 초기 계산상 graph가 baseline보다
  좋아 보였다. 그러나 pair를 직접 감사하니 질문 기능어 `어떻게`의 handler stem인 `어떻`이 cue와 external
  outcome에 동시에 남아 있었다. 의미 있는 graph hit는 1개뿐이었다.
- 이를 정상 성능으로 보고하지 않고 `어떻게/어떻`을 일반 기능어로 제외했다. invalid cue가 있는 pair는
  contaminated로 분리하고, graph hit 3개 이상, frequency보다 나은 pair 3개 이상, 개선 pair가 악화 pair보다
  많아야 한다는 robustness gate를 추가했다.
- v1 read-only 재평가는 contaminated 1, scorable 5, graph/frequency hit 모두 0,
  verdict=`insufficient_external_outcome_data`였다. 원본과 재평가 artifact는 삭제하지 않았다.

### v2.1 사전등록과 수집
- 메시지 흐름: `하늘→날씨→도시→사람→이름→비비→개발자→프로그램`.
- preflight: 7 messages, 6/6 scorable pairs, 고유 preexisting external outcome 7개, source마다 prediction 8개,
  contract SHA-256 `9c977463837208b69d3ec61054dba28fffc17158c6db0572cc07a433e911d5ce`.
- live audit: 7/7 Experience가 `external_deferred`; same-turn `prediction_error`와 `learning_progress` 없음.
  preflight cue Concept 9개의 curiosity state는 전후 동일했다.

### 최종 결과
| metric | graph | frequency | random expected |
|---|---:|---:|---:|
| mean error (낮을수록 좋음) | **0.833333** | **0.5** | 0.992315 |
| hit count | **1** | **3** | - |

- graph better/tie/worse than frequency pair는 `0/4/2`였다. data gate는 통과했지만 baseline gate와 robustness
  gate는 실패했다. verdict=`graph_did_not_beat_baselines`, `promotion_gate=false`.
- 유일한 graph hit `비비`도 frequency가 맞혔다. frequency는 graph가 놓친 `사람`, `이름`까지 맞혔다.
- 결론은 **외부 결과 데이터 수집 성공, 현재 graph-neighbor predictor 성능 실패**다. threshold를 낮출 문제가
  아니며 production에 승격하지 않는다.

### 쓰기·재현성·검증
- v1과 v2.1 live 수집은 총 14개 conversation Experience와 handler의 통상 Concept/관계를 Neo4j에 남겼다.
  evaluator는 read-only이고 deferred layer의 curiosity state write는 없었다. 라이브 기록은 감사 증거로 보존한다.
- v2.1 artifact를 라이브 호출 없이 별도 재평가해 모든 핵심 수치가 동일함을 확인했다.
- 전체 suite `58 passed`, py_compile, `pip check`, `git diff --check` 통과. 종료 후 port 8000 listener 없음.
  보호된 `conversation_handler.py` current/HEAD blob은 모두 `054d974095be7425692860909181fafd54f97a33`.
- artifacts:
  - `claudedocs/research/b5_1_external_outcome_pilot_20260715.json` (v1 원본)
  - `claudedocs/research/b5_1_external_outcome_pilot_v1_reevaluated_20260715.json` (v1 교정)
  - `claudedocs/research/b5_1_external_outcome_pilot_v2_1_20260715.json` (최종)

### 다음 [B-5.2]
추가 live 수집이나 threshold 조정 전에 저장된 sequence에서 query/ranking을 offline 진단한다. 현재 상위 예측의
hub/general concept 편향을 분해하고, per-cue top-k·transition-aware ranking·generic/hub penalty의 최소 ablation을
동일한 future-leak 없는 frequency/random baseline과 비교한다. 이 gate를 반복적으로 이길 때만 다음 live pilot을 연다.

## [B-5.2] graph predictor read-only ablation (2026-07-15)

### B5.1 선행 재감사
- 사용자 push 후 local/remote HEAD `42268bf` 일치와 clean worktree를 확인했다.
- 저장 artifact와 Neo4j read-only 재평가가 graph/frequency/random mean error
  `0.833333/0.5/0.992315`, graph/frequency hit `1/3`, `promotion_gate=false`를 그대로 재현했다.
- B5.1 성능 보고는 정확했다. push 전 작성된 체크포인트의 HEAD/미푸시 문구만 교정 대상이었다.

### 현재 predictor의 구조적 원인
- `prepare_curiosity_prediction()`은 선택 cue 전체의 `RELATES_TO` 이웃을 합친 뒤
  `max(coalesce(rel.hebb_strength, rel.strength, 0))` 한 값으로 전역 top-8을 고른다.
- candidate degree 벌점과 여러 cue의 공동 지지 보상이 없어 `문장`, `세상`, `형의` 같은 자주 연결된
  일반 concept가 한 개의 강한 edge만으로 상위권을 차지한다.
- RELATES_TO strength는 후속 학습에서 계속 변하지만 과거 버전이 없다. 현재 edge strength로 B5.1 시점을
  재계산하면 future leakage이므로 성능 ablation에는 사용하지 않았다.

### 시간누출 없는 후보와 안전장치
- source보다 엄격히 이전의 conversation Experience와 불변 `INVOLVES` concept만 사용했다.
- 후보는 historical co-occurrence 합, candidate document frequency로 hub를 누르는 cosine association,
  여러 cue에서 함께 지지된 후보를 먼저 두는 multi-cue cosine 세 가지다.
- ranking 함수에는 target input을 전달하지 않는다. source 이후 history와 mutable 관계 strength도 사용하지 않는다.
- 같은 6 pair로 후보 선택과 측정을 함께 했으므로 exploratory gate가 통과해도 production promotion은 항상 false다.

### 결과
| predictor | mean error | hit | vs frequency better/tie/worse | exploratory gate |
|---|---:|---:|---:|---|
| stored live graph | 0.833333 | 1 | 0/4/2 | false |
| historical co-occurrence | **0.75** | **2** | 1/3/2 | false |
| historical cosine | 0.916667 | 1 | 1/2/3 | false |
| historical multi-cue cosine | **0.75** | **2** | 1/3/2 | false |
| frequency baseline | **0.5** | **3** | - | - |

- co-occurrence 계열은 기존 `비비` hit에 `개발자` 하나를 부분적으로 추가했을 뿐이다. 첫 세 외부 전이
  `도시`, `사람`, `이름`과 마지막 `프로그램`은 계속 놓쳤다.
- cosine은 hub를 누르는 대신 데이터가 희박한 표면형/문장 파편을 올려 stored graph보다도 나빠졌다.
- `any_exploratory_gate_passed=false`, `production_promotion_gate=false`. production query와 threshold는 유지한다.

### transition-aware 경로가 아직 불가능한 이유
- conversation Experience `1,496`개 중 session_id, speaker_id, user_id가 있는 항목은 각각 `0`이고
  NEXT_TURN link도 `0`이다.
- timestamp로 전역 인접 Experience를 묶으면 서로 다른 사용자/실험 스트림 경계를 넘을 수 있다. 따라서
  근거 없는 transition 모델을 만들지 않았다.

### 검증과 다음 [B-5.3]
- 산출: `scripts/research/b5_2_graph_predictor_ablation.py`,
  `tests/test_b5_2_graph_predictor_ablation.py`,
  `claudedocs/research/b5_2_graph_predictor_ablation_20260715.json`.
- 전체 `64 passed`, py_compile, `pip check`, `git diff --check` 통과. DB write/Gemini/live server 호출 없음.
  FastAPI 8000 DOWN, 보호 handler current/HEAD blob `054d974…` 동일.
- 다음은 endpoint/DB층 research opt-in sequence ID와 turn index를 offline/unit으로 먼저 설계한다. 후보 선택용
  train sequence와 별도 preregistered held-out sequence가 생기기 전에는 추가 predictor tuning이나 production
  promotion을 하지 않는다.

## [B-5.3] sequence-grounded external outcome contract (2026-07-16)

### 목적
B5.2에서 conversation 1,496개에 session/user/NEXT_TURN 경계가 없음을 확인했다. timestamp 인접성을 임의로
이어 붙이는 대신, 앞으로 수집하는 external outcome turn에 명시적 sequence와 split을 부여한다. 이번 단계는
계약과 offline 검증만 수행하며 새 Gemini 대화나 Neo4j Experience write를 실행하지 않는다.

### 요청 계약과 endpoint 경계
- 필수: `external_sequence_id`, 0-based `external_turn_index`, `external_sequence_split`(`train|heldout`),
  `external_sequence_contract_sha256`.
- `external_outcome_evaluation`은 JSON boolean만 허용한다. env gate가 꺼져 있거나 metadata가 누락/단독 전달되면
  409/422로 fail-closed하며 기존 same-turn scorer로 조용히 돌아가지 않는다.
- endpoint는 handler 전에 형식과 Neo4j expected turn을 읽기 전용 검사한다. sequence 연구 metadata는 context에서
  제거해 보호된 `conversation_handler.py`에 전달하지 않는다. prediction snapshot이 없을 때도 handler 전 중단한다.

### DB 재검사와 연결
- `defer_curiosity_outcome_scoring()`은 managed write transaction 안에서 sequence state를 다시 읽는다.
- duplicate/gap, 기존 index 손상, sequence split/hash 변경, 동일 manifest hash의 train/heldout 교차 재사용을 거부한다.
- 성공 turn만 Experience에 sequence ID/index/split/hash를 기록하고 이전 Experience와
  `NEXT_EXTERNAL_TURN`을 연결한다. curiosity EMA, BrainRegion, CuriosityLog는 계속 변경하지 않는다.
- B5.1 live pilot request/audit도 새 필드를 사용하도록 갱신했다. 기존 B5.1 artifact의 read-only 재평가는
  graph/frequency error `0.833333/0.5`, promotion false를 그대로 재현했다.

### 검증
| gate | 결과 |
|---|---|
| offline contract matrix | **8/8 pass** |
| real Neo4j sequence-state query | `valid`, expected turn `0` |
| persistence Cypher | `EXPLAIN valid` (실행 write 없음) |
| DB writes / live collection | **0 / 0** |
| production promotion | `false` |
| canonical `tests/` suite | **71 passed** |

- artifact: `claudedocs/research/b5_3_sequence_contract_20260716.json`.
- py_compile, `pip check`, `git diff --check` 통과. FastAPI 8000 DOWN, 보호 handler current/HEAD blob
  `054d974095be7425692860909181fafd54f97a33` 동일.
- 기존 “전체 81 passed” 표기는 후속 B5.4 cross-check에서 중복/상이 범위 실행 수가 섞인 집계로 확인됐다.
  B5.4가 테스트 3개를 추가한 현재 canonical suite가 74개이므로 B5.3 동일 범위는 71개이며, 이를 교정했다.
- 현재 계약은 sequential single-writer research pilot용이다. production multi-writer 전에는
  `(sequence_id, turn_index)` unique constraint 또는 동등한 DB lock이 필요하다.

### 다음 [B-5.4]
1. 여러 train sequence의 문장·순서·manifest hash를 먼저 고정하고 train 데이터만 수집한다.
2. train에서 predictor와 hyperparameter를 결정한 뒤 code/algorithm hash를 freeze한다.
3. held-out 내용은 모델 선택 과정에 노출하지 않고 hash만 미리 등록한다. freeze 후 한 번만 수집·평가한다.
4. held-out에서 frequency/random 및 robustness gate를 모두 이길 때만 production 검토를 다시 연다.

## [B-5.4-A] minimal train gate and early stop (2026-07-16)

### 과검증 감사와 범위 축소
B5.1~B5.3은 target 오류, baseline 열세, sequence 경계 부재를 각각 분리했으므로 상위 목표에 필요한 단계였다.
하지만 후보 신호를 보기 전에 여러 train과 sealed held-out까지 모두 수집하면 검증 절차가 연구 병목이 된다. 따라서
B5.4-A는 B5.1 train에 새 7-turn train 하나만 더한 뒤, 합친 train에서 candidate가 frequency를 이길 가능성이
없으면 추가 수집을 중단하도록 축소했다. production lock/constraint, threshold 변경, held-out 공개는 범위에서 제외했다.

### manifest와 live 수집
- manifest: `scripts/research/manifests/b5_4_train_a_20260716.json`; SHA-256
  `3486eff0e169f3c4bf1420e924f85427d6747fa4405943dabe35dcace6911b6c`.
- 첫 read-only preflight에서 모든 문장 공통 cue `관계`를 발견했다. 이는 예측 이름이 아니라 cue 결과이므로 누출 없이
  live 전 `설명해줘` 형식으로 교정했다. B2 필터 적용 후 매 turn 핵심 cue 2개, 6/6 scorable pair, 고유 outcome
  6개, pair별 prediction count 8을 확인했다.
- live 7 turn은 모두 `external_deferred`, index `0..6`, audit error 0. Experience 7개와
  `NEXT_EXTERNAL_TURN` 6개가 저장됐고 Concept curiosity state는 무변경이었다.
- 새 sequence만 평가하면 graph/frequency error=`1.0/1.0`, hit=`0/0`; data gate=true지만 baseline/robustness/
  promotion gate=false다.

### 합친 train-only 비교와 판정
| variant | mean error | hit | vs frequency better/tie/worse | exploratory gate |
|---|---:|---:|---:|---|
| stored live graph | 0.916667 | 1 | 0 / 10 / 2 | false |
| historical co-occurrence | **0.875** | **2** | 1 / 9 / 2 | false |
| historical cosine | 0.958333 | 1 | 1 / 8 / 3 | false |
| historical multi-cue cosine | **0.875** | **2** | 1 / 9 / 2 | false |
| frequency baseline | **0.75** | 3 | — | — |

- train sequence 2개, 12 pair. random expected error `0.992371`.
- history는 source보다 엄격히 이전만 사용했고 target input, 미래 record, mutable relationship strength는 ranking에
  사용하지 않았다. candidate 중 exploratory gate를 통과한 것은 0개이며 production gate는 항상 false다.
- 이 결과는 sequence 저장 계약이 작동한다는 증거인 동시에, **현재 target/predictor 조합에는 held-out에 쓸 만한
  train 신호가 없다는 음성 증거**다. 따라서 추가 train, predictor freeze, sealed held-out를 중단했다.
- 현재 canonical `tests/` suite `74 passed`; `pip check`, py_compile, `git diff --check` 통과. 보호 handler blob
  `054d974095be7425692860909181fafd54f97a33` 무변경, 새 artifact 비밀 패턴 0건, FastAPI 8000 DOWN.

### 다음 [B-5.5]
임의의 다음 사용자 주제는 현재 cue만으로 예측 가능한 환경 outcome이 아닐 수 있다. 아기가 선택한 질문/행동에
조건부인 다음 사용자 반응, 또는 action-conditioned sensor outcome이 Phase 3의 “예측오차로 행동 선택” 목표에 더
직접 맞는지 target validity gate에서 비교한다. 이 판단 전 추가 live collection과 held-out 평가는 하지 않는다.

## [B-5.5] target validity gate (2026-07-16)

### 검증 질문
현재 예측 target이 단순히 외부에서 왔는가가 아니라, **아기가 선택한 action 뒤에 발생해 그 action의 결과를
학습하게 하는가?** target 정의와 현재 evaluation readiness를 분리해 다음 세 후보를 비교했다.

1. unconditioned next-user topic
2. action-conditioned PendingQuestion answer
3. action-conditioned next sensor outcome

필수 축은 외부성, deterministic pair, action identity, action→outcome 시간 순서, action 조건성, outcome 전 prediction,
curiosity/action-selection loop 연결이다. 새 live data와 DB write 없이 실제 Neo4j coverage와 B5.4 artifact만 읽었다.

### 관측 결과
| 후보 | 기존 pair/표본 | action/시간 근거 | pre-outcome prediction | current target gate |
|---|---:|---|---:|---|
| next-user topic | 7 turn / 6 link | assistant action과 인과 연결 없음 | 7 source snapshot | **false** |
| PendingQuestion answer | 18 question / 15 answer | 정상 시간 1, 시간 누락 14, source 누락 17 | 0 | **false** |
| next sensor outcome | 45 frame / 36 link | head pose 0, pose delta 0 | 0 | **false** |

- conversation 1,503개 모두 assistant output을 저장하고 1,263개에 질문 기호가 있으나, question action ID와 다음 user
  input을 잇는 경계가 없다. B5.4의 다음 input은 assistant 응답과 무관하게 사전 고정됐으므로 action-conditioned
  outcome으로 재해석할 수 없다.
- PendingQuestion의 question ID→answer endpoint는 구조상 가장 좋은 action→outcome 경계다. 하지만 CuriosityLog에서
  생성된 질문 0, 질문 표시 전 prediction 0이며 legacy 답변 15개는 prediction보다 먼저 노출됐다. 소급 예측은 future
  leakage이므로 coverage 증거 외에는 재사용하지 않는다.
- vision NEXT_FRAME만으로는 감각운동 target이 아니다. 실제 action 또는 head-pose delta와 그 action 전 prediction이
  모두 필요하다.

### 판정
- selected target=`null`; target-selection/evaluation-readiness/production gate 모두 false.
- **추천 schema**는 `action_conditioned_pending_question_answer`다. 이는 현재 데이터 통과가 아니라 다음 instrumentation
  비용 대비 우선순위다. 질문 ID가 action identity이고 기존 answer endpoint가 외부 결과를 명시하기 때문이다.
- artifact: `claudedocs/research/b5_5_target_validity_gate_20260716.json`.
- canonical `tests/` suite `80 passed`; `pip check`, py_compile, `git diff --check` 통과. DB write/live collection 0,
  handler blob `054d974095be7425692860909181fafd54f97a33` 무변경, FastAPI 8000 DOWN.

### 다음 [B-5.6]
PendingQuestion 생성/표시 전에 policy action provenance와 prediction snapshot을 원자적으로 저장하는 offline/unit 계약을
handler 밖 endpoint/DB층에 설계한다. 필수 필드는 `curiosity_log_id|policy_action_id`, `question_id`,
`prediction_captured_at`, `predicted_concept_ids`, train/heldout split, manifest hash다. 새 answer만 외부 outcome으로
받으며 기존 15답변 소급 점수화, 추가 live/held-out, threshold 변경은 금지한다.

## [B-5.6] PendingQuestion action-outcome contract (2026-07-16)

### 계약 경계
B5.6은 target 성능을 평가하지 않는다. 신규 연구 질문이 실제로 표시되기 전에 action provenance와 graph prediction을
고정하고, 이후 같은 question ID로 들어온 새 외부 답변만 outcome으로 닫을 수 있는지를 검증한다. 기존 질문·답변은
계약 이전 데이터이므로 coverage 외에는 사용하지 않는다.

- server env `CURIOSITY_QUESTION_OUTCOME_EVAL=1`과 request boolean을 모두 요구한다.
- provenance는 `curiosity_log_id` 또는 형식 검증된 `policy_action_id`, evaluation split은 `train|heldout`, manifest는
  64자리 SHA-256이다.
- endpoint read-only preflight 뒤 DB managed transaction이 action 중복, 동일 manifest의 split 교차 재사용,
  CuriosityLog 존재를 재검사한다.
- question/action/split/hash, `prediction_captured_at`, cue IDs, predicted IDs를 한 transaction으로 저장한 뒤에만
  Redis/SSE로 publish한다. prediction timestamp가 asked timestamp보다 늦거나 cue/prediction이 비면 거부한다.
- answer transaction은 동일 question이 pending이고 미답변인지 재검사한다. answer term 중 prediction 시각 이전에
  이미 존재했고 question cue가 아닌 Concept만 `external_outcome_concept_ids`로 기록한다.
- 이 단계는 prediction error를 계산하지 않고 Concept/BrainRegion EMA, integration priority, CuriosityLog,
  threshold/production predictor를 바꾸지 않는다.

### 호환성과 fail-closed 조건
- 연구 metadata 없이 호출되는 기존 생성·답변 API는 기존 method를 그대로 쓴다.
- 연구 metadata만 보내거나 flag가 boolean이 아니거나 server env가 꺼져 있으면 prediction/DB write 전에 거부한다.
- 연구 질문은 일반 status PATCH로 `answered`를 만들 수 없고 answer endpoint만 사용할 수 있다.
- 계약은 sequential single-writer research용이다. production multi-writer에서는 action key 중복을 DB 레벨에서 막는
  unique constraint 또는 lock이 필요하다.
- `conversation_handler.py` v30은 import/수정하지 않았다. 보호 blob은
  `054d974095be7425692860909181fafd54f97a33`으로 동일하다.

### 검증 결과
| gate/evidence | 결과 |
|---|---|
| offline contract matrix | **16/16 pass** |
| targeted B5.6 tests | **21 passed** |
| canonical `tests/` suite | **101 passed** |
| actual PendingQuestion / legacy answers | `18 / 15` |
| B5.6 research question / outcome | **`0 / 0`** |
| real outcome resolution read | preexisting Concept `1`개 반환 |
| DB query validation | state/persist/answer 포함 8종 `EXPLAIN valid` |
| DB writes / live / held-out | **`0 / 0 / 0`** |
| existing answer reuse / scoring / learning update | **`0 / 0 / 0`** |
| instrumentation contract gate | **true** |
| target validity / evaluation readiness / production | **false / false / false** |

- artifact: `claudedocs/research/b5_6_pending_question_action_outcome_20260716.json`.
- `git diff --check` 통과. B5.5 미커밋 변경을 보존해 현재 worktree에는 B5.5와 B5.6이 함께 있으며 commit/push는
  사용자가 요청하지 않아 수행하지 않았다.

### 다음 [B-5.7] — 사용자 승인 전 정지
신규 train question→answer pair만 최소 pilot로 수집한다. 먼저 action/question manifest와 hash를 고정하고,
가능하면 실제 CuriosityLog provenance를 사용한다. 이 데이터에서 target validity와 최소 train signal이 확인되기 전에는
held-out 수집, prediction scoring의 학습상태 연결, threshold 변경, production promotion을 하지 않는다.

## [B-5.7] action-conditioned train answer pilot (2026-07-16)

### 사전등록과 provenance
- train manifest: `scripts/research/manifests/b5_7_pending_question_train_a_20260716.json`
- contract SHA-256: `4e1e5d715005f3e4f391f0c761c8d081bfe452cc4ef4fd9cf09202266cc03c37`
- unused pending CuriosityLog 14개 중 cue와 graph prediction이 모두 있는 9개를 찾고, 사전 규칙에 따라 6개를 선택했다.
  source 분포는 learning-progress 1, legacy failure 3, legacy similarity 2다. 따라서 이것은 최소 action→answer
  계약 pilot이며 현재 curiosity policy의 순수 성능 표본은 아니다.
- 사용자가 앞서 준비된 여섯 설명을 최종 답변으로 명시적으로 채택했다. answer pack에는
  `answer_role=user_final`, `answer_provenance=user_reviewed_adopted`를 남겼다. 이는 사용자 승인 outcome이지만
  자발적 무보조 응답으로 과장하지 않는다.

### live 수집 절차
1. 질문을 표시하기 전에 action provenance, train split, manifest hash, cue IDs, predicted IDs와 timestamp를 transaction으로
   저장한 뒤 Redis/SSE로 publish했다.
2. 답변 직전 6개 전체를 read-only preflight했다. 모두 pending, prediction-before-question이었고 기존 non-cue outcome
   concept 수는 순서대로 `4/3/1/7/3/3`이었다. 하나라도 실패하면 첫 answer write 전에 중단하는 경계다.
3. answer endpoint로 6개를 순차 저장했다. 저장이 모두 끝난 뒤에만 봉인된 prediction IDs를 outcome IDs와 비교했다.
4. 답변 전후 해당 CuriosityLog의 status/error/progress/integration priority/update timestamp를 비교해 learning state 무변경을
   확인했다.

### 결과와 gate
| evidence/gate | 결과 |
|---|---|
| 신규 question / answer | `6 / 6` |
| action-linked ordered pair | `6 / 6` |
| external outcome | 총 `21`, 고유 `19` |
| target validity | **true** |
| exact-ID prediction hit | **`0 / 6` questions** |
| question별 recall error | **모두 `1.0`** |
| exploratory train overlap | **false** |
| learning state update | **false** |
| predictor freeze / held-out | **false / false** |
| evaluation readiness / production | **false / false** |

질문→답변 target 정의와 instrumentation은 실제 새 데이터에서도 유효했다. 하지만 현재 graph predictor는 19개 고유
outcome 중 하나도 맞히지 못했다. 이 음성 결과 때문에 추가 질문 수집, predictor freeze, held-out 수집을 중단한다.
다음 단계는 exact-ID/canonical alias 문제, cue-neighbor의 hub 편향, 질문 action과 답변 outcome의 관계 표현 부족을
read-only로 분리 진단하는 것이다. 이 진단 전 threshold와 production policy는 변경하지 않는다.

### 검증과 artifacts
- B5.7 targeted `9 passed`, B5.7+B5.6 계약 targeted `30 passed`, canonical `tests/` suite `110 passed`.
- `py_compile`, `pip check`, `git diff --check`, 변경 파일 비밀 패턴 검사 통과.
- 보호 `conversation_handler.py` blob `054d974095be7425692860909181fafd54f97a33` 무변경.
- 답변·감사 후 임시 FastAPI를 종료해 `127.0.0.1:8000`은 DOWN이다.
- answer pack: `scripts/research/inputs/b5_7_pending_question_train_a_20260716_answers.json`
- result artifact: `claudedocs/research/b5_7_pending_question_train_a_20260716.json`

## [B-5.8] measurement validity and source-aware offline ranker (2026-07-16)

### B5.7 target validity 재분류
B5.7의 기존 `target_validity_gate`는 6개 question/answer가 같은 action contract에 묶이고
`prediction≤asked≤answered`, non-empty cue/prediction/outcome을 만족하는지만 검사했다. 이는 action→outcome
**구조 계약**의 증거이지, machine-parsed outcome이 답변의 의미를 올바르게 대표한다는 증거가 아니다. 따라서 gate를
`structural_contract_gate`, `outcome_content_validity_gate`, 둘의 결합인 `target_validity_gate`로 나눴다. 기존 answer
pack은 사용자가 답변 문장을 채택한 기록은 있지만 outcome ID label을 별도로 검토한 기록은 없으므로
structural=true, semantic content=false, combined target=false다.

### outcome parser와 snapshot 수정
- 기존 parser는 cue parser의 12-term 기본 제한을 재사용해 답변 앞부분만 남겼다. `서로→서`, `맺는→맺`,
  `하는→하`, `모르는→모르` 같은 조사/어미 오인도 발생했다.
- handler 독립 전용 parser는 전체 문장에서 derived content term을 만든 뒤 최대 32개로 제한한다. 잘린 한 글자와
  일반 술어 stem/활용형을 제외하고, 후반의 `계산/로봇/제어`를 보존한다.
- question cue builder는 별도 함수로 분리해 B-2의 기존 조사/speech-act 필터와 12-term bound를 유지한다. 따라서
  answer outcome parser 수정이 질문 표시 전 prediction cue를 바꾸지 않는다.
- `1시간`, `60분`, `3,600초→3600초`, `24시간`을 compound로 보존한다. `24분의 1`의 `분`은 한국어 분수
  표현이므로 `24분` 시간 fact로 세지 않는다.
- 이후 신규 research PendingQuestion은 prediction ID 외에 name/score/rank와 snapshot version 2를 저장한다.
  live predictor 점수식은 그대로이며 동일 score에서만 candidate ID를 secondary key로 써 재현성을 확보했다.

### post-hoc source-aware ranker
offline 후보는 edge source, semantic relation direction/type, multi-cue support, candidate degree penalty와 bounded
2-hop을 사용한다. 설계 과정에서 같은 6개 train 답변을 이미 봤고 현재 relationship의 역사 버전을 복원할 수 없으므로
train diagnostic일 뿐이다. production gate는 결과와 무관하게 false다.

| evidence | 결과 |
|---|---:|
| stored outcome / 새 parser 재해석 outcome | `21 / 26` |
| bounded 2-hop reachable outcome | `10 / 26` |
| stored live top-8 hit | `0` |
| source-aware offline top-8 hit | `0` |
| semantic outcome content gate | `false` |
| held-out / production gate | `false / false` |

source/direction/hub 보정만으로 hit가 생기지 않았다. 16개 outcome은 bounded 2-hop candidate pool에도 없고, pool에
있는 10개도 top-8 밖이다. 따라서 현재 0-hit의 지배 원인은 단일 strength rank가 아니라 graph에 question action과
definition answer content의 관계가 충분히 표현되지 않은 점과 outcome label 계약 부재다.

### 검증 병목과 중단 규칙
최초 unbounded path query는 질문당 2,000개 path를 펼쳐 약 73초가 걸리고 artifact가 약 5.9MB가 됐다. 이는
과검증 자체가 연구 병목이 된 사례다. direct neighbor/cue 48, second-hop source/cue 12, neighbor/source 48의 명시적
bound를 두어 약 5초와 72KB로 줄였다. 이 bound도 train을 본 post-hoc 선택이므로 성능 주장이 아니라 진단 비용
통제다.

- artifact: `claudedocs/research/b5_8_measurement_validity_ranker_20260716.json`
- DB write, live collection, threshold/EMA/CuriosityLog update, production ranker 연결은 모두 없다.
- targeted B5.6~B5.8/live-curiosity `55 passed`, canonical suite `128 passed`; py_compile, pip check,
  diff check, literal secret scan 0건. 보호 handler blob `054d974095be7425692860909181fafd54f97a33`, port 8000 DOWN.
- 다음은 독립 reviewed semantic outcome label 계약과 action→answer relation 표현 설계다. 이를 고정하기 전에는
  held-out를 수집하지 않는다.

## [B-5.9] reviewed semantic outcome + action→answer relation proposal (2026-07-16)

### 목적과 경계

B5.8 parser가 만든 26개 token을 자동 정답으로 쓰지 않고, prediction 시점에 이미 존재한 Concept 중
답변 의미를 나타내는 후보를 별도 human-review 계약으로 분리한다. user-final answer 자체와 semantic
label 선택은 다른 provenance다. Codex가 고른 후보는 먼저 `draft_unreviewed`로 고정했고, 사용자가
6묶음 전체를 명시 승인한 뒤에만 `user_reviewed`/approved로 봉인했다.

### 구현

- `pending_question_semantics.py`: B5.7 contract hash, action/question ID, exact answer SHA-256, B5.8의
  time-valid outcome ID/name을 함께 검증한다. draft는 proposed만 허용한다. `user_reviewed`는 user role,
  timezone timestamp, 모든 후보 approve/reject, 질문당 최소 1 approved를 요구한다.
- 의미 후보는 6질문 합계 25개다. parser artifact의 `연결해` 같은 술어 조각은 제외했고, `1시간`
  답변은 예측 시점에 존재하던 scoreable Concept이 `하루`뿐이라 그것만 제안했다. `60분/3600초`는
  유용한 새 지식일 수 있으나 이 pilot의 pre-existing prediction target으로 소급 사용하지 않는다.
- action→answer는 `PendingQuestion-[:ANSWER_EVIDENCES_CONCEPT]->Concept` 25개 offline proposal로
  표현했다. 현재 Neo4j schema/transaction에는 쓰지 않았다.

### 결과와 다음 gate

- report: question 6, semantic label 25 approved, relation proposal 25, review=`user_reviewed`.
- semantic target validity=true, database write=false, heldout=false, production promotion=false.
- 신규 split/semantic/adapter-promotion unit `10 passed`, canonical suite `138 passed`, pycompile/pip/diff check 통과.
  Gemini/live server/Neo4j write/GPU 학습 없음.
- 이 6개는 train-only이므로 바로 production 승격하지 않는다. relation schema integration, leakage-safe
  core rerun과 별도 sealed heldout 설계가 남는다.

### JARVIS 방향에 대한 감사 결론

현재는 기억 그래프, 제한적 가소성, opt-in LoRA sleep consolidation, 호기심 계측을 가진 연구
프로토타입이다. 하지만 learned local core가 wake 응답에 쓰이지 않고 B5.7/B5.8 action-conditioned
예측 hit도 0이며, embodied action policy·장기 자율계획·clean continual promotion/rollback이 없다.
따라서 “스스로 학습해 JARVIS까지 간다”는 결론은 현재 증거로 지지되지 않는다. 올바른 표현은
“그 방향의 일부 메커니즘을 시험하는 기반이며, 핵심 폐루프와 스케일 가능성은 아직 미검증”이다.

## [J-0] JARVIS 방향 research domain 재설계 (2026-07-16)

B5.9의 25개 의미 후보를 사용자가 모두 승인해 semantic target validity는 true가 됐다. 그러나 이는 같은 6개
train 질문의 의미 라벨이 올바르다는 증거일 뿐 predictor 성능이나 자기성장을 뜻하지 않는다.

2025–2026 연구를 arXiv에서 찾고 Semantic Scholar year/venue/citation/influential citation으로 교차검증한 결과,
continual/test-time learning, autocurriculum, world model, safe self-modification, action verifier 각각에는 실험 근거가
있지만 open-world lifelong loop 전체의 입증된 해법은 없었다. 이 간극을 추적하기 위한 working label로
`Grounded Developmental Self-Improvement`를, Baby용 시스템 가설로 `Developmental Causal Self-Compiler`를
정의했다. 둘 다 새 분야 또는 JARVIS 달성 주장이 아니다.

다음 [J-1]은 relation DB write나 GPU 학습보다 먼저 `PendingQuestion`을 안전한 epistemic action으로 쓰는
Question-as-Experiment offline contract다. graph와 local core가 질문 전에 비교 가능한 확률 분포를 만드는지,
그 disagreement가 random보다 정보량이 큰 질문을 고르는지, reviewed label로 calibration을 측정할 수 있는지를
학습 없이 확인한다. 상세 설계·문헌표·중단 규칙은
`claudedocs/research/JARVIS_GROUNDED_DEVELOPMENTAL_SELF_IMPROVEMENT_2026-07-16.md`에 고정했다.

## [J-1.0] Question-as-Experiment offline contract + readiness audit (2026-07-16)

graph/local-core 동일 Concept universe probability, JSD 기반 deterministic 질문 선택, reviewed multi-label
Brier/log-loss/ECE/top-k evaluator를 handler/DB와 분리해 구현했다. probability에는 model snapshot뿐 아니라
calibration dataset/calibrator hash, 양성·음성 표본 수, fitted timestamp가 필요하며 출처 없는 softmax는 거부한다.

기존 6개 B5.9 질문에는 reviewed label 25개와 historical graph ranked ID가 있지만 calibrated graph/local-core
probability, multi-candidate decision, pre-question predictor/calibrator seal이 없다. 따라서 readiness artifact는
`contract_gate=false`이며 learning/DB write/heldout/production도 false다. 남은 CuriosityLog 8개 중 graph-eligible
3개는 문장 품질과 기존 질문 중복 때문에 calibration 후보에서 제외했다.

다음 [J-1.1]은 새 고품질 train-calibration 질문 사전등록과 질문 표시 전 graph/local-core raw-score shadow
capture다. calibrator를 fit하기 전 probability/JSD 성능 수치를 만들지 않는다.
