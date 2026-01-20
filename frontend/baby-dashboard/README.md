# Baby AI Dashboard

**Baby AI** 모니터링 대시보드 - 실시간 AI 상태, 감정, 뇌 구조 시각화

## 기술 스택

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Animation**: Framer Motion
- **3D**: React Three Fiber + Three.js
- **Database**: Supabase (실시간 구독)
- **Charts**: Recharts
- **PWA**: next-pwa

## 주요 기능

### 메인 대시보드 (`/`)
- BabyStateCard: AI 상태 (발달 단계, 성격 특성 등)
- EmotionRadar: 감정 상태 레이더 차트
- ActivityLog: 최근 활동 로그
- GrowthChart: 성장 추이 차트
- EmotionTimeline: 감정 변화 타임라인
- BrainCard: 뉴런 네트워크 미리보기
- MilestoneTimeline: 마일스톤 달성 타임라인
- WorldModelCard: World Model 상태

### 뇌 시각화 (`/brain`)
- 3D 뉴런 네트워크 시각화
- 카테고리별 색상 구분
- 시냅스 연결 표시
- 인터랙티브 줌/회전

### World Model (`/imagination`)
- 예측 카드 (PredictionCard)
- 상상 시각화 (ImaginationVisualizer)
- 인과관계 그래프 (CausalGraph)
- 시뮬레이션 목록

### 설정 (`/settings`)
- 알림 설정
- 데이터 표시 개수 설정
- 알림 권한 관리

## 실행 방법

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 빌드
npm run build

# 프로덕션 실행
npm start
```

## 환경 변수

`.env.local` 파일 생성:
```env
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

## 디렉토리 구조

```
src/
├── app/
│   ├── page.tsx           # 메인 대시보드
│   ├── brain/page.tsx     # 뇌 3D 시각화
│   ├── imagination/page.tsx # World Model 페이지
│   ├── settings/page.tsx  # 설정
│   └── globals.css
├── components/
│   ├── BabyStateCard.tsx
│   ├── EmotionRadar.tsx
│   ├── ActivityLog.tsx
│   ├── GrowthChart.tsx
│   ├── EmotionTimeline.tsx
│   ├── BrainVisualization.tsx  # 3D 뇌 (Three.js)
│   ├── BrainCard.tsx
│   ├── MilestoneTimeline.tsx
│   ├── WorldModelCard.tsx
│   ├── PredictionCard.tsx
│   ├── ImaginationVisualizer.tsx
│   ├── CausalGraph.tsx
│   └── ...
├── hooks/
│   ├── useBrainData.ts
│   ├── useMilestones.ts
│   ├── useWorldModel.ts
│   ├── useSettings.ts
│   ├── useNotifications.ts
│   └── usePullToRefresh.ts
└── lib/
    ├── supabase.ts
    └── database.types.ts
```

## 최근 업데이트 (2025-01-20)

### Phase 2 완료
- BrainVisualization: 3D 뉴런 네트워크 시각화 추가
- BrainCard: 뇌 구조 미리보기 카드
- WorldModelCard: World Model 상태 카드
- PredictionCard: 예측 시각화
- ImaginationVisualizer: 상상 시각화
- CausalGraph: 인과관계 그래프
- `/brain` 페이지: 전체 화면 뇌 시각화
- `/imagination` 페이지: World Model 상세
- Hydration 에러 수정 (mounted 패턴 적용)
