# Baby AI Graph Baseline — after_q1_active_only

- **Timestamp**: 2026-05-07T15:16:56.119595+00:00
- **DB**: `bolt://localhost:7687` / `neo4j`

## 1. Counts
- Concept: **819**
- RELATES_TO: **1753**
- Avg degree: **4.28**
- Isolated nodes: **324**  (39.6%)
- Density: 0.00523

## 2. Degree distribution
- min/median/p90/p99/max: 0 / 1 / 13 / 37 / 101

## 3. Power-law fit
- alpha (exponent): **1.191**
- R²: **0.730**
- → heavy-tailed but unstable mean (alpha=1.19 < 2)

## 4. Hubs (top 10)
| name | category | degree | usage | qcnt |
|---|---|---|---|---|
| 비비 | 이름 | 101 | 3812 | 0 |
| AI | agent | 91 | 1606 | 0 |
| 공부 | 행위 | 62 | 967 | 0 |
| 놀이 | 활동 | 52 | 436 | 0 |
| 검색 | 행위 | 41 | 1063 | 0 |
| 안녕하세요 | conversation | 40 | 3 | 0 |
| 날짜 | 시간 | 39 | 965 | 0 |
| 사용자 | person | 38 | 475 | 0 |
| 알려주세요 | 요청 | 37 | 53 | 0 |
| 개발자 | 인물 | 37 | 1898 | 0 |

## 5. Modularity
- Q = **0.43410670302204857**
- communities: 19
- GCC: 331 nodes (40.4% of graph)
- → moderate — some structure but blurry boundaries

## 6. Path length (sampled)
- reachable: 200/200
- avg: **3.32**
- → small-world range (healthy)

## 7. Betweenness (top 10 bridges)
| name | category | betweenness | degree |
|---|---|---|---|
| AI | agent | 0.422852 | 91 |
| 비비 | 이름 | 0.356993 | 101 |
| 기억력 | 인지 능력 | 0.098027 | 13 |
| 날짜 | 시간 | 0.088052 | 39 |
| 공부 | 행위 | 0.084539 | 62 |
| 검색 | 행위 | 0.065185 | 41 |
| 날씨 | 추상적 개념 | 0.061397 | 12 |
| 서울 | location | 0.049555 | 8 |
| 개발자 | 인물 | 0.047497 | 37 |
| 안녕하세요 | conversation | 0.044191 | 40 |

## 8. Identity concepts
| name | category | degree | strength |
|---|---|---|---|
| 비비 | 이름 | 168 | 0.96813216492917 |
| 엄마 | 인간 | 0 | 0.60036378701305 |

## 9. Category distribution
- frozen_knowledge: 151
- conversation: 87
- visual: 61
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
- occipital: 98
- temporal: 93
- motor_cortex: 80
- amygdala: 66
- parietal: 19
- cerebellum: 6
- brain_stem: 4

## 11. Quest passthrough
- n_quest_concepts: 60
- avg_degree: 5.716666666666669

---
## Health verdict (auto-derived)
- ⚠️  isolated nodes 39.6% — concept generation outpacing edge formation
- ✅ scale-free likely (R²=0.73, alpha=1.19)
- ✅ modularity Q=0.43 in healthy range
- ✅ small-world avg path=3.32