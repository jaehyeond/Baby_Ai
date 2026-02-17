# Session Start - Baby AI 프로젝트

새 세션을 시작합니다. 아래 단계를 **순서대로 실행**하세요.

## Step 1: 핵심 문서 읽기 (병렬)

다음 2개 파일을 **동시에** 읽으세요:
1. `Task.md` - Source of Truth (EF 버전, DB 통계, Phase 상태, 논문 상태)
2. `CHANGELOG.md` - **최상단 날짜 기록만** (offset 0, limit 50)

## Step 2: DB 실시간 상태 조회

Supabase에서 현재 Baby 상태를 조회하세요:

```sql
-- Baby 현재 상태
SELECT development_stage, experience_count, success_count,
       curiosity, joy, fear, frustration, boredom,
       dominant_emotion, updated_at
FROM baby_state LIMIT 1;
```

## Step 3: 상태 요약 보고

읽은 문서와 DB 조회 결과를 기반으로 사용자에게 **간결하게** 보고:

```
📊 Baby AI 세션 시작 보고
━━━━━━━━━━━━━━━━━━━━━━
🧠 발달 단계: Stage X (이름)
💭 감정: dominant_emotion (수치)
📝 마지막 작업: CHANGELOG 최신 날짜 + 요약
🔧 최신 EF: conversation-process vXX
📄 논문: Task.md 논문 섹션 요약
⏭️ 다음 단계: ROADMAP 기준 다음 Phase
━━━━━━━━━━━━━━━━━━━━━━
```

## Step 4: 사용자 지시 대기

보고 후 사용자의 작업 지시를 기다리세요.
- 작업 지시가 특정 영역이면 해당 문서 추가 확인 (ROADMAP, SQL_task 등)
- 논문 관련이면 `docs/PAPER_PLAN.md` Section 9 확인

## 주의사항

- **이미 완료된 Phase를 다시 구현하지 마세요** - Task.md "✅ 완료된 Phase" 확인
- **conversation-process 수정 시** 현재 버전 확인 필수 (CHANGELOG 최신 기록)
- **새 기능 추가 시** "정의만 되고 호출 안 됨" 패턴 방지 - 반드시 호출 지점 확인
- **DB 스키마 변경 시** SQL_task.md 확인 (현재 스키마 버전)
