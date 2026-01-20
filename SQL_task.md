# SQL Task: Robot_Brain Database Schema

**프로젝트**: Robot_Brain (extbfhoktzozgqddjcps)
**최종 업데이트**: 2025-12-31
**스키마 버전**: v008

---

## 스키마 버전 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v001 | 2025-12-31 | pgvector 확장 + brain_metadata 테이블 |
| v002 | 2025-12-31 | baby_state 테이블 (싱글톤 트리거) |
| v003 | 2025-12-31 | emotion_logs 테이블 (시계열 + 뷰) |
| v004 | 2025-12-31 | experiences 테이블 (벡터 + 기억 강화) |
| v005 | 2025-12-31 | semantic_concepts + procedural_patterns |
| v006 | 2025-12-31 | 검색 함수들 (하이브리드, 가중치) |
| v007 | 2025-12-31 | Realtime + RLS 정책 |
| v008a | 2025-12-31 | emotion↔experience FK 연결 |
| v008b | 2025-12-31 | experience_concepts 테이블 (M:N, Hebb's Law) |
| v008c | 2025-12-31 | concept_relations 테이블 (Knowledge Graph) |
| v008d | 2025-12-31 | pattern_learning_events 테이블 |
| v008e | 2025-12-31 | 시냅스 함수 5개 (강화/약화/검색) |

---

## 현재 테이블 상태

| 테이블 | 상태 | RLS | 설명 |
|--------|------|-----|------|
| brain_metadata | ✅ 완료 | ✅ | 시스템 메타데이터 (버전, 설정) |
| baby_state | ✅ 완료 | ✅ | 현재 상태 (싱글톤, Realtime) |
| emotion_logs | ✅ 완료 | ✅ | 감정 변화 히스토리 (+experience_id FK) |
| experiences | ✅ 완료 | ✅ | 에피소드 기억 (+emotion_snapshot) |
| semantic_concepts | ✅ 완료 | ✅ | 의미 기억 (개념/지식) |
| procedural_patterns | ✅ 완료 | ✅ | 절차 기억 (방법/패턴) |
| **experience_concepts** | ✅ 완료 | ✅ | 경험↔개념 M:N (Hebb's Law) |
| **concept_relations** | ✅ 완료 | ✅ | 개념 간 관계 (Knowledge Graph) |
| **pattern_learning_events** | ✅ 완료 | ✅ | 절차 학습 이벤트 |

---

## 아키텍처: Baby Brain → Jarvis 진화

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BABY BRAIN → JARVIS DB ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Phase 1: BABY BRAIN (현재 ✅)                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │ baby_state  │  │emotion_logs │  │ experiences │                      │
│  │ (싱글톤)    │  │ (시계열)    │  │ (벡터검색)  │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
│                                                                          │
│  Phase 2: CHILD BRAIN (확장 예정)                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │ semantic_   │  │ procedural_ │  │ attention_  │                      │
│  │ concepts ✅ │  │ patterns ✅ │  │ weights     │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
│                                                                          │
│  Phase 3: TEEN BRAIN (미래)                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │ meta_       │  │ goal_       │  │ context_    │                      │
│  │ cognition   │  │ hierarchy   │  │ windows     │                      │
│  └─────────────────────────────────────────────────┘                     │
│                                                                          │
│  Phase 4: JARVIS (자율)                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │ agent_      │  │ world_      │  │ self_       │                      │
│  │ registry    │  │ model       │  │ evolution   │                      │
│  └─────────────────────────────────────────────────┘                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 마이그레이션 SQL

### v001: pgvector + brain_metadata

```sql
-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- brain_metadata 테이블 (시스템 상태 추적)
CREATE TABLE brain_metadata (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  description TEXT,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 초기 메타데이터
INSERT INTO brain_metadata (key, value, description) VALUES
  ('schema_version', '"v007"', '현재 스키마 버전'),
  ('brain_stage', '"baby"', '발달 단계: baby|child|teen|jarvis'),
  ('embedding_model', '"text-embedding-3-small"', '벡터 임베딩 모델'),
  ('embedding_dimensions', '1536', '임베딩 차원');
```

**상태**: ✅ 완료
**실행일**: 2025-12-31

---

### v002: baby_state (싱글톤)

```sql
CREATE TABLE baby_state (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- 감정 상태 (0.0 ~ 1.0)
  curiosity FLOAT DEFAULT 0.5 CHECK (curiosity >= 0 AND curiosity <= 1),
  joy FLOAT DEFAULT 0.3 CHECK (joy >= 0 AND joy <= 1),
  fear FLOAT DEFAULT 0.1 CHECK (fear >= 0 AND fear <= 1),
  surprise FLOAT DEFAULT 0.2 CHECK (surprise >= 0 AND surprise <= 1),
  frustration FLOAT DEFAULT 0.1 CHECK (frustration >= 0 AND frustration <= 1),
  boredom FLOAT DEFAULT 0.2 CHECK (boredom >= 0 AND boredom <= 1),
  dominant_emotion TEXT DEFAULT 'curiosity',

  -- 발달 상태
  development_stage INT DEFAULT 0 CHECK (development_stage >= 0 AND development_stage <= 10),
  experience_count INT DEFAULT 0,
  success_count INT DEFAULT 0,
  progress FLOAT DEFAULT 0.0,
  milestones JSONB DEFAULT '[]'::jsonb,

  -- 자아 모델
  capabilities JSONB DEFAULT '{}'::jsonb,
  preferences JSONB DEFAULT '{}'::jsonb,
  limitations JSONB DEFAULT '[]'::jsonb,

  -- 확장성 (미래 발달 단계용)
  extras JSONB DEFAULT '{}'::jsonb,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 싱글톤 트리거 (1개 행만 허용)
CREATE OR REPLACE FUNCTION enforce_baby_state_singleton()
RETURNS TRIGGER AS $$
BEGIN
  IF (SELECT COUNT(*) FROM baby_state) >= 1 THEN
    RAISE EXCEPTION 'baby_state는 싱글톤입니다. 기존 행을 UPDATE하세요.';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**상태**: ✅ 완료
**실행일**: 2025-12-31

---

### v003: emotion_logs (시계열)

```sql
CREATE TABLE emotion_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- 감정 값
  curiosity FLOAT NOT NULL,
  joy FLOAT NOT NULL,
  fear FLOAT NOT NULL,
  surprise FLOAT NOT NULL,
  frustration FLOAT NOT NULL,
  boredom FLOAT NOT NULL,
  dominant_emotion TEXT NOT NULL,

  -- 컨텍스트
  trigger_task TEXT,
  trigger_type TEXT,  -- 'success', 'failure', 'novelty', 'prediction_error'
  development_stage INT,
  context JSONB DEFAULT '{}'::jsonb,

  created_at TIMESTAMPTZ DEFAULT now()
);

-- 인덱스
CREATE INDEX emotion_logs_created_idx ON emotion_logs (created_at DESC);
CREATE INDEX emotion_logs_dominant_idx ON emotion_logs (dominant_emotion, created_at DESC);

-- 통계 뷰
CREATE OR REPLACE VIEW recent_emotion_stats AS
SELECT
  date_trunc('hour', created_at) as hour,
  AVG(curiosity) as avg_curiosity,
  AVG(joy) as avg_joy,
  COUNT(*) as log_count
FROM emotion_logs
WHERE created_at > now() - interval '7 days'
GROUP BY date_trunc('hour', created_at);
```

**상태**: ✅ 완료
**실행일**: 2025-12-31

---

### v004: experiences (벡터 + 기억 강화)

```sql
CREATE TABLE experiences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- 경험 내용
  task TEXT NOT NULL,
  task_type TEXT,
  output TEXT,
  success BOOLEAN DEFAULT FALSE,

  -- 감정 및 중요도
  emotional_salience FLOAT DEFAULT 0.5,
  curiosity_signal JSONB,
  dominant_emotion TEXT,

  -- 기억 강화/약화 (Memory consolidation)
  memory_strength FLOAT DEFAULT 1.0,  -- 시간 감소, 접근 시 증가
  access_count INT DEFAULT 0,
  last_accessed_at TIMESTAMPTZ,

  -- 벡터 임베딩
  embedding vector(1536),

  -- 관련 경험
  related_experiences UUID[] DEFAULT '{}',

  -- 메타데이터
  development_stage INT,
  session_id UUID,
  tags TEXT[] DEFAULT '{}',
  extras JSONB DEFAULT '{}'::jsonb,

  created_at TIMESTAMPTZ DEFAULT now()
);

