-- ═══════════════════════════════════════════════════════════════════════════════
-- ICDL 2026 ABLATION STUDY ANALYSIS QUERIES (v2 - Schema-Corrected)
-- Baby AI System - Supabase Database
-- Generated: 2026-02-19
-- Schema: ablation_metrics(run_id, turn_number, vocabulary_size, emotional_modulator,
--         curiosity, joy, fear, surprise, frustration, boredom, development_stage, ...)
-- ═══════════════════════════════════════════════════════════════════════════════

-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 1: SUMMARY STATISTICS BY CONDITION
-- ───────────────────────────────────────────────────────────────────────────────
-- Purpose: Central tendency and dispersion measures for final vocabulary size
-- Paper relevance: Table 1 showing primary outcome metrics (§17 Results)

WITH stats_per_condition AS (
  SELECT
    condition,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY final_concept_count) AS concept_median,
    AVG(final_concept_count) AS concept_mean,
    MIN(final_concept_count) AS concept_min,
    MAX(final_concept_count) AS concept_max,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY final_concept_count) AS concept_q1,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY final_concept_count) AS concept_q3,
    STDDEV_SAMP(final_concept_count) AS concept_sd,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY final_relation_count) AS relation_median,
    AVG(final_relation_count) AS relation_mean,
    STDDEV_SAMP(final_relation_count) AS relation_sd,
    COUNT(*) AS n
  FROM ablation_runs
  WHERE status = 'completed'
  GROUP BY condition
)
SELECT
  condition,
  ROUND(concept_median::numeric, 1) AS concept_median,
  ROUND(concept_mean::numeric, 1) AS concept_mean,
  concept_min, concept_max,
  ROUND((concept_q3 - concept_q1)::numeric, 1) AS concept_iqr,
  ROUND(concept_sd::numeric, 2) AS concept_sd,
  ROUND(relation_median::numeric, 1) AS rel_median,
  ROUND(relation_mean::numeric, 1) AS rel_mean,
  ROUND(relation_sd::numeric, 2) AS rel_sd,
  n
FROM stats_per_condition
ORDER BY CASE condition
  WHEN 'C_full' THEN 1 WHEN 'C_nostage' THEN 2
  WHEN 'C_noemo' THEN 3 WHEN 'C_nosleep' THEN 4
END;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 2: VOCABULARY GROWTH TRAJECTORY (per-turn)
-- ───────────────────────────────────────────────────────────────────────────────
-- Purpose: Track concept acquisition curve across 60 conversations
-- Paper: Figure 3 - Learning curve visualization, sigmoid shape comparison with CDI
-- Uses: ablation_metrics.vocabulary_size (cumulative concepts at each turn)

SELECT
  ar.condition,
  am.turn_number,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY am.vocabulary_size) AS median_vocab,
  ROUND(AVG(am.vocabulary_size)::numeric, 1) AS mean_vocab,
  ROUND(STDDEV_POP(am.vocabulary_size)::numeric, 1) AS sd_vocab,
  MIN(am.vocabulary_size) AS min_vocab,
  MAX(am.vocabulary_size) AS max_vocab,
  COUNT(*) AS n
FROM ablation_metrics am
JOIN ablation_runs ar ON am.run_id = ar.id
WHERE ar.status = 'completed'
GROUP BY ar.condition, am.turn_number
ORDER BY CASE ar.condition
  WHEN 'C_full' THEN 1 WHEN 'C_nostage' THEN 2
  WHEN 'C_noemo' THEN 3 WHEN 'C_nosleep' THEN 4
END, am.turn_number;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 3: RELATION DENSITY (CONNECTIVITY METRIC)
-- ───────────────────────────────────────────────────────────────────────────────
-- Purpose: Semantic network connectivity (relations per concept)
-- Paper: Network topology - density indicates integration quality

