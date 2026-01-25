# Phase 9: Textual Backpropagation (텍스트 피드백 기반 학습)

**Version**: 1.0
**Created**: 2026-01-25
**Status**: ✅ Completed
**Edge Function Version**: v1

---

## Overview

Baby AI가 사용자의 텍스트 피드백을 통해 학습하는 시스템입니다.

### 핵심 개념

**일반 신경망의 Backpropagation**:
```
출력 → 손실 함수 계산 → gradient 계산 → 가중치 업데이트
```

**Textual Backpropagation**:
```
응답 → 사용자 피드백 (1-5점 + 이유) → 관련 개념/전략 강화/약화 → 행동 변화
```

### 예시

```
Baby: "강아지는 네 발로 걸어요!"
사용자: ⭐⭐⭐⭐ (4점) "맞아, 근데 강아지는 꼬리도 흔들어"

→ Backpropagation:
  1. "강아지" 개념에 "꼬리 흔듦" 속성 연결
  2. 관련 응답 전략 효과성 +0.1
  3. 해당 경험의 memory_strength +0.15
  4. 다음 "강아지" 질문 시 더 풍부한 응답
```

---

## 🚨 핵심 설계 원칙: 외부 LLM 사용 금지

Phase 7과 동일한 원칙 적용:

| ❌ 잘못된 접근 | ✅ 올바른 접근 |
|---------------|---------------|
| LLM에게 "피드백 분석해줘" 요청 | 규칙 기반 피드백 처리 |
| LLM이 개념 연결 결정 | 키워드 추출 + 벡터 유사도 |
| LLM이 강화량 결정 | 통계 기반 계산 (rating → delta) |

---

## Database Schema

### 1. response_feedback

사용자 피드백 저장

```sql
CREATE TABLE response_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 피드백 대상
    experience_id UUID REFERENCES experiences(id) ON DELETE CASCADE,

    -- 피드백 내용
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,  -- 선택적 텍스트 피드백

    -- 세부 평가 (선택)
    is_helpful BOOLEAN,
    is_accurate BOOLEAN,
    is_appropriate BOOLEAN,

    -- 메타데이터
    development_stage INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 인덱스
CREATE INDEX idx_response_feedback_experience ON response_feedback(experience_id);
CREATE INDEX idx_response_feedback_rating ON response_feedback(rating);
CREATE INDEX idx_response_feedback_created ON response_feedback(created_at DESC);
```

### 2. feedback_propagation_logs

피드백이 시스템에 미친 영향 추적

```sql
CREATE TABLE feedback_propagation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feedback_id UUID REFERENCES response_feedback(id) ON DELETE CASCADE,

    -- 전파 대상
    target_type TEXT NOT NULL,  -- concept, relation, strategy, experience
    target_id UUID,
    target_name TEXT,

    -- 변화량
    field_name TEXT NOT NULL,  -- strength, effectiveness_score, memory_strength
    value_before FLOAT,
    value_after FLOAT,
    delta FLOAT,

    -- 전파 이유
    propagation_reason TEXT,  -- direct_feedback, hebb_coactivation, similarity

    created_at TIMESTAMPTZ DEFAULT now()
);

-- 인덱스
CREATE INDEX idx_propagation_feedback ON feedback_propagation_logs(feedback_id);
CREATE INDEX idx_propagation_target ON feedback_propagation_logs(target_type, target_id);
```

### 3. 트리거: 피드백 통계 자동 업데이트

