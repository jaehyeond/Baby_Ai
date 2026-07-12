# Phase 1 가소성 규칙 실험 — 결과 보고 (2026-07-12)

> 프로그램: 자기성장 아기 뇌 (program_roadmap_2026-07). 북극성: self_learning_architecture_2026-07.
> 하니스: `scripts/baseline/plasticity_experiment.py`(정적), `scripts/baseline/prequential_experiment.py`(prequential).
> 원자료: `claudedocs/baseline/plasticity_*_20260712.json`, `prequential_*_20260712.json`. 리서치: `RESEARCH_SYNTHESIS_2026-07-12.md`.

## TL;DR (결론 먼저)
**Phase 1 자기학습 신호 = 발견됨. 단, 올바른 규칙 × 올바른 지표에서만.**
- 순진한 가소성(STDP 타이밍 + 항상성 + 양성전용 PE-게이팅)은 **정적 link-prediction에서 빈도 baseline을 못 이김**(초기 반증).
- 프런티어 리서치가 진단: 나는 **틀린 규칙을 틀린 지표로** 측정했다. 빠진 조각은 STDP가 아니라
  **Rescorla-Wagner 음성증거**(a 켜졌는데 b가 안 켜지면 w_ab를 **깎음** → w_ab→P(b|a), 보정된 확률).
  올바른 지표는 정적분할이 아니라 **prequential(예측→채점→학습)** + EdgeBank(암기) baseline.
- 재실험 결과: **RW 음성증거 규칙이 빈도(additive)와 암기(EdgeBank)를 유의·강건하게 이김**, 예측이 보정됨(ECE↓),
  그리고 그 우위는 **time-shuffle에서 붕괴**(= 진짜 시간적 학습, 밀집화 artifact 아님).

---

## 1. 목적
Phase 1 가설: co-occurrence 가산 Hebbian → "진짜 가소성 규칙"으로 바꾸면 그래프가 미래 공동활성화를
**더 잘 예측**하는가(예측오차 하강). roadmap: "여기서 가설이 서거나 반증됨."

## 2. 1차 실험 — 정적 랜덤분할 (plasticity_experiment.py)
- 입력=경험 스트림(Experience.created_at + INVOLVES→Concept, 256이벤트·483 concept). 통제: 동일 이벤트분할로
  두 규칙 각각 그래프구성(입력 동일, 규칙만 변수). 평가=inductive link-prediction, 방향성 PPR, 동일후보 채점,
  20-fold CV(≈900 paired) + 부호검정/Wilcoxon.
- **정직성 체크**: 시간순 미래분할은 평가가능 쌍 **3개**(콜드스타트 지배; 483 중 재등장 142) → CV로 검정력 확보.

### 결과 — 순진한 가소성 반증 (정적 지표)
OLD(가산,cap1.0) lift=5.34 기준, **어떤 변이도 못 이김**(모두 p<0.001 열등):
freq_nocap 5.28(=OLD 동률) · stdp_freq 4.83 · recency_only 4.18 · stdp_full 4.09 · recency_stdp 3.66.
- **PE 게이팅(양성전용 포화)**: 반복강화를 멈춰 **빈도신호를 버림** = 최대손해.
- **항상성**: 정보량 큰 허브 평탄화. **방향성 STDP(교차이벤트)**: 시간인접·주제무관 concept 연결 = PPR 잡음.

### 왜 (진단)
정적 랜덤분할 link-prediction은 **빈도**를 보상 → 가산 Hebbian=공동출현 최대우도=천장. 이 지표는
"그래프가 자란다"만으로 lift가 오른다. **틀린 규칙(양성전용) × 틀린 지표(정적).**

---

## 3. 2차 실험 — prequential test-then-train (prequential_experiment.py) ★핵심
리서치(RESEARCH_SYNTHESIS §2)가 처방한 정직한 지표. 스트림을 시간순으로 흐르며 각 경험을 **학습 전에 먼저
예측**하고 채점 → 학습. 예측오차 곡선의 하강을 본다. baseline = **EdgeBank**(최근 본 쌍 그대로 예측, 순수 암기).
동일 스트림·동일 채점, **arm만 다름**(규칙 귀속 통제). RW 규칙 = `w_ab += η(o_b − w_ab)`, o_b=1(공동활성)/
0(음성샘플) → w_ab→P(b|a). 방향성.

