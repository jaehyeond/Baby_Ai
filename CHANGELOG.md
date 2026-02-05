# CHANGELOG.md - 일별 작업 기록

> 매일 작업 내용, 성공/실패, 배운 점을 기록합니다.
> 새 세션 시작 시 이 파일을 확인하여 컨텍스트를 복구합니다.

---

## 2026-02-05

### Causal Discovery 파이프라인 활성화 ✅

**문제 발견:**
- `causal_models` 테이블이 0건 (인과관계 데이터 없음)
- `discover_causal_relation()` 함수가 정의만 되어있고 호출되지 않음
- CausalGraph UI 컴포넌트는 이미 구현되어 있었지만 데이터 없이 빈 화면

**구현 내용:**
- [x] `world_model.py`에 `extract_causal_relations_from_experience()` 함수 추가
  - 감정 기반 인과관계 추출 (`_extract_emotion_based_causality`)
  - 성공/실패 기반 인과관계 추출 (`_extract_outcome_based_causality`)
  - LLM 기반 개념 인과관계 추출 (`_extract_concept_based_causality`)
- [x] `auto_generate_from_experience()`에 causal discovery 통합
  - 경험 처리 시 자동으로 인과관계 발견
  - `causal_relations` 결과 필드 추가
- [x] `test_world_model.py` 테스트 추가
  - `test_causal_discovery()` 함수
  - DB stats에 causal_models 조회 추가

**테스트 결과:**
```
Causal Models: 3
- 질문 → 호기심 (enables, strength: 0.60)
- 학습 → 이해 (enables, strength: 0.50)
- 질문 → 이해 (enables, strength: 0.50)
```

**파일 변경 목록:**
| 파일 | 변경 |
|------|------|
| `neural/baby/world_model.py` | extract_causal_relations_from_experience() 함수 추가 |
| `scripts/test_world_model.py` | test_causal_discovery() 테스트 추가 |
| `ROADMAP.md` | Causal Discovery 파이프라인 완료 표시 |
| `CHANGELOG.md` | 작업 기록 |

**기대 효과:**
- 대화할 때마다 인과관계 자동 축적
- CausalGraph 탭에서 시각화 가능해짐
- Baby AI의 인과 추론 능력 실제 작동

---

## 2026-02-04

### 작업 내용
- [x] MD 파일 구조 정리
  - Task.md에 "현재 진행 중인 Phase" 섹션 추가
  - CHANGELOG.md 생성 (이 파일)
  - `docs/PHASE_A_PROACTIVE_QUESTIONS.md` 생성

### Phase A Day 1 완료 ✅
- [x] `pending_questions` 테이블 생성
  - 15개 컬럼: question, question_type, context, priority, status, answer 등
  - question_type: personal, preference, experience, relationship
  - status: pending, asked, answered, skipped, expired
- [x] RLS 정책 설정 (Allow all access)
- [x] Supabase Realtime 활성화 (Day 3에서 사용)
- [x] 테스트 데이터로 CRUD 검증 완료

### 마이그레이션 기록
1. `create_pending_questions_table` - 테이블 + 인덱스 + 트리거
2. `add_rls_pending_questions` - RLS + Realtime

### 배운 점 / 메모
- Task.md에 "현재 진행 중인 Phase" 섹션이 없어서 작업 추적이 어려웠음
- CHANGELOG.md로 일별 기록을 분리하면 세션 간 컨텍스트 복구가 쉬움
- 기존 `curiosity_queue`와 일관된 스타일로 테이블 설계함

### Phase A Day 2 완료 ✅
- [x] `generate-curiosity` v3 코드 분석
  - 4가지 호기심 소스: concept_gap, failure, pattern, similarity
  - 모든 호기심 → curiosity_queue → autonomous-exploration (웹 검색)
- [x] 호기심 분류 로직 설계
  - Gemini LLM으로 factual vs personal/preference/experience/relationship 분류
  - 분류 프롬프트 설계 (CLASSIFICATION_PROMPT)
