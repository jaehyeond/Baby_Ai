# Frontend Error Clear Guide

Baby Dashboard 프론트엔드 개발 중 발생한 문제들과 해결 방법 기록

---

## 1. React Three Fiber Canvas 크기 문제

### 문제
3D BrainVisualization 컴포넌트에서 Canvas가 매우 작게 렌더링됨 (거의 보이지 않음)

### 원인
React Three Fiber의 `<Canvas>`는 **직접적인 부모 컨테이너의 크기**를 상속받음. 부모에 명시적인 높이가 없으면 Canvas가 0 또는 매우 작은 크기로 렌더링됨.

### 해결 방법
```tsx
// ❌ 잘못된 방법 - Canvas 직접 부모에 높이 없음
<div className="...">
  <Canvas>...</Canvas>
</div>

// ✅ 올바른 방법 - Canvas 직접 부모에 명시적 높이
<div className="w-full h-[400px] md:h-[500px]">
  <Canvas camera={{ position: [0, 0, 8], fov: 60 }}>
    ...
  </Canvas>
</div>
```

### 핵심 포인트
- Canvas 바로 위 `<div>`에 `h-[값]` 또는 `h-full` 클래스 필수
- `h-full` 사용 시 모든 상위 컨테이너에도 높이 설정 필요
- 반응형: `h-[400px] md:h-[500px]` 형태로 모바일/데스크톱 구분

---

## 2. JSX 템플릿 리터럴 닫는 태그 누락

### 문제
```
Parsing ecmascript source code failed
Expression expected
```

### 원인
JSX에서 템플릿 리터럴(백틱)을 사용한 className에서 닫는 `>` 누락

### 예시
```tsx
// ❌ 잘못된 코드 - > 누락
<div className={`w-full ${canvasHeight}`}
  <Canvas>...</Canvas>
</div>

// ✅ 올바른 코드
<div className={`w-full ${canvasHeight}`}>
  <Canvas>...</Canvas>
</div>
```

### 예방 방법
- ESLint/TypeScript 자동 검사 활성화
- 저장 시 자동 포맷팅 설정
- 템플릿 리터럴 사용 후 `>` 확인

---

## 3. 브라우저 캐시로 인한 변경 미반영

### 문제
코드를 수정했는데 브라우저에서 이전 버전이 계속 표시됨

### 해결 방법
1. **Hard Refresh**: `Ctrl + Shift + R` (Windows) / `Cmd + Shift + R` (Mac)
2. **DevTools 캐시 비활성화**:
   - F12 → Network 탭 → "Disable cache" 체크
3. **개발 서버 재시작**: `npm run dev` 다시 실행

---

## 4. Supabase 테이블 TypeScript 타입 없음

### 문제
`semantic_concepts`, `experience_concepts` 등 새로 만든 테이블이 TypeScript 타입에 없음

### 해결 방법
```tsx
// 임시 해결: as any 사용 + 수동 타입 정의
interface RawConcept {
  id: string
  name: string
  category: string | null
  strength: number
  usage_count: number
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const { data: concepts, error } = await (supabase as any)
  .from('semantic_concepts')
  .select('...') as { data: RawConcept[] | null; error: Error | null }
```

### 영구 해결
```bash
# Supabase CLI로 타입 재생성
npx supabase gen types typescript --project-id [PROJECT_ID] > src/lib/database.types.ts
```

---

## 5. framer-motion 배열 인덱스 key 경고

### 문제
```
Warning: Each child in a list should have a unique "key" prop
```

### 해결 방법
```tsx
// ❌ 배열 인덱스만 사용
{[...Array(12)].map((_, i) => (
  <motion.circle key={i} ... />
))}

// ✅ 고유한 식별자 포함
{[...Array(12)].map((_, i) => (
  <motion.circle key={`neuron-${i}`} ... />
))}
```

---

## 6. Next.js 'use client' 누락

### 문제
```
useState/useEffect is not a function
```
또는
```
React hooks can only be called in Client Components
```

### 해결 방법
파일 최상단에 `'use client'` 추가

```tsx
'use client'  // ← 반드시 첫 줄에

import { useState, useEffect } from 'react'
// ...
```

---

## 7. Recharts ResponsiveContainer 높이 문제

### 문제
차트가 표시되지 않거나 매우 작게 렌더링됨

### 원인
`ResponsiveContainer`도 부모 컨테이너의 크기에 의존

### 해결 방법
```tsx
// 부모에 명시적 높이 설정
<div className="h-64">  {/* 또는 h-48, h-[300px] 등 */}
  <ResponsiveContainer width="100%" height="100%">
    <AreaChart data={data}>...</AreaChart>
  </ResponsiveContainer>
</div>
```

---

## 8. 컴포넌트 export 누락

### 문제
```
Module not found: Can't resolve '@/components'
```
또는 특정 컴포넌트 import 실패

### 해결 방법
`components/index.ts`에 export 추가

```tsx
// components/index.ts
export { BabyStateCard } from './BabyStateCard'
export { EmotionRadar } from './EmotionRadar'
export { NewComponent } from './NewComponent'  // ← 새 컴포넌트 추가
```

---

## Quick Checklist

새 컴포넌트 추가 시:
- [ ] `'use client'` 필요 여부 확인
- [ ] `components/index.ts`에 export 추가
- [ ] Canvas/Chart 사용 시 부모 컨테이너 높이 설정
- [ ] 템플릿 리터럴 사용 시 닫는 `>` 확인
- [ ] 리스트 렌더링 시 고유한 key 사용
- [ ] 브라우저 Hard Refresh로 변경 확인

---

## Phase 연동 준비 사항

### Phase 3: Emotion Engine 연동
파티클 효과가 Realtime 이벤트와 연동되도록 준비됨:

```tsx
// useEmotionParticles 훅 사용
const { triggerParticles } = useEmotionParticles()

// Supabase Realtime 이벤트 수신 시
supabase
  .channel('emotion_events')
  .on('broadcast', { event: 'emotion_change' }, (payload) => {
    triggerParticles(payload.emotion, payload.intensity)
  })
  .subscribe()
```

---

*최종 업데이트: 2025-01*
