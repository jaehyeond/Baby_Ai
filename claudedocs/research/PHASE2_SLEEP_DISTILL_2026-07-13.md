# Phase 2 Sleep-Distill 프로토타입 — 검증 보고 (2026-07-13)

> program_roadmap Phase 2 / self_learning_architecture. head_crossover(항상성 있는 코어가 그래프
> 이김) 후속. Phase 2 결정적 주장 = "retrieval 고정한 채 **코어 가중치만으로** 예측오차 하강 +
> CLS 안티망각". 로컬 LLM 없이 임베딩 코어 대역으로 축소 검증.
> 스크립트: `scripts/research/sleep_distill_prototype.py`(v1), `sleep_distill_v2.py`(v2).

## 구조 (CLS wake-sleep)
- **그래프 = 빠른 해마**: wake에 경험을 degree-capped co-occurrence로 흡수(코어 frozen).
- **임베딩 코어 = 느린 신피질**(norm-clip=항상성): **sleep에만** 그래프가 replay한 에피소드로 학습
  (raw 프레임 안 봄). 로컬 LLM+LoRA sleep-distill의 대역.

## v1 — 프로토타입 + adversarial 검증 (4-claim, workflow)
v1 실행 후 워크플로로 4 주장을 **적대적 검증**(6-config ablation + 4 skeptic + synthesis):

| 주장 | 검증 판정 | 근거 |
|---|---|---|
| **A. 가중치-자기학습** (그래프 frozen, 코어 MRR 상승) | **✅ CONFIRMED** | 고정 early_probe(같은 200쌍)도 0.38→0.70 상승. K=60 음성서 chance 0.076인데 동일쌍이 0.70 도달 → 풀 성장이 아닌 **진짜 임베딩 개선**. 그래프는 core.score에 안 들어감 = 가중치가 유일 변수. |
| **B. replay > raw** | **❌ REFUTED** | 독립 3시드서 online이 2승(정상 스트림선 replay 이점 없음). 헤드라인 −0.074는 미재현 단일시드. |
| **C. 안티망각** | **⚠️ TOO-WEAK(v1)** | v1엔 **망각 스트레서 없음**(그래프 누적+전노드 replay라 옛 지식 계속 재학습). 지표가 오를 수밖에. → v2에서 제대로 검증. |
| **D. no-collapse** | **❌ REFUTED** | mean-norm은 clip으로 자명(≤4). effective-rank 필요. → v2에서 stable rank로 교체. |

**v1 결론(정직)**: 로드-베어링 주장 **A만 확정** — 가중치가 sleep 통합으로 held-out 예측오차를
실제로 낮춘다(Phase 2 기본 primitive 성립). 하지만 sleep-distill의 **차별적 이점**(replay 우위·
안티망각·collapse-free)은 v1으론 미입증. adversarial 검증이 과대주장을 차단.

## v2 — CLS 안티망각의 결정적 검증 (v1 지적 반영)
**순차 태스크 커리큘럼**(진짜 분포 이동): Task A(cyc1-4) → Task B(cyc5-8), 어휘 **disjoint**.
Task B 학습 중 Task-A 연상은 fresh 데이터 못 받음 = 진짜 망각 스트레서. 3 코어 동일 예산 비교 +
frozen negative pool + effective(stable) rank + 다중시드.

### 결과 (Task-A 유지: A학습정점→B학습후 A-test MRR 변화; 음수=망각) — **5-seed N=6000 확정**
| 코어 | A_peak | A_final | Δ (retention, ±std) |
|---|---:|---:|---:|
| **online** (raw 프레임) | 0.513 | 0.178 | **−0.335 ± 0.030 파국적 망각** |
| **sleep_replay** (그래프 replay) | 0.562 | 0.608 | **+0.046 ± 0.044 유지/향상** |
| sleep_off (무작위 replay 통제) | 0.071 | 0.064 | −0.007 (구조 없어 A 학습 자체 안됨) |
*(3-seed N=3000도 동일 방향: online −0.318 vs sleep_rep +0.034.)*

### 판정
- **✅ CLS 안티망각 성립 (5-seed 확정)**: online은 Task-B 학습 시 Task-A를 **파국적으로 망각(−0.335)**,
  sleep_replay는 그래프가 A 구조 보존→replay로 **유지(+0.046)**. 분리폭(0.38)이 결합 std(~0.05)의
  **~10배** = 강건·유의. (sleep_rep는 A_peak도 online보다 높음 → 더 잘 배우고 유지.)