WITH density_per_run AS (
  SELECT
    ar.condition, ar.repetition,
    ar.final_concept_count, ar.final_relation_count,
    CASE WHEN ar.final_concept_count > 0
      THEN ar.final_relation_count::float / ar.final_concept_count ELSE 0
    END AS relation_density
  FROM ablation_runs ar
  WHERE ar.status = 'completed'
)
SELECT
  condition,
  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY relation_density)::numeric, 3) AS median_density,
  ROUND(AVG(relation_density)::numeric, 3) AS mean_density,
  ROUND(STDDEV_POP(relation_density)::numeric, 3) AS sd_density,
  ROUND(AVG(final_relation_count)::numeric, 1) AS mean_relations,
  ROUND(AVG(final_concept_count)::numeric, 1) AS mean_concepts,
  COUNT(*) AS n
FROM density_per_run
GROUP BY condition
ORDER BY CASE condition
  WHEN 'C_full' THEN 1 WHEN 'C_nostage' THEN 2
  WHEN 'C_noemo' THEN 3 WHEN 'C_nosleep' THEN 4
END;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 4: CONCEPT DIVERSITY (CATEGORICAL BREADTH)
-- ───────────────────────────────────────────────────────────────────────────────

WITH categories_per_run AS (
  SELECT
    sc.ablation_run_id,
    COUNT(DISTINCT sc.category) AS unique_categories,
    COUNT(*) AS total_concepts
  FROM semantic_concepts sc
  WHERE sc.ablation_run_id IS NOT NULL AND sc.category IS NOT NULL
  GROUP BY sc.ablation_run_id
)
SELECT
  ar.condition,
  ROUND(AVG(cpr.unique_categories)::numeric, 1) AS mean_categories,
  MIN(cpr.unique_categories) AS min_cat, MAX(cpr.unique_categories) AS max_cat,
  ROUND(AVG(cpr.unique_categories::float / NULLIF(cpr.total_concepts, 0) * 10)::numeric, 2) AS categories_per_10_concepts,
  COUNT(*) AS n
FROM categories_per_run cpr
JOIN ablation_runs ar ON cpr.ablation_run_id = ar.id
WHERE ar.status = 'completed'
GROUP BY ar.condition
ORDER BY CASE ar.condition
  WHEN 'C_full' THEN 1 WHEN 'C_nostage' THEN 2
  WHEN 'C_noemo' THEN 3 WHEN 'C_nosleep' THEN 4
END;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 5: DEVELOPMENTAL STAGE PROGRESSION
-- ───────────────────────────────────────────────────────────────────────────────
-- Purpose: Final stage + stage at each turn (from ablation_metrics.development_stage)

SELECT
  ar.condition,
  ar.repetition,
  (ar.final_baby_state->>'development_stage')::int AS final_stage,
  ar.final_concept_count,
  ROUND(EXTRACT(EPOCH FROM (ar.completed_at - ar.started_at)) / 60.0, 1) AS duration_min
FROM ablation_runs ar
WHERE ar.status = 'completed'
ORDER BY CASE ar.condition
  WHEN 'C_full' THEN 1 WHEN 'C_nostage' THEN 2
  WHEN 'C_noemo' THEN 3 WHEN 'C_nosleep' THEN 4
END, ar.repetition;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 6: EMOTIONAL MODULATOR DYNAMICS (M(e) over time)
-- ───────────────────────────────────────────────────────────────────────────────
-- Purpose: Track LC-NE M(e) values - the v28 formula in action
-- Paper: Shows inverted-U behavior and emotion→learning coupling
-- Uses: ablation_metrics.emotional_modulator (direct column)

SELECT
  ar.condition,
  ROUND(AVG(am.emotional_modulator)::numeric, 3) AS mean_M_e,
  ROUND(STDDEV_POP(am.emotional_modulator)::numeric, 3) AS sd_M_e,
  ROUND(MIN(am.emotional_modulator)::numeric, 3) AS min_M_e,
  ROUND(MAX(am.emotional_modulator)::numeric, 3) AS max_M_e,
  -- Early vs Late comparison (arousal trajectory)
  ROUND(AVG(CASE WHEN am.turn_number <= 20 THEN am.emotional_modulator END)::numeric, 3) AS M_e_early,
  ROUND(AVG(CASE WHEN am.turn_number BETWEEN 21 AND 40 THEN am.emotional_modulator END)::numeric, 3) AS M_e_mid,
  ROUND(AVG(CASE WHEN am.turn_number > 40 THEN am.emotional_modulator END)::numeric, 3) AS M_e_late,
  COUNT(DISTINCT ar.repetition) AS n
