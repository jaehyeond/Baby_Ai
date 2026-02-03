# Session Start

Baby AI 프로젝트 작업 세션을 시작합니다.

## 세션 시작 체크리스트

### 1. 핵심 문서 확인
```
필수 읽기:
1. CLAUDE.md - 프로젝트 개요, Known Issues, 설계 원칙
2. Task.md - 현재 진행 상황, Phase 상태
```

### 2. 현재 상태 조회

```sql
-- Baby 상태
SELECT development_stage, experience_count, success_count,
       curiosity, joy, dominant_emotion, updated_at
FROM baby_state
ORDER BY updated_at DESC LIMIT 1;

-- 최근 문제 확인
SELECT term, status, exploration_method, error_message
FROM curiosity_queue
WHERE status = 'failed'
ORDER BY updated_at DESC LIMIT 5;
```

### 3. 핵심 설계 원칙 상기

```
🔑 핵심 설계 원칙:

1. "Baby"는 지식이 없다는 의미가 아님
   - LLM 지식은 그대로 활용
   - 그 위에 발달적 메커니즘 추가

2. 학습 대상 구분
   ✅ 학습해야 할 것: 사용자 고유 개념 (비비, 엄마), 감정적 경험, 자아 정체성
   ❌ 학습하면 안 됨: 일반 지식 (algorithm 등) - LLM이 이미 알고 있음

3. 수면 모드 목적
   ❌ 외부 학습
   ✅ 해마 기억 재활성화
   ✅ 시냅스 정리 (약한 연결 제거)
   ✅ 정체성 강화
```

### 4. 작업 시작

```
사용 가능한 skills:
/baby-status    - Baby AI 현재 상태
/brain-analyze  - 지식 그래프 분석
/deploy-function - Edge Function 배포
/sleep-mode     - 수면 모드 트리거
/fix-issue      - 문제 진단 및 수정
```

## 세션 종료 시

1. Task.md 업데이트 (완료된 작업 체크)
2. CLAUDE.md에 새로운 이슈 기록 (있다면)
3. 다음 세션 TODO 정리
