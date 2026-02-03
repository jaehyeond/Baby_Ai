# Sleep Mode (Memory Consolidation)

Baby AI의 수면 모드 - 기억 통합을 수동으로 트리거합니다.

## 핵심 원칙 (v7 설계)

```
❌ 외부 학습 (web_search로 새 지식 습득)
✅ 해마 기억 재활성화 (오늘 경험 재생)
✅ 시냅스 정리 (약한 연결 제거)
✅ 정체성 강화 (비비 개념 강화)
```

## 수동 트리거

### Option 1: Edge Function 직접 호출
```bash
curl -X POST https://[PROJECT_ID].supabase.co/functions/v1/memory-consolidation \
  -H "Authorization: Bearer [ANON_KEY]" \
  -H "Content-Type: application/json" \
  -d '{"manual": true}'
```

### Option 2: SQL RPC 호출
```sql
-- 기억 강화 (emotional_salience > 0.3)
UPDATE experiences
SET memory_strength = LEAST(1.0, memory_strength + 0.1)
WHERE emotional_salience > 0.3
  AND created_at > NOW() - INTERVAL '24 hours';

-- 기억 감쇠 (1일 이상 미접근)
UPDATE semantic_concepts
SET strength = GREATEST(0.1, strength - 0.05)
WHERE updated_at < NOW() - INTERVAL '1 day'
  AND strength > 0.3;

-- 정체성 개념 강화
UPDATE semantic_concepts
SET strength = LEAST(1.0, strength + 0.02)
WHERE category IN ('이름', '정체성', 'identity', 'self')
  OR name ILIKE '%비비%';
```

## 현재 Edge Function 버전

- `memory-consolidation` v6
- 30분마다 scheduled 실행
- 강화 + 감쇠 + 패턴 승격

## 로그 확인

```
mcp__supabase__get_logs({ service: "edge-function" })
```

## 결과 형식

```json
{
  "success": true,
  "memories_strengthened": 15,
  "memories_decayed": 8,
  "patterns_promoted": 2,
  "identity_reinforced": true,
  "curiosities_explored": 0
}
```

## 관련 문서

- [docs/PHASE_6_MEMORY_CONSOLIDATION.md](docs/PHASE_6_MEMORY_CONSOLIDATION.md)
- [docs/PHASE_8_AUTONOMOUS_CURIOSITY.md](docs/PHASE_8_AUTONOMOUS_CURIOSITY.md)
