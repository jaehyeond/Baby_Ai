# JARVIS 방향 재검토: Grounded Developmental Self-Improvement

> 날짜: 2026-07-16 (KST)  
> 상태: 연구 가설 및 단계별 실행안. JARVIS/AGI 달성 증거가 아님.  
> 보호 경계: `conversation_handler.py` v30 무수정, DB write 없음, production promotion 없음.

## 1. 결론

JARVIS 수준으로 갈 **알려진 보장된 방법은 없다**. 그러나 방법 자체가 없다고 결론 내릴 근거도 없다. 현재 연구는 다음 구성요소를
각각 보여 주고 있다.

1. 경험을 압축하는 장기 기억과 test-time adaptation
2. 스스로 과제를 만들고 검증 가능한 보상으로 학습하는 autocurriculum
3. 세계 모델을 이용한 예측과 계획
4. 자기 코드나 파라미터 후보를 만들고 경험적으로 평가하는 self-improvement
5. 실제 행동 전후를 비교하는 forward/inverse verifier

아직 입증되지 않은 부분은 이 조각들을 개방된 현실 환경에서 안전하게 하나의 lifelong loop로 닫는 것이다. 따라서 Baby의 정직한
목표는 다음 세 단계로 나눠야 한다.

| 목표 | 현재 판단 |
|---|---|
| 개인화되고 지속적으로 개선되는 조수 | 공학적으로 도전 가능 |
| 현실 행동으로 배우는 embodied lifelong learner | 유망하지만 미해결 연구 |
| 영화 속 open-domain JARVIS/범용지능 | 달성법과 일정 모두 미확립 |

## 2. 이번 승인으로 확정된 B5.9 상태

- 6개 `PendingQuestion`의 의미 라벨 후보 25개를 사용자가 모두 명시적으로 승인했다.
- label pack은 `user_reviewed`, 각 decision은 `approved`로 봉인되었다.
- `semantic_target_validity_gate=true`이다.
- 같은 6개 질문에서 만든 train-only 데이터이므로 `heldout_gate=false`, `production_promotion_gate=false`를 유지한다.
- `PendingQuestion-[:ANSWER_EVIDENCES_CONCEPT]->Concept` 25개는 offline proposal일 뿐이며 Neo4j에는 쓰지 않았다.
- 이 승인은 “답변 의미 target이 사람의 의도와 맞는다”는 증거이지 predictor 성능 또는 자기학습 성장을 증명하지 않는다.

## 3. 관련 연구 도메인

| 도메인 | Baby에서 맡을 역할 | 현재 Baby의 상태 |
|---|---|---|
| Continual/Lifelong Learning | 새 경험을 배우면서 과거 능력을 보존 | LoRA sleep 경로는 있으나 clean future canary 재검증 전 |
| Test-Time Memory/Adaptation | 추론 중 중요 경험을 빠르게 기억 | graph memory는 있으나 core wake integration 없음 |
| Open-Ended Learning/Autocurriculum | 학습 진전에 맞춰 다음 과제를 스스로 생성 | 질문 생성은 있으나 information gain 기반 선택 없음 |
| Model-Based Reinforcement Learning | 행동 결과를 예측하고 상상 속에서 계획 | Quest action-conditioned world model 데이터가 아직 없음 |
| Forward/Inverse Action Verification | 결과가 가능한지와 어떤 행동이 원인인지 교차검증 | B5.9는 semantic outcome만 있고 causal action verifier 없음 |
| Developmental Robotics | 쉬운 감각-행동 단계에서 복잡한 자율성으로 발달 | 단계별 권한 승격 규칙이 미정 |
| Metacognition/Calibration | 모르는 것을 측정하고 안전하게 질문 | surprise/progress는 있으나 calibrated uncertainty가 아님 |
| Safe Self-Modification | 후보 모델을 격리하고 검증 후 승격/rollback | atomic adapter 저장 gate가 출발점 |
| Machine Teaching/Distillation | Gemini 지식을 local trainable core로 이전 | teacher는 가능하나 외부 현실의 정답 판정자는 아님 |