- **v1↔v2 화해**: replay 이점은 **정상 스트림선 없고(=B refuted 맞음), 분포 이동(비정상)에서 결정적**.
  = 실제 평생학습이 비정상이므로 CLS/sleep-distill의 존재이유가 바로 여기(McClelland 1995 예측 일치).
- **⚠️ collapse 플래그**: sleep_replay stable rank ≈2/48 = 낮음. 부분적 표상 collapse 가능성(또는 2-태스크
  구조라 저차원이 정상일 수도). 스케일서 감시 필요 — 미해결 caveat.

## 종합 결론 (Phase 2)
1. **Phase 2 primitive 성립(A)**: 경험이 sleep 통합으로 **코어 가중치를 바꿔 예측오차를 낮춘다** —
   north star "가중치만으로 예측오차 하강"의 축소 실증. adversarial 검증 통과.
2. **CLS 안티망각 성립(v2)**: sleep-replay가 비정상 스트림서 online의 파국적 망각을 막는다 =
   **sleep-distill 아키텍처의 존재이유 실증**.
3. **미해결/caveat**: (a) 표상 collapse(stable rank 낮음) 스케일 감시, (b) 합성 데이터(실 Quest 아님),
   (c) 용량-매칭·유의성 검정 부분적, (d) 로컬 LLM이 아닌 임베딩 대역(진짜 Phase 2는 LLM+LoRA).

## 로드맵 함의
- **Phase 2 방향 검증됨**: CLS(그래프=해마, trainable 코어=신피질, sleep=distill)가 (a) 가중치
  자기학습 (b) 안티망각 둘 다 축소 규모서 작동. **단 weight-homeostasis(norm-clip) 필수**(D·head_crossover).
- **다음**: (a) collapse 지표(effective rank) 스케일 감시 상시화, (b) 로컬 소형 LLM+LoRA로 임베딩 대역
  교체(진짜 Phase 2), (c) 실 Quest 다양장면 데이터서 재확인.

산출: `scripts/research/{sleep_distill_prototype,sleep_distill_v2}.py`, `claudedocs/research/sleep_distill{,_v2}_20260713.json`, workflow 검증(wf_e658bb65).

---

# 실물화 — LLM+LoRA 코어 (2026-07-13): 장난감 임베딩 → 진짜 로컬 LLM

> `scripts/research/llm_core_distill.py`, `claudedocs/research/llm_core_distill_20260713.json`.
> 위 축소 실증(장난감 임베딩 코어)을 **진짜 로컬 소형 LLM+LoRA**로 교체 = Phase 2 실물 첫 걸음.

## 개념 (사용자 질문 "LLM+LoRA가 뭐고 API 대체인가"의 실체)
- **로컬 LLM (Qwen2.5-0.5B)** = 학습가능 신피질. Gemini API(frozen 언어 **도구**)와 다른 상자 —
  네 GPU(RTX 4070 12GB)서 돌고 가중치가 네 것이라 **경험으로 바뀜**. 대화 API 대체가 아니라
  **장난감 임베딩 코어 대체**(자라는 뇌의 실물화). Gemini는 입출력 도구로 당장 공존.
- **LoRA** = 495M 통째 대신 어댑터 1.08M(0.22%)만 학습 → 싸고 안전한 야간 미세조정.
- **sleep-distill** = 그래프 replay 에피소드를 텍스트로 LoRA 학습 → LLM 가중치 변화.

## 환경 (실측)
RTX 4070 SUPER 12GB · torch 2.6+cu124 · transformers 5.13 · peft 0.19. Qwen2.5-0.5B fp16 = 1GB VRAM(여유).

## 결과 1 — 가중치 자기학습 (실 LLM, retrieval 없음)
"아기의 방들"(desk/kitchen/garden/… 실단어 장면) co-occurrence를 LoRA로 학습:
- **base(사전학습만) link-MRR 0.176** (chance 0.033 — 사전지식 prior 약간 있음)
- **LoRA sleep-distill 후 0.382** (Δ **+0.207**, 2배↑; loss 9.95→2.62)
→ ✅ **LoRA 가중치만으로 held-out 예측오차↓ = 진짜 자기학습**(장난감 아닌 실 LLM). 0.22% 파라미터로.

## 결과 2 — 안티망각 (실 LLM은 더 강건)
순차 Task A(desk/kitchen)→B(garden/bath), A replay 없이 online:
- **Task-A MRR: A학습후 0.431 → B학습후 0.421 (Δ−0.01, 유지)** — 파국적 망각 **없음**.
→ **장난감 임베딩 코어(full-train, Δ−0.335 파국망각)와 다름.** LoRA는 어댑터만 갱신+base frozen이라
  **본질적으로 덜 잊는다**("LoRA Learns Less and Forgets Less" TMLR 2024 일치).
