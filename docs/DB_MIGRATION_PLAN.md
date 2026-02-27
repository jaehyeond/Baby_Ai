# DB Migration Plan: Supabase → Neo4j + Redis

**작성일**: 2026-02-24
**상태**: 설계 완료, 구현 미착수
**결정**: Redis (Upstash Free) + Neo4j (AuraDB Free)

---

## 1. 왜 Neo4j인가

### 최종 아키텍처 결정

| 구성요소 | 현재 (Supabase) | 변경 후 |
|----------|-----------------|---------|
| 관계형 DB | PostgreSQL (Supabase) | **Neo4j AuraDB** (그래프 DB) |
| 벡터 검색 | pgvector HNSW | **Neo4j Vector Index** (네이티브 HNSW) |
| 실시간 구독 | Supabase Realtime (16 channels) | **Redis Pub/Sub + SSE** |
| 서버리스 함수 | Supabase Edge Functions (13개, Deno) | **FastAPI** (Python) or **Next.js API Routes** |
| 캐시 | 없음 | **Redis** (단기 기억, 세션 캐시) |

### Neo4j 선택 이유

1. **그래프 네이티브**: 488개 개념 + 616개 관계 + 9개 뇌 영역이 본질적으로 그래프
2. **Spreading Activation**: 2-hop BFS 그래프 순회가 Cypher 한 줄
3. **벡터 인덱스 내장**: 별도 벡터 DB 없이 그래프+벡터 통합 쿼리
4. **장기적 스케일**: SurrealDB → Neo4j 이중 마이그레이션 방지
5. **AI 생태계**: Graphiti, neo4j-graphrag, MCP Server 등 풍부

### SurrealDB 대신 Neo4j를 택한 결정적 이유

> "나중에가서 SurrealDB에서 Neo4j로 옮기는건 2중 삽질이야"
> "배포 급하지 않으니 금액 걱정 없고, 장기적으로 맞는 걸 선택"

---

## 2. Neo4j 벡터 인덱스: 재검증 결과

### 핵심 질문: "Neo4j 벡터 인덱스만으로 충분한가?"

**결론: 우리 스케일(500~50K)에서는 YES. 일반론으로는 NO.**

### Neo4j Vector Index 스펙 (2026.01)

| 항목 | 상세 |
|------|------|
| 알고리즘 | HNSW (Apache Lucene 기반) |
| 최대 차원 | 4,096 |
| 유사도 함수 | Cosine, Euclidean (Dot Product 없음) |
| 양자화 | 기본 scalar만 (Binary/PQ 없음) |
| 필터링 | Pre-filter (인덱스 생성 시 선언) + Post-filter |
| SEARCH 절 | 2026.01 추가 (구 프로시저 API 대체) |
| 멀티 레이블 인덱스 | 2026.01 지원 |
| GPU 가속 | 없음 |
| 자동 샤딩 | 없음 (Enterprise Fabric 필요) |

### 전문 벡터 DB 대비 열위인 점

| 기능 | Neo4j | Qdrant | Milvus |
|------|-------|--------|--------|
| 최대 차원 | 4,096 | **65,536** | 32,768 |
| 유사도 | 2종 | **4종** (+ Dot Product) | 4종 |
| 양자화 | scalar만 | **Binary(32x절약), PQ, 1.5-bit** | SQ8, PQ, IVF_PQ |
| 희소 벡터 | 없음 | **있음** | 있음 |
| GPU 가속 | 없음 | HNSW GPU | **GPU_CAGRA** |
| QPS (1M) | ~200-400 | **~1,500** | ~1,200 |

### 스케일별 성능 비교 (768-dim, cosine, 단일 쓰레드)

| 벡터 수 | Neo4j 지연 | Qdrant 지연 | 인덱스 메모리 |
|---------|-----------|------------|-------------|
| **500 (현재)** | <5ms | <2ms | ~1.7 MB |
| **5,000** | ~5-8ms | ~3ms | ~17 MB |
| **50,000** | ~20-30ms | ~8ms | ~170 MB |
| 100,000 | ~30-50ms | ~8-10ms | ~340 MB |
| 1,000,000 | ~50-100ms | ~10-15ms | ~3.4 GB |
| 10,000,000 | ~200-500ms | ~20-30ms | ~33.5 GB |

### 우리에게 충분한 이유

1. **500~50K 스케일**: 어떤 VDB든 <30ms — 차이 체감 불가
2. **200ms 지연 예산**: 50K에서도 170ms 여유
3. **그래프+벡터 통합 쿼리**가 킬러 피처:

```cypher
-- Neo4j: 벡터 유사도 검색 + 그래프 순회를 한 번에
MATCH (c:Concept)
SEARCH c IN (VECTOR INDEX `concept-embeddings` FOR $queryVector LIMIT 10)
SCORE AS similarity
MATCH (c)-[r:RELATES_TO]-(related:Concept)
WHERE similarity > 0.7
RETURN c.name, related.name, type(r), similarity
ORDER BY similarity DESC
```

