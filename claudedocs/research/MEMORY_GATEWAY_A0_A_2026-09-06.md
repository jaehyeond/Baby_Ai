# memory_gateway — A0·A 단계 구현 기록 (2026-09-06)

설계 정본: Bandi 볼트 `A2A/비비 다음 뇌 설계 — VoiceMem 좌·우뇌를 넘어서 (2026-09-06).md` (7절 구축 순서 A0·A).
브랜치: `feature/memory-gateway` (별도 worktree 에서 작업, 2026-09-07 사용자 지시로 커밋·DB_Renewal 에 merge).

## 무엇을 만들었나

| 파일 | 내용 |
|---|---|
| `neural/baby/memory_gateway.py` (신규) | 답하기 전 회상(화자 라우팅 → 어휘·벡터·확산 후보를 RRF 로 융합 → strength×관련성 → 소프트맥스(T_eff)로 K=5 → conf·FOK 와 함께 프롬프트 블록), 놀람 게이트(σ_c 표, z, 워밍업 50턴, θ=2), 세션 버퍼(턴별 Concept 슬롯 W, z 게이트), 답한 뒤 갱신(write_priority, self_/speaker_ valence·arousal, surprise_z, channel, recall 통계, strength ×= write_priority, FEELS_ABOUT, access_ts, NE 버스트 시 추가 Hebbian(η_eff−1)과 태깅 창 60분). 새 Cypher 는 전부 `Neo4jGatewayStore` 에 있다 |
| `neural/baby/conversation_handler.py` | 두 줄: import 한 줄, `_build_system_prompt` 직후 `augment_system_prompt` 호출 한 줄. `MEMORY_GATEWAY=1` 이 아니면 그대로 반환 |
| `neural/baby/api_server.py` | `/api/conversation` 에서 `handle_conversation` 직후 `post_turn` 호출(try 로 감쌈) |
| `scripts/migration/person_hub_seed.py` (신규) | A0 :Person 허브 시드. `--dry-run` / `--apply`. UserModel 마다 :Person MERGE, IDENTIFIED_BY, 가족은 owner 와 FAMILY_OF, 새 속성 다섯 초기값 |
| `tests/test_memory_gateway.py` (신규) | FakeStore 로 14개 단위 테스트. 영상 시나리오(형: 중간고사 → 이튿날 "피곤해" 회상), 화자 라우팅, 워밍업, 버퍼 축출·핀, write_priority, FEELS_ABOUT, access_ts, 버스트의 추가 Hebbian·태깅, 플래그 꺼짐 무동작, 저장소 오류가 대화를 안 막음 |

프로젝트 관례 반영: "정의만 하고 호출 안 함" 방지(두 호출 지점 배선), 조회 쿼리의 화자 범위 제한(INTERACTED_WITH), 프롬프트 [필수 규칙]의 "모르겠어요 금지" 유지(회상 지침은 "추측임을 밝히고 답하라").

## 켜는 법

```
MEMORY_GATEWAY=1            # 게이트웨이 켜기 (기본 0)
MEMORY_GATEWAY_W=5          # 세션 버퍼 슬롯 수 임시값 (기본: 발달 단계 표 3~5)
```

A0 시드는 Neo4j 가 켜진 상태에서:

```
python scripts/migration/person_hub_seed.py --dry-run
python scripts/migration/person_hub_seed.py --apply
```

## J1 보호 핸들러 해시 재기준선

| | blob (git hash-object) |
|---|---|
| HEAD ef48297 의 `conversation_handler.py` | `054d974095be7425692860909181fafd54f97a33` |
| 이 브랜치의 `conversation_handler.py` (두 줄 추가) | `c1922cc61240c75b7446306ed2b57e70d813f27d` |

J1 문서가 "무변경 ✅" 로 참조하던 값은 앞의 것이다. 이 브랜치를 합치면 뒤의 값이 새 기준선이다.

## 테스트 결과 (2026-09-06, worktree, E: 의 .venv 파이썬)

- `tests/test_memory_gateway.py`: 14 passed.
- 전체 `tests/`: 391 passed, 1 skipped, 3 failed. 실패 3건은 모두 J1 의 "repository … validates" 류로, 구현 파일의 **원시 바이트 sha256** 을 봉인값과 비교한다. 해당 파일(`relevance_cohort_generator.py` 등)은 이 브랜치에서 수정하지 않았고 git blob 은 HEAD 와 동일하다. 새 worktree 체크아웃의 바이트가 E: 작업본과 달라(줄끝 정규화) 생기는 환경 차이로 판단한다. E: 체크아웃에서 같은 테스트를 다시 돌려 확인해야 한다.

## 실행해 보지 못한 것

