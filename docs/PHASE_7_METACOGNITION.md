# Phase 7: Meta-cognition (자기 사고에 대한 사고)

**Version**: 1.1
**Created**: 2026-01-22
**Updated**: 2026-01-23
**Status**: ✅ Implementation Complete

---

## Overview

Baby AI가 자신의 사고 과정을 분석하고 학습하는 시스템입니다.

### 인간에서의 의미

- "내가 왜 이렇게 생각했지?"
- "이 방법이 효과적이었나?"
- "다음에는 다르게 해볼까?"

---

## 🚨 핵심 설계 원칙: 외부 LLM 사용 금지

### 프로젝트 철학 재확인

> **"Transformer는 '지식'을 주입하지만, 우리는 '학습하는 법'을 가르칩니다 — 감정을 가진 AI를 아기부터 키워서요."**

| | Transformer/RAG | Baby AI |
|--|----------------|---------|
| **목표** | 정보 검색/생성 | **학습 과정 자체를 이해** |
| **비유** | 백과사전 | **아이를 키우는 것** |
| **지식** | 주입된 지식 | **스스로 획득한 지식** |

### 문제점: 외부 LLM 사용 시

```
경험 발생 → GPT/Claude에게 "이 경험 분석해줘" 요청 → 분석 결과 저장
```

이것은 **"주입된 지식"**이지, Baby가 스스로 학습한 것이 아닙니다!

### 올바른 접근: Baby 자체의 내부 메커니즘

```
경험 발생 → Baby 내부 알고리즘으로 패턴 비교 → 자체 강화/약화 → 점진적 학습
```

---

## 설계 비교

| 기존 계획 (❌ 잘못됨) | 수정된 계획 (✅ Baby 내재적) |
|----------------------|---------------------------|
| LLM에게 "왜 이렇게 답했나?" 분석 요청 | **규칙 기반 자기 평가** (유사 경험 비교) |
| LLM이 전략 분류 | **통계 기반 전략 효과성** (성공률 계산) |
| LLM이 인사이트 생성 | **패턴 매칭으로 연관성 발견** |
| 비용: $15~1,500/월 | **비용: $0** (DB 연산만) |

---

## 구현 방법 (외부 LLM 없이)

### 1. 벡터 유사도 - 유사 경험 탐색

```sql
-- 현재 경험과 유사한 과거 경험 찾기
SELECT id, input, outcome,
       embedding <-> target_embedding AS distance
FROM experiences
WHERE embedding <-> target_embedding < 0.3
ORDER BY distance
LIMIT 5;
```

### 2. 통계 기반 전략 효과성

```sql
-- 전략별 성공률 계산 (실시간)
UPDATE strategy_effectiveness SET
  effectiveness_score =
    CASE WHEN (success_count + failure_count) > 0
    THEN success_count::float / (success_count + failure_count)
    ELSE 0.5 END,
  updated_at = now()
WHERE strategy_name = $1;
```

### 3. 규칙 기반 조건부 강화/약화

```sql
-- 성공 시: 관련 개념/패턴 강화
SELECT strengthen_experience_concept_link(exp_id, concept_id, 0.1);
SELECT strengthen_concept_relation(from_id, to_id, relation_type, 0.1);

-- 실패 시: 관련 개념/패턴 약화
SELECT strengthen_experience_concept_link(exp_id, concept_id, -0.05);
```

### 4. 헵의 법칙 - 연관 학습

```sql
-- "함께 활성화된 것은 함께 강해진다"
UPDATE experience_concepts
SET co_activation_count = co_activation_count + 1,
    relevance = LEAST(relevance + 0.05, 1.0)
WHERE experience_id = $1 AND concept_id = ANY($2);
```

---

## Database Schema

### 1. strategy_effectiveness

전략별 효과성 추적 (통계 기반)

```sql
CREATE TABLE strategy_effectiveness (
    strategy_name TEXT PRIMARY KEY,
    description TEXT,

    -- 통계 데이터
    success_count INT DEFAULT 0,
    failure_count INT DEFAULT 0,
    partial_count INT DEFAULT 0,

    -- 계산된 효과성 (trigger로 자동 업데이트)
    effectiveness_score FLOAT DEFAULT 0.5,

    -- 컨텍스트별 효과성
    contexts_effective JSONB DEFAULT '[]',
    contexts_ineffective JSONB DEFAULT '[]',

    -- 메타데이터
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 기본 전략 삽입
INSERT INTO strategy_effectiveness (strategy_name, description) VALUES
  ('explore', '새로운 접근법 시도'),
  ('exploit', '검증된 방법 사용'),
  ('cautious', '신중한 접근'),
  ('creative', '창의적 해결'),
  ('analytical', '분석적 접근'),
  ('imitative', '모방 학습');
```

### 2. self_evaluation_logs

자기 평가 기록 (규칙 기반)