→ **함의(정직한 수정)**: sleep-replay의 안티망각 역할은 실 LLM+LoRA에선 **덜 절박**(LoRA가 이미 완화).
  replay는 여전히 유용(통합·미세조정)하나, 축소 프로토타입이 시사한 "파국망각 방지 필수"는 **과장**.
  단 이 테스트는 2-태스크·소어휘·실단어(base가 이미 분리)라 쉬움 — 더 많은 태스크·특이연상선 재확인 필요.

## 결론 & 로드맵
- **Phase 2 실물 첫 성공**: 로컬 소형 LLM이 LoRA sleep-distill로 **가중치를 바꿔 아기 경험을 학습**.
  north star "가중치만으로 예측오차 하강"을 **진짜 모델**로 실증. Gemini(도구) 그대로 공존.
- **정직한 다음**: (a) 합성 실단어 → **실 Neo4j co-occurrence**(비비·엄마 등 아기 특이연상)로 재현,
  (b) sleep-distill을 실 파이프라인(그래프 replay→야간 LoRA)에 연결, (c) 더 많은 순차태스크서 망각
  재확인, (d) effective-rank collapse 감시, (e) 실 Quest 다양장면과 결합. beyond_api LocalProvider 전제.

산출 추가: `scripts/research/llm_core_distill.py`, `claudedocs/research/llm_core_distill_20260713.json`.

---

# 실 데이터 검증 — LLM+LoRA가 아기의 특이연상을 배우는가 (2026-07-13)

> `scripts/research/llm_real_distill.py`, `claudedocs/research/llm_real_distill_20260713.json`.
> 합성 실단어의 한계(base 0.176 = Qwen이 이미 앎 = 사전지식 복구 의심)를 넘어, **실 Neo4j
> 그래프**(비비·엄마·형 등 아기 실제 경험)로 검증. 리트머스 = base가 **모르는** 특이연상 학습?

## 방법
실 RELATES_TO 그래프(518 concept·2241 edge) → held-out 엣지 sampled-neg link-MRR, base vs LoRA
sleep-distill 후. **novelty 층화**: identity 쌍(비비/엄마/형 등) + base가 틀린 쌍(rank>5)에서
LoRA gain 측정 = 진짜 자기학습(사전지식 복구와 구분).

## 결과 (3 seed 확정)
- **base Qwen이 아기 연상 거의 모름**: link-MRR 0.089~0.095 (chance 0.024의 ~4배; 합성 0.176의 절반).
  → "사전지식 복구" 아닌 **진짜 테스트** 확인.