FROM ablation_metrics am
JOIN ablation_runs ar ON am.run_id = ar.id
WHERE ar.status = 'completed'
GROUP BY ar.condition
ORDER BY CASE ar.condition
  WHEN 'C_full' THEN 1 WHEN 'C_nostage' THEN 2
  WHEN 'C_noemo' THEN 3 WHEN 'C_nosleep' THEN 4
END;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 6b: M(e) TRAJECTORY (per turn, per condition)
-- ───────────────────────────────────────────────────────────────────────────────
-- For Figure: M(e) curve overlay across conditions

SELECT
  ar.condition,
  am.turn_number,
  ROUND(AVG(am.emotional_modulator)::numeric, 3) AS mean_M_e,
  ROUND(AVG(am.curiosity)::numeric, 3) AS mean_curiosity,
  ROUND(AVG(am.fear)::numeric, 3) AS mean_fear,
  ROUND(AVG(am.frustration)::numeric, 3) AS mean_frustration,
  ROUND(AVG(am.vocabulary_size)::numeric, 1) AS mean_vocab
FROM ablation_metrics am
JOIN ablation_runs ar ON am.run_id = ar.id
WHERE ar.status = 'completed'
GROUP BY ar.condition, am.turn_number
ORDER BY CASE ar.condition
  WHEN 'C_full' THEN 1 WHEN 'C_nostage' THEN 2
  WHEN 'C_noemo' THEN 3 WHEN 'C_nosleep' THEN 4
