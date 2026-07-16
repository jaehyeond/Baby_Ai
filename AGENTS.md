# AGENTS.md — Baby AI Brain (Claude Code · Codex 공용 마스터)

> **크로스툴 단일 진입점.** Codex는 이 파일을 자동 로드한다. Claude Code는 `CLAUDE.md` 최상단의 `@AGENTS.md`로 임포트한다.
> ⚠️ **Claude auto-memory(`C:\Users\SOGANG\.claude\projects\E--A2A\memory\`)는 Claude 전용 — Codex는 못 읽는다.** Codex는 아래 "상세 문서"의 경로를 직접 열어라. **세션 인계는 반드시 이 파일 + repo 공유 파일을 통해서만** 한다.

## 🔖 현재 상태 / 재개 (2026-07-16 체크포인트)
**"이어서 하자"면 여기부터.** 상세 이력·수치는 `CHANGELOG.md` 최상단 + `claudedocs/**/2026-07*.md`.

### 어디까지 왔나 (한눈에)
**자기학습 구성요소는 구현됐지만 JARVIS형 폐루프는 미검증** (현재 push 기준 `DB_Renewal` local/remote HEAD `ec98ed2`; B5.5 이후와 B5.9 감사 수정은 현재 미커밋).
- Phase 0 기반 ✅ · **Phase 1 가소성 ✅**: RW 음성증거(w_ab→P(b|a))=자기학습 신호, **다양성 주도**(prequential서 빈도·암기 초과, time-shuffle서 붕괴=진짜 시간학습). `PHASE1_PLASTICITY_FINDINGS.md`.
- **Phase 2 코어 내재학습 ⚠️ 증거 재감사 필요** (`PHASE2_SLEEP_DISTILL_2026-07-13.md`): 학습코어·CLS·LoRA weight update·어댑터 영속·opt-in 야간 훅은 실제 구현돼 있다. 다만 2026-07-16 감사에서 실 Neo4j 실험의 관계-row split이 동일 concept pair를 train/test에 겹치게 할 수 있고, 야간 job은 평가쌍을 같은 run replay에 직접 포함한 것을 확인했다. 현재 그래프 재현에서 기존 split의 pair overlap은 `18/250=7.2%`. 과거 identity MRR와 누적 MRR은 **fit/weight change/persistence의 탐색 증거**로 강등하며, pair-disjoint 3-seed 재실험 전 일반화·자기성장 확정 근거로 쓰지 않는다. 코드에는 pair canonicalization, train/eval 완전분리, 비퇴행 adapter save gate를 추가했다.
- **Phase 4 embodiment**: 파이프라인 준비됨(pose/depth 캡처·`NEXT_FRAME` 시퀀스)이나 **Quest 데이터 없음=병목**. `EMBODIMENT_PIPELINE_2026-07-12.md`.
- 인프라: Gap#6 brain health 모니터링 상시화 · 보안 fix(.env.bak) · torch(cu124)/transformers/peft `.venv` 설치 · RTX 4070 12GB.

### 핵심 진단 (정직)
1. **"배우지만 무기력" 일부 해소**: 그래프의 turn별 prequential 예측오차가 이제 learning-progress를 통해 **통합 우선순위와 호기심 타깃에 영향**. 단 로컬 trainable 코어 자체는 여전히 wake 응답/Gemini prompt에 직접 쓰이지 않으므로 행동 영향은 아직 부분적.
2. 병목은 데이터 밀도만이 아니다. **평가 누수 방지, action-conditioned grounded outcome, learned core→wake 행동 연결, continual promotion/rollback**도 독립적인 필수 병목이다. Quest 다양장면은 embodiment 데이터 병목을 풀지만 이것만으로 JARVIS가 되지는 않는다.

### 다음 작업 플랜 (2-트랙)
- **[A] 사용자 몫(근본 레버)**: Quest **다양장면** 수집(방·주방·야외·사람, 머리 움직이며; 스케일링연구=다양성>밀도) + 살아있는 코어 **켜기**(`LOCAL_CORE_DISTILL=1` + Neo4j 상시). 계약 `docs/QUEST_APK_CONTRACT.md`.
- **[B] Phase 3 예측오차 루프 ✅ 합성검증+라이브 배선+실 대화 운영검증(2026-07-14)**: `live_curiosity.py` + endpoint pre/post snapshot + Neo4j concept/region EMA. raw surprise는 관측만 하고 **오차 감소량만** `integration_priority`와 `CuriosityLog(source=learning_progress)`를 구동. Redis는 신규 `baby_ai_robot_v4`로 전체 SSE 경로 복구.
- **[B-2] cue 품질 개선 ✅**: endpoint 전용 조사 정규화와 cue/이웃 2단계 조회. speech-act 일반어(`설명해줘`, `궁금해`, `무엇이` 등)는 cue에서 제외하고 사용자 입력에서 복제된 비-cue Concept도 outcome 점수에서 제외한다. 실제 snapshot은 세 문장 모두 cue=`컴퓨터`만 선택. `conversation_handler.py` blob `054d974…` 무변경.
- **[B-3] 운영 표본 확대 완료 — 음성 결과가 다음 병목 확정**: 서울/컴퓨터/학습 9턴 모두 error=1.0, 후속 컴퓨터 3턴도 error=1.0·progress=0·gate=F. 초기 응답 잘림은 `gemini-flash-latest`가 512 중 thinking 487토큰을 써 `MAX_TOKENS`가 된 원인으로 분리했고, 공식 `google-genai` + stable `gemini-2.5-flash-lite` + thinking budget 0으로 완전 응답을 복구했다. 그러나 예측 `신기한`과 다음 실제 `신기하`처럼 형태별 Concept ID가 갈라져 exact-ID metric은 계속 실패한다. **다음=[B-4] handler 밖 canonical concept scoring을 offline/unit으로 먼저 설계·검증. threshold 조정·추가 live 표본 금지.**
- **[B-4] canonical scoring offline gate 실패(정직)**: 보존 12 Experience read-only replay에서 exact mean error `1.0`→canonical `0.9833`, 개선 1/12(`신기한↔신기하`)뿐. scored actual 53개 중 40개(75.5%)가 Experience 이후 신규 Concept라 사전 ID 예측 불가. 사전 존재 13개만 제한해도 scorable 9턴 mean error `0.8889`, hit 1개. 따라서 canonical scorer는 production에 연결하지 않았다. **다음=[B-5] 동일 turn의 자기생성 응답 대신 다음 사용자 입력/센서 관측 같은 외부 outcome을 예측 대상으로 삼는 offline sequence 설계.**
- **[B-5] external outcome offline gate = 데이터 부족으로 판정 불가(2026-07-15)**: 12개 보존 turn을 4개 독립 시퀀스의 8개 `t→t+1` pair로 정확히 재구성했다. 다음 사용자 입력은 모두 동일 cue 반복(`서울/컴퓨터/학습`)뿐이라 cue 제외 후 scorable external outcome `0`, graph/frequency/random error는 계산 불가. 센서 쪽은 vision Experience 45개·NEXT_FRAME 36개가 있으나 prediction snapshot이 붙은 vision Experience가 `0`이라 역시 점수화 불가. `promotion_gate=false`; production·threshold는 변경하지 않았다. **다음=[B-5.1] 최소 6쌍·고유 비-cue 외부 outcome 4개 이상을 만드는 다양한 후속 사용자 입력 수집, 또는 vision pre-frame prediction snapshot 설계 후 재평가.**
- **[B-5.1] 외부 outcome 사용자 입력 파일럿 완료 — 데이터 gate 통과, 성능 gate 실패(2026-07-15)**: 7개 사전등록 입력으로 6개 `t→t+1` pair와 고유 preexisting outcome 7개를 확보했다. same-turn LLM 점수 오염을 막는 double opt-in `external_deferred` 모드에서 Concept curiosity state는 무변경이었다. 깨끗한 v2.1 재평가에서 graph mean error `0.833333`(hit 1)로 frequency `0.5`(hit 3)보다 나빴고, graph가 frequency를 이긴 pair도 `0/6`이라 `promotion_gate=false`. **다음=[B-5.2] 추가 live 수집·threshold 조정보다 먼저, 저장된 외부 sequence에서 hub/general concept 편향을 진단하고 per-cue/transition-aware predictor를 frequency baseline과 offline 비교.**
- **[B-5.2] predictor ablation 완료 — 개선 후보도 frequency gate 실패(2026-07-15)**: production의 cue-neighbor union + `max(mutable edge strength)`는 degree penalty와 multi-cue 보상이 없고 과거 strength 버전을 복원할 수 없다. 따라서 source보다 엄격히 이전의 conversation Experience/INVOLVES만으로 co-occurrence, cosine, multi-cue cosine을 read-only 비교했다. 최고 후보 co-occurrence/multi-cue는 mean error `0.75`, hit `2`로 stored graph `0.833333`, hit `1`보다 조금 나았지만 frequency `0.5`, hit `3`에 여전히 패했다. cosine은 `0.916667`. 1,496 conversation에 session/speaker/user ID와 NEXT_TURN이 모두 `0`이라 안전한 transition 학습도 불가. **다음=[B-5.3] opt-in sequence boundary/turn-index 계약을 offline/unit으로 먼저 설계하고, train/held-out가 분리된 여러 사전등록 sequence를 확보.**
- **[B-5.3] sequence-grounded 계약 완료 — live 수집 전 fail-closed 경계 확보(2026-07-16)**: research request에 sequence ID, 0-based turn index, `train|heldout`, manifest SHA-256을 모두 요구한다. endpoint가 handler 전 형식/DB 순서를 검사하고 DB가 snapshot 저장 transaction 안에서 재검사한 뒤 `NEXT_EXTERNAL_TURN`을 연결한다. 중복·gap·split/hash 변경·train/heldout hash 재사용을 거부하고 eval env off/비 boolean flag/snapshot 없음도 normal scoring으로 fallback하지 않는다. offline matrix `8/8`, 실제 Neo4j state query와 persist Cypher `EXPLAIN` 통과, canonical `tests/` suite `71 passed`; DB write와 live collection은 `0`. **다음=[B-5.4] train manifest들을 먼저 사전등록·수집하고 predictor를 freeze한 뒤, 내용은 봉인하고 hash만 미리 고정한 별도 held-out sequence로 1회 평가.**
- **[B-5.4-A] 최소 train gate 실패 — 추가 수집·held-out 조기중단(2026-07-16)**: B5.3 push `7f0d48e`에서 시작해 새 7-turn manifest(hash `3486eff0…`)를 고정했다. 예측 이름을 보지 않는 preflight에서 일반 cue `관계`를 발견해 live 전 `설명해줘`(B2 speech-act 제외어)로 교정했고, 핵심 cue 2개·6/6 scorable pair·고유 outcome 6개를 확보했다. live 7 turn은 모두 `external_deferred`, index `0..6`, `NEXT_EXTERNAL_TURN` 6개로 저장되고 cue curiosity state는 무변경이었다. 그러나 새 sequence에서 graph/frequency 모두 error `1.0`, hit `0`; B5.1과 합친 train 12 pair에서도 최선 historical co-occurrence/multi-cue error `0.875`, hit `2`가 frequency `0.75`보다 나빴고 개선/동률/악화=`1/9/2`라 exploratory gate=false. **비용·과검증 중단 규칙에 따라 추가 train, predictor freeze, sealed held-out, production 승격을 모두 중단한다. 다음은 임의의 다음 사용자 주제가 올바른 예측 target인지 B5.5에서 재검토한다.**
- **[B-5.5] target validity gate — 현재 유효 target 0, 질문→답변 schema만 추천(2026-07-16)**: 다음 사용자 주제는 명시적 6 link·pre-turn snapshot 7개가 있어도 아기 action에 조건부가 아니고 B5.4 train signal도 없어 기각했다. `PendingQuestion`은 질문 ID→외부 답변 구조가 가장 맞지만 18개 중 답변 15, 정상 `asked_at≤answered_at` 1, 시간 누락 14, source 누락 17, CuriosityLog 생성 0, 질문 전 prediction 0이라 기존 표본은 소급 점수화할 수 없다. vision은 45 frame·36 `NEXT_FRAME`에도 head pose/pose delta/prediction이 모두 0이라 보류했다. target selection/evaluation readiness/production gate 모두 false. **다음=[B-5.6] handler 밖 PendingQuestion 생성 시 질문 표시 전에 policy action ID+prediction+split/hash를 저장하고, 새 외부 답변만 outcome으로 받는 offline/unit 계약. 기존 15답변 재사용·추가 live·held-out 금지.**
- **[B-5.6] PendingQuestion action→outcome 계약 완료 — instrumentation만 통과(2026-07-16)**: 신규 research 질문은 `CURIOSITY_QUESTION_OUTCOME_EVAL=1`과 request boolean을 함께 요구하고, `curiosity_log_id|policy_action_id`, train/heldout split, manifest SHA-256을 검사한다. endpoint preflight 후 DB transaction이 action 중복·cross-split hash·CuriosityLog 존재를 재검사하고, question/cue/prediction/captured time을 **SSE 표시 전** 원자 저장한다. 신규 answer는 prediction 시각 이전에 존재한 non-cue Concept만 외부 outcome으로 기록하며 score/EMA/CuriosityLog/threshold는 갱신하지 않는다. legacy 18질문·15답변은 그대로이며 research question/outcome 0, offline matrix `16/16`, write Cypher 8종 `EXPLAIN`, canonical tests `101 passed`, handler blob 무변경. **instrumentation gate=true지만 target validity/evaluation/production gate=false. 다음=[B-5.7] 사용자 명시 승인 후 신규 train 질문만 최소 pilot; held-out·점수화는 train signal 전 금지.**
- **[B-5.7] 신규 train 질문→답변 pilot 완료 — 구조 계약 통과, predictor signal 실패(2026-07-16)**: manifest hash `4e1e5d71…` 아래 CuriosityLog-linked 질문 6개를 prediction-before-question으로 저장하고 사용자가 검토·채택한 답변 6개를 전달했다. pair 6/6이 action/timestamp/non-cue outcome 구조를 만족하고 기존 extractor 기준 outcome 총 21·고유 19개였지만, B5.8 재감사에서 이것은 semantic target validity가 아니라 **structural contract gate**였음이 확인됐다. 봉인 해제 후 exact-ID prediction hit는 `0/6`, 모든 error `1.0`; learning state는 무변경, predictor freeze/held-out/evaluation/production은 모두 false다.
- **[B-5.8] measurement validity + offline source-aware ranker 완료 — production 승격 차단(2026-07-16)**: handler 독립 outcome parser가 첫 12개 편향과 `서/맺/하/모르` 조각을 제거하고 `1시간/60분/3600초/24시간`, 후반 `계산/로봇`을 보존한다. question cue는 별도 builder로 기존 B-2 계약을 유지한다. prediction snapshot은 이후 질문부터 score/rank까지 저장하며 live rank tie는 concept ID로 결정한다. B5.7의 `target_validity`를 structural/content gate로 분리했고 독립 검토 outcome label이 없어 semantic content gate=false로 교정했다. source·direction·relation type·multi-cue·degree와 bounded 2-hop을 쓰는 **offline-only** 랭커를 같은 6개 train에 적용했지만 새 parser 기준 outcome 26개 중 2-hop reachable 10개, top-8 hit `0`; stored live도 `0`이다. canonical tests `128 passed`, handler blob 동일. 따라서 가중치 조정 문제가 아니라 answer relation 표현/coverage 문제이며 held-out·production은 계속 금지한다. artifact `b5_8_measurement_validity_ranker_20260716.json`.
- **[B-5.9] reviewed semantic outcome + action→answer relation proposal 완료(2026-07-16)**: B5.8의 prediction-time-valid Concept에서 의미 후보 25개를 정확한 user-final answer hash/question/action에 묶었고, 사용자가 6묶음 전체를 명시 승인해 `user_reviewed`/25 approved로 봉인했다. semantic target validity gate=true지만 같은 6개 train의 사후 라벨이므로 held-out/production gate는 false다. `PendingQuestion-[:ANSWER_EVIDENCES_CONCEPT]->Concept` 25개는 schema 검토 가능한 offline proposal이며 DB write는 아직 0이다. 동시에 Phase 2 평가 누수를 교정해 pair-disjoint split과 adapter 비퇴행 저장 gate를 추가했지만 GPU 재학습은 실행하지 않았다. **다음=JARVIS형 폐루프의 research domain을 재설계하고, relation schema·clean core rerun·future canary의 우선순위를 정한다.**
- **[J-0] JARVIS 방향 연구 재설계 완료(2026-07-16)**: 2025–2026 continual/test-time learning, autocurriculum, world model, action verifier, safe self-modification 문헌을 arXiv 검색 후 Semantic Scholar로 교차검증했다. 보장된 JARVIS 경로는 없지만 조각별 근거는 있으며, Baby의 미검증 연결부를 `Grounded Developmental Self-Improvement`(working label)와 `Developmental Causal Self-Compiler` 시스템 가설로 정리했다. 새 분야·세계 최초 주장은 금지한다. Zoey OS Reel은 출처·미검증 항목을 함께 기록하고 **병렬 `관측/UI` 참고**로만 격리했다. J1–J3 gate·schema·학습 데이터는 override하지 않는다. **다음=[J-1] Question-as-Experiment offline contract: graph/local-core 사전 확률, disagreement 기반 질문 선택, reviewed label calibration을 학습 없이 먼저 측정.** 상세 `claudedocs/research/JARVIS_GROUNDED_DEVELOPMENTAL_SELF_IMPROVEMENT_2026-07-16.md`.
- **[J-1.0] Question-as-Experiment offline contract 완료·legacy readiness blocked(2026-07-16)**: graph/local-core 동일 universe probability, JSD 질문 선택, multi-label Brier/log-loss/ECE/top-k, exact question/label/model/calibrator hash와 pre-question timestamp를 fail-closed로 구현했다. 임의 softmax를 막기 위해 calibration dataset/calibrator hash와 양성·음성 표본 provenance도 요구한다. 기존 6개는 reviewed target 25개와 graph ranked ID만 있고 calibrated graph/local-core probability, multi-candidate decision, pre-question model/calibrator seal이 없어 `contract_gate=false`; DB/write/learning/heldout/production 모두 false다. 남은 legacy CuriosityLog 8개 중 graph-eligible 3개도 문장 품질·중복 때문에 채택하지 않았다. 신규 targeted `8 passed`, 전체 suite `146 passed`, handler blob 동일. **다음=[J-1.1] 새 고품질 train-calibration 질문 사전등록 → 질문 표시 전 graph/local-core raw score+snapshot hash 봉인 → calibrator fit. GPU shadow inference는 별도 명시 승인 전 실행 금지.**
- **[C] 자율·대안**: 운영화(실제 켜서 며칠 성장추적) + collapse(effective rank≈2) 장기감시.
- **⚠️ 메타**: B5.9 label content는 user-reviewed라 validity=true지만 train-only라 predictor 성능 증거는 아니다. B5.8 source-aware 2-hop은 train top-8 hit 0이며 Phase 2의 기존 실그래프/야간 MRR도 leakage-safe 재현 전 과대해석 금지다. threshold와 production predictor는 유지하고 relation schema 검토 전 DB write, clean train signal 전 held-out/승격을 금지한다. J-0의 GDSI/DCSC도 연구 가설이지 JARVIS 가능성의 실험 증거가 아니다. J1 probability는 calibration provenance 없이는 생성·보고 금지다.
- (보류·비가역, 사용자 확인 후) 방향성 엣지 마이그레이션 + RW 프로덕션 `hebbian_update` 반영.

### 전제
Neo4j(Baby_Robotics, bolt 7687) **현재 UP**(세션마다 Desktop Start 필요), B5.7 임시 FastAPI 8000은 답변 감사 후 종료해 **현재 DOWN**이다. **Redis `baby_ai_robot_v4` 현재 UP·SSE 검증 완료**(`REDIS_URL` 비밀값은 `.env`에만 보관). Phase 2 실행엔 GPU(RTX 4070)+`.venv`. 살아있는 코어 켜려면 `LOCAL_CORE_DISTILL=1`. 라이브 그래프 비파괴·conversation_handler(v30) 미변경 원칙 유지.

## 🧭 불변 원칙 (요약)
- **제1원칙**: 인간 뇌를 본떠 아기부터 키우는, 로봇 이식용 AI 뇌. **신경과학적 타당성 > 코드 최적화.** LLM = 교체 가능한 몸, 학습/기억/성장 = LLM-free 내부 그래프 알고리즘.
- **북극성**: 진짜 자기학습 = 경험이 코어 파라미터를 바꿈. frozen-LLM+graph는 자기학습 아님. **"API 탈피 = 자기학습 전환"은 같은 한 수**(→ 로컬 trainable 코어).
- **아키텍처**: Brain = FastAPI + Neo4j + Redis 백엔드; Quest/PC/로봇 = client. (구 Supabase/Edge Function 아님.)
- **프로그램**: 자기성장 아기 뇌 Phase 0~5, 장기 ~1.5~3년. 마일스톤 = 예측오차 곡선 하강(월 아님).

## ⚙️ 코드 컨벤션 (필수 — 상세는 CLAUDE.md)
- **"정의만 되고 호출 안 됨" 금지**: 새 함수 추가 시 호출 지점 grep 검증(이 프로젝트 5회+ 반복 실수).
- **`conversation_handler.py`(v30) 미변경**: 수정은 endpoint/db층에서(MVP 제약).
- 새 의존성 신중(분석 스크립트 예외). **git commit·push는 사용자 명시 시만.**
- 실행: `python -m neural.baby.api_server --port 8000`(상대 import). brain LLM = Gemini(`gemini-2.5-flash-lite`, thinking budget 0).

## 📍 상세 문서 (어디를 읽나)
| 무엇 | 경로 | 접근 |
|---|---|---|
| 세션 로그(최신) | `CHANGELOG.md` 최상단 | 공유 |
| 현재 상태 | `Task.md` 상단 배너 | 공유 |
| 상위 로드맵 | `ROADMAP.md` | 공유 |
| 설계문서 | `docs/IDENTITY_ACCESS_CONTROL.md` | 공유 |
| Claude 상세 규약(skills·subagents·세션프로토콜) | `CLAUDE.md` | 공유(Codex도 읽을 것) |
| **전략·프로그램(최상위/북극성)** | `C:\Users\SOGANG\.claude\projects\E--A2A\memory\` → `MEMORY.md`, `program_roadmap_2026-07.md`, `self_learning_architecture_2026-07.md`, `beyond_api_llm_strategy_2026-07.md`, `identity_access_control_2026-07.md` | **Claude 자동** / Codex는 경로로 직접 |
| 재사용 연구지식(자기학습 서베이) | `D:\Obsidian\Bandi\강화학습\자기학습 AI 프런티어 2026 (경험의 시대).md` | 공유(볼트) |

## 🤝 하이브리드 도구 규율 (Claude ↔ Codex)
- **동시 실행 금지**: 같은 프로젝트의 `.serena`·Claude auto-memory·MCP memory에 두 도구 **동시 쓰기 금지**(race condition). **순차 인계**: 한 도구 종료 → 공유 파일로 결과 남김 → 다른 도구 시작.
- **인계 매체 = 공유 파일**: 이 AGENTS.md("현재 상태/재개") + CHANGELOG/Task/ROADMAP/docs + Bandi 볼트. Claude auto-memory 요지는 이 파일에 반영해 둘 것(Codex가 볼 수 있도록).
- **세션 종료 시(양 도구 공통)**: `CHANGELOG.md` 갱신 + **이 파일의 "현재 상태/재개" 섹션 갱신**. (Claude는 추가로 auto-memory도 갱신.)

## 📂 어디서 열까
- **Codex**: `E:\A2A\our-a2a-project`에서 열면 이 AGENTS.md 자동 로드 → "이어서 하자" 작동.
- **Claude Code**: `E:\A2A`에서 열면 auto-memory 자동 로드(권장); `our-a2a-project`에서 열면 CLAUDE.md→`@AGENTS.md`로 이 체크포인트 로드. 어느 쪽이든 재개됨.
