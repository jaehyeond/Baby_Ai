# Phase 8: Autonomous Curiosity (자율적 호기심)

**Version**: 1.1
**Created**: 2026-01-23
**Updated**: 2026-01-23
**Status**: ✅ Implementation Complete

---

## Overview

Baby AI가 **스스로 궁금한 것을 발견하고, 탐색하고, 학습**하는 완전 자율 시스템입니다.

### 인간에서의 의미

- 아이가 "이게 뭐야?" 라고 스스로 질문함
- 모르는 것을 발견하면 알아보고 싶어함
- 탐색 → 발견 → 학습의 자발적 순환

---

## 🚨 핵심 설계 원칙: 외부 LLM 사용 금지

### 프로젝트 철학 재확인

> **"Transformer는 '지식'을 주입하지만, 우리는 '학습하는 법'을 가르칩니다"**

| 잘못된 접근 (❌) | 올바른 접근 (✅) |
|-----------------|-----------------|
| LLM에게 "뭐가 궁금해?" 물어보기 | Baby 내부 알고리즘으로 호기심 생성 |
| LLM이 검색 결과 요약 | 검색 결과를 직접 경험으로 저장 |
| LLM이 질문 생성 | 개념 그래프 분석으로 질문 도출 |

---

## 호기심 생성 알고리즘 (LLM 없이)

### 1. 개념 갭 탐지 (Concept Gap Detection)

```sql
-- 연결이 부족한 개념 찾기
-- "color"는 "red", "blue"와 연결되어야 하는데 "blue"가 없다면?

SELECT c1.name AS concept, c1.id,
       COUNT(cr.to_concept_id) AS connection_count,
       AVG(cr.strength) AS avg_strength
FROM concepts c1
LEFT JOIN concept_relations cr ON c1.id = cr.from_concept_id
GROUP BY c1.id, c1.name
HAVING COUNT(cr.to_concept_id) < 3  -- 연결이 3개 미만
   OR AVG(cr.strength) < 0.3        -- 약한 연결만 있음
ORDER BY connection_count ASC, avg_strength ASC
LIMIT 10;
```

**호기심 생성 규칙**:
- 연결 수 < 3 → "이 개념에 대해 더 알고 싶다"
- 평균 강도 < 0.3 → "이 개념을 더 잘 이해하고 싶다"

### 2. 실패 기반 호기심 (Failure-Driven Curiosity)

```sql
-- 실패한 경험에서 모르는 개념 추출
SELECT e.task, e.input, e.outcome,
       array_agg(DISTINCT ec.concept_id) AS related_concepts
FROM experiences e
LEFT JOIN experience_concepts ec ON e.id = ec.experience_id
WHERE e.success = false
  AND e.created_at > now() - interval '7 days'
GROUP BY e.id, e.task, e.input, e.outcome
ORDER BY e.created_at DESC
LIMIT 20;
```

**호기심 생성 규칙**:
- 실패 경험의 입력에서 키워드 추출
- 관련 개념이 없거나 약하면 → 호기심 큐에 추가

### 3. 패턴 기반 호기심 (Pattern-Based Curiosity)

```sql
-- 자주 등장하지만 정의가 불명확한 개념
SELECT c.name, c.id,
       COUNT(ec.experience_id) AS appearance_count,
       c.definition_strength
FROM concepts c
JOIN experience_concepts ec ON c.id = ec.concept_id
GROUP BY c.id, c.name, c.definition_strength
HAVING COUNT(ec.experience_id) > 5  -- 5번 이상 등장
   AND c.definition_strength < 0.5  -- 정의 강도 낮음
ORDER BY appearance_count DESC
LIMIT 10;
```

**호기심 생성 규칙**:
- 많이 등장하는데 잘 모르는 개념 → 우선 탐색 대상

### 4. 유사도 기반 호기심 (Similarity-Based Curiosity)

```sql
-- 비슷한 개념들 사이의 차이점 탐색
SELECT c1.name AS concept_a, c2.name AS concept_b,
       1 - (c1.embedding <-> c2.embedding) AS similarity
FROM concepts c1
JOIN concepts c2 ON c1.id < c2.id
WHERE c1.embedding IS NOT NULL
  AND c2.embedding IS NOT NULL
  AND (1 - (c1.embedding <-> c2.embedding)) > 0.7  -- 매우 유사
  AND NOT EXISTS (  -- 하지만 직접 연결 없음
    SELECT 1 FROM concept_relations cr
    WHERE (cr.from_concept_id = c1.id AND cr.to_concept_id = c2.id)
       OR (cr.from_concept_id = c2.id AND cr.to_concept_id = c1.id)
  )
ORDER BY similarity DESC
LIMIT 10;
```