END, am.turn_number;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 7: EFFECT SIZE CALCULATION (COHEN'S D)
-- ───────────────────────────────────────────────────────────────────────────────
-- Uses STDDEV_SAMP for proper pooled SD with small n (n=5 per condition)

WITH baseline AS (
  SELECT AVG(final_concept_count) AS mu, STDDEV_SAMP(final_concept_count) AS sd, COUNT(*) AS n
  FROM ablation_runs WHERE condition = 'C_full' AND status = 'completed'
),
ablation AS (
  SELECT condition, AVG(final_concept_count) AS mu, STDDEV_SAMP(final_concept_count) AS sd, COUNT(*) AS n
  FROM ablation_runs WHERE condition != 'C_full' AND status = 'completed'
  GROUP BY condition
)
SELECT
  a.condition,
  ROUND(b.mu::numeric, 1) AS mean_full,
  ROUND(a.mu::numeric, 1) AS mean_ablation,
  ROUND((b.mu - a.mu)::numeric, 1) AS diff,
  ROUND(SQRT(((b.n-1)*POWER(b.sd,2) + (a.n-1)*POWER(a.sd,2)) / NULLIF(b.n+a.n-2, 0))::numeric, 2) AS pooled_sd,
  ROUND(((b.mu - a.mu) / NULLIF(SQRT(((b.n-1)*POWER(b.sd,2) + (a.n-1)*POWER(a.sd,2)) / NULLIF(b.n+a.n-2, 0)), 0))::numeric, 3) AS cohens_d,
  CASE
    WHEN ABS((b.mu - a.mu) / NULLIF(SQRT(((b.n-1)*POWER(b.sd,2) + (a.n-1)*POWER(a.sd,2)) / NULLIF(b.n+a.n-2, 0)), 0)) < 0.2 THEN 'negligible'
    WHEN ABS((b.mu - a.mu) / NULLIF(SQRT(((b.n-1)*POWER(b.sd,2) + (a.n-1)*POWER(a.sd,2)) / NULLIF(b.n+a.n-2, 0)), 0)) < 0.5 THEN 'small'
    WHEN ABS((b.mu - a.mu) / NULLIF(SQRT(((b.n-1)*POWER(b.sd,2) + (a.n-1)*POWER(a.sd,2)) / NULLIF(b.n+a.n-2, 0)), 0)) < 0.8 THEN 'medium'
    ELSE 'large'
  END AS effect_size,
  b.n AS n_full, a.n AS n_ablation
FROM ablation a CROSS JOIN baseline b
ORDER BY CASE a.condition
  WHEN 'C_nostage' THEN 1 WHEN 'C_noemo' THEN 2 WHEN 'C_nosleep' THEN 3
END;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 8: DATA QUALITY + OUTLIER DETECTION
-- ───────────────────────────────────────────────────────────────────────────────

WITH condition_stats AS (
  SELECT condition,
    AVG(final_concept_count) AS mu,
    STDDEV_POP(final_concept_count) AS sd
  FROM ablation_runs WHERE status = 'completed'
  GROUP BY condition
)
SELECT
  ar.condition, ar.repetition, ar.final_concept_count, ar.final_relation_count,
  ROUND(cs.mu::numeric, 1) AS condition_mean,
  ROUND(cs.sd::numeric, 2) AS condition_sd,
  ROUND(((ar.final_concept_count - cs.mu) / NULLIF(cs.sd, 0))::numeric, 2) AS z_score,
  CASE
    WHEN ABS((ar.final_concept_count - cs.mu) / NULLIF(cs.sd, 0)) > 3 THEN 'EXTREME'
    WHEN ABS((ar.final_concept_count - cs.mu) / NULLIF(cs.sd, 0)) > 2 THEN 'outlier'
    ELSE 'normal'
  END AS status
FROM ablation_runs ar
JOIN condition_stats cs ON ar.condition = cs.condition
WHERE ar.status = 'completed'
ORDER BY ABS((ar.final_concept_count - cs.mu) / NULLIF(cs.sd, 0)) DESC;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 9: CONCEPT ACQUISITION RATE BY STAGE (learning acceleration)
-- ───────────────────────────────────────────────────────────────────────────────
-- Purpose: Measure new concepts per turn at each developmental stage
-- Paper: Tests whether stage gates create vocabulary "spurts" (cf. CDI 18-24mo)

WITH per_turn AS (
  SELECT
    ar.condition,
    am.turn_number,
    am.development_stage,
    am.vocabulary_size,
    am.vocabulary_size - LAG(am.vocabulary_size, 1, 0) OVER (
      PARTITION BY am.run_id ORDER BY am.turn_number
    ) AS new_this_turn
  FROM ablation_metrics am
  JOIN ablation_runs ar ON am.run_id = ar.id
  WHERE ar.status = 'completed'
)
SELECT
  condition,
  development_stage,
  COUNT(*) AS n_turns,
  ROUND(AVG(new_this_turn)::numeric, 2) AS mean_new_per_turn,
  ROUND(SUM(new_this_turn)::numeric / COUNT(DISTINCT turn_number), 2) AS concepts_per_turn,
  ROUND(STDDEV_POP(new_this_turn)::numeric, 2) AS sd_new
FROM per_turn
WHERE new_this_turn IS NOT NULL
GROUP BY condition, development_stage
ORDER BY CASE condition
  WHEN 'C_full' THEN 1 WHEN 'C_nostage' THEN 2
  WHEN 'C_noemo' THEN 3 WHEN 'C_nosleep' THEN 4
END, development_stage;


-- ═══════════════════════════════════════════════════════════════════════════════
-- CDI-ALIGNED ANALYSIS QUERIES (using ablation_concepts_normalized view)
-- ═══════════════════════════════════════════════════════════════════════════════

-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 10: CDI-NORMALIZED CATEGORY BREADTH PER CONDITION
-- ───────────────────────────────────────────────────────────────────────────────
-- Purpose: Compare categorical diversity across conditions using CDI-aligned categories
-- Paper: Table 2 - Shows whether ablation conditions limit conceptual breadth

SELECT
  ar.condition,
  ar.repetition,
  COUNT(DISTINCT acn.cdi_category) AS unique_cdi_categories,
  COUNT(*) AS total_concepts,
  ROUND(COUNT(DISTINCT acn.cdi_category)::numeric / NULLIF(COUNT(*), 0) * 10, 2) AS categories_per_10_concepts,
  STRING_AGG(DISTINCT acn.cdi_category, ', ' ORDER BY acn.cdi_category) AS categories_present
FROM ablation_concepts_normalized acn
JOIN ablation_runs ar ON acn.ablation_run_id = ar.id
WHERE ar.status = 'completed'
GROUP BY ar.condition, ar.repetition
ORDER BY CASE ar.condition
  WHEN 'C_full' THEN 1 WHEN 'C_nostage' THEN 2
  WHEN 'C_noemo' THEN 3 WHEN 'C_nosleep' THEN 4
END, ar.repetition;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 11: CDI CATEGORY DISTRIBUTION SUMMARY BY CONDITION
-- ───────────────────────────────────────────────────────────────────────────────
-- Purpose: Aggregate category distribution per condition (median across reps)
-- Paper: Figure 5 - Stacked bar chart of category proportions

WITH per_run_cats AS (
  SELECT
    ar.condition,
    ar.id AS run_id,
    acn.cdi_category,
    COUNT(*) AS n
  FROM ablation_concepts_normalized acn
  JOIN ablation_runs ar ON acn.ablation_run_id = ar.id
  WHERE ar.status = 'completed'
  GROUP BY ar.condition, ar.id, acn.cdi_category
)
SELECT
  condition,
  cdi_category,
  ROUND(AVG(n)::numeric, 1) AS mean_count,
  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY n)::numeric, 1) AS median_count,
  COUNT(*) AS n_runs_with_category