```sql
-- experiences 테이블에 피드백 통계 컬럼 추가
ALTER TABLE experiences ADD COLUMN IF NOT EXISTS
    feedback_count INT DEFAULT 0;
ALTER TABLE experiences ADD COLUMN IF NOT EXISTS
    avg_rating FLOAT;
ALTER TABLE experiences ADD COLUMN IF NOT EXISTS
    last_feedback_at TIMESTAMPTZ;

-- 피드백 삽입 시 자동 업데이트
CREATE OR REPLACE FUNCTION update_experience_feedback_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE experiences
    SET
        feedback_count = feedback_count + 1,
        avg_rating = (
            SELECT AVG(rating)::FLOAT
            FROM response_feedback
            WHERE experience_id = NEW.experience_id
        ),
        last_feedback_at = now()
    WHERE id = NEW.experience_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_experience_feedback_stats
AFTER INSERT ON response_feedback
FOR EACH ROW
EXECUTE FUNCTION update_experience_feedback_stats();
```

---

## Backpropagation 알고리즘

### 1. 피드백 수신 및 저장

```typescript
interface FeedbackInput {
  experience_id: string;
  rating: 1 | 2 | 3 | 4 | 5;
  feedback_text?: string;
  is_helpful?: boolean;
  is_accurate?: boolean;
  is_appropriate?: boolean;
}
```

### 2. Delta 계산

```typescript
function calculateDelta(rating: number): number {
  // 1점: -0.15, 2점: -0.05, 3점: 0, 4점: +0.10, 5점: +0.20
  const deltaMap: Record<number, number> = {
    1: -0.15,
    2: -0.05,
    3: 0,
    4: 0.10,
    5: 0.20
  };
  return deltaMap[rating];
}
```

### 3. 개념 강화/약화 (Concept Propagation)

```typescript
async function propagateToConcepts(
  experienceId: string,
  delta: number,
  feedbackId: string
): Promise<number> {
  // 경험과 연결된 개념들 가져오기
  const { data: links } = await supabase
    .from('experience_concepts')
    .select('concept_id, relevance')
    .eq('experience_id', experienceId);

  let propagatedCount = 0;

  for (const link of links || []) {
    // 관련도에 비례하여 delta 적용
    const adjustedDelta = delta * link.relevance;

    // 개념 strength 업데이트
    const { data: concept } = await supabase
      .from('semantic_concepts')
      .select('strength')
      .eq('id', link.concept_id)
      .single();

    const oldStrength = concept?.strength || 0.5;
    const newStrength = Math.max(0.1, Math.min(1.0, oldStrength + adjustedDelta));

    await supabase
      .from('semantic_concepts')
      .update({ strength: newStrength, updated_at: new Date().toISOString() })
      .eq('id', link.concept_id);

    // 전파 로그 기록
    await supabase.from('feedback_propagation_logs').insert({
      feedback_id: feedbackId,
      target_type: 'concept',
      target_id: link.concept_id,
      field_name: 'strength',
      value_before: oldStrength,
      value_after: newStrength,
      delta: adjustedDelta,
      propagation_reason: 'direct_feedback'
    });

    propagatedCount++;
  }

  return propagatedCount;
}
```

### 4. 전략 효과성 업데이트 (Strategy Propagation)

```typescript
async function propagateToStrategy(
  experienceId: string,
  rating: number,
  feedbackId: string
): Promise<string | null> {
  // 해당 경험의 self_evaluation 찾기
  const { data: evaluation } = await supabase
    .from('self_evaluation_logs')
    .select('strategy_used')
    .eq('experience_id', experienceId)
    .single();

  if (!evaluation?.strategy_used) return null;

  const strategyName = evaluation.strategy_used;

  // 전략 효과성 통계 업데이트
  const outcomeField = rating >= 4 ? 'success_count'
                     : rating <= 2 ? 'failure_count'
                     : 'partial_count';

  const { data: strategy } = await supabase
    .from('strategy_effectiveness')
    .select('*')
    .eq('strategy_name', strategyName)
    .single();

  if (!strategy) return null;

  const oldScore = strategy.effectiveness_score;

  // 카운트 업데이트
  await supabase
    .from('strategy_effectiveness')
    .update({
      [outcomeField]: strategy[outcomeField] + 1,
      updated_at: new Date().toISOString()
    })
    .eq('strategy_name', strategyName);

  // effectiveness_score 재계산 (트리거가 없다면 직접)
  const total = strategy.success_count + strategy.failure_count + strategy.partial_count + 1;
  const successWeight = (outcomeField === 'success_count' ? strategy.success_count + 1 : strategy.success_count);
  const partialWeight = (outcomeField === 'partial_count' ? strategy.partial_count + 1 : strategy.partial_count) * 0.5;
  const newScore = (successWeight + partialWeight) / total;

  await supabase
    .from('strategy_effectiveness')
    .update({ effectiveness_score: newScore })
    .eq('strategy_name', strategyName);

  // 전파 로그 기록
  await supabase.from('feedback_propagation_logs').insert({
    feedback_id: feedbackId,
    target_type: 'strategy',
    target_name: strategyName,
    field_name: 'effectiveness_score',
    value_before: oldScore,
    value_after: newScore,
    delta: newScore - oldScore,
    propagation_reason: 'direct_feedback'
  });

  return strategyName;
}
```

