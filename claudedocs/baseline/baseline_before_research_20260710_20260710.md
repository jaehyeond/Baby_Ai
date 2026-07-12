# Baby AI Graph Baseline — before_research_20260710

- **Timestamp**: 2026-07-10T10:07:30.337439+00:00
- **DB**: `bolt://localhost:7687` / `neo4j`

## 1. Counts
- Concept: **978**
- RELATES_TO: **1793**
- Avg degree: **3.67**
- Isolated nodes: **473**  (48.4%)
- Density: 0.00375

## 2. Degree distribution
- min/median/p90/p99/max: 0 / 1 / 11 / 38 / 102

## 3. Power-law fit
- alpha (exponent): **1.147**
- R²: **0.728**
- → heavy-tailed but unstable mean (alpha=1.15 < 2)

## 4. Hubs (top 10)
| name | category | degree | usage | qcnt |
|---|---|---|---|---|
| 비비 | 이름 | 102 | 3812 | 0 |
| AI | agent | 92 | 1606 | 0 |
| 공부 | 행위 | 63 | 967 | 0 |
| 놀이 | 활동 | 53 | 436 | 0 |
| 검색 | 행위 | 41 | 1063 | 0 |
| 안녕하세요 | conversation | 41 | 3 | 0 |
| 날짜 | 시간 | 40 | 965 | 0 |
| 사용자 | person | 39 | 475 | 0 |
| 알려주세요 | 요청 | 38 | 53 | 0 |
| 개발자 | 인물 | 38 | 1898 | 0 |

## 5. Modularity
- Q = **0.4341076114999923**
- communities: 19
- GCC: 334 nodes (34.2% of graph)
- → moderate — some structure but blurry boundaries

## 6. Path length (sampled)
- reachable: 200/200
- avg: **3.16**
- → small-world range (healthy)

## 7. Betweenness (top 10 bridges)
| name | category | betweenness | degree |
|---|---|---|---|
| AI | agent | 0.4202 | 92 |
| 비비 | 이름 | 0.354314 | 102 |
| 기억력 | 인지 능력 | 0.097188 | 13 |
| 날짜 | 시간 | 0.087347 | 40 |
| 공부 | 행위 | 0.084006 | 63 |
| 검색 | 행위 | 0.064179 | 41 |
| 날씨 | 추상적 개념 | 0.060834 | 12 |
| 서울 | location | 0.049056 | 8 |
| 개발자 | 인물 | 0.047377 | 38 |
| 기억 | cognitive_ability | 0.043256 | 34 |

## 8. Identity concepts
| name | category | degree | strength |
|---|---|---|---|
| 비비 | 이름 | 168 | 0.96813216492917 |
| 엄마 | 인간 | 0 | 0.60036378701305 |

## 9. Category distribution
- frozen_knowledge: 151
- conversation: 87
- visual: 69
- 감정: 57
- 행위: 54
- 사물: 28
- 추상적 개념: 26
- 활동: 19
- 행동: 18
- 상태: 17
- 시간: 15
- 정보: 15
- 속성: 15
- 음식: 14
- person: 11

## 10. Region distribution (MAPPED_TO)
- prefrontal: 561
- occipital: 106
- temporal: 93
- motor_cortex: 80
- amygdala: 66
- parietal: 19
- cerebellum: 6
- brain_stem: 4

## 11. Quest passthrough
- n_quest_concepts: 60
- avg_degree: 5.750000000000001

---
## Health verdict (auto-derived)
- ⚠️  isolated nodes 48.4% — concept generation outpacing edge formation
- ✅ scale-free likely (R²=0.73, alpha=1.15)
- ✅ modularity Q=0.43 in healthy range
- ✅ small-world avg path=3.16