```sql
CREATE TABLE self_evaluation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 평가 대상
    experience_id UUID REFERENCES experiences(id),

    -- 유사 경험 분석 (벡터 기반)
    similar_experiences UUID[],
    similarity_scores FLOAT[],

    -- 결과
    outcome TEXT NOT NULL,  -- success, failure, partial
    strategy_used TEXT REFERENCES strategy_effectiveness(strategy_name),

    -- 패턴 매칭 결과
    pattern_match_score FLOAT,  -- 유사 경험과의 일치도
    expected_outcome TEXT,      -- 유사 경험 기반 예측
    prediction_correct BOOLEAN, -- 예측 정확 여부

    -- 자동 조정
    concepts_strengthened UUID[],
    concepts_weakened UUID[],
    strength_delta FLOAT,

    -- 메타데이터
    development_stage INT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 3. 자동 효과성 업데이트 트리거

```sql
CREATE OR REPLACE FUNCTION update_strategy_effectiveness()
RETURNS TRIGGER AS $$
BEGIN
    -- 전략 효과성 통계 업데이트
    IF NEW.outcome = 'success' THEN
        UPDATE strategy_effectiveness
        SET success_count = success_count + 1,
            last_used_at = now(),
            updated_at = now()
        WHERE strategy_name = NEW.strategy_used;
    ELSIF NEW.outcome = 'failure' THEN
        UPDATE strategy_effectiveness
        SET failure_count = failure_count + 1,
            last_used_at = now(),
            updated_at = now()
        WHERE strategy_name = NEW.strategy_used;
    ELSE
        UPDATE strategy_effectiveness
        SET partial_count = partial_count + 1,
            last_used_at = now(),
            updated_at = now()
        WHERE strategy_name = NEW.strategy_used;
    END IF;

    -- effectiveness_score 재계산
    UPDATE strategy_effectiveness
    SET effectiveness_score =
        CASE WHEN (success_count + failure_count + partial_count) > 0
        THEN (success_count + partial_count * 0.5)::float /
             (success_count + failure_count + partial_count)
        ELSE 0.5 END
    WHERE strategy_name = NEW.strategy_used;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_strategy_effectiveness
AFTER INSERT ON self_evaluation_logs
FOR EACH ROW
EXECUTE FUNCTION update_strategy_effectiveness();
```

---

## Edge Function: self-evaluation

### 엔드포인트

```
POST /functions/v1/self-evaluation
```

### Actions

#### 1. evaluate - 경험 자기 평가

```typescript
interface EvaluateRequest {
  action: 'evaluate';
  experience_id: string;
  outcome: 'success' | 'failure' | 'partial';
}

interface EvaluateResponse {
  success: boolean;
  evaluation: {
    similar_experiences: Array<{
      id: string;
      similarity: number;
      outcome: string;
    }>;
    pattern_match_score: number;
    strategy_used: string;
    concepts_adjusted: number;
  };
}
```

#### 2. get_best_strategy - 최적 전략 추천

```typescript
interface GetBestStrategyRequest {
  action: 'get_best_strategy';
  context?: string;  // 현재 상황 설명
}

