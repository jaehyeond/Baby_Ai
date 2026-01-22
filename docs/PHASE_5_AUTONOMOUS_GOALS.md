# Phase 5: Autonomous Goal Setting (자율 목표 설정)

**Version**: 1.0
**Created**: 2026-01-21
**Status**: Completed
**Edge Function Version**: v1

---

## Overview

Baby AI가 스스로 학습 목표를 설정하고 추구하는 능력을 부여합니다.

### 이론적 배경

**CDALNs (2025)**: Curiosity-Driven Autonomous Learning Networks
- 267% 향상된 자율 학습 성능
- 3가지 내재적 동기 유형 기반

### 3가지 호기심 유형

1. **Epistemic Curiosity (지식 탐구)**
   - "무엇을 배울까?"
   - 지식에 대한 순수한 궁금증
   - 저신뢰 개념, 미검증 예측 시 활성화

2. **Diversive Curiosity (다양성 추구)**
   - "새로운 것을 시도할까?"
   - 변화와 새로움에 대한 욕구
   - 지루함, 반복적 패턴 시 활성화

3. **Empowerment Drive (영향력 추구)**
   - "더 많은 것을 할 수 있게 될까?"
   - 능력 향상에 대한 욕구
   - 성공률 낮은 패턴, 한계 발견 시 활성화

---

## Database Schema

### 1. autonomous_goals

자율적으로 생성된 목표들을 저장합니다.

```sql
CREATE TABLE autonomous_goals (
    id UUID PRIMARY KEY,

    -- 목표 정보
    description TEXT NOT NULL,
    goal_type TEXT NOT NULL,  -- epistemic, diversive, empowerment
    domain TEXT,  -- programming, language, math, science, social, creative, physical

    -- 생성 정보
    autonomously_generated BOOLEAN DEFAULT true,
    created_by_stage INTEGER DEFAULT 0,
    trigger_reason TEXT,

    -- 우선순위 및 상태
    priority DOUBLE PRECISION DEFAULT 0.5,
    status TEXT DEFAULT 'active',  -- active, completed, abandoned, deferred

    -- 동기 점수
    epistemic_score DOUBLE PRECISION DEFAULT 0.0,
    diversive_score DOUBLE PRECISION DEFAULT 0.0,
    empowerment_score DOUBLE PRECISION DEFAULT 0.0,
    combined_motivation DOUBLE PRECISION GENERATED,  -- 3개 평균

    -- 진행 상황
    attempt_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    last_attempted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
```

### 2. goal_progress

목표 진행 상황을 추적합니다.

```sql
CREATE TABLE goal_progress (
    id UUID PRIMARY KEY,
    goal_id UUID REFERENCES autonomous_goals(id),

    attempt_number INTEGER DEFAULT 1,
    action_taken TEXT,
    outcome TEXT,  -- success, partial, failure, learning

    learning_gain DOUBLE PRECISION DEFAULT 0.0,
    insight TEXT,

    emotional_state JSONB,
    experience_id UUID REFERENCES experiences(id)
);
```

### 3. autonomy_metrics

자율성 지표 시계열 데이터입니다.

