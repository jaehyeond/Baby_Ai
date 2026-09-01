# A2A CodePipeline 기준선 — sdk_pilot

- run: `pipeline_sdk_pilot_20260831-2024`  ·  구조: linear: coder -> tester -> reviewer (no fan-out, no verdict, no back-edge)
- 과제 1 × 반복 1 = 1회

| 지표 | 비율 |
|---|---|
| `steps_ok` | 100 % |
| `code_extracted` | 100 % |
| `syntax_ok` | 100 % |
| `contract_ok` | 100 % |
| `tests_pass` | 100 % |

- 1회 평균 46.4 s (최소 46.4 / 최대 46.4)
- 에이전트별 누적: coder 7s, reviewer 29s, tester 10s

## 과제별 tests_pass

| 과제 | 통과/시도 |
|---|---|
| reverse_words | 1/1 |