### 결과 (실제 시간순 스트림)
| arm | MRR | hit@1 | hit@10 | ECE(보정) | vs EdgeBank |
|---|---:|---:|---:|---:|---:|
| edgebank (암기) | 0.4255 | 0.297 | 0.633 | — | 1.00 |
| additive (빈도) | 0.4938 | 0.378 | 0.728 | — (확률아님) | 1.16 |
| **rw (음성증거)** | **0.510** | 0.399 | 0.743 | **0.038** | **1.20** |
| rw_recency | 0.513 | 0.400 | 0.752 | **0.024** | 1.21 |

- **RW vs additive**: paired 부호검정 484/282 win, **p≈0**. 다중시드(6): 0.510±0.002, **최악시드(0.507)도 additive(0.494) 초과** = 강건.
- **RW vs EdgeBank**: 814/281, p≈0 → 암기가 아니라 **일반화**. (additive도 EdgeBank 이김 738/321 → 그래프 구조가 암기 이상.)
- **보정**: RW의 w_ab는 ECE 0.038(+recency 0.024)로 **진짜 확률**. additive 가중치는 확률조차 아님.
- 예측오차 곡선 상승(+0.08).

### 반증 통제 — time-shuffle (필수)
타임스탬프를 무작위화하면:
- **RW의 additive 대비 우위 붕괴**: robust win → 시드편차 내(RW 0.459±0.001 vs add 0.459), paired p 0.0→0.03.
- **곡선 상승 사라짐**(❌).
→ RW의 우위는 **스트림의 시간구조를 진짜로 이용**한 것(순서 파괴 시 소멸). 만약 우위가 단순 밀집화 artifact였다면
  shuffle에도 살아남았을 것 → 살아남지 않음 = **진짜 시간적 예측학습**임을 falsification으로 확인.
- 주의(정직): 실제 스트림의 곡선 상승 일부는 데이터 순서효과(초기=신규탐색, 후기=기존개념 재활성)임. 따라서
  "곡선이 오른다" 단독이 아니라 **RW-vs-additive 동일위치 격차 + shuffle 붕괴**가 핵심 증거다.

---

## 3.5 3차 실험 — 학습가능 head (trainable_head_experiment.py, gap#1 리허설)
북극성 정의의 자기학습 = **경험이 코어 파라미터를 바꿈**. 규칙(additive/RW)은 그래프 스칼라를
손갱신 — backprop 아님. 그래서 **학습가능 링크예측 head**(Concept 방향성 임베딩 E_out/E_in,
score(a→b)=<E_out[a],E_in[b]>, BCE 온라인 SGD, 순수 numpy)를 **동일 prequential 프로토콜**로
같은 스트림에서 학습·평가. = Phase 2 로컬코어의 축소 리허설.

### 결과 — 파라미터 코어가 스칼라 규칙을 **못 이김** (리서치 scale caveat 실증)
| arm | MRR | hit@1 | hit@10 | 곡선기울기 |
|---|---:|---:|---:|---:|
| additive | 0.494 | 0.378 | 0.728 | +0.09 |
| rw | 0.512 | 0.398 | 0.750 | +0.07 |
| **trainable_head** | **0.415** | 0.265 | 0.741 | **−0.065** |