- **identity 쌍(Qwen 불가지) 학습**: base 0.072/0.097/0.075 → LoRA 0.137/0.168/**0.222** (Δ **+0.065/
  +0.071/+0.147**, 평균 **+0.094 ≈ 2.2배**). 3시드 전부 견고, **전체 gain(+0.017~+0.039)의 4배.**
- novelty 층화(base rank>5): +0.025~+0.037 일관 양수. 전체: +0.017~+0.039.

## 판정 (2026-07-16 감사로 수정)
당시 결과는 LoRA weight가 graph replay에 맞춰 변한 탐색 신호지만 **clean held-out 일반화 확정으로
사용하지 않는다.** relationship row 단위 split은 동일 concept pair의 parallel/source별 관계를 train/test에
동시에 둘 수 있었다. 현재 그래프 재현에서는 test 250쌍 중 18쌍(7.2%)이 train에도 존재했다. 당시
2241-edge snapshot 자체가 보존되지 않아 과거 3 seed의 정확한 overlap은 계산할 수 없다. 따라서
identity MRR 증가는 유망하지만 pair-canonicalized 3-seed 재실험 전 “실 데이터 자기학습 확정” 주장은
보류한다.

## 전체 연구 프로그램 귀결
Phase 1 가소성(RW) → Phase 2 코어(스케일서 그래프 역전, 항상성 필수) → 실 LLM+LoRA가 실 데이터
특이연상 학습 가설은 남지만 **자기학습 체인 end-to-end 검증으로 부르지 않는다.** 데이터 밀도·다양성
외에도 leakage-free evaluation, grounded action outcome, learned core의 wake 행동 연결, continual
promotion/rollback이 독립 병목이다.

산출 추가: `scripts/research/llm_real_distill.py`, `claudedocs/research/llm_real_distill_20260713.json`.

---

# (B) 라이브 트리거 연결 (2026-07-13): 코어가 "밤마다" 자동 성장

> `scripts/research/sleep_distill_job.py` + `neural/baby/api_server.py` `_spawn_local_core_distill()`.
> 연구 job을 실 시스템에 연결 — 아기가 대화/관찰할 때 그래프가 차고, 코어는 야간 통합으로 자동 성장.

## 설계 (무거운 GPU 학습이라 안전 우선)
- **하루 1회 게이팅 + 락**: job `--daily-gate` → 오늘 이미 돌았으면 즉시 skip(4.9s, 모델 로드 X),
  동시실행은 원자적 lock(`models/.distill.lock`)으로 차단, hard-kill 대비 **stale-lock TTL 2h**.
- **실패 안전**: Neo4j 다운 시 traceback 없이 clean skip(exit 0) + 마커 미기록(=다음에 재시도).
  성공(그래프 학습)했을 때만 "오늘 완료" 마킹.
- **consolidate(수면) 훅**: `/api/memory/consolidate`(full) 종료 시 `_spawn_local_core_distill()`가
  job을 **detached 서브프로세스**로 spawn(비차단·guarded, consolidate에 영향 0). Neo4j 확실히 켜진
  시점이라 견고. 단 GPU 학습이라 **기본 OFF**.

## 켜는 법 (opt-in)
```bash
# 방법 1 — 수면 훅 (권장): 서버 실행 시 env
LOCAL_CORE_DISTILL=1 python -m neural.baby.api_server --port 8000
#   → 브레인이 잘 때(consolidate) 하루 1회 코어가 자동 학습·성장. Neo4j 켜져 있어야 함.

# 방법 2 — 야간 스케줄 (서버 무관, Neo4j 켜져 있을 때만 유효)
schtasks /create /tn "BabyLocalCoreDistill" /sc daily /st 03:00 \
  /tr "E:\A2A\our-a2a-project\.venv\Scripts\python.exe E:\A2A\our-a2a-project\scripts\research\sleep_distill_job.py --daily-gate --steps 200"

# 수동 1회 (테스트)
python scripts/research/sleep_distill_job.py --daily-gate --steps 200
python scripts/research/sleep_distill_job.py --fresh          # 어댑터 초기화
```

## 검증 (2026-07-13, 2026-07-16 감사 주석)
- 당시 측정: run1 0.089→0.123, run2 0.123(=run1 학습후 정확일치)→0.152, 어댑터 영속(4.5MB).
- **감사 교정**: 당시 job은 test `edges[:250]`을 평가한 뒤 전체 `adj`에서 replay하여 test pair를 같은
  run 학습에 직접 포함했다. 그러므로 위 수치는 persistence/same-probe fit 증거이며 unseen generalization
  또는 “매일 성장”의 증거가 아니다. 두 run의 loss도 각각 3.891→5.775, 2.187→5.421로 종료값이 높다.
- 2026-07-16부터 parallel/reverse 관계를 concept pair로 합친 deterministic pair-disjoint split을 쓰고,
  MRR/identity 비퇴행 gate 통과 때만 adapter를 저장한다. 기존 resumed adapter는 현재 관계를 과거에
  봤을 수 있어 새 평가도 clean future-heldout으로 부르지 않는다. 별도 sealed future canary가 필요하다.
- 게이팅: 같은 날 2회차 즉시 skip(4.9s). Neo4j 다운 시 clean skip(exit 0). 락 finally 해제 + stale TTL.
- 프로덕션 안전: 훅 기본 OFF, 비차단 Popen, 실패 격리. **adversarial review(wf_42f17ed5)가 enable-path
  결함 3개 발견→수정**: OOM clean 처리(try/except+VRAM 프리플라이트), retry-storm 방지(`.last_attempt`
  30분 backoff), 락 무조건 획득(수동 실행 충돌→어댑터 손상 방지). backoff·OOM·락 전부 재테스트 통과.

## 상태 / 남은 것
- **완료**: 코어 학습·영속·게이팅·훅·실패안전 구현. pair-disjoint split과 비퇴행 저장 gate 추가.
- **미완료**: leakage-safe 3-seed 재실험, future canary, forgetting suite, wake 행동 연결. 자율 성장 확정 아님.
- **사용자 액션**: (a) 실제로 켜려면 `LOCAL_CORE_DISTILL=1` + Neo4j 상시 가동, (b) 데이터 밀도 병목은
  Quest 다양장면 수집으로만 풀림(하드웨어). (c) collapse(effective rank) 장기 감시 권장.