**호기심 생성 규칙**:
- "A와 B가 비슷한데 어떤 관계지?" → 관계 탐색 호기심

---

## Database Schema

### 1. curiosity_queue (호기심 큐)

```sql
CREATE TABLE curiosity_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 호기심 내용
    query TEXT NOT NULL,                    -- 탐색할 질문/키워드
    query_type TEXT NOT NULL,               -- 질문 유형

    -- 호기심 출처 (LLM이 아닌 내부 알고리즘)
    source TEXT NOT NULL CHECK (source IN (
        'concept_gap',      -- 개념 연결 부족
        'failure',          -- 실패 경험에서 발생
        'pattern',          -- 자주 등장하지만 불명확
        'similarity',       -- 유사 개념 간 관계 탐색
        'temporal',         -- 시간 기반 재탐색
        'emotional'         -- 감정 반응 기반
    )),

    -- 관련 데이터
    source_concept_id UUID REFERENCES concepts(id),
    source_experience_id UUID REFERENCES experiences(id),
    related_concepts UUID[],

    -- 우선순위 (0.0 ~ 1.0, 내부 알고리즘으로 계산)
    priority FLOAT DEFAULT 0.5,
    priority_factors JSONB DEFAULT '{}',    -- 우선순위 계산 요소들

    -- 상태
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending',      -- 대기 중
        'exploring',    -- 탐색 중
        'learned',      -- 학습 완료
        'failed',       -- 탐색 실패
        'deferred'      -- 나중으로 미룸
    )),

    -- 탐색 결과
    exploration_count INT DEFAULT 0,        -- 탐색 시도 횟수
    last_explored_at TIMESTAMPTZ,
    learned_experience_ids UUID[],          -- 학습으로 생성된 경험들

    -- 감정 반응 (탐색 전/후)
    curiosity_intensity FLOAT,              -- 호기심 강도
    satisfaction_after FLOAT,               -- 탐색 후 만족도

    -- 메타데이터
    development_stage INT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 인덱스
CREATE INDEX idx_curiosity_queue_status ON curiosity_queue(status);
CREATE INDEX idx_curiosity_queue_priority ON curiosity_queue(priority DESC);
CREATE INDEX idx_curiosity_queue_source ON curiosity_queue(source);
```

### 2. exploration_logs (탐색 기록)

```sql
CREATE TABLE exploration_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 탐색 대상
    curiosity_id UUID REFERENCES curiosity_queue(id),
    query TEXT NOT NULL,

    -- 탐색 방법
    exploration_method TEXT NOT NULL CHECK (exploration_method IN (
        'web_search',       -- 웹 검색
        'internal_graph',   -- 내부 그래프 탐색
        'memory_recall',    -- 기억 회상
        'pattern_match'     -- 패턴 매칭
    )),

    -- 결과
    raw_results JSONB,                      -- 원본 결과 (검색 결과 등)
    processed_results JSONB,                -- 처리된 결과

    -- 학습 결과
    new_concepts_created UUID[],            -- 생성된 새 개념
    concepts_strengthened UUID[],           -- 강화된 개념
    new_relations_created UUID[],           -- 생성된 새 관계
    experiences_created UUID[],             -- 생성된 새 경험

    -- 평가 (규칙 기반)
    success BOOLEAN,
    relevance_score FLOAT,                  -- 관련성 점수 (키워드 매칭)
    novelty_score FLOAT,                    -- 새로움 점수 (기존 지식과 비교)

    -- 감정 변화
    emotion_before JSONB,
    emotion_after JSONB,

    -- 메타데이터
    duration_ms INT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 3. concepts 테이블 확장

```sql
-- concepts 테이블에 컬럼 추가
ALTER TABLE concepts ADD COLUMN IF NOT EXISTS
    definition_strength FLOAT DEFAULT 0.5;  -- 정의 명확도

ALTER TABLE concepts ADD COLUMN IF NOT EXISTS
    last_explored_at TIMESTAMPTZ;           -- 마지막 탐색 시점