별도 VDB면: VDB 쿼리 → ID 추출 → Neo4j 그래프 쿼리 → 앱 조인 (2배 지연)

### 확장 로드맵 (나중에 벡터 DB 분리 시점)

```
현재~50K:    Neo4j 단독 (graph + vector) ← 지금 여기
   ↓ 50만 돌파 시
50K~500K:   Neo4j(graph) + Qdrant(vector) 분리
   ↓ 500만 돌파 시
500K+:      Neo4j(graph) + Milvus(GPU vector)
```

---

## 3. 현재 Supabase 의존성 감사

### 3-1. Edge Functions (13개)

| Function | Version | 대체 전략 |
|----------|---------|-----------|
| `conversation-process` | v30 | **FastAPI** (가장 복잡, 800줄+ Deno → Python) |
| `vision-process` | v4 | FastAPI (Gemini Vision 호출) |
| `world-understanding` | v2 | FastAPI |
| `audio-transcribe` | v2 | FastAPI (Gemini STT) |
| `speech-synthesize` | v2 | FastAPI (Google TTS) |
| `memory-consolidation` | v6 | FastAPI (수면 기억 통합, Cypher 배치) |
| `generate-curiosity` | v4 | FastAPI |
| `autonomous-exploration` | v5 | FastAPI |
| `self-evaluation` | v2 | FastAPI |
| `autonomous-goals` | v2 | FastAPI |
| `textual-backpropagation` | v1 | FastAPI |
| `imagination-engine` | v1 | FastAPI |
| `test-tts` | v2 | 삭제 (테스트용) |

**대체 전략**: 13개 Deno Edge Functions → **Python FastAPI 서버 1개**로 통합
- Python이 이미 `neural/baby/` 모듈에 있으므로 재활용 극대화
- `db.py` 800줄 BrainDatabase 클래스를 `neo4j_db.py`로 변환

### 3-2. Database 테이블 (18개 핵심)

| 테이블 | 레코드 | Neo4j 노드/관계 |
|--------|--------|-----------------|
| `semantic_concepts` | 488 | `:Concept` 노드 |
| `concept_relations` | 616 | `(:Concept)-[:RELATES_TO]->(:Concept)` |
| `brain_regions` | 9 | `:BrainRegion` 노드 |
| `concept_brain_mapping` | 452 | `(:Concept)-[:MAPPED_TO]->(:BrainRegion)` |
| `experiences` | 965 | `:Experience` 노드 |
| `experience_concepts` | N/A | `(:Experience)-[:INVOLVES]->(:Concept)` |
| `neuron_activations` | 0+ | `:Activation` 노드 (TTL 자동 삭제) |
| `emotion_logs` | 211+ | `:EmotionLog` 노드 |
| `baby_state` | 1 | `:BabyState` 싱글톤 노드 |
| `predictions` | 8+ | `:Prediction` 노드 |
| `imagination_sessions` | 9 | `:Imagination` 노드 |
| `causal_models` | 3 | `(:Concept)-[:CAUSES]->(:Concept)` |
| `procedural_patterns` | 102 | `:Procedure` 노드 |
| `memory_consolidation_logs` | 553 | `:SleepLog` 노드 |
| `visual_experiences` | 13 | `:VisualExperience` 노드 |
| `pending_questions` | 8 | `:PendingQuestion` 노드 |
| `curiosity_queue` | 9 | `:CuriosityLog` 노드 |
| `autonomous_goals` | 24 | `:AutonomousGoal` 노드 |
| `ablation_runs` | 20 | `:AblationRun` 노드 (ICDL 논문용) |

### 3-3. RPC Functions (4개)

| RPC | 용도 | Neo4j 대체 |
|-----|------|-----------|
| `reinforce_memory` | 경험 강도 증가 | Cypher `SET exp.strength = exp.strength + 1` |
| `decay_all_connections` | 시냅스 약화 | Cypher 배치 `SET r.strength = r.strength * decay` |
| `get_brain_activation_summary` | 뇌 활성화 요약 | Cypher 집계 쿼리 |
| `increment_experiment_count` | 실험 카운트 | Cypher `SET exp.count = exp.count + 1` |

### 3-4. Realtime Channels (16개)