- Neo4j 가 꺼져 있어(bolt 7687 거부) `Neo4jGatewayStore` 의 Cypher 와 A0 시드 `--apply` 는 실행하지 않았다. 문법은 눈으로만 확인했다.
- 경험 노드에 임베딩이 저장되지 않으므로(`insert_experience` 에 embedding 을 넘기는 곳이 없음) 벡터 후보는 빈 목록이다. 회상은 어휘 일치와 확산 활성화로만 돈다. 임베딩 저장은 별도 결정(OpenAI 호출 비용)이다.
- Redis 인스턴스 가동 여부는 확인하지 않았다. 게이트웨이의 Redis 사용(버스트 이벤트, affect_state 캐시)은 실패해도 대화를 막지 않는다.
- Gemini 를 실제로 부르는 대화 1회 테스트(설계 8절 8항 시나리오 재현)는 Neo4j·API 키가 있는 환경에서 해야 한다.

## 설계와 다른 점·미결

- Experience 의 화자 라우팅은 설계의 :Person 이 아니라 기존 INTERACTED_WITH→UserModel 로 했다(A0 시드가 :Person 을 만들어도 IDENTIFIED_BY 로 UserModel 에 붙으므로 그대로 동작).
- 화자별 후보 예산은 상수 20 이다(social_salience 재계산은 C단계).
- 확신도 온도 s 는 점수 범위(0~1) 기준 0.1 로 두었다(설계의 "s = 1" 은 척도 미지정).
- 설계 13절의 미검토 항목 3개(오차 정의, coverage 분모, social_salience 시점)는 그대로 열려 있다.

## 실행 결과 (2026-09-07, Neo4j 가동 후)

단계별로 확인했다.

1. **Neo4j 기동**: Desktop 인스턴스 `Baby_Robotics` 를 `bin\neo4j.bat console` (번들 JDK 21) 로 띄움. bolt 7687 열림. Concept 1,111 / Experience 3,152 / UserModel 6 / Person 1(owner_pjh, mom·brother 를 별칭으로 IDENTIFIED_BY).
2. **A0 시드**: dry-run → apply. owner Person 에 새 속성 6개 채움, 식별 안 된 화자 4명(guest, stranger_x, b5_1_pilot, b5_4_train_a_20260716) 을 stranger :Person 으로 생성·IDENTIFIED_BY. FAMILY_OF 0(mom·brother 가 owner 별칭이라 기대대로). 제약은 기존 `person_pid` 사용.
3. **시나리오(같은 프로세스, 두 턴)**: `scripts/research/memory_gateway_scenario.py --same-process` → **PASS**. 2턴("요즘 너무 피곤해")에서 회상 4건(중간고사 경험 2건 포함, conf 0.62, FOK 1.0)이 프롬프트에 들어갔고 Gemini 답변이 "혹시... 알고리즘 중간고사 때문에 그런 거야?" 라고 물었다. 첫 실행은 FAIL 이었고 원인은 확산 시드(발화+세션 버퍼)를 이웃으로만 쓰고 직접 일치로는 안 써서 강도 0.05 의 새 엣지가 상위 20 이웃에 못 든 것. 시드 직접 일치를 0순위로 넣고 확산 결과 중복을 제거해 고쳤다(단위 테스트 14개 유지).
4. **시나리오(새 프로세스, 2턴만)**: `--second-only` → 게이트웨이 회상에 중간고사 경험 없음(**기준 미달**). 세션 버퍼가 비고, 피곤해–중간고사 그래프 엣지가 없으며, 임베딩은 OpenAI 크레딧 소진(429 insufficient_quota)으로 꺼져 있어 의미 경로가 없다. 답변은 그래도 "혹시 중간고사 때문에 그래?" 라고 했는데 기존 UserModel 관심사 요약(중간고사·알고리즘이 상위로 갱신됨)이 프롬프트에 들어간 효과로 보인다(회상 블록 조각 60자에는 없었음).
5. **부작용 검증**: 회상된 경험에 access_ts 기록(두 번 회상된 것은 2개), brother→개념 FEELS_ABOUT 12개(중간고사 valence −1.0), Concept access_ts 22개. NE 버스트는 워밍업 50턴 동안 없음(z=0).

환경 사실
- Redis(Upstash `arriving-impala-41945`) DNS 실패 = 인스턴스 소멸(5월과 같은 증상). 핸들러의 publish 와 게이트웨이의 이벤트·캐시는 실패해도 대화를 막지 않는다.
- OpenAI 크레딧 0 → 임베딩 생성 불가. 벡터 인덱스 이름도 코드가 찾는 `experience_embeddings` 가 아니라 자동 생성 이름(`index_…`)이라 벡터 검색은 예외→빈 목록.
- 화자 감정 키워드 사전에 "피곤" 이 없어 speaker_word 는 neutral 로 기록됨(A0 사상표의 입력 한계).

남은 것
- 세션(프로세스) 밖 회상은 임베딩 복구(크레딧) 또는 공출현으로 생기는 Hebbian 경로에 기댄다. B단계 전에 임베딩 저장 여부를 결정해야 한다.
- 워밍업 50턴 뒤의 NE 버스트·태깅·추가 Hebbian 은 실대화에서 아직 관측되지 않았다(단위 테스트만).
