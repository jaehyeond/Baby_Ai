# Sleep Page Navigation Issue - Troubleshooting Record

## Issue Date
2026-01-23

## Problem Summary
`/sleep` 페이지의 뒤로가기 버튼(←)이 클릭해도 메인 페이지(`/`)로 이동하지 않는 문제

## Root Causes Identified

### 1. Duplicate Supabase Client (Primary Issue)
**증상:**
- 브라우저 콘솔에 `Multiple GoTrueClient instances detected` 경고
- WebSocket 연결 실패 다수 발생
- JavaScript 실행 환경 불안정

**원인:**
`MemoryConsolidationCard.tsx`에서 자체적으로 Supabase 클라이언트를 생성함:
```tsx
// 잘못된 코드
import { createClient } from '@supabase/supabase-js'
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
```

이미 `@/lib/supabase.ts`에서 싱글톤 클라이언트가 존재하는데 중복 생성함.

**해결:**
```tsx
// 수정된 코드
import { supabase } from '@/lib/supabase'
// 공유 클라이언트 사용
```

### 2. Next.js Link Component Navigation Issue
**증상:**
- `<Link href="/">` 컴포넌트가 클릭 이벤트를 제대로 처리하지 않음
- `cursor-pointer`, `z-10` 추가해도 해결 안됨

**시도한 해결책:**
1. Link + 스타일 추가 → 실패
2. `useRouter().push('/')` → 실패
3. `window.location.href = '/'` → 성공

**최종 해결:**
```tsx
<button
  type="button"
  onClick={() => {
    console.log('[SleepPage] Back button clicked')
    window.location.href = '/'
  }}
  className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 active:scale-95 transition-all touch-manipulation cursor-pointer"
  aria-label="메인 페이지로 돌아가기"
>
  <ArrowLeft className="w-5 h-5 text-slate-400" />
</button>
```

## Why `window.location.href` Worked

### Next.js App Router의 클라이언트 사이드 네비게이션 문제
1. **Link 컴포넌트**: prefetch와 클라이언트 사이드 라우팅에 의존
2. **useRouter.push()**: 내부적으로 History API 사용, 상태 관리 필요
3. **window.location.href**: 브라우저 네이티브 네비게이션, 가장 확실함

Supabase 클라이언트 중복으로 인한 JavaScript 런타임 불안정 상태에서는 Next.js의 복잡한 클라이언트 사이드 라우팅이 제대로 작동하지 않았을 가능성이 높음.

## TypeScript 타입 이슈

**문제:**
`memory_consolidation_logs`, `procedural_memory` 테이블이 `Database` 타입에 정의되지 않음

**에러:**
```
Argument of type '"memory_consolidation_logs"' is not assignable to parameter of type...
```

**해결:**
타입 어설션으로 우회:
```tsx
const supabaseAny = supabase as unknown as {
  from: (table: string) => {
    select: (columns: string) => {
      order: (column: string, options: { ascending: boolean }) => {
        limit: (count: number) => Promise<{ data: unknown[] | null; error: unknown }>
      }
    }
  }
}

const [logsRes, procRes] = await Promise.all([
  supabaseAny.from('memory_consolidation_logs').select('*')...
])
```

## Files Modified

| File | Changes |
|------|---------|
| `src/app/sleep/page.tsx` | Link → button with `window.location.href` |
| `src/components/MemoryConsolidationCard.tsx` | 중복 Supabase 클라이언트 제거, 타입 어설션 추가 |

## Lessons Learned

1. **싱글톤 패턴 준수**: Supabase 같은 클라이언트는 반드시 하나의 인스턴스만 사용
2. **네비게이션 문제 디버깅**: console.log로 클릭 이벤트 도달 여부 먼저 확인
3. **폴백 전략**: Next.js 라우팅 실패 시 `window.location.href`가 가장 확실한 대안
4. **타입 안전성 vs 실용성**: Database 타입에 없는 테이블은 타입 어설션으로 처리 (나중에 타입 업데이트 필요)

## Prevention

- [ ] `@/lib/supabase`에서만 클라이언트 import하도록 ESLint 규칙 추가 고려
- [ ] Database 타입에 `memory_consolidation_logs`, `procedural_memory` 테이블 추가
- [ ] 새 페이지 생성 시 네비게이션 테스트 체크리스트 추가