| Channel | 파일 | 구독 테이블 | 중요도 |
|---------|------|------------|--------|
| `brain-activity` | useNeuronActivations.ts | neuron_activations | **HIGH** (뇌 시각화) |
| `pending_questions_inserts` | usePendingQuestions.ts | pending_questions | **HIGH** (질문 알림) |
| `world-model-changes` | useWorldModel.ts | causal_models | MEDIUM |
| `predictions-recent` | useWorldModel.ts | predictions | MEDIUM |
| `imagination-active` | useWorldModel.ts | imagination_sessions | MEDIUM |
| `visual_experiences` | sense/page.tsx | visual_experiences | MEDIUM |
| `emotional_influence` | EmotionalInfluenceCard | baby_state | LOW (폴링 가능) |
| `physical_objects_changes` | PhysicalWorldCard | physical_objects | LOW |
| `tracking_events_changes` | PhysicalWorldCard | object_tracking_events | LOW |
| `autonomous_goals_changes` | AutonomousGoalsCard | autonomous_goals | LOW |
| `autonomy_metrics_changes` | AutonomousGoalsCard | autonomy_metrics | LOW |
| `metacognition_changes` | MetacognitionCard | self_evaluation_logs | LOW |
| `curiosity_changes` | CuriosityCard | curiosity_queue | LOW |
| `memory_consolidation_changes` | MemoryConsolidationCard | memory_consolidation_logs | LOW |
| `procedural_memory_changes` | MemoryConsolidationCard | procedural_memory | LOW |
| `feedback_changes` | TextualBackpropCard | response_feedback | LOW |

**대체 전략**: HIGH → Redis Pub/Sub + SSE, MEDIUM → SSE, LOW → 폴링 (5-10초)

### 3-5. Frontend Supabase 의존성 (파일별)

| 파일 | 의존 유형 | 변경 필요 |
|------|----------|-----------|
| `src/lib/supabase.ts` | 클라이언트 생성, Realtime 헬퍼 | **삭제** → Neo4j client + Redis SSE |
| `src/lib/database.types.ts` | 4500줄 타입 정의 | **삭제** → TypeScript 인터페이스 수동 |
| 16개 hooks | `.from()` 쿼리 + `.channel()` 구독 | **전면 재작성** |
| 12개 API routes | Edge Function fetch 호출 | **FastAPI 엔드포인트로 변경** |
| 10+ components | `(supabase as any).from()` 직접 호출 | **API route 경유로 변경** |

---

## 4. Neo4j 그래프 스키마 설계

### 4-1. 노드 (Labels)

```cypher
-- Core Brain Nodes
(:Concept {
  id: string,          -- UUID
  name: string,
  category: string,
  description: string,
  strength: float,
  activation_count: int,
  embedding: [float],  -- 768-dim vector
  created_at: datetime,
  updated_at: datetime
})

(:BrainRegion {
  id: string,
  name: string,        -- 'amygdala', 'hippocampus', etc.
  display_name: string,
  color: string,
  theta_min: float, theta_max: float,
  phi_min: float, phi_max: float,
  radius: float,
  development_stage_min: int,
  is_internal: boolean
})

(:Experience {
  id: string,
  task: string,
  output: string,
  emotion: string,
  salience: float,
  embedding: [float],  -- 768-dim
  created_at: datetime
})

-- State & Logs
(:BabyState {
  id: string,
  development_stage: int,
  total_experience: int,
  curiosity: float,
  joy: float,
  fear: float,
  surprise: float,
  frustration: float,
  updated_at: datetime
})

(:EmotionLog {
  id: string,
  curiosity: float, joy: float, fear: float,
  surprise: float, frustration: float,
  trigger: string,
  created_at: datetime
})

(:Prediction {
  id: string,
  scenario: string,
  prediction: string,
  actual_outcome: string,
  correct: boolean,
  confidence: float,
  created_at: datetime
})

(:Imagination {
  id: string,
  topic: string,
  type: string,         -- 'what_if', 'prediction', 'creative'
  thoughts: [string],   -- JSON array
  connections_discovered: [string],
  created_at: datetime
})

(:Procedure {
  id: string,
  trigger: string,
  action: string,
  success_rate: float,
  execution_count: int,
  created_at: datetime
})

(:SleepLog {
  id: string,
  memories_consolidated: int,
  patterns_found: int,
  pruned_connections: int,
  duration_ms: int,
  created_at: datetime
})

(:PendingQuestion {
  id: string,
  question: string,
  domain: string,
  priority: float,
  status: string,       -- 'pending', 'answered', 'expired'
  answer: string,
  created_at: datetime
})

(:AutonomousGoal {
  id: string,
  goal: string,
  motivation: string,
  status: string,
  progress: float,
  created_at: datetime
})

(:VisualExperience {
  id: string,
  description: string,
  objects_detected: [string],
  embedding: [float],
  image_url: string,
  created_at: datetime
})

(:CuriosityLog {
  id: string,
  question: string,
  domain: string,
  explored: boolean,
  created_at: datetime
})

(:AblationRun {
  id: string,
  condition: string,    -- 'C_full', 'C_noemo', 'C_nosleep', 'C_nostage'
  rep: int,
  metrics: string,      -- JSON
  created_at: datetime
})

-- Transient (TTL)
(:Activation {
  id: string,
  trigger_type: string, -- 'conversation', 'vision', 'memory', 'emotion'
  intensity: float,
  created_at: datetime  -- TTL: 자동 삭제 (10초 후)
})
```

### 4-2. 관계 (Relationships)

