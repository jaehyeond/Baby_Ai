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
- 남은 검증: FastAPI 전체 스택과 실제 반복 대화를 통한 신호 빈도/질 평가. Gemini 실 호출은 이번 구현
  검증에서 수행하지 않았으며, 실측 전 threshold를 조정하지 않는다.
