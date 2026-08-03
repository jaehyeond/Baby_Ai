# J1-R2 Rolling-Development Generator Review

## 1. Purpose

This bundle is the next J1-R2 gate before any lexical baseline. It tests the
task-aligned relevance-scorer interface with deterministic questions and
explicit answer-bearing graph concepts.

It is not evidence for:

- grounded Quest or tool learning;
- held-out performance;
- continual self-improvement;
- production promotion.

The source is a fixed synthetic environment because using Baby's live graph
relations as truth would let the subject memory system define its own exam.
No subject model, external API, personal memory, or live graph relation was
used to generate or grade these questions.

## 2. Label Contract

Each question has:

- exactly one answer-bearing positive concept;
- zero or more context concepts that remain unscored;
- exactly three explicit closed-world decoys;
- every other graph concept left unlabeled.

Unlabeled concepts are never converted to negatives. This preserves the J1-R1
rule and prevents 1,069-vocabulary ranking from creating thousands of false
negative labels.

## 3. Sample Plan

| Item | Count |
|---|---:|
| Questions | 12 |
| Positive labels | 12 |
| Explicit negative labels | 36 |
| Fit-pool targets | 8 |
| Development-challenge targets | 4 |
| Lockbox-challenge targets | 0 |

The cohort is descriptive and may be used for model selection only. It cannot
support inferential, held-out, performance, or production claims.

## 4. Review Questions

| # | Question | Positive | Context, unscored | Explicit negatives |
|---:|---|---|---|---|
| 1 | 대한민국의 행정 중심이 되는 수도 도시는 어디야? | 서울 | 한국, 수도 | 달, 중력, 카메라 |
| 2 | 지구 주위를 공전하는 자연 위성은 무엇이야? | 달 | 지구 | 서울, 알고리즘, 음악 |
| 3 | 하늘에서 작은 물방울이 모여 보이는 것은 무엇이야? | 구름 | 물 | 컴퓨터, 중력, 계산기 |
| 4 | 그래프에서 두 지점 사이의 비용 합이 가장 작은 경로를 무엇이라고 해? | 최단경로 | 알고리즘, 문제 | 서울, 카메라, 음악 |
| 5 | 귀로 소리를 받아들이는 감각을 무엇이라고 해? | 청각 | 소리 | 달, 알고리즘, 계산기 |
| 6 | 물체를 지구 쪽으로 끌어당기는 힘은 무엇이야? | 중력 | 지구, 힘 | 서울, 카메라, 음악 |
| 7 | 빛을 받아 장면을 사진으로 기록하는 장치는 무엇이야? | 카메라 | 없음 | 중력, 달, 계산기 |
| 8 | 문제를 해결하기 위해 순서대로 정의한 절차를 무엇이라고 해? | 알고리즘 | 문제 | 서울, 구름, 음악 |
| 9 | 숫자 연산을 수행하도록 만든 도구는 무엇이야? | 계산기 | 계산 | 달, 카메라, 청각 |
| 10 | 리듬과 음을 조합해 듣는 예술을 무엇이라고 해? | 음악 | 소리 | 중력, 알고리즘, 서울 |
| 11 | 센서로 환경을 관찰하고 정해진 동작을 수행하는 기계는 무엇이야? | 로봇 | 없음 | 달, 구름, 수도 |
| 12 | 컴퓨터가 실행할 수 있도록 작성된 명령의 묶음은 무엇이야? | 프로그램 | 컴퓨터 | 서울, 중력, 음악 |

## 5. Sealed Inputs

- sample-size plan:
  `17b705ddbd7533bacf1bcaffc3cba637a2cba6db8a37567a644567b75fc628f7`
- generator implementation:
  `69b6e28805c5bd3bf443e3bdcd664cb7f5eca44a9d1ba4c5a3bc1e1bec3f3488`
- generator specification:
  `f900d8a097eaa61298dd0980b98b5a35c0efcb27fac93c5a4fe7108b85a057f5`
- review packet:
  `e5aded97a12ef997ab72d7687cd39e63edfd1e9fa8126f71b8eabaeb8b5f7624`

The user explicitly approved all 12 questions and their sealed
positive/context/negative mappings without modification.

## 6. Reviewed Successors

- review decisions:
  `dc9a25573965979796febbd4d2d974b78065e79360f81e3729266125a66c5652`
- reviewed label pack:
  `10773ee23beefc13620477898021d30c34ae4585fc89b5f99b6cb22759325e9d`
- rolling-development manifest:
  `f93e8c1e975763c8b06d045d905e15a777d95ae1948247e1196ffd8d3a27a982`
- successor readiness:
  `2353d97796211cf77080c683e3a3d540548e98fdb4ce4a27c6c0870ded4aa231`

The approval record binds `reviewer_role=user`, 12 ordered approvals,
`content_modifications=[]`, and
`positive_context_negative_mapping=approved_as_sealed`.

Current gates are `development=true`, `lockbox_generator=false`, and
`lexical_baseline=false`. The separate one-time lockbox generator must be
explicitly reviewed and frozen before the lexical baseline can run.