```cypher
-- 개념 간 관계 (시냅스)
(:Concept)-[:RELATES_TO {
  type: string,         -- 'is_a', 'has_property', 'part_of', 'causes', etc.
  strength: float,
  evidence: int,
  created_at: datetime
}]->(:Concept)

-- 인과관계 (별도 강조)
(:Concept)-[:CAUSES {
  strength: float,
  evidence: int
}]->(:Concept)

-- 개념 → 뇌 영역 매핑
(:Concept)-[:MAPPED_TO {
  activation_level: float
}]->(:BrainRegion)

-- 경험 → 개념 연결
(:Experience)-[:INVOLVES {
  relevance: float
}]->(:Concept)

-- 활성화 이벤트
(:Activation)-[:ACTIVATES]->(:Concept)
(:Activation)-[:IN_REGION]->(:BrainRegion)

-- 시각 경험 → 개념
(:VisualExperience)-[:PERCEIVED]->(:Concept)

-- 목표 → 개념
(:AutonomousGoal)-[:TARGETS]->(:Concept)

-- 호기심 → 개념
(:CuriosityLog)-[:ABOUT]->(:Concept)
```

### 4-3. 벡터 인덱스

```cypher
-- 개념 임베딩 벡터 인덱스
CREATE VECTOR INDEX `concept-embeddings` IF NOT EXISTS
FOR (c:Concept) ON c.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
}

-- 경험 임베딩 벡터 인덱스
CREATE VECTOR INDEX `experience-embeddings` IF NOT EXISTS
FOR (e:Experience) ON e.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
}

-- 시각 경험 임베딩 벡터 인덱스
CREATE VECTOR INDEX `visual-embeddings` IF NOT EXISTS
FOR (v:VisualExperience) ON v.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
}
```

### 4-4. 일반 인덱스 (성능)

```cypher
-- Unique constraints
CREATE CONSTRAINT concept_name_unique IF NOT EXISTS
FOR (c:Concept) REQUIRE c.name IS UNIQUE

CREATE CONSTRAINT brain_region_name_unique IF NOT EXISTS
FOR (br:BrainRegion) REQUIRE br.name IS UNIQUE

-- Lookup indexes
CREATE INDEX concept_category IF NOT EXISTS FOR (c:Concept) ON c.category
CREATE INDEX experience_created IF NOT EXISTS FOR (e:Experience) ON e.created_at
CREATE INDEX activation_created IF NOT EXISTS FOR (a:Activation) ON a.created_at
CREATE INDEX pending_question_status IF NOT EXISTS FOR (pq:PendingQuestion) ON pq.status
CREATE INDEX emotion_log_created IF NOT EXISTS FOR (el:EmotionLog) ON el.created_at
```

---

## 5. 핵심 쿼리 매핑 (Supabase SQL → Neo4j Cypher)

### 5-1. Memory Recall Pipeline (conversation-process v30 핵심)

```sql
-- 현재 (Supabase)
SELECT * FROM semantic_concepts
WHERE category = ANY($categories)
ORDER BY strength DESC LIMIT 10;

SELECT * FROM experiences
WHERE task ILIKE '%keyword%'
ORDER BY created_at DESC LIMIT 5;
```

```cypher
-- Neo4j: 벡터 유사도 + 그래프 순회 통합
MATCH (c:Concept)
SEARCH c IN (VECTOR INDEX `concept-embeddings` FOR $queryEmbedding LIMIT 20)
SCORE AS similarity
WHERE similarity > 0.6
OPTIONAL MATCH (c)-[r:RELATES_TO]-(related:Concept)
OPTIONAL MATCH (c)<-[:INVOLVES]-(exp:Experience)
RETURN c.name, c.description, c.category, similarity,
       collect(DISTINCT {name: related.name, type: type(r)}) AS relations,
       collect(DISTINCT {task: exp.task, emotion: exp.emotion})[..3] AS experiences
ORDER BY similarity DESC
LIMIT 10
```

### 5-2. Spreading Activation (현재 conversation-process 내 2-hop BFS)

```sql
-- 현재: 2단계 수동 조인
SELECT cr.*, sc.name FROM concept_relations cr
JOIN semantic_concepts sc ON sc.id = cr.target_concept_id
WHERE cr.source_concept_id = ANY($ids);
```

```cypher
-- Neo4j: 가변 길이 경로 (1-2 홉)
MATCH path = (seed:Concept)-[:RELATES_TO*1..2]-(activated:Concept)
WHERE seed.id IN $seedIds
WITH activated,
     reduce(s = 1.0, r IN relationships(path) | s * r.strength) AS propagated_strength
WHERE propagated_strength > 0.3
RETURN DISTINCT activated.name, activated.id, propagated_strength
ORDER BY propagated_strength DESC
LIMIT 20
```

### 5-3. Sleep Consolidation (Hebbian Strengthening)

```sql
-- 현재: RPC function
SELECT reinforce_memory(exp_id);
SELECT decay_all_connections(0.95);
```