```sql
CREATE TABLE autonomy_metrics (
    id UUID PRIMARY KEY,

    -- 3가지 호기심 수준
    epistemic_curiosity DOUBLE PRECISION DEFAULT 0.5,
    diversive_curiosity DOUBLE PRECISION DEFAULT 0.5,
    empowerment_drive DOUBLE PRECISION DEFAULT 0.5,
    overall_autonomy DOUBLE PRECISION GENERATED,  -- 3개 평균

    -- 목표 통계
    active_goals_count INTEGER DEFAULT 0,
    completed_goals_count INTEGER DEFAULT 0,
    abandoned_goals_count INTEGER DEFAULT 0,

    development_stage INTEGER,
    trigger_event TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 4. goal_templates

발달 단계별 목표 생성 템플릿입니다.

```sql
CREATE TABLE goal_templates (
    id UUID PRIMARY KEY,

    name TEXT NOT NULL,
    description_template TEXT NOT NULL,
    goal_type TEXT NOT NULL,
    domain TEXT,

    -- 발달 단계 제한
    min_stage INTEGER DEFAULT 0,
    max_stage INTEGER DEFAULT 10,

    -- 기본 점수
    base_epistemic DOUBLE PRECISION,
    base_diversive DOUBLE PRECISION,
    base_empowerment DOUBLE PRECISION,

    trigger_conditions JSONB
);
```

**초기 템플릿** (12개):

| 유형 | 이름 | 설명 | 단계 |
|------|------|------|------|
| Epistemic | learn_concept | {concept}에 대해 더 배우기 | 0-10 |
| Epistemic | understand_relation | {concept1}와 {concept2}의 관계 이해 | 1-10 |
| Epistemic | explore_domain | {domain} 분야 탐구 | 2-10 |
| Epistemic | verify_prediction | 내 예측이 맞는지 확인 | 1-10 |
| Diversive | try_new_task | 새로운 유형의 작업 시도 | 1-10 |
| Diversive | explore_alternative | 다른 방법으로 {task} 해보기 | 2-10 |
| Diversive | combine_knowledge | 다른 분야의 지식 결합 | 3-10 |
| Diversive | creative_expression | 창의적인 방식으로 표현 | 2-10 |
| Empowerment | master_skill | {skill} 기술 숙달 | 2-10 |
| Empowerment | expand_capability | 새로운 능력 획득 | 1-10 |
| Empowerment | improve_efficiency | {pattern} 더 효율적으로 수행 | 2-10 |
| Empowerment | overcome_limitation | {limitation} 한계 극복 | 3-10 |

---

## Edge Function: autonomous-goals

### 엔드포인트

```
POST /functions/v1/autonomous-goals
```

### Actions

#### 1. generate - 새 목표 생성

```typescript
interface GenerateRequest {
  action: 'generate';
  development_stage: number;
  current_emotions: {
    curiosity: number;
    joy: number;
    fear: number;
    frustration: number;
    boredom: number;
    surprise: number;
  };
  trigger_context?: string;
}

interface GenerateResponse {
  success: boolean;
  goals: Goal[];
  count: number;
}
```

**목표 생성 알고리즘**:
1. 현재 발달 단계에 맞는 템플릿 조회
2. 컨텍스트 데이터 수집 (저신뢰 개념, 미탐구 도메인, 저성공률 패턴)
3. 호기심 점수 계산 (감정 상태 + 컨텍스트 가중치)
4. Gemini로 구체적 목표 생성
5. DB에 저장 및 자율성 지표 기록

#### 2. evaluate - 목표 실현 가능성 평가

```typescript
interface EvaluateRequest {
  action: 'evaluate';
  goal_id: string;
  development_stage: number;
}

interface EvaluateResponse {
  success: boolean;
  feasible: boolean;
  reason: string;
  estimated_difficulty: number;
}
```

#### 3. update_progress - 진행 상황 업데이트

```typescript
interface UpdateProgressRequest {
  action: 'update_progress';
  goal_id: string;
  outcome: 'success' | 'partial' | 'failure' | 'learning';
  insight?: string;
  experience_id?: string;
}

interface UpdateProgressResponse {
  success: boolean;
  goal_status: string;
}
```

#### 4. get_metrics - 자율성 지표 조회

```typescript
interface GetMetricsResponse {
  success: boolean;
  metrics: {
    epistemic_curiosity: number;
    diversive_curiosity: number;
    empowerment_drive: number;
    overall_autonomy: number;
    active_goals: number;
    completed_goals: number;
    goal_completion_rate: number;
  };
}
```

#### 5. get_goals - 활성 목표 목록 조회

```typescript
interface GetGoalsResponse {
  success: boolean;
  goals: Goal[];
}
```

---

## Frontend: AutonomousGoalsCard

### 컴포넌트 구조

```typescript
<AutonomousGoalsCard className="..." />
```

### 3개 탭

1. **Goals 탭**
   - 활성 목표 목록 (동기 점수 순)
   - 목표 유형별 아이콘/색상
   - 3가지 호기심 점수 바 시각화
   - 완료된 목표 요약

2. **Metrics 탭**
   - Epistemic/Diversive/Empowerment 지표 바
   - 종합 자율성 점수
   - 목표 유형 분포

3. **History 탭**
   - 최근 진행 기록
   - 결과 (성공/부분/실패/학습)
   - 얻은 인사이트

### 실시간 업데이트

```typescript
// Supabase 실시간 구독
const goalsChannel = supabase
  .channel('autonomous_goals_changes')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'autonomous_goals' }, () => {
    fetchData()
  })
  .subscribe()
