# Phase 6: Long-term Memory Consolidation (장기 기억 통합)

**Version**: 1.0
**Created**: 2026-01-22
**Status**: Completed
**Edge Function Version**: v1

---

## Overview

Baby AI가 수면과 유사한 과정을 통해 기억을 정리하고 강화하는 시스템입니다.

### 이론적 배경

**인간 뇌의 수면 중 기억 통합 (Memory Consolidation)**:
- 낮에 해마(Hippocampus)에 저장된 단기 기억
- 수면 중 피질(Cortex)로 이동하며 장기 기억화
- 감정적으로 중요한 기억은 강화
- 불필요한 기억은 삭제 (시냅스 가지치기)

### 구현된 기능

1. **감정 기반 기억 강화** - 감정 강도가 높은 경험은 기억력 증가
2. **시간 기반 기억 감쇠** - 오래 접근 안 된 기억은 점진적 약화
3. **패턴 → 절차 기억 승격** - 반복되는 패턴은 자동화된 절차 기억으로
4. **의미적 연결 생성** - 유사한 경험들 사이 연결 생성
5. **개념 관계 통합** - 지식 그래프 관계 강화/약화

---

## Database Schema

### 1. memory_consolidation_logs

통합 작업 히스토리를 기록합니다.

```sql
CREATE TABLE memory_consolidation_logs (
    id UUID PRIMARY KEY,

    -- 실행 정보
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    trigger_type TEXT NOT NULL, -- scheduled, idle, manual

    -- 처리 통계
    experiences_processed INT DEFAULT 0,
    memories_strengthened INT DEFAULT 0,
    memories_decayed INT DEFAULT 0,
    patterns_promoted INT DEFAULT 0,
    concepts_consolidated INT DEFAULT 0,

    -- 결과
    success BOOLEAN DEFAULT false,
    error_message TEXT,
    processing_time_ms INT,

    development_stage INT,
    extras JSONB
);
```

### 2. procedural_memory

절차적 기억 (암묵적 기억, 자동화된 패턴)을 저장합니다.

```sql
CREATE TABLE procedural_memory (
    id UUID PRIMARY KEY,

    -- 패턴 정보
    pattern_name TEXT NOT NULL,
    pattern_type TEXT, -- conversation, action, response
    pattern_description TEXT,

    -- 활성화 조건
    trigger_conditions JSONB,
    context_requirements JSONB,

    -- 학습 데이터
    source_experiences UUID[],
    repetition_count INT DEFAULT 1,
    success_rate FLOAT DEFAULT 0.5,

    -- 강도 및 감쇠
    strength FLOAT DEFAULT 0.5,
    last_activated_at TIMESTAMPTZ,
    activation_count INT DEFAULT 0,

    acquired_at_stage INT,
    created_at TIMESTAMPTZ
);
```

### 3. semantic_links

경험 간 의미적 연결을 저장합니다.

```sql
CREATE TABLE semantic_links (
    id UUID PRIMARY KEY,

    experience_id_1 UUID REFERENCES experiences(id),
    experience_id_2 UUID REFERENCES experiences(id),

    similarity_score FLOAT,
    link_type TEXT, -- semantic, temporal, emotional, causal
    strength FLOAT,
    co_activation_count INT,

    UNIQUE(experience_id_1, experience_id_2),
    CHECK (experience_id_1 < experience_id_2)
);
```

---

## Edge Function: memory-consolidation

### 엔드포인트

```
POST /functions/v1/memory-consolidation
```

### Actions

#### 1. consolidate - 전체 통합 실행

```typescript
interface ConsolidateRequest {
  action: 'consolidate';
  trigger_type: 'scheduled' | 'idle' | 'manual';
  hours_window?: number;  // 기본: 24
  decay_threshold_days?: number;  // 기본: 30
}

interface ConsolidateResponse {
  success: boolean;
  stats: {
    experiences_processed: number;
    memories_strengthened: number;
    memories_decayed: number;
    patterns_promoted: number;
    concepts_consolidated: number;
    semantic_links_created: number;
  };
}
```

#### 2. strengthen - 감정 기억 강화만

```typescript
interface StrengthenRequest {
  action: 'strengthen';
  hours_window?: number;
}
```

#### 3. decay - 미사용 기억 감쇠만

```typescript
interface DecayRequest {
  action: 'decay';
  decay_threshold_days?: number;
}
```

#### 4. promote_patterns - 패턴 승격만

```typescript
interface PromoteRequest {
  action: 'promote_patterns';
  hours_window?: number;
}
```

#### 5. get_stats - 통계 조회

```typescript
interface GetStatsResponse {
  success: boolean;
  stats: {
    total_consolidations: number;
    last_consolidation: string | null;
    total_memories_strengthened: number;
    total_memories_decayed: number;
    total_patterns_promoted: number;
    procedural_memory_count: number;
    semantic_links_count: number;
  };
}
```

#### 6. get_procedural_memories - 절차 기억 조회

```typescript
interface GetProceduralResponse {
  success: boolean;
  memories: ProceduralMemory[];
}
```

---

## 통합 알고리즘

### 1. 감정 기반 강화

```typescript
async function strengthenEmotionalMemories(hoursWindow: number) {
  // 감정 강도 > 60%인 경험 조회
  const experiences = await getRecentHighEmotionExperiences(hoursWindow);

  for (const exp of experiences) {
    // 감정 강도에 비례하여 강화 (최대 1.5배)
    const boost = 1 + (exp.emotional_salience - 0.6) * 1.25;
    const newStrength = Math.min(exp.memory_strength * boost, 2.0);

    await updateMemoryStrength(exp.id, newStrength);
  }
}
```