### 5. 경험 기억력 업데이트 (Memory Propagation)

```typescript
async function propagateToMemory(
  experienceId: string,
  delta: number,
  feedbackId: string
): Promise<void> {
  const { data: experience } = await supabase
    .from('experiences')
    .select('memory_strength')
    .eq('id', experienceId)
    .single();

  if (!experience) return;

  const oldStrength = experience.memory_strength || 1.0;
  // 피드백은 기억력에 1.5배 영향 (중요한 학습 순간)
  const newStrength = Math.max(0.1, Math.min(2.0, oldStrength + delta * 1.5));

  await supabase
    .from('experiences')
    .update({ memory_strength: newStrength })
    .eq('id', experienceId);

  // 전파 로그 기록
  await supabase.from('feedback_propagation_logs').insert({
    feedback_id: feedbackId,
    target_type: 'experience',
    target_id: experienceId,
    field_name: 'memory_strength',
    value_before: oldStrength,
    value_after: newStrength,
    delta: delta * 1.5,
    propagation_reason: 'direct_feedback'
  });
}
```

### 6. 텍스트 피드백에서 새 개념 추출

```typescript
async function extractConceptsFromFeedback(
  experienceId: string,
  feedbackText: string,
  feedbackId: string
): Promise<number> {
  if (!feedbackText || feedbackText.length < 5) return 0;

  // 간단한 키워드 추출 (외부 LLM 없이)
  const keywords = extractKeywords(feedbackText);

  let newConceptsLinked = 0;

  for (const keyword of keywords) {
    // 기존 개념 찾기 또는 생성
    let { data: concept } = await supabase
      .from('semantic_concepts')
      .select('id')
      .eq('name', keyword)
      .single();

    if (!concept) {
      // 새 개념 생성
      const { data: newConcept } = await supabase
        .from('semantic_concepts')
        .insert({
          name: keyword,
          category: 'feedback_derived',
          strength: 0.6,
          source: 'user_feedback'
        })
        .select('id')
        .single();

      concept = newConcept;
    }

    if (concept) {
      // 경험-개념 연결
      await supabase.from('experience_concepts').upsert({
        experience_id: experienceId,
        concept_id: concept.id,
        relevance: 0.8,  // 피드백에서 온 개념은 높은 관련도
        co_activation_count: 1
      }, { onConflict: 'experience_id,concept_id' });

      newConceptsLinked++;

      // 전파 로그
      await supabase.from('feedback_propagation_logs').insert({
        feedback_id: feedbackId,
        target_type: 'concept',
        target_id: concept.id,
        target_name: keyword,
        field_name: 'linked',
        value_before: 0,
        value_after: 1,
        delta: 1,
        propagation_reason: 'feedback_text_extraction'
      });
    }
  }

  return newConceptsLinked;
}

// 간단한 키워드 추출 (외부 LLM 없이)
function extractKeywords(text: string): string[] {
  // 한글/영문/숫자만 추출, 2글자 이상
  const words = text.match(/[가-힣a-zA-Z0-9]+/g) || [];

  // 불용어 제거
  const stopwords = new Set([
    '그리고', '하지만', '그런데', '그래서', '이것', '저것', '그것',
    '는', '은', '이', '가', '을', '를', '에', '의', '로', '으로',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
    '있어', '없어', '해요', '하세요', '거야', '이야', '야', '요'
  ]);

  return words
    .filter(w => w.length >= 2 && !stopwords.has(w.toLowerCase()))
    .slice(0, 5);  // 최대 5개
}
```

