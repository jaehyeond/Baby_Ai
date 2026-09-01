# A2A CodePipeline 기준선 — before_graph

- run: `pipeline_before_graph_20260831-1951`  ·  구조: linear: coder -> tester -> reviewer (no fan-out, no verdict, no back-edge)
- 과제 5 × 반복 3 = 15회

| 지표 | 비율 |
|---|---|
| `steps_ok` | 67 % |
| `code_extracted` | 100 % |
| `syntax_ok` | 100 % |
| `contract_ok` | 100 % |
| `tests_pass` | 100 % |

- 1회 평균 37.0 s (최소 30.5 / 최대 43.6)
- 에이전트별 누적: coder 60s, reviewer 338s, tester 157s

## 과제별 tests_pass

| 과제 | 통과/시도 |
|---|---|
| reverse_words | 3/3 |
| merge_intervals | 3/3 |
| is_balanced | 3/3 |
| top_k_frequent | 3/3 |
| roman_to_int | 3/3 |
