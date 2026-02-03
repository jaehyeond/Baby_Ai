# Phase A: 비비의 능동적 질문 시스템

**시작일**: 2026-02-04
**상태**: 🔄 진행 중
**예상 기간**: 5일

---

## 1. 개요

### 1.1 문제 정의

현재 Baby AI(비비)의 호기심 시스템은:
- `generate-curiosity` → 호기심 생성
- `autonomous-exploration` → 웹 검색으로 학습

**문제**: 모든 호기심을 "웹 검색"으로 해결하려 함
- "엄마가 좋아하는 색깔은?" → 웹 검색 불가
- "우리 집 강아지 이름은?" → 웹 검색 불가
- 이런 질문들은 **사용자에게 직접 물어봐야 함**

### 1.2 해결책

호기심을 **두 가지 유형**으로 분류:

| 유형 | 예시 | 해결 방법 |
|------|------|----------|
| **사실적 지식** | "태양계 행성 개수", "Python 문법" | 웹 검색 (기존 방식) |
| **개인/관계/경험** | "엄마 좋아하는 색", "내 생일" | 사용자에게 질문 |

### 1.3 기대 효과

1. **진정한 상호작용**: 비비가 먼저 질문 → 대화 주도
2. **개인화된 학습**: 사용자 고유 정보 학습 가능
3. **관계 형성**: "나에 대해 궁금해하는 AI" 경험

---

## 2. 아키텍처

### 2.1 데이터 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    PROACTIVE QUESTION FLOW                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [generate-curiosity v4]                                    │
│         ↓                                                   │
│  ┌─────────────────────────────────────┐                   │
│  │ Curiosity Classification            │                   │
│  │ (Gemini LLM)                        │                   │
│  │                                     │                   │
│  │ "엄마가 좋아하는 색깔은?"            │                   │
│  │  → type: "personal"                 │                   │
│  │  → target: "user"                   │                   │
│  └─────────────────────────────────────┘                   │
│         ↓                                                   │
│  ┌───────────────┬───────────────────┐                     │
│  │ type=factual  │ type=personal     │                     │
│  │      ↓        │       ↓           │                     │
│  │ curiosity_    │ pending_          │                     │
│  │ queue         │ questions         │ ← NEW TABLE         │
│  │      ↓        │       ↓           │                     │
│  │ autonomous-   │ Supabase          │                     │
│  │ exploration   │ Realtime          │                     │
│  │      ↓        │       ↓           │                     │
│  │ 웹 검색       │ Frontend UI       │                     │
│  └───────────────┴───────────────────┘                     │
│                          ↓                                  │
│                  ┌───────────────────┐                     │
│                  │ QuestionBubble    │                     │
│                  │ Component         │                     │
│                  │                   │                     │
│                  │ "비비가 궁금해요: │                     │
│                  │  엄마가 좋아하는  │                     │
│                  │  색깔이 뭐예요?"  │                     │
│                  └───────────────────┘                     │
│                          ↓                                  │
│                  사용자 응답                                │
│                          ↓                                  │
│                  semantic_concepts에 저장                   │
│                  (category: 'family', 'preference')         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 새 테이블: `pending_questions`

```sql
CREATE TABLE pending_questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question TEXT NOT NULL,
  question_type VARCHAR(50) NOT NULL,  -- 'personal', 'preference', 'experience', 'relationship'
  context TEXT,                         -- 왜 이 질문을 하게 됐는지
  priority FLOAT DEFAULT 0.5,          -- 0.0 ~ 1.0
  source_curiosity_id UUID,            -- 원래 호기심 ID (있으면)
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'asked', 'answered', 'skipped'
  answer TEXT,                          -- 사용자 응답
  created_at TIMESTAMPTZ DEFAULT NOW(),
  asked_at TIMESTAMPTZ,
  answered_at TIMESTAMPTZ
);

-- 인덱스
CREATE INDEX idx_pending_questions_status ON pending_questions(status);
CREATE INDEX idx_pending_questions_priority ON pending_questions(priority DESC);
```

### 2.3 호기심 분류 프롬프트

```typescript
const CLASSIFICATION_PROMPT = `
당신은 Baby AI의 호기심을 분류하는 시스템입니다.

