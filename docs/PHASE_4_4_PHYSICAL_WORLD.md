# Phase 4.4: Physical World Understanding

**Version**: 1.0
**Created**: 2026-01-21
**Status**: ✅ Completed
**Edge Function Version**: v1

---

## Overview

Baby AI가 물리 세계를 이해하고 추론하는 능력을 부여합니다.

### 핵심 개념

1. **객체 영속성 (Object Permanence)**
   - 객체가 시야에서 사라져도 존재한다는 것을 학습
   - 피아제(Piaget) 발달 이론 기반
   - 영아 8-12개월에 발달하는 핵심 인지 능력

2. **공간 관계 이해 (Spatial Relations)**
   - 객체들 간의 위치 관계 분석
   - 위(on), 아래(under), 안(in), 밖(outside), 근처(near) 등
   - 자기 중심적 참조 프레임 지원

3. **물리 직관 (Intuitive Physics)**
   - 중력, 지지, 연속성 등 기본 물리 원리 학습
   - Elizabeth Spelke의 Core Knowledge 이론 기반

---

## Database Schema

### 1. physical_objects

인식된 물리적 객체들을 저장합니다.

```sql
CREATE TABLE physical_objects (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,  -- person, animal, furniture, toy, food, vehicle, nature, tool

    -- 시각적 특성
    visual_features JSONB,  -- {color, shape, size, texture}
    typical_size TEXT,  -- tiny, small, medium, large, huge

    -- 물리적 속성
    physical_properties JSONB,  -- {solid, heavy, soft, ...}
    can_move BOOLEAN,
    is_animate BOOLEAN,

    -- 객체 영속성
    permanence_learned BOOLEAN,
    times_disappeared INTEGER,
    times_reappeared INTEGER,

    -- 친숙도
    familiarity DOUBLE PRECISION,  -- 0.0 ~ 1.0
    interaction_count INTEGER
);
```

### 2. spatial_relations

객체들 간의 공간 관계를 저장합니다.

```sql
CREATE TABLE spatial_relations (
    id UUID PRIMARY KEY,
    subject_object_id UUID REFERENCES physical_objects(id),
    reference_object_id UUID REFERENCES physical_objects(id),

    relation_type TEXT,  -- on, in, under, above, below, near, far, inside, outside
    relation_description TEXT,  -- "공이 책상 위에 있다"
    estimated_distance TEXT,  -- touching, very_close, close, medium, far

    is_current BOOLEAN,  -- 현재 유효한 관계인지
    confidence DOUBLE PRECISION
);
```

### 3. physics_intuitions

학습된 물리 직관을 저장합니다.

```sql
CREATE TABLE physics_intuitions (
    id UUID PRIMARY KEY,
    principle_name TEXT,  -- gravity, support, containment, occlusion, ...
    principle_type TEXT,  -- core_knowledge (선천적) / learned (학습됨)

    understanding_level TEXT,  -- none, implicit, developing, stable, explicit
    confidence DOUBLE PRECISION,

    predictions_made INTEGER,
    predictions_correct INTEGER,
    prediction_accuracy DOUBLE PRECISION GENERATED
);
```

**초기 물리 원리** (8개):
| 원리 | 유형 | 설명 | 습득 단계 |
|------|------|------|----------|
| solidity | core_knowledge | 고체는 서로 통과 불가 | 0 |
| continuity | core_knowledge | 연속적 이동 | 0 |
| gravity | learned | 지지 없으면 낙하 | 1 |
| support | learned | 위에 있으려면 지지 필요 | 1 |
| containment | learned | 물체가 담길 수 있음 | 2 |
| occlusion | learned | 가려져도 존재 (영속성) | 2 |
| inertia | learned | 관성 | 3 |
| collision | learned | 충돌 시 방향 변화 | 3 |

### 4. object_tracking_events

객체 추적 이벤트를 저장합니다 (영속성 학습용).

```sql
CREATE TABLE object_tracking_events (
    id UUID PRIMARY KEY,
    object_id UUID REFERENCES physical_objects(id),

    event_type TEXT,  -- appeared, disappeared, reappeared, moved, transformed
    location_before JSONB,
    location_after JSONB,

    surprise_level DOUBLE PRECISION,  -- 예측 오차
    permanence_belief_before DOUBLE PRECISION,
    permanence_belief_after DOUBLE PRECISION
);
```

---

## Edge Function: world-understanding

### 엔드포인트

```
POST /functions/v1/world-understanding
```

### 요청 파라미터

```typescript
interface WorldUnderstandingRequest {
  image_data?: string;          // Base64 이미지
  mime_type?: string;           // image/jpeg 등
  visual_experience_id?: string; // 연결된 시각 경험 ID
  objects_detected?: Array<{    // 감지된 객체들
    name: string;
    category: string;
    confidence: number;
  }>;
  previous_objects?: PhysicalObject[];  // 이전 프레임 객체들
  development_stage?: number;   // 발달 단계
  action?: 'analyze' | 'track_objects' | 'get_spatial_relations' | 'check_permanence';
}
```