```cypher
-- Neo4j: 배치 Hebbian 강화
MATCH (e:Experience)-[:INVOLVES]->(c:Concept)
WHERE e.salience > 0.7 AND e.created_at > datetime() - duration('P1D')
MATCH (c)-[r:RELATES_TO]-(neighbor:Concept)
SET r.strength = r.strength * 1.1  -- Hebbian: 동시 활성 → 강화

-- 전체 시냅스 약화 (decay)
MATCH ()-[r:RELATES_TO]-()
SET r.strength = r.strength * $decayRate
```

### 5-4. 뇌 활성화 요약 (RPC: get_brain_activation_summary)

```cypher
MATCH (br:BrainRegion)<-[:MAPPED_TO]-(c:Concept)
OPTIONAL MATCH (a:Activation)-[:IN_REGION]->(br)
WHERE a.created_at > datetime() - duration('PT10S')
RETURN br.name, br.display_name, br.color,
       count(DISTINCT c) AS concept_count,
       count(DISTINCT a) AS recent_activations,
       avg(a.intensity) AS avg_intensity
ORDER BY recent_activations DESC
```

### 5-5. 개념 자동 영역 매핑 (현재: PostgreSQL Trigger)

```cypher
-- Neo4j: 새 개념 생성 시 Cypher에서 직접 매핑
CREATE (c:Concept {name: $name, category: $category, ...})
WITH c
MATCH (br:BrainRegion)
WHERE br.name = CASE
  WHEN c.category IN ['emotion', '감정'] THEN 'amygdala'
  WHEN c.category IN ['visual', '시각'] THEN 'occipital'
  WHEN c.category IN ['language', '언어', 'identity', '정체성'] THEN 'temporal'
  WHEN c.category IN ['spatial', '공간'] THEN 'parietal'
  WHEN c.category IN ['action', '행동', 'motor'] THEN 'motor_cortex'
  WHEN c.category IN ['procedural', '절차'] THEN 'cerebellum'
  ELSE 'prefrontal'
END
CREATE (c)-[:MAPPED_TO {activation_level: 0.0}]->(br)
RETURN c
```

---

## 6. Realtime 대체 전략: Redis Pub/Sub + SSE

### 아키텍처

```
[FastAPI] ──publish──> [Redis Pub/Sub] ──subscribe──> [Next.js SSE Route] ──stream──> [Browser]
```

### 구현 설계

#### SSE Route Handler (`/api/events/route.ts`)

```typescript
import { NextRequest } from 'next/server'
import Redis from 'ioredis'

export async function GET(req: NextRequest) {
  const subscriber = new Redis(process.env.REDIS_URL!)
  const channels = [
    'neuron_activation', 'baby_state', 'pending_question',
    'prediction', 'imagination', 'experience'
  ]
  const encoder = new TextEncoder()
  let isClosed = false

  const stream = new ReadableStream({
    async start(controller) {
      controller.enqueue(encoder.encode(`data: ${JSON.stringify({type:'connected'})}\n\n`))
      await subscriber.subscribe(...channels)

      subscriber.on('message', (channel, message) => {
        if (isClosed) return
        const data = `event: ${channel}\ndata: ${message}\n\n`
        controller.enqueue(encoder.encode(data))
      })

      req.signal.addEventListener('abort', () => {
        isClosed = true
        subscriber.unsubscribe().then(() => subscriber.quit())
        controller.close()
      })

      // Keep-alive every 30s
      const keepAlive = setInterval(() => {
        if (isClosed) { clearInterval(keepAlive); return }
        try { controller.enqueue(encoder.encode(': keep-alive\n\n')) }
        catch { clearInterval(keepAlive) }
      }, 30_000)
    },
    cancel() { isClosed = true; subscriber.quit().catch(() => {}) }
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive'
    }
  })
}
```

#### Frontend Hook (`useSSESubscription.ts`)

```typescript
'use client'
import { useEffect, useRef, useCallback } from 'react'

type EventHandlers = Record<string, (data: any) => void>

export function useSSESubscription(handlers: EventHandlers, disabled = false) {
  const handlersRef = useRef(handlers)
  useEffect(() => { handlersRef.current = handlers }, [handlers])

  useEffect(() => {
    if (disabled || typeof window === 'undefined') return

    const source = new EventSource('/api/events')

    Object.keys(handlersRef.current).forEach(type => {
      source.addEventListener(type, (e) => {
        try {
          const data = JSON.parse((e as MessageEvent).data)
          handlersRef.current[type]?.(data)
        } catch {}
      })
    })

    source.onerror = () => {
      source.close()
      setTimeout(() => { /* reconnect logic */ }, 3000)
    }

    return () => source.close()
  }, [disabled])
}
```

#### Python Publish (`neural/baby/realtime.py`)

```python
import os, json, redis.asyncio as aioredis

_redis = None

async def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(os.environ.get("REDIS_URL", ""))
    return _redis

async def publish_event(channel: str, data: dict) -> bool:
    try:
        r = await get_redis()
        await r.publish(channel, json.dumps(data))
        return True
    except Exception:
        return False
```