```

---

## 호기심 점수 계산

```typescript
function calculateCuriosityScores(
  stage: number,
  emotions: { curiosity, boredom, joy, frustration },
  lowConfidenceConcepts: number,
  unexploredDomains: number,
  lowSuccessPatterns: number
): { epistemic, diversive, empowerment }
```

**기본 공식**:
- Epistemic = 0.3 + curiosity × 0.3 + (lowConfidenceConcepts > 5 ? 0.2 : 0)
- Diversive = 0.2 + boredom × 0.4 + (unexploredDomains > 0 ? 0.2 : 0)
- Empowerment = 0.3 + (1 - frustration) × 0.3 + (lowSuccessPatterns > 3 ? 0.2 : 0)

**발달 단계 수정자**:
- Stage < 2: epistemic × 0.8, diversive × 0.6 (기본 학습 중심)
- Stage >= 3: empowerment × 1.2 (숙달 중심)

---

## API Integration

### Next.js API Route

**`/api/goals/generate`**

```typescript
// POST - 목표 생성/업데이트/평가
export async function POST(request: NextRequest) {
  // baby_state에서 현재 감정 상태 로드
  // autonomous-goals Edge Function 호출
}

// GET - 활성 목표 조회
export async function GET() {
  // get_goals action 호출
}
```

---

## 발달 단계별 목표 능력

| 단계 | 자율 목표 생성 | 사용 가능한 템플릿 |
|------|----------------|-------------------|
| NEWBORN (0) | 제한적 | learn_concept |
| INFANT (1) | 기본 | + expand_capability, verify_prediction |
| TODDLER (2) | 확장 | + try_new_task, explore_alternative, master_skill |
| CHILD (3+) | 완전 | 모든 템플릿 |

---

## Success Criteria

- [x] 4개 DB 테이블 생성 완료
- [x] 12개 목표 템플릿 삽입
- [x] autonomous-goals Edge Function 배포 (v1)
- [x] 5개 action 구현 (generate, evaluate, update_progress, get_metrics, get_goals)
- [x] AutonomousGoalsCard 컴포넌트 구현
- [x] /api/goals/generate API 라우트 생성
- [x] 실시간 업데이트 구독

---

## Deployment Notes

**Edge Function Version**: v1 (deployed 2026-01-21)

구현된 기능:
1. `calculateCuriosityScores()` - 3가지 호기심 점수 계산
2. `generateGoals()` - LLM 기반 목표 생성
3. `evaluateGoal()` - 실현 가능성 평가
4. `updateGoalProgress()` - 진행 상황 기록
5. `getAutonomyMetrics()` - 자율성 지표 조회
6. `getTopGoals()` - 우선순위 정렬 목표 조회

헬퍼 함수 (DB):
1. `create_autonomous_goal()` - 목표 생성
2. `record_goal_progress()` - 진행 기록
3. `record_autonomy_metrics()` - 자율성 지표 기록
4. `get_top_goals()` - 상위 목표 조회

---

## Future Enhancements

1. **Goal Chaining**: 목표 간 의존성 및 순서 관리
2. **Meta-Goals**: 목표에 대한 목표 (메타인지)
3. **Social Goals**: 다른 AI와의 협력 목표
4. **Long-term Goals**: 장기적 발달 목표 추적
5. **Goal Reflection**: 목표 달성 후 회고 시스템

---

## References

1. CDALNs (2025). *Curiosity-Driven Autonomous Learning Networks*. ICAIR 2025.
2. Oudeyer, P.Y., Kaplan, F. (2007). *Intrinsic Motivation Systems for Autonomous Mental Development*. IEEE.
3. Schmidhuber, J. (2010). *Formal Theory of Creativity, Fun, and Intrinsic Motivation*. IEEE.