- [x] `generate-curiosity` v4 배포
  - `classifyCuriosity()`: Gemini로 호기심 분류
  - `saveToPendingQuestions()`: 개인적 질문 저장
  - `curiosityToQuestion()`: 개념 → 자연스러운 질문 변환
  - 새 action: `get_pending_questions`
- [x] v4 테스트 검증
  - 30개 호기심 생성 → 29 factual + 1 experience
  - factual → curiosity_queue ✅
  - experience → pending_questions ✅

### v4 변경 요약
```
v3: 호기심 → curiosity_queue → 웹 검색
v4: 호기심 → 분류(Gemini) → factual? → curiosity_queue → 웹 검색
                           → personal? → pending_questions → 사용자에게 질문
```

### Phase A Day 3 완료 ✅
- [x] `pending_questions` 타입 추가 (`database.types.ts`)
  - Row, Insert, Update 타입 정의
  - PendingQuestion, QuestionType, QuestionStatus 헬퍼 타입
- [x] `usePendingQuestions` hook 생성 (`hooks/usePendingQuestions.ts`)
  - Supabase Realtime INSERT 이벤트 구독
  - 질문 목록 fetch (priority 정렬)
  - `markAsAsked()`, `submitAnswer()`, `skipQuestion()` 메서드
  - `newQuestionAlert` 상태로 새 질문 알림
- [x] `QuestionNotification` 컴포넌트 생성 (`components/QuestionNotification.tsx`)
  - 슬라이드-인 토스트 알림 UI
  - 질문 타입별 색상/이모지 (personal, preference, experience, relationship)
  - "답변하기" / "나중에" 버튼
  - 15초 자동 dismiss
- [x] 메인 페이지 통합 (`app/page.tsx`)
  - usePendingQuestions hook 연결
  - QuestionNotification 렌더링
  - 브라우저 알림 연동 (sendNotification)
  - window.prompt로 임시 답변 UI (Day 4에서 모달로 개선)
- [x] 빌드 테스트 통과

### Day 3 파일 변경 목록
| 파일 | 변경 |
|------|------|
| `src/lib/database.types.ts` | pending_questions 타입 추가 |
| `src/hooks/usePendingQuestions.ts` | 새 파일 생성 |
| `src/hooks/index.ts` | usePendingQuestions export 추가 |
| `src/components/QuestionNotification.tsx` | 새 파일 생성 |
| `src/components/index.ts` | QuestionNotification export 추가 |
| `src/app/page.tsx` | Realtime 구독 + 알림 UI 통합 |

### Phase A Day 4 완료 ✅
- [x] `QuestionBubble` 모달 컴포넌트 생성 (`components/QuestionBubble.tsx`)
  - Full-screen 모달 오버레이
  - Textarea로 답변 입력
  - 확신도 선택 (💯확실해요 / 👍대체로 / 🤔잘 모르겠어요)
  - Ctrl+Enter로 빠른 제출
  - "나중에 답변할게요" 스킵 옵션
- [x] 답변 → semantic_concepts 저장 로직 (`usePendingQuestions.ts`)
  - `saveAnswerAsConcept()`: 답변을 semantic_concepts 테이블에 저장
  - 질문 타입별 카테고리 매핑 (personal→user_info, preference→user_preference 등)
  - `extras`에 질문 메타데이터 저장 (source, question_id, question_text 등)
  - `learned_concept_id`로 pending_questions와 연결
- [x] `QuestionList` 컴포넌트 생성 (`components/QuestionList.tsx`)
  - 여러 질문 목록 표시 (priority 정렬)
  - 확장/축소 가능한 카드 UI
  - 첫 번째 질문에 "우선" 뱃지 표시
  - 빈 상태 UI (궁금한 게 없을 때)
- [x] 메인 페이지 통합 (`app/page.tsx`)
  - window.prompt → QuestionBubble 모달로 교체
  - "질문" 탭 추가 (pending questions 개수 뱃지)
  - QuestionList 컴포넌트 렌더링
- [x] 빌드 테스트 통과