interface GetBestStrategyResponse {
  success: boolean;
  recommendations: Array<{
    strategy_name: string;
    effectiveness_score: number;
    success_rate: string;  // e.g., "75% (15/20)"
  }>;
}
```

#### 3. get_stats - 메타인지 통계

```typescript
interface GetStatsResponse {
  success: boolean;
  stats: {
    total_evaluations: number;
    strategy_usage: Record<string, number>;
    average_prediction_accuracy: number;
    most_effective_strategy: string;
    least_effective_strategy: string;
  };
}
```

---

## 알고리즘 상세

### 1. 유사 경험 기반 자기 평가

```typescript
async function evaluateExperience(experienceId: string, outcome: string) {
  // 1. 현재 경험의 임베딩 가져오기
  const experience = await getExperience(experienceId);

  // 2. 유사 경험 찾기 (벡터 검색)
  const similarExperiences = await findSimilarExperiences(
    experience.embedding,
    threshold: 0.3,
    limit: 5
  );

  // 3. 패턴 매칭 점수 계산
  const patternMatchScore = calculatePatternMatch(
    experience,
    similarExperiences
  );

  // 4. 예측 결과 비교 (유사 경험들의 outcome 분포)
  const expectedOutcome = predictOutcome(similarExperiences);
  const predictionCorrect = expectedOutcome === outcome;

  // 5. 전략 결정 (현재 경험의 특성 기반)
  const strategyUsed = inferStrategy(experience);

  // 6. 개념 강화/약화 (헵의 법칙)
  const adjustments = await adjustConceptStrengths(
    experienceId,
    outcome,
    patternMatchScore
  );

  // 7. 자기 평가 기록 저장
  return await saveEvaluationLog({
    experience_id: experienceId,
    similar_experiences: similarExperiences.map(e => e.id),
    similarity_scores: similarExperiences.map(e => e.similarity),
    outcome,
    strategy_used: strategyUsed,
    pattern_match_score: patternMatchScore,
    expected_outcome: expectedOutcome,
    prediction_correct: predictionCorrect,
    concepts_strengthened: adjustments.strengthened,
    concepts_weakened: adjustments.weakened,
    strength_delta: adjustments.delta
  });
}
```

### 2. 전략 추론 (규칙 기반)

```typescript
function inferStrategy(experience: Experience): string {
  // 규칙 기반 전략 추론 (LLM 없이)

  // 새로운 카테고리? → explore
  if (experience.is_novel_category) return 'explore';

  // 과거 성공 경험과 유사? → exploit
  if (experience.similar_success_rate > 0.7) return 'exploit';

  // 과거 실패 경험과 유사? → cautious
  if (experience.similar_failure_rate > 0.5) return 'cautious';

  // 복잡한 입력? → analytical
  if (experience.input_complexity > 0.7) return 'analytical';

  // 창의적 작업? → creative
  if (experience.task_type === 'creative') return 'creative';

  // 기본: 모방 학습
  return 'imitative';
}
```

### 3. 개념 강도 조정 (헵의 법칙)

```typescript
async function adjustConceptStrengths(
  experienceId: string,
  outcome: string,
  patternMatchScore: number
): Promise<Adjustments> {
  // 경험과 연결된 개념들 가져오기
  const concepts = await getExperienceConcepts(experienceId);

  const strengthened: string[] = [];
  const weakened: string[] = [];

  // 결과에 따른 조정량 결정
  const delta = outcome === 'success' ? 0.1
              : outcome === 'failure' ? -0.05
              : 0.02;  // partial

  // 패턴 매칭 점수로 조정량 가중
  const adjustedDelta = delta * (0.5 + patternMatchScore * 0.5);

  for (const concept of concepts) {
    if (adjustedDelta > 0) {
      await strengthenExperienceConceptLink(experienceId, concept.id, adjustedDelta);
      strengthened.push(concept.id);
    } else {
      await strengthenExperienceConceptLink(experienceId, concept.id, adjustedDelta);
      weakened.push(concept.id);
    }
  }

  return { strengthened, weakened, delta: adjustedDelta };
}
```

---

## Frontend Component: MetacognitionCard

### 컴포넌트 구조

```typescript
<MetacognitionCard className="..." />
```

### 3개 탭

1. **Strategies 탭**
   - 전략별 효과성 점수 바 차트
   - 성공/실패/부분 성공 수
   - 마지막 사용 시간

2. **Evaluations 탭**
   - 최근 자기 평가 목록
   - 유사 경험 매칭 결과
   - 예측 정확도

3. **Insights 탭**
   - 가장 효과적인 전략
   - 가장 비효과적인 전략
   - 평균 예측 정확도
   - 개선 추세

---

## 비용 비교

| 항목 | 외부 LLM 사용 (기존 계획) | 내부 메커니즘 (수정된 계획) |
|------|-------------------------|--------------------------|
| 소규모 (100 경험/일) | $1.5/월 | **$0** |
| 중규모 (1,000 경험/일) | $15/월 | **$0** |
| 대규모 (10,000 경험/일) | $150/월 | **$0** |
| 초대규모 (100,000 경험/일) | $1,500/월 | **$0** |

**추가 이점**:
- 외부 API 의존성 없음
- 더 빠른 응답 (DB 쿼리만)
- 프로젝트 철학에 부합

---

## Success Criteria

- [x] 2개 DB 테이블 생성 ✅
- [x] self-evaluation Edge Function 배포 ✅
- [x] 5개 action 구현 (evaluate, get_best_strategy, get_stats, get_evaluations, get_strategies) ✅
- [x] MetacognitionCard 컴포넌트 구현 ✅
- [x] 자동 트리거 (트리거 함수로 효과성 자동 업데이트) ✅
- [x] 실시간 업데이트 구독 ✅

---

## 구현 완료 내역

1. ✅ **DB 테이블 생성** - strategy_effectiveness, self_evaluation_logs
2. ✅ **트리거 함수** - update_strategy_effectiveness() 자동 효과성 업데이트
3. ✅ **Edge Function** - self-evaluation v1 (5개 action)
4. ✅ **Frontend** - MetacognitionCard (전략/평가/인사이트 3개 탭)
5. ✅ **API Route** - /api/metacognition

---

## References

1. Flavell, J. H. (1979). *Metacognition and cognitive monitoring*. American Psychologist.
2. Hebb, D. O. (1949). *The Organization of Behavior*. Wiley.
3. Kahneman, D. (2011). *Thinking, Fast and Slow*. Farrar, Straus and Giroux.

---

## Document History

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-22 | 초안 작성, 외부 LLM 사용 금지 원칙 확립 |
| 1.1 | 2026-01-23 | 구현 완료 - DB, Edge Function, Frontend |
