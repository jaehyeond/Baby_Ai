# 합성 스케일링 연구 — 진행 보고 (2026-07-13)

> program_roadmap Phase 4 / [[phase1_plasticity_result_2026-07]]. 데이터 밀도가 바인딩 제약
> (3회 확인)이라, 실제 Quest 데이터가 하드웨어 의존인 동안 **통제된 합성 스트림**으로
> 자기학습 스택의 스케일 거동을 규명한다.
> 스크립트: `scripts/research/{synth_world,scaling_study}.py`. 원자료: `claudedocs/research/scaling_*.json`.

## 목적 — 3개 질문
- **Q1**: RW 음성증거의 빈도(additive) 대비 우위가 **밀도(N)·다양성(scenes)**에 따라 커지는가?
  (실데이터선 +3.5%뿐 — 데이터가 늘면 결정적이 되는가?)
- **Q2**: 학습 파라미터 코어(trainable head)가 그래프를 **어느 N에서 역전**하는가?
  (=Phase 2 로컬코어가 정당해지는 지점. 현재 518노드선 그래프가 이김.)
- **Q3**: embodied next-frame 예측에서 그래프가 **popularity를 언제 넘는가**? 움직임이 돕는가?

## 방법
- **합성 world 생성기** (`synth_world.py`): 잠재 세계 = n_scenes 장면(각 장면 = ghome 전역최빈객체
  + 장면별 home + stable 객체 각도배치 + shared 구조). 에이전트 pose(scene, head angle)로 이동,
  프레임 = FOV 안 객체 + transient(일부 재등장). 노브: N·scenes·motion·transient·noise.
- **캘리브레이션 (정직성)**: 실제 45프레임 통계에 맞춤. **~13% 평균편차** (2026-07-13):

  | 지표 | 합성(N=220) | 실제 타깃 | 편차 |
  |---|---:|---:|---:|
  | objs/frame | 6.15 | 5.44 | 13% |
  | Jaccard(연속) | 0.324 | 0.309 | 5% |
  | new/frame | 3.32 | 3.11 | 7% |
  | top_share(최빈 점유) | 0.91 | 0.80 | 14% |
  | singleton_frac | 0.38 | 0.51 | 25%(가장 약함, scale의존) |

  → objs/frame·Jaccard·new-rate는 near-perfect. 최빈객체 지배 + novelty tail이라는 **동일 regime**
  재현. singleton은 가장 약한 매치(스케일 의존적, 정직히 명시). 판타지가 아닌 **캘리브레이션된 외삽**.
- **평가 = 기존 하니스 재사용**: `prequential_experiment.run_arm`(edgebank/additive/rw MRR),
  `trainable_head_experiment.run_head`(코어 MRR), + embodied next-frame(graph vs popularity, pose 층화).
  합성 events = `synth_world.to_events` (동일 포맷 → 리팩터 0).
- **격자**: N∈{256,1024,4096} × scenes=8 (밀도·head축) + N=2048 × scenes∈{1,4,16,32} (다양성축).

## 한계 (정직)
- **N 상한 4096**: prequential PPR 채점이 ghome 허브(≈모든 프레임 등장)에서 O(V²) 폭주 → N=12000은
  3분+ 미완(kill). 대규모 N(head 역전 regime)은 더 싼 scorer 필요 = 후속. 리서치 scale caveat상
  head 역전은 orders-of-magnitude 필요라, 4096서 안 나오는 건 예상 범위.
- 합성 = 캘리브레이션했으나 실제 아님. EdgeBank/popularity 바닥선으로 "쉬워서 이김" 착시 방어.

## 결과 (7셀, 2026-07-13)

### 두 축 분리 (스크립트의 N별 평균은 두 축을 섞으니 분리해 본다)
**밀도 축** (scenes=8 고정):
| N | vocab | additive MRR | rw MRR | RW우위 | head−graph | graph−pop |
|---:|---:|---:|---:|---:|---:|---:|
| 256 | 128 | 0.534 | 0.571 | +6.8% | −0.022 | +0.029 |
| 1024 | 395 | 0.556 | 0.586 | +5.4% | −0.049 | +0.048 |
| 4096 | 1369 | 0.538 | 0.561 | **+4.3%** | −0.039 | +0.031 |

