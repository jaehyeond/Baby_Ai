# 비비 W1·W2 / E3·센서 계약 구현 결과

2026-09-12. 작업 기준은 `DB_Renewal`의 `1a2d0d7`이다. 구현과 검증은 `feature/bibi-foundation-20260912` / `.worktrees/bibi-foundation-20260912`에 통합했다. 원래 checkout의 미커밋 문서를 보존했고 commit/push/브랜치 merge는 하지 않았다.

## 완료 범위와 실제 상태

| 묶음 | 결과 | 확인한 근거 |
|---|---|---|
| W1 기억 보존·복원 | 온라인 전체 백업과 독립 복원, 시스템 DB·서버 식별자 보존 | 노드 9,753 / 관계 10,852 및 속성·스키마 fingerprint 일치 |
| W1 설치 재현 | Python 3.12 빈 환경에 의존성 80개 + 프로젝트 wheel 설치 | hash lock 설치, dependency check, `neural` import 경로가 venv `site-packages`임을 확인 |
| W2 준비 상태·Redis | 실제 dependency 검사, 자동 생성 인덱스 이름 지원, TLS 검증 | 정상 200, Redis 중단 503, liveness 200, 같은 API의 재연결 |
| W2 실행/결과 구분 | 호기심 explore와 상상 predict/simulate/verify 등의 가짜 성공·쓰기를 차단 | 실제 HTTP 검증, 과거 `was_correct`는 미검증 진단값으로 분리 |
| E3 | 60행의 사용자 검토 입력과 검증기 | 60행 모두 결정 대기, fit 가능 0, 진단 24행 제외, context의 binary negative화 차단 |
| 센서 | 실행 가능한 offline 계약·CLI | 단위/좌표계/순서/주체/인과관계 검증, 반대 방향·다른 회전축 오류 검출 |
| 회귀 | 통합 canonical suite | **473 passed, 1 skipped**, 10.52초 |

검증 API(18000), 복원 Neo4j(17687/17474), 작업용 Redis(16379)는 검증 후 종료했다. 원본 Neo4j Desktop(7687)은 그대로 실행 중이다. 최종 C: 여유 공간은 약 0.25 GiB이며 큰 새 파일은 E:에 배치했다. `.runtime` 전체는 약 349 MB였다. C: 감소의 전체 원인은 이번 검사로 확정하지 않았다. WSL의 C: swap 파일 약 36 MiB를 확인했으나 그것만으로 감소량을 설명할 수 없다.

**현재 PC를 꺼도 실행되는 상태는 아니다.** 상시 host 배치, 공개/원격 접속, 무인 학습 job, 실물 동작은 이번 구현의 완료 주장에 포함하지 않는다. `LOCAL_CORE_DISTILL=0`이며 모델 다운로드·추론·학습·lockbox 소비·실물 센서 수집은 0이다.

## worktree와 모델 배치

| 역할 | 브랜치 | worktree | 실행 모델 |
|---|---|---|---|
| W1·통합·실제 복원 검증 | `feature/bibi-foundation-20260912` | `bibi-foundation-20260912` | 기존 root Codex |
| W2 runtime | `feature/bibi-runtime-20260912` | `bibi-runtime-20260912` | GPT-5.6 Sol high |
| E3 계약 | `feature/bibi-e3-contract-20260912` | `bibi-e3-20260912` | GPT-5.6 Sol high |
| 센서 계약 | `feature/bibi-sensor-contract-20260912` | `bibi-sensor-20260912` | GPT-5.6 Sol high |
| 뇌 구조 문헌·영상 | `research/bibi-brain-architecture-20260912` | `bibi-brain-research-20260912` | GPT-5.6 Sol high |

Claude는 사용하지 않았다. 9월 16일까지 지정한 worker 모델 정책을 유지한다. 저장소에 `main` 브랜치는 없고 현재 작업 기준은 `DB_Renewal`이다. 로컬 `origin/HEAD`는 `origin/master`를 가리킨다. 이것을 현재 개발 기준 브랜치와 혼동하지 않는다. 원격 ref는 이번에 fetch하지 않았으므로 서버의 최신 상태라는 주장은 하지 않는다.

서로 다른 checkout에서 병렬 구현했다. 반환된 파일 목록만 통합 checkout에 복사했고 부모가 다시 검사·실행했다. E3는 다른 작업자가 읽기 전용 독립 검토했다. 배포 도구는 독립 검토에서 지적한 경로·프로세스 소유권·설치 코드 우회 문제를 수정하고 최종 PASS를 받았다.

## 복원과 이식