호기심을 다음 중 하나로 분류하세요:

1. factual: 객관적 사실, 일반 지식 (웹 검색으로 해결 가능)
   예: "태양계에 행성이 몇 개야?", "Python에서 리스트 정렬하는 방법"

2. personal: 사용자나 가족에 대한 개인 정보
   예: "엄마 생일이 언제야?", "우리 집 강아지 이름은?"

3. preference: 사용자의 취향, 선호도
   예: "엄마가 좋아하는 색깔은?", "아빠가 좋아하는 음식은?"

4. experience: 과거 경험, 추억
   예: "우리 처음 만난 날 기억나?", "어제 뭐 했어?"

5. relationship: 관계, 감정
   예: "엄마는 나를 어떻게 생각해?", "우리 사이는 어때?"

호기심: "{curiosity}"

JSON 형식으로 응답하세요:
{
  "type": "factual" | "personal" | "preference" | "experience" | "relationship",
  "confidence": 0.0-1.0,
  "reasoning": "분류 이유"
}
`;
```

---

## 3. 구현 계획

### Day 1: 데이터베이스 (2026-02-04)

- [ ] `pending_questions` 테이블 생성
- [ ] RLS 정책 설정
- [ ] 테스트 데이터 삽입

### Day 2: generate-curiosity v4 (2026-02-05)

- [ ] 호기심 분류 로직 추가
- [ ] factual → curiosity_queue (기존)
- [ ] personal/preference/experience/relationship → pending_questions
- [ ] Edge Function 배포

### Day 3: Supabase Realtime (2026-02-06)

- [ ] `pending_questions` INSERT 이벤트 구독
- [ ] Frontend에서 Realtime 연결
- [ ] 새 질문 도착 시 알림

### Day 4: UI 컴포넌트 (2026-02-07)

- [ ] `QuestionBubble` 컴포넌트 생성
- [ ] 질문 표시 UI
- [ ] 응답 입력 UI
- [ ] 응답 저장 로직

### Day 5: 통합 테스트 (2026-02-08)

- [ ] End-to-end 흐름 테스트
- [ ] 에러 처리 검증
- [ ] 성능 확인

---

## 4. 파일 변경 목록

| 파일 | 변경 내용 |
|------|----------|
| `supabase/migrations/` | `pending_questions` 테이블 마이그레이션 |
| `supabase/functions/generate-curiosity/index.ts` | 호기심 분류 로직 추가 |
| `frontend/src/hooks/usePendingQuestions.ts` | 새 hook 생성 |
| `frontend/src/components/QuestionBubble.tsx` | 새 컴포넌트 생성 |
| `frontend/src/app/page.tsx` | QuestionBubble 통합 |

---

## 5. 테스트 시나리오

### 5.1 호기심 분류 테스트

| 입력 | 예상 분류 |
|------|----------|
| "Python에서 딕셔너리 사용법" | factual |
| "엄마 생일이 언제야?" | personal |
| "아빠가 좋아하는 음식은?" | preference |
| "어제 뭐 했어?" | experience |
| "엄마는 나를 어떻게 생각해?" | relationship |

### 5.2 E2E 테스트

1. 대화 중 "엄마"에 대한 호기심 발생
2. `generate-curiosity` 호출
3. 분류 결과: "preference"
4. `pending_questions`에 저장
5. Realtime으로 Frontend에 푸시
6. QuestionBubble 표시
7. 사용자 응답 입력
8. `semantic_concepts`에 저장

---

## 6. 롤백 계획

문제 발생 시:
1. `generate-curiosity`를 v3로 롤백
2. `pending_questions` 테이블은 유지 (데이터 보존)
3. Frontend에서 QuestionBubble 숨김

---

## 7. 관련 문서

- [PHASE_8_AUTONOMOUS_CURIOSITY.md](PHASE_8_AUTONOMOUS_CURIOSITY.md) - 기존 호기심 시스템
- [Task.md](../Task.md) - 작업 추적
- [CLAUDE.md](../CLAUDE.md) - Known Issues

---

## 8. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-02-04 | 초안 작성 |