FROM per_run_cats
GROUP BY condition, cdi_category
ORDER BY CASE condition
  WHEN 'C_full' THEN 1 WHEN 'C_nostage' THEN 2
  WHEN 'C_noemo' THEN 3 WHEN 'C_nosleep' THEN 4
END, mean_count DESC;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 12: SHANNON DIVERSITY INDEX PER RUN
-- ───────────────────────────────────────────────────────────────────────────────
-- Purpose: Quantitative measure of categorical diversity (H' = -Σ pi ln(pi))
-- Paper: Single metric for diversity comparison; higher H' = more diverse vocabulary

WITH category_counts AS (
  SELECT
    acn.ablation_run_id,
    acn.cdi_category,
    COUNT(*) AS n
  FROM ablation_concepts_normalized acn
  GROUP BY acn.ablation_run_id, acn.cdi_category
),
run_totals AS (
  SELECT ablation_run_id, SUM(n) AS total
  FROM category_counts
  GROUP BY ablation_run_id
),
proportions AS (
  SELECT
    cc.ablation_run_id,
    cc.cdi_category,
    cc.n::float / rt.total AS p_i
  FROM category_counts cc
  JOIN run_totals rt ON cc.ablation_run_id = rt.ablation_run_id
)
SELECT
  ar.condition,
  ar.repetition,
  ar.final_concept_count,
  -- Shannon diversity: H' = -Σ(pi * ln(pi))
  ROUND((-SUM(p.p_i * LN(p.p_i)))::numeric, 3) AS shannon_H,
  -- Pielou evenness: J = H' / ln(S) where S = number of categories
  ROUND((-SUM(p.p_i * LN(p.p_i)) / LN(COUNT(*)))::numeric, 3) AS pielou_J,
  COUNT(*) AS n_categories
FROM proportions p
JOIN ablation_runs ar ON p.ablation_run_id = ar.id
WHERE ar.status = 'completed'
GROUP BY ar.condition, ar.repetition, ar.final_concept_count
ORDER BY CASE ar.condition
  WHEN 'C_full' THEN 1 WHEN 'C_nostage' THEN 2
  WHEN 'C_noemo' THEN 3 WHEN 'C_nosleep' THEN 4
END, ar.repetition;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 13: NON-PARAMETRIC EFFECT SIZE (CLIFF'S DELTA)
-- ───────────────────────────────────────────────────────────────────────────────
-- Purpose: Robust effect size for small samples (n=5) — preferred over Cohen's d
-- Paper: §17.6 Statistical methodology - reports Cliff's delta with interpretation
-- Note: Cliff's δ = (n_dominant - n_dominated) / (n1 * n2)

WITH full_runs AS (
  SELECT final_concept_count AS x
  FROM ablation_runs WHERE condition = 'C_full' AND status = 'completed'
),
ablation_runs_cte AS (
  SELECT condition, final_concept_count AS y
  FROM ablation_runs WHERE condition != 'C_full' AND status = 'completed'
),
comparisons AS (
  SELECT
    a.condition,
    SUM(CASE WHEN f.x > a.y THEN 1 WHEN f.x < a.y THEN -1 ELSE 0 END) AS dominance_sum,
    COUNT(*) AS n_pairs,
    (SELECT COUNT(*) FROM full_runs) AS n_full,
    COUNT(DISTINCT a.y) AS n_ablation_distinct
  FROM ablation_runs_cte a
  CROSS JOIN full_runs f
  GROUP BY a.condition
)
SELECT
  condition,
  ROUND((dominance_sum::float / n_pairs)::numeric, 3) AS cliffs_delta,
  CASE
    WHEN ABS(dominance_sum::float / n_pairs) < 0.147 THEN 'negligible'
    WHEN ABS(dominance_sum::float / n_pairs) < 0.33 THEN 'small'
    WHEN ABS(dominance_sum::float / n_pairs) < 0.474 THEN 'medium'
    ELSE 'large'
  END AS effect_interpretation,
  n_pairs,
  dominance_sum
FROM comparisons
ORDER BY CASE condition
  WHEN 'C_nostage' THEN 1 WHEN 'C_noemo' THEN 2 WHEN 'C_nosleep' THEN 3
END;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 14: CONCEPT STRENGTH COMPARISON (EMOTION MODULATION EFFECT)
-- ───────────────────────────────────────────────────────────────────────────────
-- Purpose: Compare concept strength distributions across conditions
-- Paper: Tests whether M(e) > 1 produces measurably stronger concepts
-- Expected: C_full/C_nostage ≈ 0.60, C_noemo ≈ 0.50 (M(e)=1.0), C_nosleep varies

SELECT
  ar.condition,
  ROUND(AVG(sc.strength)::numeric, 4) AS mean_strength,
  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sc.strength)::numeric, 4) AS median_strength,
  ROUND(STDDEV_POP(sc.strength)::numeric, 4) AS sd_strength,
  ROUND(MIN(sc.strength)::numeric, 4) AS min_strength,
  ROUND(MAX(sc.strength)::numeric, 4) AS max_strength,
  COUNT(*) AS n_concepts,
  COUNT(DISTINCT ar.id) AS n_runs