### LOW 중요도 채널 → 폴링 전환

기존 16개 Realtime 채널 중 LOW 12개는 5-10초 폴링으로 변환:
- `useQuery` (React Query/SWR) + `refetchInterval: 5000`
- Realtime 복잡성 대폭 감소, 사용자 체감 차이 없음

---

## 7. FastAPI 서버 설계

### 기존 Edge Functions → FastAPI 엔드포인트 매핑

```
FastAPI Server (Python 3.12+)
├── /api/conversation          ← conversation-process v30
├── /api/vision/process        ← vision-process v4
├── /api/world/understand      ← world-understanding v2
├── /api/audio/transcribe      ← audio-transcribe v2
├── /api/speech/synthesize     ← speech-synthesize v2
├── /api/memory/consolidate    ← memory-consolidation v6
├── /api/curiosity             ← generate-curiosity v4
├── /api/exploration           ← autonomous-exploration v5
├── /api/metacognition         ← self-evaluation v2
├── /api/goals                 ← autonomous-goals v2
├── /api/feedback              ← textual-backpropagation v1
├── /api/imagination           ← imagination-engine v1
└── /api/events (SSE)          ← Realtime 대체
```

### 핵심 의존성

```
fastapi
uvicorn
neo4j              # 공식 Neo4j Python 드라이버
neo4j-graphrag     # RAG 파이프라인 (VectorRetriever 등)
redis[hiredis]     # Redis 클라이언트
google-generativeai # Gemini API
httpx              # 비동기 HTTP
pydantic           # 데이터 검증
```

### 장점: Python 통합

현재 `neural/baby/` 모듈 (db.py, emotions.py, world_model.py, development.py)을
FastAPI에서 **직접 import** 가능. Deno에서 Python 로직을 재구현하던 이중 작업 해소.

```python
# 현재 (Deno Edge Function에서 Python 로직 재구현)
# conversation-process.ts: 800줄+ TypeScript로 감정/발달/기억 로직 재구현

# 변경 후 (Python에서 직접 사용)
from neural.baby.emotions import EmotionalCore
from neural.baby.development import DevelopmentManager
from neural.baby.neo4j_db import BrainDatabase  # db.py → neo4j_db.py
```

---

## 8. 데이터 마이그레이션 계획

### Phase 0: 환경 세팅 (Day 1)

- [ ] Neo4j AuraDB Free 인스턴스 생성 (50K nodes, 175K relationships)
- [ ] Upstash Redis Free 인스턴스 생성 (10K commands/day)
- [ ] 환경변수 설정 (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `REDIS_URL`)
- [ ] Python `neo4j` + `redis` 드라이버 설치
- [ ] 연결 테스트 스크립트

### Phase 1: 스키마 & 데이터 이관 (Day 2-3)

- [ ] Neo4j Cypher 스키마 생성 (노드 레이블, 제약, 인덱스)
- [ ] 벡터 인덱스 3개 생성 (concept, experience, visual)
- [ ] Supabase → JSON 내보내기 스크립트
- [ ] JSON → Neo4j LOAD CSV or Cypher 배치 삽입
- [ ] 488 Concepts + 616 Relations 이관 확인
- [ ] 965 Experiences 이관 확인
- [ ] 기타 테이블 이관 (emotion_logs, predictions, etc.)
- [ ] 데이터 정합성 검증 (개수, 관계)

### Phase 2: Python 백엔드 변환 (Day 4-6)

- [ ] `neural/baby/neo4j_db.py` 작성 (db.py 800줄 → Neo4j 변환)
- [ ] FastAPI 서버 구조 생성
- [ ] `conversation-process` v30 → FastAPI 엔드포인트 (가장 복잡)
  - Memory Recall Pipeline (벡터 검색 + 그래프 순회)
  - LC-NE Adaptive Gain 감정 조절
  - Spreading Activation (Cypher 가변 경로)
  - Ablation isolation
- [ ] 나머지 12개 Edge Function → FastAPI 엔드포인트
- [ ] Redis Pub/Sub publish 로직 삽입 (활성화, 상태 변경 시)
- [ ] 단위 테스트

### Phase 3: Realtime 대체 (Day 7)

- [ ] SSE Route Handler (`/api/events/route.ts`)
- [ ] `useSSESubscription` React Hook
- [ ] HIGH 채널 2개: neuron_activation, pending_question
- [ ] MEDIUM 채널 4개: world-model, predictions, imagination, visual
- [ ] LOW 채널 10개: 폴링으로 전환 (refetchInterval)
- [ ] Realtime 동작 확인

### Phase 4: Frontend 변환 (Day 8-10)

