# Brain Health Monitor — Gap#6 상시 모니터링

> RESEARCH_SYNTHESIS_2026-07-12 §3 gap#6. "lift 숫자 하나로는 continual-learning 실패모드를
> 못 본다." 자기학습 시스템은 개선처럼 보이며 무너질 수 있다 → **4-지표 시계열 + 임계 알림.**

## 무엇을 보는가 (4 지표)

| # | 지표 | 감지 대상 | 계산 |
|---|---|---|---|
| 1 | **prediction** | 구조적 예측력 저하 | held-out link-prediction lift/MRR (measure_prediction 재사용) |
| 2 | **collapse** | 허브지배·가중치 붕괴·고립 | degree Gini · 가중치 엔트로피 · 고립률 · 최대허브 |
| 3 | **forgetting** | 과거 연상 망각 | 고정 probe(강한 엣지 30개) recall@10, baseline 대비 하락 |
| 4 | **plasticity** | 신규 학습능력 상실 | synthetic 연상 주입→회상 확인→rollback (비파괴) |

*주: 진짜 plasticity-loss(가중치, Dohare/Sutton)는 Phase 2 trainable 코어 이후 측정. 현재는
그래프 학습 메커니즘 헬스체크.*

## 출력
- `claudedocs/monitoring/brain_health.jsonl` — append-only 시계열(한 줄=한 실행). 추세 분석용.
- `claudedocs/monitoring/forgetting_probe.json` — 첫 실행시 생성되는 **고정 probe 집합**(이후 불변).
- 콘솔: 직전 실행 대비 추세(Δ) + 🟢OK / 🔴ALERT.

## 임계값 (breach 시 alert) — 초기값, 데이터 쌓이며 조정
```
isolated_ratio    > 0.55   (고립 노드 과다)
degree_gini       > 0.88   (허브지배)
weight_entropy    < 0.35   (가중치 붕괴)
prediction_lift   < 2.0    (구조 예측력 붕괴)
forgetting recall drop > 0.20  (baseline 대비 망각)
plasticity 실패            (신규 연상 학습·회상 불가)
```
현재 baseline(2026-07-12): 840 concept(518 connected)/2085 edge, lift **7.86**, isolated **0.383**,
gini 0.65, W-entropy 0.867, forgetting recall **0.70**, plasticity ✅ → 🟢 전부 정상.

## 상시화 (어떻게 정기 실행되나)
**주 경로 = consolidate(수면) 훅**: `POST /api/memory/consolidate` (mode=full) 이 끝날 때
`_spawn_health_monitor()`가 이 스크립트를 **detached 백그라운드**로 실행(비차단·실패무해).
→ 브레인이 잘 때마다 자동 스냅샷. Neo4j가 확실히 켜진 시점이라 견고. (frontend idle-sleep이
consolidate를 트리거하므로 사용자 개입 불필요.)

**수동/추가 스케줄** (선택):
```bash
# 즉시 1회
python scripts/monitoring/brain_health_monitor.py
# probe 재생성 (그래프 대폭 변경 후)
python scripts/monitoring/brain_health_monitor.py --reset-probe
# Windows 야간 스케줄 (Neo4j 켜져 있을 때만 유효)
schtasks /create /tn "BabyBrainHealth" /tr "E:\A2A\our-a2a-project\.venv\Scripts\python.exe E:\A2A\our-a2a-project\scripts\monitoring\brain_health_monitor.py" /sc daily /st 03:00
```

## 추세 보기
```bash
# 최근 5개 스냅샷의 핵심 지표
python -c "import json;[print(j['timestamp'][:19], 'lift',j['prediction']['lift_vs_random'],'iso',j['collapse']['isolated_ratio'],'recall',j['forgetting']['recall@10'],j['health']) for j in map(json.loads, open('claudedocs/monitoring/brain_health.jsonl',encoding='utf-8').read().splitlines()[-5:])]"
```

## 왜 이 지표들인가 (근거)
continual learning의 3대 실패모드 = catastrophic forgetting(지표3) · model/representation collapse
(지표2) · loss of plasticity(지표4). 여기에 최종 성능 대리(지표1)를 더해, "개선"과 "붕괴"를
구별한다. 데이터(embodiment 스트림)가 쌓이고 가소성 규칙(RW)·Phase2 코어가 들어올 때 이 4개가
동시에 건강 범위를 유지하는지가 자기학습이 **안전하게** 진행되는지의 판정.
