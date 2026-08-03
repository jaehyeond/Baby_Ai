# J1-R2-E3 Primary Review - Agent Recommendations

Status: `agent_proposal_not_user_reviewed_not_training_data`

## Bound Inputs

- Pending review packet:
  `aec20a9d0c714e768c560d8eb4d517edf604ca6c03cd7fc01ed8830fbf2339e4`
- Read-only audit:
  `696fe080b26bbb40af6e433394956b8cf6649ca1aff40d843d11288b2f3a04b4`
- Scope: the 60 rows with selection reason `top_unjudged`.
- Excluded: the 24 `positive_rank_neighbor_for_top8_miss` rows. They are
  diagnostic-only and must not become learned-head negatives.

These recommendations are not reviewed labels. They must be approved or
corrected by the user and materialized in a separate decision artifact.

## Decision Meaning

- `positive`: acceptable answer or answer-equivalent concept.
- `context`: related concept that must not become a binary negative.
- `hard_negative`: plausible confound but not an acceptable answer.
- `unrelated_negative`: semantically unrelated to the requested answer.
- `uncertain`: insufficient basis for a stable decision.
- `canonical`: usable standalone graph concept surface.
- `alias`: alternate surface for another canonical concept.
- `fragment`: incomplete grammatical or extraction fragment.
- `malformed`: surface noise such as an attached sentence-period variant.

## Proposed Decisions

### 00 - 대한민국의 행정 중심이 되는 수도 도시는 어디야?

Reviewed positive: `서울`

| Rank | Candidate | Relevance proposal | Vocabulary proposal | Reason |
|---:|---|---|---|---|
| 1 | 수도 | context | canonical | 역할/범주이며 도시 이름 자체는 아님 |
| 2 | 한국의 수도 | context | canonical | 질문을 바꿔 말하지만 도시 이름을 답하지 않음 |
| 3 | 도시 | context | canonical | 상위 범주 |
| 5 | 가장 중요한 곳 | context | canonical | 느슨한 설명 문맥 |
| 6 | 서울특별시 | positive | alias | `서울`의 공식 명칭으로 답 허용 가능 |

### 01 - 지구 주위를 공전하는 자연 위성은 무엇이야?

Reviewed positive: `달`

| Rank | Candidate | Relevance proposal | Vocabulary proposal | Reason |
|---:|---|---|---|---|
| 1 | 지구 | context | canonical | 공전의 중심 천체 |
| 2 | 공전 | context | canonical | 관계/동작 |
| 3 | 자연이 | context | fragment | 질문의 `자연 위성`에서 잘린 조사 결합형 |
| 4 | 우주 | context | canonical | 넓은 배경 문맥 |
| 5 | 별 | hard_negative | canonical | 천체라는 점에서 그럴듯하지만 달은 별이 아님 |

### 02 - 하늘에서 작은 물방울이 모여 보이는 것은 무엇이야?

Reviewed positive: `구름`

| Rank | Candidate | Relevance proposal | Vocabulary proposal | Reason |
|---:|---|---|---|---|
| 1 | 물방울 | context | canonical | 구성 요소 |
| 2 | 하늘 | context | canonical | 위치 문맥 |
| 3 | 반짝반짝 작은 별 | hard_negative | canonical | 하늘에 보이는 다른 대상으로 그럴듯한 혼동 |
| 5 | 하늘을 나는 것 | context | canonical | 하늘 대상의 느슨한 범주 |
| 6 | 우주 | unrelated_negative | canonical | 질문의 물방울 집합과 직접 관계가 약함 |

### 03 - 그래프에서 두 지점 사이의 비용 합이 가장 작은 경로를 무엇이라고 해?

Reviewed positive: `최단경로`

| Rank | Candidate | Relevance proposal | Vocabulary proposal | Reason |
|---:|---|---|---|---|
| 1 | 그래프에서. | context | fragment | 문제 영역을 나타내는 조사 결합형과 구두점 |
| 2 | 그래프에서 | context | fragment | 문제 영역을 나타내는 조사 결합형 |
| 3 | 경로. | context | malformed | 상위 개념에 문장 마침표가 결합됨 |
| 4 | 알고리즘으로. | context | fragment | 방법 문맥의 조사 결합형과 구두점 |
| 5 | 알고리즘으로 | context | fragment | 방법 문맥의 조사 결합형 |

### 04 - 귀로 소리를 받아들이는 감각을 무엇이라고 해?

Reviewed positive: `청각`

| Rank | Candidate | Relevance proposal | Vocabulary proposal | Reason |
|---:|---|---|---|---|
| 1 | 귀 | context | canonical | 감각 기관 |
| 2 | 소리 종류 | context | canonical | 감각 입력의 분류 |
| 4 | 착각 | unrelated_negative | canonical | 철자/형태 유사성 외 의미 관계가 약함 |
| 5 | 소리 | context | canonical | 감각 입력 |
| 6 | 큰 소리 | context | canonical | 감각 입력의 사례 |

### 05 - 물체를 지구 쪽으로 끌어당기는 힘은 무엇이야?

Reviewed positive: `중력`

