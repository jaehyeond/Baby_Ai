# W6 sensor/action/outcome contract 준비 기록 (2026-09-12)

## 범위와 판정

W6의 첫 capture 전에 사용할 엄격한 입력 계약과 read-only audit CLI를 구현했다. legacy
`/api/vision/quest-concepts`와 Neo4j 저장 경로는 변경하지 않았다. 새 HTTP request validation,
DB 연결, APK 송신 구현, 장치 capture는 이 작업 범위에 포함되지 않는다.

현재 판정은 **contract preparation implemented, physical validation not performed**다. 함께 둔
JSONL은 schema와 CLI를 실행하기 위한 **synthetic test fixture**이며 실제 센서 데이터, 실제
비비 행동, 모델 inference, 학습 또는 성능 증거가 아니다.

## 구현

- `neural/baby/sensor_contract.py`: 레코드·cross-record 검증, 순서/중복/session 경계 감사,
  prediction-before-outcome 인과 순서, pose 비교를 구현했다.
- `scripts/research/sensor_contract_audit.py`: JSON/JSONL을 읽고 deterministic JSON report를
  stdout으로 내보내는 실제 호출 지점이다. DB/API write는 없다.
- `tests/test_sensor_contract.py`: 정상 Bibi chain, human/scripted agency 제한, measured/heuristic/
  missing depth 구분, q/-q 불변성, 비정상 pose, 중복/역전, cross-session, timestamp causality,
  반대 방향 이동 residual, 같은 각도의 다른 회전축, coordinate-frame 변경 시 비교 차단,
  CLI deterministic output을 합성 fixture로 검사한다.

레코드 validity와 evidence sufficiency는 분리했다. human/scripted action과 heuristic/missing
depth는 정직하게 기록된 경우 valid할 수 있다. 다만 human/scripted는 Bibi agency가 아니며,
heuristic/missing depth는 measured depth 증거가 아니다.

## 합성 실행 예시

입력:
[`sensor_contract_synthetic_fixture_v1.jsonl`](sensor_contract_synthetic_fixture_v1.jsonl)

```powershell
E:/A2A/our-a2a-project/.venv/Scripts/python.exe -B scripts/research/sensor_contract_audit.py claudedocs/research/sensor_contract_synthetic_fixture_v1.jsonl --require-bibi-agency
```

이 fixture의 기대값은 7 accepted, 0 rejected, 0 insufficient evidence, 완전 chain 1,
Bibi-agency chain 1이다. 실제 capture에 같은 결과가 나온다는 뜻은 아니다.

## Runtime 통합 경계

후속 API/DB 담당자는 strict version을 명시적으로 opt-in하는 별도 경계에서
`audit_records`와 같은 규칙을 적용해야 한다. legacy payload를 ID/timestamp/actor가 있는 것처럼
추정 변환하지 않는다. 저장 transaction은 동일 device/session의 ID 중복, frame order,
prediction timestamp가 outcome observation capture보다 이른지 다시 검사해야 한다.

현재 `link_vision_frame_sequence`는 최근 vision Experience를 30초 기준으로 고르고 7-element
pose L2를 계산하므로 strict session/action 계약을 충족하지 않는다. 이 기록은 후속 변경 범위를
명확히 하는 진단이며 DB가 이미 strict하다는 주장이 아니다.

엄격 motion 비교는 공통 좌표계의 실제 translation vector와 명령 vector의 residual norm을
사용한다. 회전 명령은 axis-angle rotation vector(rad)이며 실제 상대 quaternion과의 geodesic
오차를 계산한다. 방향/축을 제거한 magnitude 차이를 action error라고 표시하지 않는다.