-- 벡터 인덱스 (IVFFlat)
CREATE INDEX experiences_embedding_idx ON experiences
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 기억 강화 함수
CREATE OR REPLACE FUNCTION reinforce_memory(exp_id UUID)
RETURNS void AS $$
BEGIN
  UPDATE experiences
  SET
    memory_strength = LEAST(memory_strength * 1.1, 2.0),
    access_count = access_count + 1,
    last_accessed_at = now()
  WHERE id = exp_id;
END;
$$ LANGUAGE plpgsql;
```

**상태**: ✅ 완료
**실행일**: 2025-12-31

---

### v005: semantic_concepts + procedural_patterns

```sql
-- 의미 기억
CREATE TABLE semantic_concepts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT UNIQUE NOT NULL,
  category TEXT,
  description TEXT,
  relations JSONB DEFAULT '[]'::jsonb,
  strength FLOAT DEFAULT 0.5,
  usage_count INT DEFAULT 0,
  embedding vector(1536),
  acquired_at_stage INT DEFAULT 0,
  extras JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 절차 기억
CREATE TABLE procedural_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_type TEXT NOT NULL,
  approach TEXT NOT NULL,
  success_count INT DEFAULT 0,
  failure_count INT DEFAULT 0,
  success_rate FLOAT GENERATED ALWAYS AS (
    CASE WHEN success_count + failure_count > 0
    THEN success_count::FLOAT / (success_count + failure_count)
    ELSE 0 END
  ) STORED,
  total_uses INT DEFAULT 0,
  avg_completion_time_ms INT,
  effective_contexts JSONB DEFAULT '[]'::jsonb,
  min_stage_required INT DEFAULT 0,
  extras JSONB DEFAULT '{}'::jsonb,
  last_used TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(task_type, approach)
);
```

**상태**: ✅ 완료
**실행일**: 2025-12-31

---

### v006: 검색 함수

```sql
-- 기본 유사 경험 검색
CREATE OR REPLACE FUNCTION search_similar_experiences(
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  task TEXT,
  task_type TEXT,
  output TEXT,
  success BOOLEAN,
  similarity FLOAT,
  memory_strength FLOAT,
  emotional_salience FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    e.id, e.task, e.task_type, e.output, e.success,
    (1 - (e.embedding <=> query_embedding))::FLOAT AS similarity,
    e.memory_strength, e.emotional_salience
  FROM experiences e
  WHERE e.embedding IS NOT NULL
    AND (1 - (e.embedding <=> query_embedding)) > match_threshold
  ORDER BY e.embedding <=> query_embedding
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- 가중치 적용 검색
CREATE OR REPLACE FUNCTION search_experiences_weighted(
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.5,
  match_count INT DEFAULT 10,
  weight_strength BOOLEAN DEFAULT TRUE,
  weight_emotion BOOLEAN DEFAULT TRUE,
  success_only BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (...) AS $$ ... $$;

-- 빠른 검색
CREATE OR REPLACE FUNCTION quick_search_experiences(
  query_embedding vector(1536),
  match_count INT DEFAULT 5
)
RETURNS TABLE (...) AS $$ ... $$;

-- 텍스트 기반 검색 (하이브리드)
CREATE OR REPLACE FUNCTION search_experiences_by_text(
  search_query TEXT,
  match_count INT DEFAULT 10
)
RETURNS TABLE (...) AS $$ ... $$;
```

**상태**: ✅ 완료
**실행일**: 2025-12-31

---

### v007: Realtime + RLS

```sql
-- Realtime 활성화
ALTER PUBLICATION supabase_realtime ADD TABLE baby_state;
ALTER PUBLICATION supabase_realtime ADD TABLE emotion_logs;

-- RLS 활성화
ALTER TABLE brain_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE baby_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE emotion_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiences ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic_concepts ENABLE ROW LEVEL SECURITY;
ALTER TABLE procedural_patterns ENABLE ROW LEVEL SECURITY;

-- RLS 정책: 읽기 공개, 쓰기 service_role만
CREATE POLICY "read_all" ON [table] FOR SELECT USING (true);
CREATE POLICY "write_service" ON [table] FOR ALL USING (auth.role() = 'service_role');
```

**상태**: ✅ 완료
**실행일**: 2025-12-31

---

### v008a: emotion↔experience FK 연결

```sql
-- emotion_logs에 experience_id FK 추가 (어떤 경험이 이 감정을 유발했는지)
ALTER TABLE emotion_logs
ADD COLUMN experience_id UUID REFERENCES experiences(id) ON DELETE SET NULL;

CREATE INDEX emotion_logs_experience_idx ON emotion_logs (experience_id);

-- experiences에 emotion_snapshot JSONB 추가 (경험 당시 감정 상태)
ALTER TABLE experiences
ADD COLUMN emotion_snapshot JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN emotion_logs.experience_id IS '이 감정을 유발한 경험 (편도체→해마 연결)';
COMMENT ON COLUMN experiences.emotion_snapshot IS '경험 당시 감정 상태 스냅샷';
```

**상태**: ✅ 완료
**실행일**: 2025-12-31

---

### v008b: experience_concepts (M:N, Hebb's Law)

```sql
-- 경험 ↔ 개념 다대다 연결 (Hebb's Law 구현)
CREATE TABLE experience_concepts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experience_id UUID NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
  concept_id UUID NOT NULL REFERENCES semantic_concepts(id) ON DELETE CASCADE,

  -- 연결 강도 및 신뢰도
  confidence FLOAT DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
  relevance FLOAT DEFAULT 0.5 CHECK (relevance >= 0 AND relevance <= 1),

  -- Hebb's Law: "함께 발화하는 뉴런은 함께 연결된다"
  co_activation_count INT DEFAULT 1,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(experience_id, concept_id)
);

-- 인덱스
CREATE INDEX experience_concepts_exp_idx ON experience_concepts (experience_id);
CREATE INDEX experience_concepts_concept_idx ON experience_concepts (concept_id);
CREATE INDEX experience_concepts_coact_idx ON experience_concepts (co_activation_count DESC);
```

**상태**: ✅ 완료
**실행일**: 2025-12-31

---

### v008c: concept_relations (Knowledge Graph)

```sql
-- 개념 간 관계 (지식 그래프)
CREATE TABLE concept_relations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_concept_id UUID NOT NULL REFERENCES semantic_concepts(id) ON DELETE CASCADE,
  to_concept_id UUID NOT NULL REFERENCES semantic_concepts(id) ON DELETE CASCADE,

  -- 관계 유형: is_a, has_a, part_of, similar_to, opposite_of, causes, requires
  relation_type TEXT NOT NULL,

  -- 관계 강도
  strength FLOAT DEFAULT 0.5 CHECK (strength >= 0 AND strength <= 1),
  evidence_count INT DEFAULT 1,
  bidirectional BOOLEAN DEFAULT FALSE,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(from_concept_id, to_concept_id, relation_type),
  CHECK (from_concept_id != to_concept_id)
);

-- 인덱스
CREATE INDEX concept_relations_from_idx ON concept_relations (from_concept_id);
CREATE INDEX concept_relations_to_idx ON concept_relations (to_concept_id);
CREATE INDEX concept_relations_type_idx ON concept_relations (relation_type);
```

**상태**: ✅ 완료
**실행일**: 2025-12-31

---

### v008d: pattern_learning_events

```sql
-- 절차 학습 이벤트 (강화 학습 히스토리)
CREATE TABLE pattern_learning_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pattern_id UUID NOT NULL REFERENCES procedural_patterns(id) ON DELETE CASCADE,
  experience_id UUID NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,

  -- 학습 결과
  outcome TEXT NOT NULL CHECK (outcome IN ('success', 'failure', 'partial', 'refinement')),

  -- 강화 학습 신호
  reward_signal FLOAT DEFAULT 0,
  prediction_error FLOAT DEFAULT 0,

  -- 컨텍스트
  context JSONB DEFAULT '{}'::jsonb,

  created_at TIMESTAMPTZ DEFAULT now()
);