---

## Edge Function: textual-backpropagation

### 엔드포인트

```
POST /functions/v1/textual-backpropagation
```

### Actions

#### 1. submit_feedback - 피드백 제출 및 전파

```typescript
interface SubmitFeedbackRequest {
  action: 'submit_feedback';
  experience_id: string;
  rating: 1 | 2 | 3 | 4 | 5;
  feedback_text?: string;
  is_helpful?: boolean;
  is_accurate?: boolean;
  is_appropriate?: boolean;
}

interface SubmitFeedbackResponse {
  success: boolean;
  feedback_id: string;
  propagation: {
    concepts_adjusted: number;
    strategy_adjusted: string | null;
    memory_adjusted: boolean;
    new_concepts_linked: number;
  };
}
```

#### 2. get_feedback_history - 피드백 히스토리 조회

```typescript
interface GetFeedbackHistoryRequest {
  action: 'get_feedback_history';
  limit?: number;  // 기본: 20
}

interface GetFeedbackHistoryResponse {
  success: boolean;
  feedbacks: Array<{
    id: string;
    experience_id: string;
    rating: number;
    feedback_text: string | null;
    created_at: string;
    propagation_count: number;
  }>;
}
```

#### 3. get_propagation_stats - 전파 통계

```typescript
interface GetPropagationStatsRequest {
  action: 'get_propagation_stats';
}

interface GetPropagationStatsResponse {
  success: boolean;
  stats: {
    total_feedbacks: number;
    average_rating: number;
    concepts_affected: number;
    strategies_affected: number;
    total_propagations: number;
    rating_distribution: Record<number, number>;
  };
}
```

#### 4. get_impact_report - 특정 피드백의 영향 리포트

```typescript
interface GetImpactReportRequest {
  action: 'get_impact_report';
  feedback_id: string;
}

interface GetImpactReportResponse {
  success: boolean;
  feedback: {
    id: string;
    rating: number;
    feedback_text: string | null;
  };
  impacts: Array<{
    target_type: string;
    target_name: string;
    field_name: string;
    value_before: number;
    value_after: number;
    delta: number;
  }>;
}
```

---

## Frontend Components

### 1. FeedbackButtons

대화 메시지 아래 피드백 버튼

```typescript
interface FeedbackButtonsProps {
  experienceId: string;
  onFeedbackSubmit?: (rating: number) => void;
}

// 컴포넌트: 1-5 별점 + 선택적 텍스트 입력
```

### 2. TextualBackpropCard

대시보드 카드

```typescript
// 3개 탭:
// 1. Overview: 총 피드백 수, 평균 평점, 전파 통계
// 2. History: 최근 피드백 목록
// 3. Impact: 피드백이 학습에 미친 영향 시각화
```

---

## API Routes

### /api/conversation/feedback

```typescript
// POST: 피드백 제출
export async function POST(request: Request) {
  const body = await request.json();

  const response = await fetch(
    `${SUPABASE_URL}/functions/v1/textual-backpropagation`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        action: 'submit_feedback',
        ...body
      })
    }
  );

  return Response.json(await response.json());
}

// GET: 피드백 히스토리/통계
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const action = searchParams.get('action') || 'get_propagation_stats';

  // ...
}
```

---