**다양성 축** (N=2048 고정):
| scenes | vocab | additive MRR | rw MRR | RW우위 | head−graph | graph−pop |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 589 | 0.647 | 0.644 | −0.5% | −0.076 | +0.004 |
| 4 | 660 | 0.584 | 0.605 | +3.7% | −0.059 | +0.055 |
| 16 | 866 | 0.509 | 0.533 | +4.7% | −0.020 | +0.016 |
| 32 | 969 | 0.507 | 0.555 | **+9.5%** | −0.029 | +0.013 |

### 판정
- **Q1 — RW 우위 = 밀도가 아니라 다양성 주도.** 밀도 축에선 우위가 오히려 완만히 **감소**(6.8→4.3%).
  다양성 축에선 **단조 증가**(−0.5%→+9.5%). 메커니즘: 장면이 많을수록 marginal 빈도와 다른
  조건부확률 P(b|a)이 많아짐 → 빈도 카운터(additive)는 뒤처지고 **보정된 조건부(RW)가 일반화**로 이김.
  (검증: 다양성↑ 시 additive 0.647→0.507로 급락, rw 0.644→0.555로 완만 → RW가 다양성에 강건.)
  MRR 차이(~0.02–0.05)는 RW 다중시드 std(~0.002)의 10–25배 → 노이즈 아님.
- **Q2 — head 역전 없음 (N≤4096 전부 그래프 우위, −0.02~−0.076).** 다양성↑ 시 격차가 줄긴 하나(−0.076→−0.02)
  여전히 그래프가 이김. scale caveat대로 역전은 훨씬 큰 N/더 나은 코어설계 필요. → **Phase 2 로컬코어는
  여전히 시기상조.** 그래프가 강한 baseline.
- **Q3 — 그래프가 popularity를 근소 초과(+0.004~+0.055), 강한 스케일링 신호 없음.** pose 조건부: 고움직임
  0.348 vs 저움직임 0.337 — 움직임이 돕지만 **약함**. embodied 구조예측은 이 regime에서도 어렵다(실데이터와 동형).

## 결론 & 다음 (로드맵 반영)
1. **핵심 함의 — 데이터 수집 스펙 변경**: RW 자기학습 신호를 결정적으로 만드는 건 "많은 프레임"이 아니라
   **"많은 서로 다른 장면(맥락)"**. → Quest 수집은 **장면 다양성 최우선**(한 데스크 반복 ✗, 방·주방·야외·
   사람 등 다양한 맥락 ✓). `docs/QUEST_APK_CONTRACT.md` 반영.
2. **Phase 2 판정 유지**: 학습 코어는 N≤4096서 그래프 못 이김 → 밀도+다양성 확보 전엔 착수 보류(재확인).
3. **한계·후속**: N=12000+ head 역전 regime은 PPR 채점 O(V²) 폭주로 미측정 → 더 싼 scorer(직접엣지/근사
   PPR)로 대규모 head-crossover probe가 다음 후보. 합성↔실제 gap은 실 Quest 다양장면 수집 후 재측정으로 검증.

산출: `scripts/research/{synth_world,scaling_study}.py`, `claudedocs/research/scaling_20260713.json`.

---

# Q2 후속 — Head-Crossover Probe (2026-07-13): 학습 코어가 그래프를 역전하는가

> `scripts/research/head_crossover_probe.py`, `claudedocs/research/head_crossover_20260713.json`.
> scaling_study가 N≤4096서 "코어 못 이김"으로 남긴 Q2를, 두 병목을 풀어 대규모(N≤48k)로 재측정.