ALTER TABLE concepts ADD COLUMN IF NOT EXISTS
    exploration_count INT DEFAULT 0;        -- 탐색 횟수
```

---

## Edge Functions

### 1. generate-curiosity (호기심 생성)

**트리거**:
- 새 경험 저장 후
- 주기적 (1시간마다)
- 수면 시작 시

```typescript
// POST /functions/v1/generate-curiosity
interface GenerateCuriosityRequest {
  action: 'generate' | 'get_queue' | 'get_stats';
  limit?: number;
  source_filter?: string[];
}

interface GenerateCuriosityResponse {
  success: boolean;
  curiosities_generated: number;
  queue: Array<{
    id: string;
    query: string;
    source: string;
    priority: number;
  }>;
}
```

**알고리즘** (LLM 없이):

```typescript
async function generateCuriosities(supabase: SupabaseClient) {
  const curiosities: CuriosityItem[] = [];

  // 1. 개념 갭 탐지
  const conceptGaps = await findConceptGaps(supabase);
  for (const gap of conceptGaps) {
    curiosities.push({
      query: gap.concept_name,  // 단순히 개념 이름
      query_type: 'concept_definition',
      source: 'concept_gap',
      source_concept_id: gap.id,
      priority: calculateGapPriority(gap),  // 연결 수, 강도 기반
      priority_factors: {
        connection_count: gap.connection_count,
        avg_strength: gap.avg_strength
      }
    });
  }

  // 2. 실패 기반 호기심
  const failures = await findRecentFailures(supabase);
  for (const failure of failures) {
    // 입력에서 키워드 추출 (규칙 기반: 명사, 고유명사)
    const keywords = extractKeywords(failure.input);
    for (const keyword of keywords) {
      curiosities.push({
        query: keyword,
        query_type: 'unknown_term',
        source: 'failure',
        source_experience_id: failure.id,
        priority: 0.7,  // 실패는 높은 우선순위
        priority_factors: {
          failure_count: failure.similar_failure_count
        }
      });
    }
  }

  // 3. 패턴 기반 호기심
  const frequentUnknowns = await findFrequentUnknowns(supabase);
  for (const unknown of frequentUnknowns) {
    curiosities.push({
      query: unknown.name,
      query_type: 'frequent_unknown',
      source: 'pattern',
      source_concept_id: unknown.id,
      priority: calculatePatternPriority(unknown),
      priority_factors: {
        appearance_count: unknown.appearance_count,
        definition_strength: unknown.definition_strength
      }
    });
  }

  // 4. 유사도 기반 호기심
  const similarPairs = await findSimilarWithoutRelation(supabase);
  for (const pair of similarPairs) {
    curiosities.push({
      query: `${pair.concept_a} ${pair.concept_b}`,  // 두 개념 함께
      query_type: 'relation_discovery',
      source: 'similarity',
      related_concepts: [pair.id_a, pair.id_b],
      priority: pair.similarity * 0.8,
      priority_factors: {
        similarity: pair.similarity
      }
    });
  }

  // 중복 제거 및 저장
  const unique = deduplicateCuriosities(curiosities);
  await saveCuriositiesToQueue(supabase, unique);

  return unique;
}