### 2. 시간 기반 감쇠

```typescript
async function decayUnusedMemories(thresholdDays: number) {
  // 오래되고 접근 횟수 < 3인 경험 조회
  const experiences = await getOldLowAccessExperiences(thresholdDays);

  for (const exp of experiences) {
    const daysSinceAccess = getDaysSinceLastAccess(exp);

    // 30일마다 10% 감소
    const decayFactor = Math.max(0.9 - (daysSinceAccess / 30) * 0.1, 0.5);
    const newStrength = Math.max(exp.memory_strength * decayFactor, 0.1);

    await updateMemoryStrength(exp.id, newStrength);
  }
}
```

### 3. 패턴 → 절차 기억 승격

```typescript
async function promoteToProceduralMemory(hoursWindow: number) {
  // 최근 성공한 경험들 조회
  const experiences = await getRecentSuccessfulExperiences(hoursWindow);

  // LLM으로 반복 패턴 감지
  const patterns = await detectRepeatingPatterns(experiences);

  for (const pattern of patterns) {
    if (pattern.repetition_count >= 3) {
      await createOrReinforceProceduralMemory(pattern);
    }
  }
}
```

### 4. 의미적 연결 생성

```typescript
async function createSemanticLinks(hoursWindow: number) {
  // 임베딩이 있는 최근 경험들 조회
  const experiences = await getRecentExperiencesWithEmbedding(hoursWindow);

  // 각 쌍에 대해 코사인 유사도 계산
  for (let i = 0; i < experiences.length; i++) {
    for (let j = i + 1; j < experiences.length; j++) {
      const similarity = cosineSimilarity(
        experiences[i].embedding,
        experiences[j].embedding
      );

      if (similarity > 0.7) {
        await createSemanticLink(experiences[i].id, experiences[j].id, similarity);
      }
    }
  }
}
```

---

## Frontend: MemoryConsolidationCard

### 컴포넌트 구조

```typescript
<MemoryConsolidationCard className="..." />
```

### 3개 탭

1. **Overview 탭**
   - 총 통합 횟수
   - 절차 기억 수
   - 강화/감쇠/승격 통계
   - 마지막 통합 시간
   - 작동 원리 설명

2. **Procedural 탭**
   - 학습된 패턴 목록
   - 패턴 유형 (conversation/action/response)
   - 강도 바 시각화
   - 반복/활성화 횟수

3. **History 탭**
   - 통합 기록 목록
   - 트리거 유형 표시
   - 처리 통계 (처리/강화/감쇠/패턴)
   - 처리 시간

### 실시간 업데이트

```typescript
const logsChannel = supabase
  .channel('memory_consolidation_changes')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'memory_consolidation_logs' }, () => {
    fetchData()
  })
  .subscribe()
```

---

## 트리거 방식

| 방식 | 트리거 | 설명 |
|------|--------|------|
| `scheduled` | pg_cron 매일 새벽 3시 | 자동 일일 통합 |
| `idle` | 30분 이상 대화 없음 | 유휴 시간 활용 |
| `manual` | 사용자 버튼 클릭 | 수동 실행 |

### pg_cron 설정 (선택)

```sql
SELECT cron.schedule(
  'nightly-consolidation',
  '0 3 * * *',  -- 매일 새벽 3시
  $$
    SELECT net.http_post(
      url := 'https://extbfhoktzozgqddjcps.supabase.co/functions/v1/memory-consolidation',
      body := '{"action": "consolidate", "trigger_type": "scheduled"}'::jsonb
    );
  $$
);
```

---

## Success Criteria

- [x] 3개 DB 테이블 생성 완료
- [x] memory-consolidation Edge Function 배포 (v1)
- [x] 6개 action 구현
- [x] MemoryConsolidationCard 컴포넌트 구현
- [x] /api/memory/consolidate API 라우트 생성
- [x] 실시간 업데이트 구독

---

## Deployment Notes

**Edge Function Version**: v1 (deployed 2026-01-22)

구현된 기능:
1. `strengthenEmotionalMemories()` - 감정 기반 강화
2. `decayUnusedMemories()` - 시간 기반 감쇠
3. `promoteToProceduralMemory()` - 패턴 승격
4. `createSemanticLinks()` - 의미 연결 생성
5. `consolidateConceptRelations()` - 개념 관계 정리
6. `runFullConsolidation()` - 전체 통합 실행

---

## 뉴런/시냅스 표시 수정

### 문제
- 뉴런이 100개 이상 표시 안 됨
- 시냅스가 0개로 표시됨

### 원인
- [useBrainData.ts:73](../frontend/baby-dashboard/src/hooks/useBrainData.ts#L73): `.limit(100)` 하드코딩
- DB에는 302개 개념, 221개 관계가 있음
- 100개 뉴런 외의 개념과 연결된 시냅스는 필터링됨

### 해결
- limit 100 → 500으로 증가
- concept_relations limit 200 → 500으로 증가

---

## Future Enhancements

1. **Dream Replay**: 중요한 경험을 시뮬레이션 재생
2. **Sleep Cycles**: REM/Non-REM 수면 단계 모방
3. **Forgetting Curve**: 에빙하우스 망각 곡선 적용
4. **Emotional Tagging**: 편도체 모방 감정 태깅
5. **Schema Integration**: 새 경험을 기존 스키마에 통합

---

## References

1. Born, J., & Wilhelm, I. (2012). *System consolidation of memory during sleep*. Psychological Research.
2. Stickgold, R., & Walker, M. P. (2013). *Sleep-dependent memory triage*. Nature Neuroscience.
3. Tononi, G., & Cirelli, C. (2014). *Sleep and the price of plasticity*. Neuron.