FROM semantic_concepts sc
JOIN ablation_runs ar ON sc.ablation_run_id = ar.id
WHERE ar.status = 'completed'
GROUP BY ar.condition
ORDER BY CASE ar.condition
  WHEN 'C_full' THEN 1 WHEN 'C_nostage' THEN 2
  WHEN 'C_noemo' THEN 3 WHEN 'C_nosleep' THEN 4
END;


-- ───────────────────────────────────────────────────────────────────────────────
-- QUERY 15: SLEEP CONSOLIDATION EFFECT (STRENGTH BEFORE/AFTER)
-- ───────────────────────────────────────────────────────────────────────────────
-- Purpose: Measure sleep consolidation boost by comparing strength at consolidation points
-- Paper: Tests Stickgold (2005) memory consolidation hypothesis
-- Consolidation happens at turns 10, 20, 30, 40, 50 (every 10 turns)

SELECT
  ar.condition,
  ROUND(AVG(CASE WHEN am.turn_number IN (9,19,29,39,49) THEN am.vocabulary_size END)::numeric, 1)
    AS mean_vocab_before_sleep,
  ROUND(AVG(CASE WHEN am.turn_number IN (11,21,31,41,51) THEN am.vocabulary_size END)::numeric, 1)
    AS mean_vocab_after_sleep,
  ROUND(AVG(CASE WHEN am.turn_number IN (11,21,31,41,51) THEN am.vocabulary_size END)
    - AVG(CASE WHEN am.turn_number IN (9,19,29,39,49) THEN am.vocabulary_size END))::numeric, 2)
    AS mean_sleep_boost,
  COUNT(DISTINCT ar.id) AS n_runs
FROM ablation_metrics am
JOIN ablation_runs ar ON am.run_id = ar.id
WHERE ar.status = 'completed'
GROUP BY ar.condition
ORDER BY CASE ar.condition
  WHEN 'C_full' THEN 1 WHEN 'C_nostage' THEN 2
  WHEN 'C_noemo' THEN 3 WHEN 'C_nosleep' THEN 4
END;
