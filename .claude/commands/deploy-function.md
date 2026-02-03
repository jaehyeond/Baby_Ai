# Deploy Edge Function

Supabase Edge Function을 배포합니다.

## 사용법

```
/deploy-function <function-name>
```

## 배포 가능한 함수들

| 함수명 | 설명 | verify_jwt |
|--------|------|------------|
| conversation-process | 대화 처리 (핵심) | false |
| memory-consolidation | 수면 모드 기억 통합 | false |
| autonomous-exploration | 자율 탐색 | true |
| generate-curiosity | 호기심 생성 | true |
| vision-process | 시각 처리 | false |
| audio-transcribe | 음성 인식 | false |
| speech-synthesize | 음성 합성 | false |

## 배포 절차

1. **현재 버전 확인**
   - `mcp__supabase__get_edge_function` 으로 현재 코드 조회

2. **코드 수정**
   - 로컬에서 수정 또는 직접 작성

3. **배포**
   - `mcp__supabase__deploy_edge_function` 사용
   - 버전 자동 증가

4. **로그 확인**
   - `mcp__supabase__get_logs` service: "edge-function"

## 예시

```typescript
// conversation-process v17 배포
mcp__supabase__deploy_edge_function({
  name: "conversation-process",
  entrypoint_path: "index.ts",
  verify_jwt: false,
  files: [{ name: "index.ts", content: "..." }]
})
```

## 주의사항

- verify_jwt: false = 모든 요청 허용 (개발용)
- verify_jwt: true = Supabase 인증 필요 (프로덕션)
- 배포 후 항상 로그 확인
