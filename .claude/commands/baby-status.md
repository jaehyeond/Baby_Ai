# Baby AI Status Check

Baby AI의 현재 상태를 조회합니다.

## 실행 순서

1. **Supabase에서 baby_state 조회**
   - development_stage, experience_count, success_count
   - 감정 상태 (curiosity, joy, fear, surprise, frustration, boredom)

2. **semantic_concepts 통계 조회**
   - 총 개념 수
   - 카테고리별 분포
   - 가장 강한 개념 TOP 5

3. **최근 experiences 조회**
   - 최근 24시간 경험 수
   - 성공률

4. **curiosity_queue 상태**
   - pending, exploring, learned, failed 각 개수

## MCP 도구 사용

```sql
-- baby_state 조회
SELECT * FROM baby_state ORDER BY updated_at DESC LIMIT 1;

-- semantic_concepts 통계
SELECT category, COUNT(*) as count, AVG(strength) as avg_strength
FROM semantic_concepts
GROUP BY category
ORDER BY count DESC;

-- 강한 개념 TOP 5
SELECT name, category, strength, usage_count
FROM semantic_concepts
ORDER BY strength DESC
LIMIT 5;

-- 최근 24시간 경험
SELECT COUNT(*) as total,
       SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count
FROM experiences
WHERE created_at > NOW() - INTERVAL '24 hours';

-- curiosity_queue 상태
SELECT status, COUNT(*) as count
FROM curiosity_queue
GROUP BY status;
```

## 결과 형식

```
🧒 Baby AI Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━
발달 단계: [STAGE] (경험 [N]회)
성공률: [X]%

💭 감정 상태
호기심: ██████░░ 75%
기쁨: ████░░░░ 50%
...

🧠 지식 그래프
개념: [N]개
관계: [N]개
가장 강한 개념: 비비 (0.88)

🔍 호기심 대기열
pending: [N] | exploring: [N] | learned: [N] | failed: [N]
```