-- 인덱스
CREATE INDEX pattern_learning_pattern_idx ON pattern_learning_events (pattern_id);
CREATE INDEX pattern_learning_experience_idx ON pattern_learning_events (experience_id);
CREATE INDEX pattern_learning_outcome_idx ON pattern_learning_events (outcome, created_at DESC);
```

**상태**: ✅ 완료
**실행일**: 2025-12-31

---

### v008e: 시냅스 함수 (강화/약화/검색)

```sql
-- 1. 경험-개념 연결 강화 (Hebb's Law)
CREATE OR REPLACE FUNCTION strengthen_experience_concept_link(
  p_experience_id UUID,
  p_concept_id UUID,
  p_strength_delta FLOAT DEFAULT 0.1
)
RETURNS void AS $$
BEGIN
  INSERT INTO experience_concepts (experience_id, concept_id, co_activation_count)
  VALUES (p_experience_id, p_concept_id, 1)
  ON CONFLICT (experience_id, concept_id) DO UPDATE
  SET
    confidence = LEAST(experience_concepts.confidence + p_strength_delta, 1.0),
    co_activation_count = experience_concepts.co_activation_count + 1,
    updated_at = now();
END;
$$ LANGUAGE plpgsql;

-- 2. 개념 관계 강화
CREATE OR REPLACE FUNCTION strengthen_concept_relation(
  p_from_id UUID,
  p_to_id UUID,
  p_relation_type TEXT,
  p_strength_delta FLOAT DEFAULT 0.1
)
RETURNS void AS $$
BEGIN
  INSERT INTO concept_relations (from_concept_id, to_concept_id, relation_type)
  VALUES (p_from_id, p_to_id, p_relation_type)
  ON CONFLICT (from_concept_id, to_concept_id, relation_type) DO UPDATE
  SET
    strength = LEAST(concept_relations.strength + p_strength_delta, 1.0),
    evidence_count = concept_relations.evidence_count + 1,
    updated_at = now();
END;
$$ LANGUAGE plpgsql;

-- 3. 시냅스 약화 (시간 기반 감쇠)
CREATE OR REPLACE FUNCTION decay_all_connections(
  p_decay_rate FLOAT DEFAULT 0.01
)
RETURNS void AS $$
BEGIN
  -- experience_concepts 감쇠
  UPDATE experience_concepts
  SET confidence = GREATEST(confidence - p_decay_rate, 0.1)
  WHERE confidence > 0.1;

  -- concept_relations 감쇠
  UPDATE concept_relations
  SET strength = GREATEST(strength - p_decay_rate, 0.1)
  WHERE strength > 0.1;

  -- experiences 기억 강도 감쇠
  UPDATE experiences
  SET memory_strength = GREATEST(memory_strength * (1 - p_decay_rate), 0.1)
  WHERE memory_strength > 0.1;
END;
$$ LANGUAGE plpgsql;

-- 4. 연관 개념 찾기
CREATE OR REPLACE FUNCTION find_associated_concepts(
  p_experience_id UUID,
  p_min_confidence FLOAT DEFAULT 0.3,
  p_limit INT DEFAULT 10
)
RETURNS TABLE (
  concept_id UUID,
  concept_name TEXT,
  confidence FLOAT,
  co_activation_count INT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    sc.id,
    sc.name,
    ec.confidence,
    ec.co_activation_count
  FROM experience_concepts ec
  JOIN semantic_concepts sc ON sc.id = ec.concept_id
  WHERE ec.experience_id = p_experience_id
    AND ec.confidence >= p_min_confidence
  ORDER BY ec.co_activation_count DESC, ec.confidence DESC
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- 5. 감정 기반 기억 강화
CREATE OR REPLACE FUNCTION boost_memory_by_emotion(
  p_experience_id UUID,
  p_emotion_intensity FLOAT
)
RETURNS void AS $$
DECLARE
  v_boost FLOAT;
BEGIN
  -- 감정 강도에 비례하여 기억 강화 (최대 2배)
  v_boost := 1.0 + (p_emotion_intensity * 1.0);

  UPDATE experiences
  SET
    memory_strength = LEAST(memory_strength * v_boost, 2.0),
    emotional_salience = GREATEST(emotional_salience, p_emotion_intensity)
  WHERE id = p_experience_id;
END;
$$ LANGUAGE plpgsql;
```

**상태**: ✅ 완료
**실행일**: 2025-12-31

---

## 핵심 기능

### 1. 기억 강화/약화 (Memory Consolidation)

```sql
-- 기억 접근 시 강화
SELECT reinforce_memory('experience-uuid');

-- 시간 기반 망각 (pg_cron으로 주기적 실행)
SELECT decay_all_memory_strength();
```

### 2. 유사 경험 검색 (Hybrid Search)

```sql
-- 벡터 유사도 검색
SELECT * FROM search_similar_experiences(
  '[0.1, 0.2, ...]'::vector,  -- 쿼리 임베딩
  0.7,                         -- 임계값
  5                            -- 개수
);

-- 텍스트 검색
SELECT * FROM search_experiences_by_text('fibonacci function');
```

### 3. 최적 접근법 조회

```sql
SELECT * FROM get_best_approaches('function', 3, 5);
```

---

## 롤백 SQL

필요시 테이블 삭제:

```sql
-- 주의: 모든 데이터 삭제됨
DROP TABLE IF EXISTS procedural_patterns;
DROP TABLE IF EXISTS semantic_concepts;
DROP TABLE IF EXISTS experiences;
DROP TABLE IF EXISTS emotion_logs;
DROP TABLE IF EXISTS baby_state;
DROP TABLE IF EXISTS brain_metadata;
DROP EXTENSION IF EXISTS vector;
```

---

## 연결 정보

```typescript
// Supabase 클라이언트 설정
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://extbfhoktzozgqddjcps.supabase.co'
const supabaseKey = process.env.SUPABASE_ANON_KEY  // 읽기 전용
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY  // 쓰기용

const supabase = createClient(supabaseUrl, supabaseKey)
```

---

## 다음 단계

1. **Python 연동** (다음 세션 권장):
   - `supabase-py` 설치 및 클라이언트 설정
   - `neural/baby/memory.py` 수정하여 Supabase 연동
   - 기존 `.baby_memory/` JSON 데이터 마이그레이션
2. **임베딩 생성**: OpenAI text-embedding-3-small로 경험 벡터화
3. **프론트엔드**: Realtime 구독으로 감정/발달 상태 실시간 시각화
4. **스케일링**: 데이터 증가 시 IVFFlat → HNSW 인덱스 전환

---

## 참고

- [task_baby_brain.md](./task_baby_brain.md) - 작업 진행 상황
- [Supabase pgvector Docs](https://supabase.com/docs/guides/database/extensions/pgvector)
- [Supabase Realtime Docs](https://supabase.com/docs/guides/realtime)
