# A2A CodePipeline 기준선 — before_graph

- run: `pipeline_before_graph_20260831-1945`  ·  구조: linear: coder -> tester -> reviewer (no fan-out, no verdict, no back-edge)
- 과제 1 × 반복 1 = 1회

| 지표 | 비율 |
|---|---|
| `steps_ok` | 0 % |
| `code_extracted` | 0 % |
| `syntax_ok` | 0 % |
| `contract_ok` | 0 % |
| `tests_pass` | 0 % |

- 1회 평균 1.5 s (최소 1.5 / 최대 1.5)
- 에이전트별 누적: coder 0s, reviewer 1s, tester 1s

## 과제별 tests_pass

| 과제 | 통과/시도 |
|---|---|
| reverse_words | 0/1 |

## 실패 이유

- `no_code_block`