head 다중시드(4): 0.415±0.015, paired로 additive(546/803)·RW(473/826) 모두 **p≈0 열세**.
곡선 기울기 **음수** = 스트림 진행에도 안정적으로 학습 못 함(콜드스타트+과소표본 SGD 잡음).
- **해석(정직)**: 518 concept / 256 이벤트 규모에선 학습 파라미터 코어가 손튜닝 스칼라를 못 이긴다.
  리서치 §5 scale caveat("학습 임베딩은 embodiment로 스트림이 orders-of-magnitude 커지기 전엔
  손튜닝 스칼라를 못 이길 수 있다")를 **실증 확인.** hit@10은 비슷(거친 구조는 잡음) but hit@1
  나쁨(정밀 랭킹 못함). 단발 온라인 SGD의 한계 — 배치/replay 학습이면 나아질 수 있음(future work).

## 4. 판정 (정정)
- ❌ 순진한 가소성(STDP/항상성/양성게이팅)은 이 데이터에서 예측을 **개선 안 함**.
- ✅ **Rescorla-Wagner 음성증거 규칙**은 정직한 prequential 지표에서 빈도·암기를 **유의·강건하게 이기고, 보정된
  조건부확률을 학습**하며, 그 우위는 **시간적**(shuffle-controlled). = **Phase 1 자기학습 신호 성립.**
- 초기 "반증" 결론은 **틀린 지표+틀린 규칙 탓**이었음. measure-first + 리서치 교차검증이 이를 바로잡음.

## 5. 로드맵 함의 (실증 기반 재정렬)
1. **Phase 1은 죽은 길이 아님**: RW 음성증거 = 싸고(LLM-free) 진짜인 개선. 보정된 w_ab=P(b|a)는 Phase 2가
   필요로 하는 **예측오차 신호의 원천**(three-factor 게이팅·surprise 보상)이다.
2. **⚠️ 순서 재정렬 (3차 실험의 실증적 함의)**: 학습가능 코어(Phase 2)는 현 데이터 규모에서 **스칼라 규칙보다
   나쁨** → **Phase 2를 먼저 밀면 손해.** 결정 순서는 **데이터 밀도(Phase 4 embodiment) 먼저/병행 → 그 다음
   로컬 trainable 코어.** embodiment로 스트림이 orders-of-magnitude 커지기 전엔 파라미터 코어의 이득이 없다.
3. 효과크기는 완만(RW +3.5%). 큰 레버는 **밀집·접지된 경험(Phase 4)** → **로컬 코어(Phase 2)** 순.
   RW는 초석(예측오차 신호 확보)이지 종착이 아님.
4. 리서치 처방과 정합: 음성증거·prequential·EdgeBank·falsification·scale-caveat = 전부 실증 확인. (RESEARCH_SYNTHESIS §2·§5.)

## 6. 남는 자산 (durable)
- `plasticity_experiment.py`(정적 A/B, 동일후보 채점·paired·CV·콜드스타트 정직성) + `prequential_experiment.py`
  (prequential·EdgeBank·ECE·다중시드·time-shuffle). = Phase 1이 요구한 eval harness의 실체. 향후 규칙/스트림 A/B에 재사용.
- **방법론 교훈**: 지표가 틀리면 옳은 규칙도 반증된다. baseline(EdgeBank)·falsification(shuffle) 없이는 "학습"과
  "암기/밀집화"를 구별 못 한다.

## 7. 다음 (권고)
- (안전·가역) RW 규칙은 **오프라인 검증 완료**. 프로덕션 반영(방향성 엣지 마이그레이션 RELATES_TO 무향→
  w_fwd/w_bwd, blast radius ~2085→4170엣지·전 Cypher 영향)은 **비가역**이라 사용자 확인 후.
- **Gap #1(학습 head)은 지금 착수 보류** — 3차 실험이 현 규모에서 손해임을 실증. 대신 **밀도 우선**:
  - **최우선 레버 = embodiment 데이터 파이프라인(Phase 4)**: Quest per-frame 감지객체+coarse depth bins+head-pose
    delta 를 Experience 로 ingest(reuse `visual_cooc` source) → 공동활성 스트림을 orders-of-magnitude 확장.
    이것이 있어야 (a) STDP 타이밍/recency 가 신호를 갖고 (b) 학습 head/로컬코어가 스칼라를 이길 수 있음.
  - 그 다음/병행 **Gap #6 모니터링**(예측오차 곡선·forgetting probe·collapse 엔트로피/Gini) 상시화.
  - 마지막에 **Phase 2 로컬 코어**(스트림이 충분히 커진 뒤).
- 3차 실험 산출: `trainable_head_experiment.py`(Phase 2 코어 축소 리허설, 재사용).