## 방법 (두 병목 해결)
- **병목1 eval O(V)** → **sampled-negative 랭킹**: 참 타깃을 K=60 샘플음성 중 랭킹(표준 대규모 LP).
  O(60)로 고정 → 어휘 커도 tractable. eval_frac 0.25(채점 샘플, 학습 100%).
- **병목2 허브 O(V²)** → **degree-cap**: 노드당 fan-out ≤48(생물 시냅스 한계 정합) + direct-edge +
  bounded common-neighbor 스코어러. **matched-capacity**: 그래프 cap 48 vs 코어 임베딩 dim 48.
- 4 arm 동일 스트림·동일 샘플음성 완전 paired: edgebank/additive/rw/head(numpy 임베딩, 온라인 SGD).
- scenes ∝ N (실제처럼 다양성 동반).

## ⚠️ 결정적 버그 → 결정적 발견 (초기 결론 반전)
1차 실행서 head 임베딩이 대규모(N≥16k)서 **수치 발산(overflow)** — norm 무제한 성장. 이게
`trainable_head_experiment`의 "코어가 그래프 못 이김"(518노드) 결론까지 오염시킨 원인일 개연성 큼.
**수정 = 임베딩 L2 norm clipping(≤4.0) = 항상성**(그래프 degree-cap의 파라미터 판; Zenke-Gerstner
"항상성은 필수" 실증). 수정 후 결과가 **역전**:

| N | scenes | graph(best) MRR | head MRR | head−graph |
|---:|---:|---:|---:|---:|
| 1,000 | 4 | 0.723 | 0.718 | −0.8% |
| 4,000 | 5 | 0.805 | 0.840 | **+4.4%** |
| 16,000 | 20 | 0.841 | 0.912 | **+8.4%** |
| 48,000 | 60 | 0.862 | 0.944 | **+9.5%** |

(EdgeBank 암기 baseline은 0.80 — head 0.94가 압도 → 암기 아닌 일반화. N=100k는 timeout, 추세 명확.)

## 판정
- **역전점 N≈2,000–4,000. 이후 코어 우위가 단조 증가**(−0.8%→+9.5%). head MRR은 0.72→0.94로 상승,
  degree-cap 그래프는 0.86서 정체 — **용량 한계 그래프 vs 분산 임베딩**의 CLS 구도: 스케일에서
  파라미터 코어가 비파라미터 기억을 일반화로 추월.
- **초기 "코어 열위" 결론은 항상성 부재(발산) 아티팩트였다.** = 리서치 mandate(homeostasis 필수) 실증.
- **로버스트니스 (causal 확인, N=8000)**: 크로스오버가 MAX_NORM ∈ {2,4,8,16} 전부서 성립(head +2.4~+5.8%),
  **clip off(=1000)면 head 다시 짐(−0.8%)**. → 하이퍼파라미터 체리픽 아님 + **항상성이 인과적 원인**임을
  직접 증명(clip on→이김, off→짐). clip=4가 최적 근처(+5.8%).

## 한계 (정직)
- **matched-capacity 규정 의존**: 크로스오버 N은 그래프 cap vs 코어 dim의 상대용량에 의존. cap을 크게
  주면 역전 지연. 정성적 결론("코어가 이길 수 있다 + 항상성 필수")은 강건, **정확한 N은 규정 의존**.
- 합성 데이터(캘리브레이션됨, 실제 아님). 실 Quest 다양장면 수집 후 재확인 필요.

## 로드맵 함의 (Phase 2 재평가)
**Phase 2(로컬 trainable 코어)가 생각보다 유망** — 단 **weight-homeostasis를 day-1부터 탑재해야**
(norm bound/synaptic scaling/continual-backprop). "그래프가 근본적으로 코어보다 낫다"는 틀림 —
그건 **항상성 없는(발산하는) 코어** 얘기였다. 밀도·다양성이 *언제* 이득이 나는지를 지배하지만,
충분한 다양성·규모에선 코어가 이긴다. → Phase 2 우선순위 상향(단 안전장치 필수).