### 응답

```typescript
interface WorldUnderstandingResponse {
  success: boolean;
  physical_objects?: PhysicalObject[];
  spatial_relations?: SpatialRelation[];
  tracking_events?: ObjectTrackingEvent[];
  physics_insights?: Array<{
    principle: string;
    observation: string;
    confidence: number;
  }>;
  emotional_response?: {
    curiosity_change: number;
    joy_change: number;
    surprise_change: number;
  };
}
```

### 처리 흐름

1. **물리적 속성 분석** (Gemini Vision)
   - 각 객체의 크기, 색상, 질감, 무게 추정
   - 움직임 가능 여부, 생물 여부 판단

2. **공간 관계 분석** (Gemini Vision)
   - 객체들 간의 위치 관계 추출
   - 거리 추정 (touching, close, far 등)

3. **물리 원리 관찰**
   - 발달 단계에 따라 관찰 가능한 원리 제한
   - Stage 0+: solidity, continuity
   - Stage 1+: gravity, support
   - Stage 2+: containment, occlusion

4. **객체 추적**
   - 이전 프레임과 비교하여 appeared/disappeared 감지
   - 영속성 믿음 업데이트

---

## Frontend: PhysicalWorldCard

### 컴포넌트 구조

```typescript
<PhysicalWorldCard className="..." />
```

### 3개 탭

1. **Objects 탭**
   - 인식된 객체 목록 (카테고리 아이콘)
   - 친숙도 바 시각화
   - 영속성 학습 여부 표시
   - 최근 공간 관계 목록

2. **Physics 탭**
   - 8개 물리 원리 카드
   - 이해 수준 배지 (none/implicit/developing/stable)
   - 신뢰도 바
   - 예측 정확도 표시

3. **Permanence 탭**
   - 영속성 학습된 객체 수
   - 이해율 퍼센티지
   - 최근 객체 추적 이벤트 (appeared/disappeared/reappeared)
   - 설명 카드

### 실시간 업데이트

```typescript
// Supabase 실시간 구독
const objectsChannel = supabase
  .channel('physical_objects_changes')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'physical_objects' }, () => {
    fetchData()
  })
  .subscribe()
```

---

## API Integration

### vision/process → world-understanding 연결

`/api/vision/process`에서 이미지 처리 후 자동으로 `world-understanding` 호출:

```typescript
// Phase 4.4: Call world-understanding for physical world analysis
if (enable_world_understanding && data.visual_experience) {
  const worldResponse = await fetch(`${SUPABASE_URL}/functions/v1/world-understanding`, {
    body: JSON.stringify({
      image_data: image,
      visual_experience_id: data.visual_experience.id,
      objects_detected: data.visual_experience.objects_detected,
      development_stage: data.visual_experience.development_stage,
      action: 'analyze',
    }),
  })

  data.world_understanding = worldData
}
```

---

## 발달 단계별 능력

| 단계 | 객체 영속성 | 공간 관계 | 물리 직관 |
|------|-------------|-----------|-----------|
| NEWBORN (0) | 없음 | 기본 | solidity, continuity |
| INFANT (1) | 부분적 | 간단한 관계 | + gravity, support |
| TODDLER (2) | 발달 중 | 복잡한 관계 | + containment, occlusion |
| CHILD (3+) | 완전 | 추상적 관계 | + inertia, collision |

---

## Success Criteria

- [x] 4개 DB 테이블 생성 완료
- [x] world-understanding Edge Function 배포 (v1)
- [x] PhysicalWorldCard 컴포넌트 구현
- [x] vision-process → world-understanding 통합
- [x] 실시간 업데이트 구독
- [x] 8개 물리 원리 초기 데이터 삽입

---

## Deployment Notes

**Edge Function Version**: v1 (deployed 2026-01-21)

구현된 기능:
1. `analyzePhysicalProperties()` - 물리적 속성 분석
2. `analyzeSpatialRelations()` - 공간 관계 분석
3. `detectPhysicsInScene()` - 물리 원리 관찰
4. `trackObjects()` - 객체 추적 (appeared/disappeared)
5. `savePhysicalObjects()` - DB 저장 + 친숙도 업데이트
6. `updatePhysicsIntuitions()` - 물리 직관 학습
7. `update_object_familiarity()` - 친숙도 헬퍼 함수
8. `update_permanence_belief()` - 영속성 믿음 헬퍼 함수

---

## Future Enhancements

1. **A-not-B 테스트**: 고전적인 객체 영속성 실험 구현
2. **시공간 연속성 추적**: 객체의 연속적 이동 경로 추적
3. **인과 관계 학습**: 물리적 상호작용에서 인과관계 추출
4. **물리 시뮬레이션**: 간단한 물리 예측 시뮬레이션