- [ ] `@supabase/supabase-js` 제거
- [ ] `src/lib/supabase.ts` → `src/lib/neo4j-client.ts` (또는 API 경유)
- [ ] `src/lib/database.types.ts` → TypeScript 인터페이스 수동 정의
- [ ] 16개 hooks 재작성 (Supabase `.from()` → fetch API)
- [ ] 12개 API routes 변경 (Supabase EF URL → FastAPI URL)
- [ ] 10+ components Realtime → SSE/폴링
- [ ] 빌드 확인 + Vercel 배포

### Phase 5: 검증 & 정리 (Day 11-12)

- [ ] E2E 테스트: 대화 → 기억 → 감정 → 뇌 시각화
- [ ] ablation 실험 재현성 확인 (ICDL 논문)
- [ ] 성능 벤치마크: 응답 지연, 벡터 검색 정확도
- [ ] Supabase 프로젝트 아카이브 (삭제하지 않음)
- [ ] 문서 업데이트 (Task.md, MEMORY.md)

---

## 9. 리스크 & 대응

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| AuraDB Free 50K 노드 한도 초과 | 낮음 (현재 ~2K) | 중 | AuraDB Pro 업그레이드 or 자체 호스팅 |
| Neo4j 벡터 검색 성능 저하 | 매우 낮음 (<50K) | 중 | Qdrant 분리 (확장 로드맵) |
| Deno→Python 변환 버그 | 중간 | 높 | Edge Function별 단위 테스트 |
| Realtime 지연 증가 | 낮음 | 중 | Redis → 직접 WebSocket 전환 |
| ICDL 논문 ablation 재현 실패 | 낮음 | 매우 높 | 이관 전 전체 ablation 데이터 백업 |
| Vercel Cold Start + FastAPI | 중간 | 중 | Railway/Fly.io에 FastAPI 배포 |

---

## 10. 비용 비교

| 항목 | 현재 (Supabase) | 변경 후 |
|------|-----------------|---------|
| DB | Supabase Free ($0) | Neo4j AuraDB Free ($0) |
| 벡터 DB | pgvector (Supabase 내장) | Neo4j Vector Index (내장) |
| Realtime | Supabase Realtime (내장) | Upstash Redis Free ($0) |
| 서버리스 함수 | Supabase Edge Functions (내장) | Railway/Fly.io (~$5-7/mo) |
| Frontend | Vercel Free ($0) | Vercel Free ($0) |
| **합계** | **$0/mo** | **$0~7/mo** |

> FastAPI 서버만 별도 호스팅 비용 발생.
> 개발 단계에서는 로컬 실행으로 $0 유지 가능.

---

## 11. 미래 확장: Qdrant 벡터 DB 사전 설계

> 현재는 Neo4j Vector Index만 사용. 50K+ 개념 돌파 시 Qdrant 분리를 위한 사전 설계.

### 분리 시점 기준

| 지표 | 현재 | 분리 트리거 |
|------|------|------------|
| 개념 수 | ~500 | >50,000 |
| 벡터 검색 지연 | <5ms | >100ms |
| 인덱스 메모리 | ~1.7MB | >2GB |

### Qdrant 컬렉션 설계 (사전 정의)

```yaml
# Collection: baby_concepts
name: baby_concepts
vectors:
  size: 768            # text-embedding-3-small
  distance: Cosine
  on_disk: false       # <1M이면 메모리 유지
  quantization:
    scalar:
      type: int8       # 4x 메모리 절약, recall -1%
payload_schema:
  concept_id: keyword  # Neo4j 노드 ID (외래키)
  name: keyword
  category: keyword    # 필터링용
  brain_region: keyword
  strength: float
  created_at: datetime

# Collection: baby_experiences
name: baby_experiences
vectors:
  size: 768
  distance: Cosine
payload_schema:
  experience_id: keyword
  emotion: keyword
  salience: float
  created_at: datetime

# Collection: baby_visual
name: baby_visual
vectors:
  size: 768
  distance: Cosine
payload_schema:
  visual_id: keyword
  objects: keyword[]
  created_at: datetime
```

### 쿼리 패턴 (분리 후)

```python
# Step 1: Qdrant에서 벡터 유사도 검색
results = qdrant_client.search(
    collection_name="baby_concepts",
    query_vector=query_embedding,
    query_filter=Filter(must=[
        FieldCondition(key="category", match=MatchAny(any=["emotion", "identity"]))
    ]),
    limit=20,
    score_threshold=0.6
)

# Step 2: Neo4j에서 그래프 확장 (concept_ids로 조회)
concept_ids = [r.payload["concept_id"] for r in results]
cypher = """
MATCH (c:Concept)-[r:RELATES_TO]-(related:Concept)
WHERE c.id IN $ids
RETURN c.name, related.name, r.strength
"""
graph_context = neo4j_session.run(cypher, ids=concept_ids)

# Step 3: 결과 병합
combined = merge_vector_and_graph(results, graph_context)
```

### 마이그레이션 절차 (Neo4j → Qdrant 분리 시)