백업은 Neo4j Enterprise **2026.03.1**의 기존 Java 21/라이브러리를 사용해 원본 온라인 backup port 6362에서 받았다. 원본을 멈추거나 raw DB 파일을 실행 중 복사하지 않았다. `neo4j` 데이터 backup과 `system` backup은 각각 일관된 backup이다. 두 DB 전체에 걸친 동시 transaction snapshot이라는 뜻은 아니다.

`system` backup만 새 서버 ID로 시작하면 이전 서버에 database 할당이 남아 `DatabaseNotFound`가 발생했다. 독립된 새 복원 디렉터리에 원본 `data/server_id`를 먼저 보존한 뒤 두 DB를 복원해 해결했다. 복원 인스턴스는 모든 listener를 loopback의 별도 포트로 사용한다. 기존 DB/다른 서버 식별자를 덮어쓰는 복원은 거부한다.

공식 동작 범위는 [Neo4j의 backup restore 문서](https://neo4j.com/docs/operations-manual/current/backup-restore/restore-backup/)를 참조한다. 이번에는 **동일 버전 Enterprise/Windows 복원만 실제 검증**했다. 다른 버전·Community·Linux로의 파일 호환성과 운영 배치는 별도 rehearsal이 필요하다.

백업·자격정보·복원 데이터·프로세스 로그는 Git에서 제외한 `.runtime/`에 있다. 공개 검증 artifact에는 개인 대화/벡터/암호를 쓰지 않고 개수와 digest만 기록했다. 현재 백업은 같은 E:에 있으므로 드라이브 고장에 대한 별도 off-device 사본은 아직 없다.

### 재실행 예시

아래는 **통합 worktree**에서 실행한다. `.runtime/restored.env`는 이 PC의 비공개 복원용 설정이며 Git에 포함하지 않는다. 새 PC에서는 별도 비밀 전달 절차로 만든다.

```powershell
# Python은 이미 설치된 3.12, uv는 설치된 실행 파일의 경로를 지정한다.
./scripts/deployment/install_runtime.ps1 -Python 'C:/Users/SOGANG/AppData/Local/Programs/Python/Python312/python.exe' -Uv 'C:/Users/SOGANG/.local/bin/uv.exe'

# 복원 DB 기동: 원본 Java와 lib를 읽지만 data/logs는 E:의 복원 디렉터리다.
./.runtime/venv/Scripts/python.exe -B scripts/deployment/neo4j_instance.py start --home .runtime/neo4j-restore-final --java 'C:/Users/SOGANG/.Neo4jDesktop2/Cache/runtime/zulu21.44.17-ca-jdk21.0.8-win_x64/bin/java.exe' --distribution 'C:/Users/SOGANG/.Neo4jDesktop2/Data/dbmss/dbms-450628b3-7bc9-46e9-9607-ddb4ab2bb840'

# Redis: 이 PC의 기존 Ubuntu-22.04 사용. 실행 파일·AOF는 E:에 있다.
wsl.exe -d Ubuntu-22.04 --exec sh /mnt/e/A2A/our-a2a-project/.worktrees/bibi-foundation-20260912/scripts/deployment/redis_local.sh start /mnt/e/A2A/our-a2a-project/.worktrees/bibi-foundation-20260912/.runtime

./.runtime/venv/Scripts/python.exe -B scripts/deployment/bibi_runtime.py start --env-file .runtime/restored.env
./.runtime/venv/Scripts/python.exe -B scripts/deployment/bibi_runtime.py status
./.runtime/venv/Scripts/python.exe -B scripts/deployment/bibi_runtime.py stop
./.runtime/venv/Scripts/python.exe -B scripts/deployment/neo4j_instance.py stop --home .runtime/neo4j-restore-final
```

Redis는 같은 `redis_local.sh stop <runtime>` 명령으로 AOF 저장 후 종료한다. 시작은 준비 완료와 구분되며 실제 사용 가능 여부는 `/health`의 `ready`를 확인한다. 새 복원은 `neo4j_recovery.py restore --help`, 온라인 백업은 `backup --help`, 비교는 `compare --help`를 사용한다. `system` 복원에는 같은 출처의 `--server-id`가 필요하다. 기존 backup/검증 결과를 덮어쓰지 않도록 새 output 경로를 사용한다.

일반 API 시작은 schema/seed를 쓰지 않는다. 새 빈 DB의 명시적 초기화는 `bibi_runtime.py initialize --env-file <설정> --schema` 또는 `--seed`를 별도 호출한다. 이 명령은 데이터를 쓸 수 있으며 **이번 복원 검증에서는 실행하지 않았다**.

### Redis와 Python 설치에 관한 확인

- Redis **8.2.9** source SHA-256 `531b314e5557ad76d941f605b3e3162ac61dc141f37c407e1f91fcfe17ea8c30`을 검증하고 E:에서 빌드했다. 기존 WSL의 gcc/make/OpenSSL headers를 사용했다. [공식 source hash 목록](https://github.com/redis/redis-hashes/blob/master/README), [공식 빌드 안내](https://redis.io/docs/latest/operate/oss_and_stack/install/build-stack/).
- 새 WSL 배포판·Docker image·GPU 모델은 설치하지 않았다. Redis startup 직후 준비 시간은 bounded polling으로 처리한다.
- FastAPI와 multipart 의존성 누락, wheel에서 `neural` 누락, `neural` import의 불필요한 Claude Agent SDK 결합을 고쳤다. 기존 공개 `neural` export는 lazy import로 유지한다.
- Python 3.12/Windows dependency lock은 설치된 기존 버전을 기준으로 hash까지 고정했다. 전체 패키지 업그레이드는 하지 않았다. Linux용 lock/설치 검증은 별도다.
- Windows venv redirector의 자식 프로세스까지 소유 관계로 종료한다. PID 재사용을 검사하고 lifecycle lock/atomic state write로 중복 시작을 막는다.

## 연구 계약 경계

E3의 [검토·학습 계약](../research/J1_R2_E3_REVIEW_TRAINING_CONTRACT_2026-09-12.md)은 사용자 의미 판정을 자동으로 채우지 않는다. `generate` 재호출도 기존 검토 파일을 덮어쓸 수 없다. 이번 진행 지시를 60개 의미 라벨 승인으로 해석하지 않았다. 학습·DB cleanup·lockbox·성능 승격은 계속 false다.

[센서 계약](../research/W6_SENSOR_ACTION_OUTCOME_CONTRACT_2026-09-12.md)은 `device_id/session_id/frame_id/frame_index`, timestamp, 좌표계, 위치 m, quaternion, 깊이 출처, actor, prediction-before-outcome을 검증한다. translation은 벡터 잔차, rotation은 명시한 axis-angle `rotation_vector_rad`와 상대 quaternion의 geodesic 오차로 비교한다. `q/-q`는 동일 자세로 취급한다. 사람이 움직인 기록은 비비의 자율 행동 증거가 아니다. 예제 파일은 합성 fixture이며 실제 센서 수집·APK 배선·실물 검증은 하지 않았다.

## 검증 파일

- `restore_final_comparison_2026-09-12.json`: 최종 도구로 만든 복원본과 원본의 비교.
- `post_runtime_graph_comparison_2026-09-12.json`: HTTP/SSE 검증 뒤에도 원본/복원본 속성·스키마 일치.
- `runtime_integration_2026-09-12.json`: Redis 중단/재시작·AOF 유지·HTTP 준비 상태·SSE 두 연결의 실제 결과.
- `vector_registry_probe_2026-09-12.json`: 저장된 실제 벡터로 Experience/Concept/region 결합 조회 3개 성공. 임베딩 모델 호출 없음.
- `foundation_evidence_2026-09-12.json`: backup/wheel/lock hashes, 테스트, 원본 문서/handler 보존, 종료 시 포트/용량.

`conversation_handler.py`는 Git blob `c1922cc61240c75b7446306ed2b57e70d813f27d`로 HEAD와 같다. 새 worktree의 LF와 원본 checkout의 CRLF 차이 때문에 raw byte SHA는 다르지만 정규화한 내용과 Git blob은 같으며 편집하지 않았다.

## 다음 우선순위

1. **W3:** 저장된 과거 대화를 새 프로세스에서 실제 회상하도록 경험 embedding/후보 범위/화자 경계를 복구한다. 현재 vector query 성공은 대화 기억 내용 복구까지 뜻하지 않는다.
2. **E3 사용자 검토:** 60행의 relevance/vocabulary 판단을 확정한 뒤 successor decision artifact를 만든다. 그 뒤에만 학습 목표·데이터 충분성을 판단한다.
3. **센서:** 한 개의 실제 과제를 선택하고 완료한 계약에 맞는 action→외부 outcome을 수집한다. 연구 worktree의 뇌 구조 권고와 연결한다.
4. **상시 host:** 복원·실행 절차를 바탕으로 전원이 유지되는 다른 장비/외부 서버를 선정하고 예산·저장·backup·원격 접속을 확정한다. 유료 모델 API는 핵심 제어의 필수 조건으로 두지 않는다.

뇌 구조 연구는 별도 `research/bibi-brain-architecture-20260912`에서 수행했으며 해당 보고서의 근거 등급·제약을 따른다. 이번 구현을 world model 학습이나 일반화 성능 향상의 증거로 해석하지 않는다.
