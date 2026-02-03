# Fix Issue

Baby AI 프로젝트의 문제를 진단하고 수정합니다.

## 진단 순서

### 1. 문제 분류
- **기억 문제**: 비비가 뭔가를 기억 못함
- **대화 문제**: 응답이 이상함
- **수면 문제**: memory-consolidation 실패
- **탐색 문제**: curiosity_queue 실패율 높음
- **시각 문제**: 카메라/이미지 분석 안됨

### 2. 공통 진단 쿼리

```sql
-- 최근 오류 확인
SELECT task, output, success, created_at
FROM experiences
WHERE success = false
ORDER BY created_at DESC
LIMIT 10;

-- curiosity_queue 실패 분석
SELECT term, exploration_method, error_message, updated_at
FROM curiosity_queue
WHERE status = 'failed'
ORDER BY updated_at DESC
LIMIT 10;

-- 감정 로그 확인
SELECT dominant_emotion, trigger_task, created_at
FROM emotion_logs
ORDER BY created_at DESC
LIMIT 10;
```

### 3. Edge Function 로그
```
mcp__supabase__get_logs({ service: "edge-function" })
```

### 4. 문제별 해결책

| 문제 | 확인 사항 | 해결책 |
|------|----------|--------|
| 이름 기억 못함 | semantic_concepts에 "비비" 있는지 | conversation-process에 identity 조회 추가 |
| 대화 응답 이상 | Gemini API 키 유효한지 | .env 확인 |
| 수면 모드 안됨 | scheduled 설정 확인 | Supabase Dashboard에서 확인 |
| 탐색 실패 | LLM 지식 중복 학습 시도 | exploration_method 수정 필요 |

## CLAUDE.md 업데이트

문제 발견 시 반드시 `CLAUDE.md`의 "Known Issues & Lessons Learned" 섹션에 기록:

```markdown
### YYYY-MM-DD: [문제 제목]

**문제**: [증상]
**원인**: [근본 원인]
**해결**: [해결 방법]
```

## 관련 문서

- [CLAUDE.md](CLAUDE.md) - Known Issues 섹션
- [docs/PHASE_8_AUTONOMOUS_CURIOSITY.md](docs/PHASE_8_AUTONOMOUS_CURIOSITY.md) - 설계 재검토
