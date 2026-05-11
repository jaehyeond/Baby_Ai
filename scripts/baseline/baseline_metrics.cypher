// =============================================================================
// Baby AI Graph Baseline Metrics — Pure Cypher (no GDS required)
// Created: 2026-05-07
// Purpose: 기준선 측정용. Agentic Deep Graph Reasoning 도입 전후 비교 위함.
// Run: Neo4j Browser 또는 cypher-shell. 각 쿼리 단위로 실행.
// =============================================================================


// -----------------------------------------------------------------------------
// [1] Counts — 전체 규모
// -----------------------------------------------------------------------------
MATCH (c:Concept)            WITH count(c) AS n_concept
MATCH ()-[r:RELATES_TO]->()  WITH n_concept, count(r) AS n_rel
MATCH (e:Experience)         WITH n_concept, n_rel, count(e) AS n_exp
MATCH (br:BrainRegion)       WITH n_concept, n_rel, n_exp, count(br) AS n_region
MATCH ()-[m:MAPPED_TO]->()   WITH n_concept, n_rel, n_exp, n_region, count(m) AS n_mapped
MATCH ()-[i:INVOLVES]->()    WITH n_concept, n_rel, n_exp, n_region, n_mapped, count(i) AS n_inv
RETURN n_concept, n_rel, n_exp, n_region, n_mapped, n_inv,
       toFloat(n_rel) / n_concept AS avg_degree;


// -----------------------------------------------------------------------------
// [2] Degree distribution — Concept 별 연결 수 (방향 무시, RELATES_TO만)
// -----------------------------------------------------------------------------
MATCH (c:Concept)
OPTIONAL MATCH (c)-[r:RELATES_TO]-()
WITH c, count(r) AS deg
RETURN deg, count(c) AS n_nodes
ORDER BY deg;


// -----------------------------------------------------------------------------
// [3] Hub formation — Top 30 by degree (정체성 concept이 hub여야 함)
// -----------------------------------------------------------------------------
MATCH (c:Concept)
OPTIONAL MATCH (c)-[r:RELATES_TO]-()
WITH c, count(r) AS deg
ORDER BY deg DESC LIMIT 30
RETURN c.name AS name,
       c.category AS category,
       deg,
       c.usage_count AS usage,
       coalesce(c.quest_observation_count, 0) AS qcnt,
       c.strength AS strength;


// -----------------------------------------------------------------------------
// [4] Isolated nodes — 연결 없는 고립 concept (그래프 건강성 지표)
// -----------------------------------------------------------------------------
MATCH (c:Concept)
WHERE NOT (c)-[:RELATES_TO]-()
RETURN count(c) AS isolated_count,
       collect(c.name)[..20] AS sample_names;


// -----------------------------------------------------------------------------
// [5] Category distribution — Concept이 어느 영역에 쏠려있는가
// -----------------------------------------------------------------------------
MATCH (c:Concept)
RETURN coalesce(c.category, '<null>') AS category,
       count(c) AS n
ORDER BY n DESC;


// -----------------------------------------------------------------------------
// [6] BrainRegion mapping distribution — MAPPED_TO 분포
// -----------------------------------------------------------------------------
MATCH (c:Concept)-[:MAPPED_TO]->(br:BrainRegion)
RETURN br.name AS region,
       count(c) AS n_concepts
ORDER BY n_concepts DESC;


// -----------------------------------------------------------------------------
// [7] Edge weight distribution — RELATES_TO strength 분포 (Hebbian 효과 측정)
// -----------------------------------------------------------------------------
MATCH ()-[r:RELATES_TO]->()
WITH coalesce(r.strength, r.weight, 0.0) AS w
RETURN min(w) AS min_w, max(w) AS max_w, avg(w) AS avg_w,
       percentileCont(w, 0.5) AS median_w,
       percentileCont(w, 0.9) AS p90_w,
       count(*) AS n_edges;


// -----------------------------------------------------------------------------
// [8] Sampled shortest paths — 무작위 100쌍 평균 경로 길이 (small-world)
// 주의: 큰 그래프에선 비싸므로 LIMIT으로 sample
// -----------------------------------------------------------------------------
MATCH (a:Concept), (b:Concept)
WHERE id(a) < id(b)
WITH a, b, rand() AS r
ORDER BY r LIMIT 100
MATCH p = shortestPath((a)-[:RELATES_TO*..10]-(b))
RETURN avg(length(p)) AS avg_path_len,
       max(length(p)) AS max_path_len,
       min(length(p)) AS min_path_len,
       count(p) AS reachable_pairs;
// reachable_pairs / 100 = 연결성 비율


// -----------------------------------------------------------------------------
// [9] Identity hub check — 정체성 concept (비비, 엄마 등) degree
// -----------------------------------------------------------------------------
MATCH (c:Concept)
WHERE c.name IN ['비비', 'baby', '엄마', 'mom', '아빠', 'dad']
   OR c.category = 'identity'
OPTIONAL MATCH (c)-[r:RELATES_TO]-()
RETURN c.name AS name, c.category AS category, count(r) AS degree
ORDER BY degree DESC;


// -----------------------------------------------------------------------------
// [10] Quest passthrough source breakdown — A4.x 추적
// -----------------------------------------------------------------------------
MATCH (c:Concept)
WHERE 'quest_passthrough' IN coalesce(c.sources, [])
OPTIONAL MATCH (c)-[r:RELATES_TO]-()
WITH c, count(r) AS deg
RETURN count(c) AS n_quest_concepts,
       avg(deg) AS avg_quest_degree,
       collect({name: c.name, deg: deg, qcnt: c.quest_observation_count})[..15] AS top_samples;