### Day 4 파일 변경 목록
| 파일 | 변경 |
|------|------|
| `src/components/QuestionBubble.tsx` | 새 파일 생성 |
| `src/components/QuestionList.tsx` | 새 파일 생성 |
| `src/components/index.ts` | QuestionBubble, QuestionList export 추가 |
| `src/hooks/usePendingQuestions.ts` | saveAnswerAsConcept 로직 추가 |
| `src/app/page.tsx` | QuestionBubble 모달 + questions 탭 통합 |

### Day 4 핵심 변경
```
Day 3: 알림 → window.prompt → 답변 저장
Day 4: 알림 → QuestionBubble 모달 → 답변 저장 + semantic_concepts 연동
       + questions 탭에서 전체 질문 목록 관리
```

### Phase A Day 5 완료 ✅ - E2E 통합 테스트
- [x] 테스트 환경 확인
  - Supabase URL: `https://extbfhoktzozgqddjcps.supabase.co`
  - `generate-curiosity` v4 Edge Function ACTIVE
  - `pending_questions` 테이블 Realtime 활성화 확인
- [x] generate-curiosity 호출 테스트
  - 21개 호기심 생성 → 20 factual + 1 experience
  - 분류 로직 정상 동작 (Gemini 2.0 Flash)
  - factual → curiosity_queue, personal → pending_questions
- [x] pending_questions INSERT 테스트
  - 테스트 질문: "아빠가 제일 좋아하는 노래가 뭐야?" (preference, priority 0.9)
  - Realtime INSERT 이벤트 발생 확인
- [x] 답변 → semantic_concepts 저장 flow 검증
  - 답변: "아빠는 김광석의 서른 즈음에를 제일 좋아해요"
  - semantic_concepts 저장 완료 (category: user_preference)
  - pending_questions.learned_concept_id 연결 확인
  - pending_questions.status → 'answered' 전환 확인

### Day 5 E2E Flow 검증 결과
```
generate-curiosity (v4)
    ↓ Gemini 분류
    ↓ personal/preference/experience/relationship
    ↓
pending_questions INSERT
    ↓ Realtime 이벤트
    ↓
Frontend usePendingQuestions
    ↓ newQuestionAlert
    ↓
QuestionNotification → QuestionBubble
    ↓ 사용자 답변 입력
    ↓
semantic_concepts INSERT (user_preference)
    ↓
pending_questions UPDATE (answered + learned_concept_id)
```

### 테스트 데이터
| 항목 | 값 |
|------|-----|
| question_id | aab0fd73-05fc-44bf-80b6-f79bb7d6466c |
| question | 아빠가 제일 좋아하는 노래가 뭐야? |
| answer | 아빠는 김광석의 "서른 즈음에"를 제일 좋아해요 |
| concept_id | 005f02d3-7290-4c1f-8397-1fc698fd0f9b |
| concept_category | user_preference |
| concept_source | proactive_question |

### Phase A 완료 요약 🎉
**Day 1**: `pending_questions` 테이블 설계 + Realtime 활성화
**Day 2**: `generate-curiosity` v4 - Gemini 분류 로직
**Day 3**: `usePendingQuestions` hook + `QuestionNotification` 알림
**Day 4**: `QuestionBubble` 모달 + `QuestionList` + semantic_concepts 저장
**Day 5**: End-to-end 통합 테스트 완료

### 다음 단계 제안
- [ ] 실제 프론트엔드 배포 후 브라우저에서 라이브 테스트
- [ ] 추가 질문 타입 (personal, relationship) 테스트
- [ ] 질문 만료 로직 구현 (status: expired)
- [ ] 답변 품질에 따른 concept strength 조정 로직

---

## 템플릿

```markdown
## YYYY-MM-DD

### 작업 내용
- [ ] 작업 1
- [ ] 작업 2

### 성공
- 무엇이 잘 됐는지

### 실패 / 문제
- 무엇이 안 됐는지
- **원인**:
- **해결**:

### 배운 점 / 메모
- 기억해야 할 것

### 다음 세션 TODO
- [ ] 다음에 할 것
```