## 4. 2025–2026 중심 근거 지도

인용 수는 2026-07-16 Semantic Scholar 조회 스냅샷이다. 서로 다른 버전/record를 합친 절대값이 아니므로 시간에 따라 변할 수 있다.
표는 citation count 내림차순이다.

| 연구 | 연도 | Semantic Scholar venue | citations / influential | 신뢰도 라벨 | Baby에 주는 조각 |
|---|---:|---|---:|---|---|
| [DreamerV3 / Mastering diverse control tasks through world models](https://www.nature.com/articles/s41586-025-08744-2) | arXiv 2023, Nature 2025 | arXiv record; Nature 논문 별도 확인 | 1253 / 174 | **[peer-reviewed]**, Nature | world model, imagination, fixed configuration의 범용 control |
| [V-JEPA 2](https://arxiv.org/abs/2506.09985) | 2025 | arXiv.org | 511 / 74 | preprint, peer review 미확인 | latent video world model과 소량 robot video 기반 planning |
| [Absolute Zero](https://arxiv.org/abs/2505.03335) | 2025 | NeurIPS | 275 / 23 | **[peer-reviewed]**, top-tier | 과제 제안과 풀이를 code executor의 검증 가능한 보상으로 연결 |
| [Titans](https://arxiv.org/abs/2501.00663) | 2024/2025 venue | NeurIPS | 275 / 33 | **[peer-reviewed]**, top-tier | test-time neural long-term memory |
| [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) | 2025 | Robotics | 149 / 7 | venue tier 미확인 | 자기수정 후보 archive와 benchmark 기반 경험적 승격 |
| [SEAL: Self-Adapting Language Models](https://arxiv.org/abs/2506.10943) | 2025 | arXiv.org | 46 / 4 | preprint, peer review 미확인 | 모델이 자체 update directive와 training data를 생성하고 weight에 통합 |
| [Self-Challenging Language Model Agents](https://arxiv.org/abs/2506.01716) | 2025 | NeurIPS | 42 / 2 | **[peer-reviewed]**, top-tier | instruction+verifier+tests가 있는 자가생성 task로 agent RL |
| [World Action Verifier](https://arxiv.org/abs/2604.01985) | 2026 | arXiv.org | 6 / 0 | **[early-stage research]** | state plausibility와 action reachability의 forward/inverse cycle 검증 |

### World Action Verifier 심화 확인

Semantic Scholar에서 인용 논문 6개는 확인되었지만 reference 목록은 0개로 반환되었다. 이는 “참고문헌이 없다”는 뜻보다는 2026년
신규 preprint의 색인 불완전 가능성이 크다. 따라서 World Action Verifier는 Baby의 verifier 설계에 유용한 **초기 가설**로 사용하되,
확립된 표준으로 취급하지 않는다.

## 5. 새 작업 도메인 가설: GDSI

### 이름

**Grounded Developmental Self-Improvement (GDSI)**  
한국어 작업명: **근거 기반 발달형 자기개선**

이 정확한 영문 구문이 확립된 2025–2026 연구 분야인지 arXiv 검색으로 확인되지 않았다. 따라서 새 분야를 세계 최초로 만들었다고
주장하지 않고, Baby가 결합하려는 문제를 추적하기 위한 **working label**로만 사용한다.

### 조작적 정의

GDSI는 다음 조건을 모두 만족하는 embodied agent 연구다.

1. agent가 예상 학습 진전 또는 가설 간 disagreement를 기준으로 저위험 질문/행동을 고른다.
2. 행동 전에 외부 결과의 확률적 예측을 기록한다.
3. 행동 후 센서·사람 답변·도구 실행 결과로 예측을 검증한다.
4. 검증된 경험만 graph, world model, trainable core에 consolidation한다.
5. 기존 능력, calibration, safety, 실제 wake utility를 미래 canary에서 통과한 후보만 승격한다.

핵심은 “많이 기억한다”가 아니라 **외부 결과로 틀림을 측정하고 그 오차가 다음 파라미터와 다음 행동을 바꾸는 것**이다.

## 6. 새 시스템 가설: Developmental Causal Self-Compiler

**Developmental Causal Self-Compiler (DCSC)**는 GDSI를 Baby에 구현하기 위한 시스템 가설이다. “self-compiler”는 경험을 그대로
저장하는 데서 끝내지 않고, 검증된 경험을 graph relation, world-model sample, LoRA update로 각각 컴파일한다는 뜻이다.

### 전체 루프

1. **Independent hypotheses**  
   질문/행동 전에 Neo4j graph, local core, latent world model이 서로 독립된 결과 분포를 낸다.
2. **Disagreement-driven epistemic action**  
   단순 surprise 최대화가 아니라 모델들의 가설을 가장 잘 구분할 질문 또는 안전한 머리 움직임을 고른다.
3. **Grounded triple verifier**  
   `forward outcome prediction`, `inverse action reconstruction`, `state plausibility`를 함께 계산한다.
4. **Causal Experience Ledger**  
   `(before_state, action, predicted_distribution, observed_after, verifier_scores, provenance, controls)`를 변경 불가능한 연구 record로 남긴다.
5. **Sleep self-compile**  
   검증을 통과한 record만 semantic/action graph edge, latent world-model sample, LoRA self-edit episode로 변환한다.
6. **Adapter population archive**  
   production core를 직접 덮지 않고 여러 LoRA 후보를 만든다. 미래 canary prediction, forgetting, calibration, safety, wake utility의
   Pareto gate를 통과한 후보만 atomic promotion하고 실패하면 rollback한다.
7. **Shadow wake integration**  
   처음에는 local core가 답을 직접 지배하지 않고 prediction/reranking만 수행한다. Gemini는 언어 teacher로 남고 외부 현실의
   ground truth 역할은 맡지 않는다.
8. **Developmental authority ladder**  
   `PendingQuestion` → Quest head motion → 저위험 물체 관찰/조작 순으로 단계별 권한을 넓힌다.

### 현재 코드와의 연결

| 현재 자산 | DCSC 역할 | 필요한 연결 |
|---|---|---|
| `PendingQuestion` + B5.9 labels | 첫 번째 안전한 epistemic action과 human semantic outcome | 질문 후보별 사전 분포와 정보이득 |
| Neo4j concept graph | episodic/semantic hippocampus와 graph hypothesis | answer relation schema 및 provenance |
| `live_curiosity.py` | learning-progress 관찰 | disagreement·calibration을 추가한 action selector |
| local LoRA core | trainable cortex 후보 | wake shadow prediction과 clean promotion evidence |
| `sleep_distill_job.py` | consolidation과 atomic adapter gate | candidate population 및 future canary |
| Quest pose/depth/SSE | embodied external outcome | pre/post latent snapshot과 action delta |
| Gemini | teacher, task proposer, language renderer | verifier/ground truth와 분리 |

### 병렬 UI/Ops 참고: Zoey OS Reel

#### 출처와 확인 범위

- 사용자 제공 공개 Reel: `https://www.instagram.com/reel/DaSw8Balfqk/`
- 확인일: 2026-07-16 KST
- 공개 MP4 길이: 9.356초
- 영상에서 직접 확인한 요소: 음성/채팅 명령, companion/bot 노드 그래프, companion 간 작업 위임·메시지,
  Knowledge 폴더·파일·업로드 화면, 관계 그래프 시각화
- 공개 캡션의 주장: Zoey가 여러 agent를 만들고 agent들이 서로 통신함
- 확인하지 못한 요소: 공개 문서, 소스 코드, benchmark, 파라미터 학습, 외부 outcome verifier,
  continual-learning promotion/rollback, embodied learning. `zoeyos.ai`를 공식 제품 도메인으로 확인하지 못했다.

따라서 이 Reel은 **기능 증명 또는 자기학습 선행연구가 아니라 UI/Ops 참고자료**로만 취급한다. 영상·캡션의
`Jarvis` 표현을 Baby의 능력 주장이나 평가 통과 근거로 가져오지 않는다.

#### 프로그램 내 위치

Zoey 참고사항은 상위 program roadmap의 **병렬 트랙 `관측/UI`**에 둔다. J1–J3의 연구 critical path,
성공 gate, DB schema, predictor, 학습 데이터는 변경하지 않는다.

```text
J1 Question-as-Experiment contract
  → J2 grounded action verifier
  → J3 verified sleep self-compile

병렬 UI/Ops (비차단)
  → Hypothesis Council 시각화
  → predictor 간 message/provenance 표시
  → agent ablation 및 기여도 화면
  → Causal Experience Ledger 탐색
```

UI 구현은 J1 predictor 출력 계약이 안정된 뒤 시작한다. 외피가 먼저 만들어져 가짜 데이터나 임의 agent 상태를
표시하는 것을 금지한다. 화면의 각 node/message는 실제 predictor snapshot ID, timestamp, provenance, metric에
연결되어야 한다.

#### 가져올 것과 가져오지 않을 것

| 구분 | 결정 |
|---|---|
| companion graph UX | `graph predictor`, `local core`, `world model`, `verifier`의 Hypothesis Council로 변형 |
| agent 메시지 | 자연어 장식이 아니라 prediction probability, 근거 provenance, disagreement 전송 |
| knowledge graph UI | Causal Experience Ledger와 검증 상태를 탐색하는 read-only 화면으로 사용 |
| 다중 agent 수 | agent별 ablation에서 외부 outcome을 개선한 구성요소만 유지 |
| `Jarvis` 마케팅 문구 | 능력 주장과 학습 target에서 제외 |
| 설치·파일 업로드·API key 입력 | 문서·privacy·network behavior 검증 전 금지 |

이 기록은 아이디어 참고의 provenance를 보존하기 위한 것이며 Zoey를 dependency로 채택하거나 현재 계획을
override하는 결정이 아니다.

## 7. 가장 작은 반증 가능한 실험 순서

### J0 — B5.9 semantic seal (완료)

- 6개 질문, 25개 label을 사용자 승인 상태로 고정했다.
- 아직 DB write, heldout, production promotion은 하지 않는다.

### J1 — Question-as-Experiment (다음 권장 단계)

1. `PendingQuestion`을 가장 안전한 action으로 사용한다.
2. graph와 local core가 질문 후보별 의미 outcome 분포를 질문 전에 각각 출력한다.
3. 두 predictor의 disagreement와 예상 정보이득으로 2개 후보 중 하나를 선택한다.
4. 사용자 답변과 reviewed semantic label을 외부 결과로 삼는다.
5. 첫 실험은 **학습 없이 prediction/calibration만** 측정한다.

성공 기준은 “정답 한 번 맞힘”이 아니다. 시간순 future sample에서 random/frequency 대비 log loss 또는 Brier score가 좋아지고,
선택된 질문이 random 질문보다 더 큰 entropy reduction을 보여야 한다.

#### J1.0 offline contract + legacy readiness audit 결과 (2026-07-16)

J1 첫 단계는 구현했지만 기존 6개 B5.9 질문은 J1 성능 실험으로 재사용할 수 없다는 결론이 나왔다.

- `question_experiment.py`: graph/local-core가 같은 Concept universe에 대해 pre-question relevance probability를
  제출하도록 강제한다. 두 predictor의 Jensen-Shannon divergence가 가장 큰 질문을 deterministic하게 선택한다.
- reviewed multi-label target에 대해 Brier, binary log loss, Expected Calibration Error, top-k recall을 계산한다.
- `offline_shadow_no_learning`, train-only, DB write 없음, held-out/production false를 강제한다.
- probability는 임의 softmax로 만들 수 없다. Platt/isotonic/temperature scaling 중 하나, calibration dataset hash,
  calibrator hash, positive/negative sample count, fitted timestamp가 predictor capture보다 앞서는지를 검사한다.
- 정확한 question text, semantic label pack hash, graph/local-core model snapshot hash, selection-before-asked timestamp가
  하나라도 다르면 fail-closed한다.

실제 B5.9 artifact를 audit한 결과는 `contract_gate=false`다.

| readiness item | 결과 |
|---|---|
| question text + user-reviewed semantic targets | 있음 (`6 questions / 25 labels`) |
| historical graph ranked IDs | 있음 |
| calibrated graph probabilities | 없음 |
| local-core pre-question probabilities | 없음 |
| 2개 이상 후보를 동시에 비교한 decision batch | 없음 |
| predictor/model/calibrator hash의 pre-question seal | 없음 |
| learning disabled | true |

ranked ID나 post-hoc score를 확률로 변환하지 않았다. artifact:
`claudedocs/research/j1_question_as_experiment_readiness_20260716.json`.

남은 CuriosityLog를 read-only로 조사하면 8개 중 graph prediction이 있는 후보는 3개뿐이다.
`이야기 궁금한 것을 설명해줘`, `하루 1시간 뒤를 설명해줘`, `궁금한 것 비밀을 설명해줘`인데 기존 6개와
의미가 겹치고 문장 품질이 낮아 calibration 데이터로 채택하지 않았다. DB write는 없었다.

**다음 J1.1**은 새 고품질 train-calibration 질문을 먼저 사전등록하고, 질문을 사용자에게 보여 주기 전에 graph와
local core의 raw score와 model snapshot hash를 함께 봉인하는 단계다. 그 결과로 calibrator를 fit한 뒤에만 두 후보
질문의 probability/JSD 선택을 시작한다. local-core shadow inference는 GPU 학습이 아니라 read-only 추론이지만,
현재 턴에는 실행하지 않았다.

신규 J1 targeted test `8 passed`였다. 당시 전체 canonical suite를 `146 passed`로 기록했지만 J1.1 재감사에서
현재 pushed HEAD 단독 `136 passed`가 재현됐고 삭제·실패 테스트는 없었다. 146은 다른/중복 범위가 섞인
부정확한 집계로 교정한다. py_compile과 diff check는 통과했다.
보호 `conversation_handler.py` blob은 HEAD와 동일한 `054d974095be7425692860909181fafd54f97a33`이며 비밀값
패턴 노출은 0건이다.

### J2 — Quest Latent Action Verifier

- action: 제한된 head yaw/pitch 이동
- state: pixel reconstruction 대신 pre/post visual embedding과 pose
- verifier: forward latent prediction + inverse action classification + state plausibility
- 먼저 수동/고정 정책으로 데이터를 모으고 policy learning은 이후에 한다.

### J3 — Verified Sleep Self-Compile

- 검증된 J1/J2 record만 candidate LoRA와 world model에 학습한다.
- 동일 pair leakage를 차단하고 chronological future canary를 봉인한다.
- 후보가 성능을 높여도 old-canary forgetting 또는 calibration이 악화되면 폐기한다.

### J4 — Shadow Wake A/B

- local core on/off만 바꿔 실제 질문 선택 또는 reranking utility를 비교한다.
- Gemini 출력 품질이 아니라 local core가 없을 때 대비 외부 outcome prediction 향상을 측정한다.

### J5 — 제한된 자율 행동

- J1–J4가 반복 재현된 뒤에만 Quest/robot action selector의 권한을 늘린다.
- 자기 코드 수정은 별도 branch/archive에서만 허용하고 production self-overwrite는 금지한다.

## 8. 필수 지표와 중단 규칙

| 축 | 지표 | 중단 조건 |
|---|---|---|
| 예측 | chronological NLL, Brier, Expected Calibration Error | frequency/random baseline을 반복해서 못 넘음 |
| 인과성 | intervention action 대비 random action의 information gain | 차이가 없거나 action 전 기록이 누락됨 |
| world model | forward latent error, inverse action accuracy, cycle consistency | 정적 shortcut으로도 같은 성능 |
| continual learning | future canary 향상과 old-canary forgetting delta | leakage 또는 forgetting gate 실패 |
| wake utility | local core on/off A/B | local core가 결과를 바꾸지 않음 |
| 안전 | 허용 action 위반, rollback 성공률 | 단 한 번의 경계 위반도 자동 승격 중단 |

추가 데이터 수집이나 큰 모델 학습은 위 병목 중 무엇을 해결하는지 사전에 명시할 때만 한다. baseline을 못 넘는 상태에서 threshold,
edge weight, 모델 크기만 반복 조정하지 않는다.

## 9. 비판적 위험 분석

1. **자기생성 데이터의 폐쇄 루프**: model의 오류를 model이 다시 정답으로 학습할 수 있다. 외부 verifier와 sealed canary가 필요하다.
2. **reward hacking**: 쉬운 질문만 만들거나 verifier의 허점을 이용할 수 있다. 학습 진전, 난이도, 다양성, 안전을 함께 gate해야 한다.
3. **기억과 학습의 혼동**: graph retrieval 향상은 core parameter 성장과 다르다. 두 효과를 ablation으로 분리한다.
4. **평가 오염**: 현재 Phase 2의 과거 MRR처럼 동일 concept pair가 train/test에 겹치면 성장 주장이 무너진다.
5. **교사 의존성**: Gemini가 모든 task와 answer를 만들면 Baby는 teacher compression은 해도 자율적 현실 학습을 증명하지 못한다.
6. **현실 grounding 비용**: 공개 웹 지식을 찾는 능력은 행동 결과의 진실성을 대신하지 않는다. 실제 센서·사람·도구 실행의 결과가 필요하다.
7. **통합 병목**: 각 논문의 성공을 단순 합치면 성공한다는 보장은 없다. Baby의 장점은 이 통합 가설을 작은 반증 실험으로 줄이는 데 있다.

## 10. 다음 결정

가장 합리적인 다음 단계는 DB relation write나 GPU retraining이 아니다. **J1.0 Question-as-Experiment offline
contract는 완료됐고 기존 6개는 probability provenance 부족으로 blocked됐다.** 다음 J1.1에서 아래 세 가지를
새 train-calibration 질문으로 검증해야 한다.

1. 동일 질문에 대해 graph와 local core가 실제로 비교 가능한 사전 확률 분포를 낼 수 있는가?
2. 분포 간 disagreement가 random selection보다 더 유익한 질문을 고르는가?
3. B5.9 reviewed labels로 calibration을 측정하되 같은 6개 train sample을 성능 증거로 오해하지 않는가?

이 세 조건이 성립하면 별도의 heldout 질문을 수집하고 J1 학습을 시작한다. 성립하지 않으면 model 규모가 아니라 outcome
ontology와 predictor interface를 먼저 고친다.

## 11. 1차 출처

- Hafner et al., [Mastering diverse control tasks through world models](https://www.nature.com/articles/s41586-025-08744-2), Nature, 2025.
- Zhao et al., [Absolute Zero](https://arxiv.org/abs/2505.03335), 2025.
- Zhou et al., [Self-Challenging Language Model Agents](https://arxiv.org/abs/2506.01716), 2025.
- Assran et al., [V-JEPA 2](https://arxiv.org/abs/2506.09985), 2025.
- Behrouz et al., [Titans](https://arxiv.org/abs/2501.00663), 2024/2025.
- Kumar et al., [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954), 2025.
- Zweiger et al., [SEAL](https://arxiv.org/abs/2506.10943), 2025.
- Wang et al., [World Action Verifier](https://arxiv.org/abs/2604.01985), 2026.
