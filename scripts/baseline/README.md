# Baby AI Graph Baseline Measurement

> **목적**: Concept/RELATES_TO 그래프의 구조적·기능적 baseline을 정량 측정한다.
> Agentic Deep Graph Reasoning (arXiv 2502.13025) 같은 신규 메커니즘 도입 전후 비교에 사용.

## 왜 baseline인가

새 시스템 도입 후 "Concept이 1500개 됐다"는 숫자만 보고는 **건강한 성장 vs 폭증**을 구별할 수 없다.
도입 전(=baseline) 측정값과의 diff 가 있어야 효과를 주장할 수 있다.

## 의존성

- Neo4j 5+ (현재 2026.03.1 동작 확인)
- Python: `neo4j`, `networkx>=3`, `scipy`, `python-dotenv`
- **GDS 플러그인 불필요** (networkx로 modularity/betweenness 처리)

## 파일

| 파일 | 용도 |
|---|---|
| `baseline_metrics.cypher` | Neo4j Browser에서 직접 실행 가능한 raw Cypher (재현성용) |
| `measure_baseline.py` | 구조 메트릭 — degree dist, hubs, modularity, path, betweenness, power-law |
| `functional_tests.py` | 기능 테스트 — identity reach, spreading reach, color binding (A4.4) |
| `README.md` | 운영 규약 (이 파일) |

## 사용법

```bash
# 1) 도입 전 baseline (반드시 측정)
python scripts/baseline/measure_baseline.py --tag before_adgr
python scripts/baseline/functional_tests.py --tag before_adgr

# 2) 신규 메커니즘 도입 (예: Agentic Deep Graph Reasoning v1)

# 3) 도입 후 측정
python scripts/baseline/measure_baseline.py --tag after_adgr_v1
python scripts/baseline/functional_tests.py --tag after_adgr_v1

# 4) Diff 확인
diff claudedocs/baseline/baseline_before_adgr_*.md \
     claudedocs/baseline/baseline_after_adgr_v1_*.md
```

## 측정 시점 규약

다음 시점에 자동/수동 측정한다:

- ✅ **신규 메커니즘 도입 직전** (필수, baseline)
- ✅ **신규 메커니즘 도입 직후** (효과 측정)
- 🟡 매 phase 종료 시 (A4.5α, A4.5C, A4.5D 등)
- 🟡 수면 모드 대량 실행 후 (Hebbian decay/strengthen 효과)
- 🟡 월 1회 정기 (장기 추세 추적)

`tag` 명명 규칙: `<phase>_<state>_<vN>` 예: `a4.4_after`, `before_adgr`, `weekly_2026w19`.

## 출력

`claudedocs/baseline/` 에 두 형태로 저장:

```
baseline_<tag>_<YYYYMMDD>.json   # 머신용 (diff/grep)
baseline_<tag>_<YYYYMMDD>.md     # 사람용 (PR/논문)
functional_<tag>_<YYYYMMDD>.json
```

## 메트릭 해석 가이드

### 구조 (measure_baseline.py)

| 메트릭 | 건강 범위 | 해석 |
|---|---|---|
| isolated ratio | < 10% | 노드는 늘었는데 엣지가 따라오지 못하면 위험 |
| power-law alpha | 2.0–3.0 | 인간 뇌·SNS 같은 자연 그래프 범위 |
| power-law R² | ≥ 0.7 | scale-free 가설의 강도 |
| modularity Q | 0.3–0.75 | 너무 낮으면 분화 X, 너무 높으면 통합 X |
| avg path length | 3–6 | 작은 세계(small-world) |
| hub identity | 정체성 concept이 top-30 안 | "비비"가 hub가 아니면 자아 학습 부족 |

### 기능 (functional_tests.py)

| 테스트 | 합격 기준 | 의미 |
|---|---|---|
| identity reach (6hop) | ≥ 80% | 정체성이 그래프 어디서든 짧은 경로로 도달 가능 |
| spreading reach (k=3) | ≥ 5–20% of graph | 너무 적으면 sparse, 너무 많으면 hub 한 개에 쏠림 |
| color binding | bound > standalone | A4.4 binding이 작동 중 |

## 한계 (의식적으로 명시)

1. **메트릭은 수학적 건강성**이지 인지적 정확성은 아님. 실제 대화·발달 품질은 별도 평가 필요
2. **shortest path는 200쌍 sampling** — 분산 큼. 결정적 결론 전 multiple seed 권장
3. **betweenness는 970 노드는 full 계산**, 5k 초과 시 자동 k-sample (정확도 ↓)
4. **Louvain은 stochastic** — `seed=42` 고정했지만 공식 결정론은 아님
5. **인간 뇌 비교 baseline 없음** — "정상 범위"는 graph theory 일반론 기준일 뿐

## 다음 단계

- [x] 첫 baseline 측정 (2026-05-07) → `initial_2026-05-07` tag
- [x] Phase Q1 처리: visual_cooc Hebbian + backfill (2026-05-08) → `after_q1_visual_cooc` tag
- [ ] spreading_reach 11.3%→5.9% 감소 원인 규명 (sample size↑, cluster overlap)
- [ ] 단발 Experience (saved<2) sleep mode replay 검증
- [ ] Agentic Deep Graph Reasoning 미니 구현 (별도 source='adgr_v1')
- [ ] 도입 후 재측정 → diff 분석

## 관련 메모리

- [q1_visual_cooc_completed.md](../../../../../C:/Users/SOGANG/.claude/projects/e--A2A/memory/q1_visual_cooc_completed.md) — Q1 작업 상세
- `scripts/maintenance/backfill_visual_cooc.py` — backfill 스크립트
