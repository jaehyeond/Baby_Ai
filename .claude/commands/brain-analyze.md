# Brain Analyze

Baby AI의 뇌(지식 그래프)를 분석합니다.

## 분석 항목

### 1. 개념 분포 분석
```sql
-- 카테고리별 개념 분포
SELECT category, COUNT(*) as count,
       ROUND(AVG(strength)::numeric, 2) as avg_strength,
       ROUND(AVG(usage_count)::numeric, 1) as avg_usage
FROM semantic_concepts
GROUP BY category
ORDER BY count DESC
LIMIT 20;
```

### 2. 핵심 개념 (뉴런) 분석
```sql
-- 가장 활성화된 개념
SELECT name, category, strength, usage_count,
       (SELECT COUNT(*) FROM concept_relations
        WHERE from_concept_id = sc.id OR to_concept_id = sc.id) as connections
FROM semantic_concepts sc
ORDER BY usage_count DESC
LIMIT 10;
```

### 3. 시냅스 강도 분석
```sql
-- 관계 유형별 통계
SELECT relation_type, COUNT(*) as count,
       ROUND(AVG(strength)::numeric, 3) as avg_strength
FROM concept_relations
GROUP BY relation_type
ORDER BY count DESC;

-- 가장 강한 연결
SELECT
  (SELECT name FROM semantic_concepts WHERE id = from_concept_id) as from_name,
  relation_type,
  (SELECT name FROM semantic_concepts WHERE id = to_concept_id) as to_name,
  strength
FROM concept_relations
ORDER BY strength DESC
LIMIT 10;
```

### 4. 클러스터 분석 (예비)
```sql
-- 같은 카테고리 내 관계
SELECT sc1.category,
       COUNT(*) as intra_cluster_relations
FROM concept_relations cr
JOIN semantic_concepts sc1 ON cr.from_concept_id = sc1.id
JOIN semantic_concepts sc2 ON cr.to_concept_id = sc2.id
WHERE sc1.category = sc2.category
GROUP BY sc1.category
ORDER BY intra_cluster_relations DESC;
```

## 시각화 연동

결과를 `/brain` 페이지에 반영하려면:
1. `useBrainData.ts` 훅이 Supabase에서 데이터 조회
2. `BrainVisualization.tsx`에서 3D 렌더링
3. 개념 = 뉴런(Sphere), 관계 = 시냅스(Line)

## 사용 시나리오

- **디버깅**: 왜 특정 개념이 기억 안 되는지
- **최적화**: 약한 연결 정리
- **모니터링**: 지식 성장 추적