```
1. Qdrant Cloud Free 인스턴스 생성 (1GB, 1M vectors)
2. Neo4j에서 모든 임베딩 추출:
   MATCH (c:Concept) WHERE c.embedding IS NOT NULL
   RETURN c.id, c.name, c.category, c.embedding
3. Qdrant에 배치 upsert (1000개씩)
4. FastAPI에 QdrantClient 추가
5. 벡터 검색 로직을 Neo4j SEARCH → Qdrant search로 교체
6. Neo4j에서 embedding 프로퍼티 제거 (메모리 절약)
7. Neo4j Vector Index 삭제
```

### Qdrant 인프라 옵션

| 옵션 | 비용 | 벡터 한도 | 장점 |
|------|------|----------|------|
| Qdrant Cloud Free | $0 | 1GB (~200K @ 768dim) | 관리 불필요 |
| Qdrant Cloud Pro | ~$25/mo | 무제한 | 자동 스케일링 |
| Self-hosted (Docker) | 인프라 비용 | 무제한 | 완전 제어 |

---

## 12. MCP 서버 설정

### 설치할 MCP 서버 (3개)

#### 1. Neo4j MCP (공식, GA) — 필수

개발 중 Claude가 직접 Neo4j 그래프를 쿼리/검증할 수 있게 함.

```bash
# 방법 A: Go 바이너리 다운로드
# https://github.com/neo4j/mcp/releases 에서 neo4j-mcp.exe 다운로드 후:
claude mcp add neo4j-mcp -- neo4j-mcp \
  --uri "bolt+s://YOUR_AURA_URI" \
  --username "neo4j" \
  --password "YOUR_PASSWORD" \
  --database "neo4j" \
  --read-only

# 방법 B: Python (uvx) — APOC 필요
claude mcp add neo4j-cypher -- uvx mcp-neo4j-cypher@latest
# 환경변수: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_READ_ONLY=true
```

**도구**: `get-schema`, `read-cypher`, `write-cypher` (read-only 시 비활성)
**안전**: `--read-only` 필수 (실수로 데이터 변경 방지)

#### 2. Upstash Redis MCP — 필수

Redis 캐시/Pub/Sub 상태를 Claude가 직접 검사할 수 있게 함.

```bash
claude mcp add upstash -- npx -y @upstash/mcp-server@latest \
  --email YOUR_UPSTASH_EMAIL \
  --api-key YOUR_UPSTASH_API_KEY
```

**도구**: `run_single_redis_command` (임의 Redis 명령 실행), DB 통계, 백업 등 17개
**주의**: FLUSHALL 등 파괴적 명령도 실행 가능 → Claude에게 읽기 전용으로 사용 지시

#### 3. Neo4j Data Modeling MCP — 마이그레이션 중 임시

스키마 검증, Mermaid 다이어그램, Pydantic 모델 생성.

```bash
claude mcp add neo4j-data-modeling -- uvx mcp-neo4j-data-modeling@latest
```

**도구**: 14개 (validate_data_model, get_mermaid_config_str, export_to_pydantic_models 등)
**삭제 시점**: 마이그레이션 완료 후

### 설치하지 않는 MCP 서버

| 서버 | 이유 |
|------|------|
| `mcp-neo4j-memory` | 기존 `mcp__memory__*`와 도구명 충돌, MEMORY.md로 충분 |
| `mcp-neo4j-cloud-aura-api` | Free 티어 관리 기능 제한, 인스턴스 삭제 리스크 |
| `@modelcontextprotocol/server-redis` | Archived (2025-04), 기본 get/set만 지원, Upstash가 상위호환 |

---

## 13. 기술 스택 요약

```
┌──────────────────────────────────────────────────┐
│  Frontend (Vercel)                               │
│  Next.js 16 + React 19 + Three.js                │
│  ├── fetch('/api/...') → FastAPI                 │
│  ├── EventSource('/api/events') → SSE            │
│  └── React Query (폴링 for LOW priority)         │
├──────────────────────────────────────────────────┤
│  Backend (Railway/Fly.io or Local)               │
│  FastAPI + Python 3.12+                          │
│  ├── neo4j (driver) + neo4j-graphrag             │
│  ├── redis (Pub/Sub publish)                     │
│  ├── google-generativeai (Gemini)                │
│  └── neural.baby.* (기존 Python 모듈 재활용)     │
├──────────────────────────────────────────────────┤
│  Data Layer                                      │
│  ├── Neo4j AuraDB (graph + vector)               │
│  ├── Upstash Redis (Pub/Sub + cache)             │
│  └── [미래] Qdrant Cloud (벡터 분리, 50K+ 시)    │
├──────────────────────────────────────────────────┤
│  MCP Servers (개발 도구)                          │
│  ├── neo4j-mcp (GA) — 그래프 쿼리/검증           │
│  ├── upstash-mcp — Redis 캐시/Pub/Sub 검사       │
│  └── neo4j-data-modeling — 스키마 설계 (임시)     │
└──────────────────────────────────────────────────┘
```