| Rank | Candidate | Relevance proposal | Vocabulary proposal | Reason |
|---:|---|---|---|---|
| 1 | 지구 | context | canonical | 힘의 기준 천체 |
| 2 | 힘 | context | canonical | 상위 범주 |
| 3 | 등에 업히기 | unrelated_negative | canonical | 질문의 물리적 힘과 직접 관계가 없음 |
| 4 | 우주 | context | canonical | 넓은 물리 배경 |
| 5 | 에너지 | hard_negative | canonical | 힘과 혼동하기 쉬운 물리 개념이지만 답은 아님 |

### 06 - 빛을 받아 장면을 사진으로 기록하는 장치는 무엇이야?

Reviewed positive: `카메라`

| Rank | Candidate | Relevance proposal | Vocabulary proposal | Reason |
|---:|---|---|---|---|
| 2 | 카메라 따 놓기 | context | fragment | 카메라를 포함하지만 독립 장치명이 아닌 행위 구절 |
| 3 | 출력. | context | malformed | 결과 문맥에 문장 마침표가 결합됨 |
| 4 | 사용. | context | malformed | 일반 행위 표면에 문장 마침표가 결합됨 |
| 5 | 장치 | context | canonical | 상위 범주 |
| 6 | 영화 | context | canonical | 카메라 활용 결과 문맥 |

### 07 - 문제를 해결하기 위해 순서대로 정의한 절차를 무엇이라고 해?

Reviewed positive: `알고리즘`

| Rank | Candidate | Relevance proposal | Vocabulary proposal | Reason |
|---:|---|---|---|---|
| 1 | 해결 | context | canonical | 목적/동작 |
| 2 | 방법으로 | context | fragment | 조사 결합형 |
| 3 | 문제 | context | canonical | 입력 문제 문맥 |
| 4 | 문제였을 | context | fragment | 문장 일부의 활용형 |
| 5 | 사용. | context | malformed | 일반 행위 표면에 문장 마침표가 결합됨 |

### 08 - 숫자 연산을 수행하도록 만든 도구는 무엇이야?

Reviewed positive: `계산기`

| Rank | Candidate | Relevance proposal | Vocabulary proposal | Reason |
|---:|---|---|---|---|
| 1 | 숫자의 | context | fragment | 관형격 조사 결합형 |
| 2 | 숫자로 | context | fragment | 조사 결합형 |
| 4 | 알고리즘으로. | context | fragment | 방법 문맥의 조사 결합형과 구두점 |
| 5 | 알고리즘으로 | context | fragment | 방법 문맥의 조사 결합형 |
| 6 | 숫자 | context | canonical | 연산 대상 |

### 09 - 리듬과 음을 조합해 듣는 예술을 무엇이라고 해?

Reviewed positive: `음악`

| Rank | Candidate | Relevance proposal | Vocabulary proposal | Reason |
|---:|---|---|---|---|
| 1 | 연주 | context | canonical | 음악을 수행하는 행위 |
| 3 | 이야기 듣기 | hard_negative | canonical | 청취 활동이지만 음악은 아님 |
| 4 | 노래 부르기 | context | canonical | 음악 활동의 사례 |
| 5 | 소리 | context | canonical | 구성 매체 |
| 6 | 소리 종류 | context | canonical | 입력/매체 분류 |

### 10 - 센서로 환경을 관찰하고 정해진 동작을 수행하는 기계는 무엇이야?

Reviewed positive: `로봇`

| Rank | Candidate | Relevance proposal | Vocabulary proposal | Reason |
|---:|---|---|---|---|
| 1 | 구현. | context | malformed | 개발 행위에 문장 마침표가 결합됨 |
| 2 | 테스트하는 | context | fragment | 뒤 명사가 없는 관형형 |
| 3 | 검출하는 | context | fragment | 뒤 명사가 없는 관형형 |
| 4 | 출력. | context | malformed | 시스템 결과 문맥에 마침표가 결합됨 |
| 5 | 장치 | context | canonical | 상위 범주 |

### 11 - 컴퓨터가 실행할 수 있도록 작성된 명령의 묶음은 무엇이야?

Reviewed positive: `프로그램`

| Rank | Candidate | Relevance proposal | Vocabulary proposal | Reason |
|---:|---|---|---|---|
| 1 | 명령 | context | canonical | 구성 요소 |
| 2 | 컴퓨터에 | context | fragment | 조사 결합형 |
| 3 | 출력. | context | malformed | 실행 결과 문맥에 마침표가 결합됨 |
| 4 | 코딩 | context | canonical | 작성 행위 |
| 5 | 자료구조를 | context | fragment | 목적격 조사 결합형 |

## Proposal Summary

Relevance proposals:

- positive: `1`
- context: `52`
- hard-negative: `4`
- unrelated-negative: `3`
- uncertain: `0`

Vocabulary proposals:

- canonical: `36`
- alias: `1`
- fragment: `16`
- malformed: `7`
- uncertain: `0`

## Critical Interpretation

Only four of the 60 primary rows are proposed as hard negatives. Most high-rank
unjudged concepts are context, parts, hypernyms, or graph extraction fragments.
Treating all 60 as binary negatives would train the head to suppress useful
semantic neighborhoods. The next data contract therefore needs at least:

1. positive labels for acceptable answer aliases;
2. context exclusion or a separate context class;
3. reviewed hard negatives only;
4. vocabulary-quality decisions independent of relevance;
5. diagnostic-only neighbor rows excluded from training.
