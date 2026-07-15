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