## 학습 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                    TEXTUAL BACKPROPAGATION                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User provides feedback                                     │
│  ┌─────────────────┐                                       │
│  │ ⭐⭐⭐⭐ (4점)   │ + "꼬리도 흔들어"                    │
│  └────────┬────────┘                                       │
│           ↓                                                 │
│  ┌─────────────────────────────────────────┐               │
│  │ 1. Delta 계산: rating 4 → +0.10         │               │
│  └────────┬────────────────────────────────┘               │
│           ↓                                                 │
│  ┌─────────────────────────────────────────┐               │
│  │ 2. Concept Propagation                   │               │
│  │    - "강아지" strength +0.08            │               │
│  │    - "네 발" strength +0.06             │               │
│  └────────┬────────────────────────────────┘               │
│           ↓                                                 │
│  ┌─────────────────────────────────────────┐               │
│  │ 3. Strategy Propagation                  │               │
│  │    - "imitative" success_count +1       │               │
│  │    - effectiveness_score 0.65 → 0.68    │               │
│  └────────┬────────────────────────────────┘               │
│           ↓                                                 │
│  ┌─────────────────────────────────────────┐               │
│  │ 4. Memory Propagation                    │               │
│  │    - experience memory_strength +0.15   │               │
│  └────────┬────────────────────────────────┘               │
│           ↓                                                 │
│  ┌─────────────────────────────────────────┐               │
│  │ 5. New Concept Extraction                │               │
│  │    - "꼬리" 개념 생성 및 연결           │               │
│  │    - "강아지" ↔ "꼬리" 관계 생성        │               │
│  └─────────────────────────────────────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Success Criteria

- [x] 2개 DB 테이블 생성 (response_feedback, feedback_propagation_logs) ✅
- [x] experiences 테이블에 피드백 통계 컬럼 추가 ✅
- [x] textual-backpropagation Edge Function 배포 (v1) ✅
- [x] 4개 action 구현 (submit_feedback, get_feedback_history, get_propagation_stats, get_impact_report) ✅
- [x] FeedbackButtons 컴포넌트 구현 ✅
- [x] TextualBackpropCard 대시보드 카드 구현 ✅
- [x] /api/conversation/feedback API 라우트 생성 ✅
- [x] ConversationView에 피드백 UI 통합 (QuickFeedback) ✅

---

## Future Enhancements

1. **Confidence-based Feedback**: Baby가 먼저 자신감을 표시하고 피드백 요청
2. **Negative Feedback Learning**: 부정 피드백에서 "하지 말아야 할 것" 학습
3. **Feedback Clustering**: 유사한 피드백 패턴 자동 분류
4. **Proactive Learning**: 피드백 없이도 자체 예측 기반 학습
5. **Multi-modal Feedback**: 이미지/음성 피드백 지원

---

## References

1. Raffel, C. et al. (2019). *Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer*. arXiv:1910.10683.
2. Ouyang, L. et al. (2022). *Training language models to follow instructions with human feedback*. arXiv:2203.02155.
3. Hebb, D. O. (1949). *The Organization of Behavior*. Wiley.

---

## Deployment Notes

**Edge Function Version**: v1 (deployed 2026-01-25)

### 구현된 기능

1. `submit_feedback` - 피드백 제출 및 전파 실행
2. `get_feedback_history` - 피드백 히스토리 조회
3. `get_propagation_stats` - 전파 통계 조회
4. `get_impact_report` - 특정 피드백의 영향 리포트

### 전파 메커니즘

| 대상 | Delta 적용 방식 |
|------|----------------|
| Concept | `delta * relevance` (개념과 경험의 관련도에 비례) |
| Strategy | 평점에 따라 success/partial/failure_count +1 |
| Memory | `delta * 1.5` (피드백은 기억에 1.5배 영향) |

### Delta 값

| 평점 | Delta |
|------|-------|
| 1점 | -0.15 |
| 2점 | -0.05 |
| 3점 | 0 |
| 4점 | +0.10 |
| 5점 | +0.20 |

---

## Document History

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-25 | 구현 완료 - DB, Edge Function, Frontend |