// 키워드 추출 (LLM 없이, 규칙 기반)
function extractKeywords(text: string): string[] {
  // 1. 기본 전처리
  const cleaned = text.toLowerCase().trim();

  // 2. 단어 분리
  const words = cleaned.split(/\s+/);

  // 3. 불용어 제거
  const stopwords = ['the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'how', 'why'];
  const filtered = words.filter(w => !stopwords.includes(w) && w.length > 2);

  // 4. 명사 추정 (간단한 규칙: 대문자 시작, 특정 접미사)
  const nouns = filtered.filter(w =>
    /^[A-Z]/.test(w) ||  // 대문자 시작
    /tion$|ment$|ness$|ity$/.test(w)  // 명사 접미사
  );

  return nouns.length > 0 ? nouns : filtered.slice(0, 3);
}

// 우선순위 계산 (규칙 기반)
function calculateGapPriority(gap: ConceptGap): number {
  let priority = 0.5;

  // 연결이 적을수록 높은 우선순위
  if (gap.connection_count === 0) priority += 0.3;
  else if (gap.connection_count < 2) priority += 0.2;

  // 강도가 약할수록 높은 우선순위
  if (gap.avg_strength < 0.2) priority += 0.2;
  else if (gap.avg_strength < 0.4) priority += 0.1;

  return Math.min(priority, 1.0);
}
```

### 2. autonomous-exploration (자율 탐색)

**트리거**:
- 수면 상태 시작 시
- 호기심 큐에 pending 항목이 있을 때
- 주기적 (30분마다)

```typescript
// POST /functions/v1/autonomous-exploration
interface ExplorationRequest {
  action: 'explore' | 'explore_batch' | 'get_status';
  curiosity_id?: string;
  batch_size?: number;
}

interface ExplorationResponse {
  success: boolean;
  explorations: Array<{
    curiosity_id: string;
    query: string;
    method: string;
    results_count: number;
    concepts_created: number;
    experiences_created: number;
  }>;
}
```

**알고리즘**:

```typescript
async function exploreAutonomously(
  supabase: SupabaseClient,
  curiosityId: string
) {
  // 1. 호기심 가져오기
  const curiosity = await getCuriosity(supabase, curiosityId);
  if (!curiosity) return { success: false, error: 'not_found' };

  // 2. 상태 업데이트
  await updateCuriosityStatus(supabase, curiosityId, 'exploring');

  // 3. 탐색 방법 결정 (규칙 기반)
  const method = selectExplorationMethod(curiosity);

  // 4. 탐색 실행
  let results;
  switch (method) {
    case 'internal_graph':
      results = await exploreInternalGraph(supabase, curiosity);
      break;
    case 'memory_recall':
      results = await recallFromMemory(supabase, curiosity);
      break;
    case 'web_search':
      results = await searchWeb(curiosity.query);
      break;
    case 'pattern_match':
      results = await matchPatterns(supabase, curiosity);
      break;
  }

  // 5. 결과 처리 (LLM 없이)
  const processed = await processResults(supabase, curiosity, results);

  // 6. 학습 적용
  const learned = await applyLearning(supabase, curiosity, processed);

  // 7. 로그 저장
  await saveExplorationLog(supabase, {
    curiosity_id: curiosityId,
    query: curiosity.query,
    exploration_method: method,
    raw_results: results,
    processed_results: processed,
    ...learned
  });

  // 8. 상태 업데이트
  const newStatus = learned.success ? 'learned' : 'failed';
  await updateCuriosityStatus(supabase, curiosityId, newStatus);

  return { success: true, learned };
}

// 탐색 방법 선택 (규칙 기반)
function selectExplorationMethod(curiosity: Curiosity): string {
  // 1. 내부 그래프에 관련 개념이 있으면 내부 탐색 우선
  if (curiosity.related_concepts?.length > 0) {
    return 'internal_graph';
  }

  // 2. 과거 경험에서 유사한 것이 있으면 기억 회상
  if (curiosity.source === 'failure' || curiosity.source === 'pattern') {
    return 'memory_recall';
  }

  // 3. 유사도 기반이면 패턴 매칭
  if (curiosity.source === 'similarity') {
    return 'pattern_match';
  }

  // 4. 그 외는 웹 검색
  return 'web_search';
}

// 결과 처리 (LLM 없이, 규칙 기반)
async function processResults(
  supabase: SupabaseClient,
  curiosity: Curiosity,
  rawResults: any
): Promise<ProcessedResults> {
  const processed: ProcessedResults = {
    keywords: [],
    definitions: [],
    relations: []
  };

  if (!rawResults || !rawResults.items) {
    return processed;
  }

  for (const item of rawResults.items) {
    // 1. 키워드 추출 (규칙 기반)
    const keywords = extractKeywords(item.title + ' ' + item.snippet);
    processed.keywords.push(...keywords);

    // 2. 정의 추출 (패턴 매칭)
    const definitions = extractDefinitions(item.snippet, curiosity.query);
    processed.definitions.push(...definitions);

    // 3. 관계 추출 (패턴 매칭)
    const relations = extractRelations(item.snippet, curiosity.query);
    processed.relations.push(...relations);
  }

  // 중복 제거
  processed.keywords = [...new Set(processed.keywords)];

  return processed;
}

// 정의 추출 (규칙 기반 패턴 매칭)
function extractDefinitions(text: string, query: string): Definition[] {
  const definitions: Definition[] = [];
  const patterns = [
    // "X is Y" 패턴
    new RegExp(`${query}\\s+is\\s+([^.]+)\\.`, 'gi'),
    // "X means Y" 패턴
    new RegExp(`${query}\\s+means\\s+([^.]+)\\.`, 'gi'),
    // "X, which is Y" 패턴
    new RegExp(`${query},\\s+which\\s+is\\s+([^.]+)\\.`, 'gi'),
    // "X refers to Y" 패턴
    new RegExp(`${query}\\s+refers\\s+to\\s+([^.]+)\\.`, 'gi'),
  ];

  for (const pattern of patterns) {
    const matches = text.matchAll(pattern);
    for (const match of matches) {
      definitions.push({
        term: query,
        definition: match[1].trim(),
        confidence: 0.7  // 패턴 매칭 기반 신뢰도
      });
    }
  }

  return definitions;
}

// 관계 추출 (규칙 기반 패턴 매칭)
function extractRelations(text: string, query: string): Relation[] {
  const relations: Relation[] = [];
  const patterns = [
    // "X is a type of Y"
    { pattern: new RegExp(`${query}\\s+is\\s+a\\s+type\\s+of\\s+(\\w+)`, 'gi'), type: 'is_type_of' },
    // "X is part of Y"
    { pattern: new RegExp(`${query}\\s+is\\s+part\\s+of\\s+(\\w+)`, 'gi'), type: 'is_part_of' },
    // "X contains Y"
    { pattern: new RegExp(`${query}\\s+contains\\s+(\\w+)`, 'gi'), type: 'contains' },
    // "X and Y"
    { pattern: new RegExp(`${query}\\s+and\\s+(\\w+)`, 'gi'), type: 'related_to' },
  ];

  for (const { pattern, type } of patterns) {
    const matches = text.matchAll(pattern);
    for (const match of matches) {
      relations.push({
        from: query,
        to: match[1],
        type,
        confidence: 0.6
      });
    }
  }

  return relations;
}

// 학습 적용 (DB에 저장)
async function applyLearning(
  supabase: SupabaseClient,
  curiosity: Curiosity,
  processed: ProcessedResults
): Promise<LearningResult> {
  const result: LearningResult = {
    success: false,
    new_concepts_created: [],
    concepts_strengthened: [],
    new_relations_created: [],
    experiences_created: []
  };

  // 1. 새 개념 생성
  for (const keyword of processed.keywords) {
    const existing = await findConceptByName(supabase, keyword);
    if (!existing) {
      const newConcept = await createConcept(supabase, {
        name: keyword,
        category: 'learned',
        source: 'autonomous_exploration',
        definition_strength: 0.3  // 초기 낮은 강도
      });
      result.new_concepts_created.push(newConcept.id);
    }
  }

  // 2. 정의 적용 (개념 강화)
  for (const def of processed.definitions) {
    const concept = await findConceptByName(supabase, def.term);
    if (concept) {
      await strengthenConcept(supabase, concept.id, def.confidence * 0.2);
      result.concepts_strengthened.push(concept.id);
    }
  }

  // 3. 관계 생성
  for (const rel of processed.relations) {
    const fromConcept = await findOrCreateConcept(supabase, rel.from);
    const toConcept = await findOrCreateConcept(supabase, rel.to);

    await createConceptRelation(supabase, {
      from_concept_id: fromConcept.id,
      to_concept_id: toConcept.id,
      relation_type: rel.type,
      strength: rel.confidence
    });
    result.new_relations_created.push({ from: fromConcept.id, to: toConcept.id });
  }

  // 4. 새 경험 생성 (탐색 자체가 경험)
  const experience = await createExperience(supabase, {
    task: 'autonomous_exploration',
    input: curiosity.query,
    output: JSON.stringify(processed),
    success: processed.definitions.length > 0 || processed.relations.length > 0,
    task_type: 'exploration',
    autonomous: true
  });
  result.experiences_created.push(experience.id);

  result.success = result.new_concepts_created.length > 0 ||
                   result.concepts_strengthened.length > 0 ||
                   result.new_relations_created.length > 0;

  return result;
}
```

### 3. 웹 검색 통합

```typescript
// 검색 API 선택 (비용 효율성)
const SEARCH_PROVIDERS = {
  // 1순위: Brave Search API (무료 티어 있음)
  brave: {
    url: 'https://api.search.brave.com/res/v1/web/search',
    freeQuota: 2000,  // 월 2000회 무료
    costPer1000: 0,
  },
  // 2순위: SerpAPI (유료)
  serp: {
    url: 'https://serpapi.com/search',
    freeQuota: 100,
    costPer1000: 50,
  },
  // 3순위: Google Custom Search (유료)
  google: {
    url: 'https://www.googleapis.com/customsearch/v1',
    freeQuota: 100,
    costPer1000: 5,
  }
};

async function searchWeb(query: string): Promise<SearchResults> {
  // Brave Search API 사용 (무료)
  const response = await fetch(
    `https://api.search.brave.com/res/v1/web/search?q=${encodeURIComponent(query)}&count=5`,
    {
      headers: {
        'X-Subscription-Token': Deno.env.get('BRAVE_SEARCH_API_KEY') || '',
        'Accept': 'application/json'
      }
    }
  );

  if (!response.ok) {
    throw new Error(`Search failed: ${response.status}`);
  }

  const data = await response.json();

  return {
    items: data.web?.results?.map((r: any) => ({
      title: r.title,
      url: r.url,
      snippet: r.description
    })) || []
  };
}
```

---

## 자율 탐색 루프

### 전체 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS CURIOSITY LOOP                 │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │ 호기심   │ → │ 탐색     │ → │ 결과     │ → │ 학습   │ │
│  │ 생성     │    │ 실행     │    │ 처리     │    │ 적용   │ │
│  └──────────┘    └──────────┘    └──────────┘    └────────┘ │
│       ↑                                              │       │
│       │              ┌─────────────┐                 │       │
│       └──────────────│ 새로운     │←────────────────┘       │
│                      │ 호기심 발생│                          │
│                      └─────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

### 트리거 조건

| 트리거 | 조건 | 액션 |
|--------|------|------|
| **수면 시작** | idle 30분 후 | generate-curiosity → autonomous-exploration |
| **새 경험** | experiences INSERT | generate-curiosity (1개만) |
| **주기적** | 매 1시간 | generate-curiosity (배치) |
| **호기심 축적** | curiosity_queue > 10개 | autonomous-exploration (배치) |

### 감정 연동

```typescript
// 호기심이 만족되면 기쁨 증가
async function updateEmotionAfterLearning(
  supabase: SupabaseClient,
  success: boolean,
  novelty: number
) {
  const emotionChange = {
    curiosity: success ? -0.1 : 0.05,  // 만족되면 감소, 실패하면 증가
    joy: success ? 0.15 * novelty : 0, // 새로운 것 배우면 기쁨
    frustration: success ? -0.1 : 0.1  // 실패하면 좌절
  };

  await updateBabyEmotion(supabase, emotionChange);
}
```

---

## Frontend Component: CuriosityCard

### 3개 탭

1. **Queue 탭**
   - 현재 호기심 목록
   - 우선순위 시각화
   - 출처별 분류

2. **Exploring 탭**
   - 실시간 탐색 상태
   - 현재 탐색 중인 질문
   - 진행률

3. **Learned 탭**
   - 최근 학습 결과
   - 생성된 개념/관계
   - 만족도 통계

---

## 비용 분석

| 구성요소 | 비용 | 비고 |
|----------|------|------|
| **DB 연산** | $0 | Supabase 무료 티어 |
| **Edge Functions** | $0 | 월 500K 호출 무료 |
| **Brave Search** | $0 | 월 2000회 무료 |
| **벡터 연산** | $0 | pgvector 내장 |
| **총 비용** | **$0/월** | 소규모 운영 시 |

---

## Success Criteria

- [x] 2개 DB 테이블 생성 (curiosity_queue, exploration_logs) ✅
- [x] concepts 테이블 확장 (definition_strength, exploration_count) ✅
- [x] generate-curiosity Edge Function 배포 ✅
- [x] autonomous-exploration Edge Function 배포 ✅
- [x] Brave Search API 연동 (설정 시 자동 사용) ✅
- [x] CuriosityCard 컴포넌트 구현 ✅
- [x] 감정 시스템 연동 ✅
- [x] 수면 시 자동 탐색 연동 ✅

---

## 구현 완료 내역

1. ✅ **DB 테이블 생성**
   - `curiosity_queue`: 호기심 큐 (query, source, priority, status 등)
   - `exploration_logs`: 탐색 기록 (method, results, learning 등)

2. ✅ **semantic_concepts 확장**
   - `definition_strength`: 정의 명확도
   - `last_explored_at`: 마지막 탐색 시점
   - `exploration_count`: 탐색 횟수
   - `examples`: 학습된 예시들
   - `definition_text`: 탐색으로 학습된 정의

3. ✅ **Edge Functions**
   - `generate-curiosity`: 4가지 방법으로 호기심 생성 (concept_gap, failure, pattern, similarity)
   - `autonomous-exploration`: 4가지 탐색 방법 (web_search, internal_graph, memory_recall, pattern_match)

4. ✅ **Frontend**
   - `CuriosityCard`: 3개 탭 (대기열/탐색 중/학습 완료)
   - `/api/curiosity`: API route
   - 메인 대시보드 '호기심' 탭 추가

5. ✅ **감정 연동**
   - 학습 성공 시: curiosity -0.1, joy +0.15
   - 학습 실패 시: curiosity +0.05, frustration +0.1

6. ✅ **수면 시 자동 탐색 연동**
   - `useIdleSleep` 훅 확장
   - 수면 시 3단계 실행:
     1. 기억 통합 (memory consolidation)
     2. 호기심 생성 (최대 5개)
     3. 자동 탐색 (최대 3개, 내부 방법 우선)

7. ✅ **Brave Search API 연동**
   - Base 플랜: $3/1000 requests, **월 2천만 requests**
   - Supabase Edge Function Secrets에 `BRAVE_SEARCH_API_KEY` 저장
   - autonomous-exploration에서 `web_search` method로 사용

---

## References

1. Berlyne, D. E. (1960). *Conflict, Arousal, and Curiosity*. McGraw-Hill.
2. Loewenstein, G. (1994). *The Psychology of Curiosity*. Psychological Bulletin.
3. Kidd, C., & Hayden, B. Y. (2015). *The Psychology and Neuroscience of Curiosity*. Neuron.

---

## Document History

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-23 | 초안 작성, LLM 없이 자율 호기심 시스템 설계 |
| 1.1 | 2026-01-23 | 구현 완료 - DB, Edge Functions, Frontend |
| 1.2 | 2026-01-23 | 수면 시 자동 탐색 연동 완료, Brave Search API 연동 |

---

## Idle Sleep 연동

### 작동 원리

대시보드에서 **30분간 사용자 활동이 없으면** 자동으로 sleep cycle이 실행됩니다.

**감지하는 이벤트**: `mousedown`, `mousemove`, `keydown`, `touchstart`, `scroll`

**상세 내용**: [PHASE_6_MEMORY_CONSOLIDATION.md#idle-감지-기준-상세](./PHASE_6_MEMORY_CONSOLIDATION.md#idle-감지-기준-상세) 참조

### Sleep Cycle 3단계

```
┌─────────────────────────────────────────────────────────┐
│  30분 Idle 감지 (대시보드 탭 열려있어야 함)              │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 1: Memory Consolidation                          │
│  - POST /api/memory/consolidate                         │
│  - 감정 강화, 기억 감쇠, 패턴 승격, 의미 연결            │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 2: Generate Curiosities (최대 5개)               │
│  - POST /api/curiosity { action: 'generate' }           │
│  - methods: concept_gap, failure, pattern, similarity   │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 3: Autonomous Exploration (최대 3개)             │
│  - POST /api/curiosity { action: 'explore_batch' }      │
│  - methods: internal_graph, memory_recall, pattern_match│
│  - (수면 중에는 내부 방법 우선, web_search는 제외)       │
└─────────────────────────────────────────────────────────┘
```

### SleepStats 반환 값

```typescript
interface SleepStats {
  // Phase 1: Memory
  experiences_processed: number
  memories_strengthened: number
  memories_decayed: number
  patterns_promoted: number
  concepts_consolidated: number
  semantic_links_created: number

  // Phase 2 & 3: Curiosity
  curiosities_generated?: number    // 생성된 호기심 수
  explorations_completed?: number   // 탐색 완료 수
  new_knowledge_acquired?: number   // 새로 학습한 지식 (개념+관계)
}
```
