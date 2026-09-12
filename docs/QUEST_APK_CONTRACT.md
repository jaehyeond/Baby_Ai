# Quest APK → Brain 수신 계약

> 현재 `POST /api/vision/quest-concepts`는 하위 호환용 legacy 경로다. 서버는 아래 필드를
> **선택(optional)** 으로 이미 받는다(2026-07-12,
> `neural/baby/api_server.py`). **Quest APK가 이 필드를 채워 보내기 시작해야** 감각운동
> 신호가 기록된다. 안 채우면 기존 동작 그대로(하위호환) — 단 그럴 경우 pose/depth 는 영원히
> null 이라 embodied 예측이 성립하지 않는다(아래 §근거).

## Legacy 엔드포인트(현재 운영 호환)
`POST http://<brain-host>:8000/api/vision/quest-concepts`

## 요청 JSON 필드

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `timestamp` | string(ISO8601) | ✅ | 프레임 캡처 시각(기기) |
| `vlm_response` | string | ✅ | SmolVLM raw 텍스트 |
| `concepts_raw` | string[] | ✅ | 추출 객체 라벨 |
| `source` | string | | 기본 `quest_passthrough` |
| `model` | string | | 기본 `SmolVLM-500M-Q8` |
| `image_meta` | {width,height,camera} | | 프레임 메타 |
| `inference_ms` | int | | 온디바이스 추론 시간 |
| `jpeg_path` | string | | 프레임 저장 경로 |
| **`head_pose`** | float[] | 🆕 **추가 요망** | 헤드셋 6DoF 자세 = `[px,py,pz, qx,qy,qz,qw]` (위치 m + 쿼터니언). Unity/OVR: `OVRManager` centerEyeAnchor / `InputTracking.GetLocalPosition(Node.Head)` + `GetLocalRotation`. |
| **`depth_bins`** | float[] | 🆕 **추가 요망** | coarse depth 히스토그램 정규화 비율, 예 `[near, mid, far]`(합=1). Quest Depth API 또는 근사(화면 하단=근거리 heuristic). 3~5 bin 권장. |

## Unity(C#) 최소 예시 (추가분만)
```csharp
// 프레임 캡처 시점
var p = InputTracking.GetLocalPosition(XRNode.CenterEye);
var q = InputTracking.GetLocalRotation(XRNode.CenterEye);
payload.head_pose = new float[] { p.x, p.y, p.z, q.x, q.y, q.z, q.w };
// depth_bins: EnvironmentDepth 사용 시 근/중/원 픽셀 비율. 없으면 생략 가능(null).
payload.depth_bins = ComputeDepthHistogram();  // float[]{near,mid,far}, 합=1
```

## 서버 동작 (이미 구현됨)
- `head_pose`/`depth_bins` 를 Experience 노드에 1급 속성 + `extras` 로 저장.
- 직전 vision 프레임(≤30s)과 `(:Experience)-[:NEXT_FRAME {dt_sec, pose_delta}]->(:Experience)` 연결.
  `pose_delta` = 직전 프레임 대비 head_pose L2 이동량(양쪽 pose 있을 때).
- 응답에 `frame_linked`, `pose_delta` 추가.

이 legacy 경로에는 `device_id`/`session_id`/`frame_id`, actor, action, 사전 prediction,
outcome 결박이 없다. 또한 기존 `pose_delta`는 7개 pose 원소를 한 L2 값으로 합쳐 위치(m)와
쿼터니언 성분을 섞는다. 따라서 이 경로의 저장 성공이나 `frame_linked=true`만으로 유효한
감각운동 action→outcome 또는 비비의 행동 증거라고 판정하면 안 된다.

## 엄격 capture 계약 v1(오프라인 준비 완료, runtime 미연결)

버전은 `bibi.sensor-action-outcome/v1`이다. 현재 이 버전을 받는 HTTP endpoint와 Neo4j 저장
경로는 아직 연결하지 않았다. 캡처 송신부를 연결하기 전에는 JSON/JSONL을 파일로 내보낸 뒤
다음 read-only CLI로 검사한다.

```powershell
E:/A2A/our-a2a-project/.venv/Scripts/python.exe -B scripts/research/sensor_contract_audit.py <capture.jsonl>
```

`--require-bibi-agency`를 추가하면 구조적으로 유효한 `actor=bibi` action→prediction→outcome
chain이 하나도 없을 때 exit code 2를 반환한다. 파싱/파일 오류는 1, record reject는 2,
요구 gate 충족은 0이다. CLI는 DB/API에 접근하거나 파일을 수정하지 않는다.

### 레코드 순서와 공통 필드

한 세션의 JSONL 순서는 다음과 같다.

`session_start → observation → action → prediction → 다음 observation → outcome → session_end`

모든 레코드는 다음 공통 필드를 가진다.

| 필드 | 설명 |
|---|---|
| `schema_version` | 정확히 `bibi.sensor-action-outcome/v1` |
| `record_type` | `session_start`, `observation`, `action`, `prediction`, `outcome`, `session_end` 중 하나 |
| `record_id` | 스트림 전체에서 중복되지 않는 ID |
| `device_id`, `session_id` | 모든 참조 레코드에서 정확히 일치해야 하는 장치/세션 경계 |
| `provenance` | 비어 있지 않은 `source`, `producer` 문자열 |

`session_start`/`session_end`에는 timezone이 있는 ISO 8601 `recorded_at`을 기록한다. 경계가
없는 부분 파일은 각 레코드가 유효할 수는 있지만 완전한 세션 증거는 아니다.

### observation

- `observation_id`, `frame_id`, 0부터 증가하는 정수 `frame_index`
- `captured_at`과 `received_at`을 따로 기록하고 `captured_at <= received_at`이어야 한다.
- `coordinate_frame`을 명시한다.
- `pose.position_m`은 유한한 숫자 3개(m), `pose.orientation_xyzw`는 유한하고 정규화된
  쿼터니언 4개다.
- `depth.provenance`는 `measured|heuristic|missing` 중 하나다. measured/heuristic은
  `method`, `units=normalized_fraction`, 정규화된 3~5개 `bins`를 포함한다. missing은
  `bins=null`로 기록한다. heuristic 값을 measured depth로 승격하지 않는다.

프레임 ID 중복과 frame index/캡처 시각 역전은 reject한다. index gap, depth missing,
heuristic depth는 유효성 reject와 분리해 evidence insufficiency로 집계한다.

### action, prediction, outcome

- action: `action_id`, `source_observation_id`, `recorded_at`, `actor=human|scripted|bibi`,
  `motion.coordinate_frame`, `translation_m[3]`, `rotation_vector_rad[3]`. translation은 해당
  공통 좌표계의 방향 벡터(m)다. rotation vector는 같은 좌표계의 axis-angle 표현으로,
  벡터 방향이 회전축이고 norm이 최단 회전각(rad, 0..pi)이다. `actor=bibi`에는 실제 선택을
  추적할 `policy_decision_id`가 필수다.
- prediction: `prediction_id`, `action_id`, `based_on_observation_id`, `recorded_at`, 비어 있지
  않은 `expected`. outcome 관측 전에 기록되어야 한다.
- outcome: `outcome_id`, `action_id`, `prediction_id`, `observation_id`, `recorded_at`. source와
  다른 observation을 가리키며 같은 device/session 안에서만 연결한다.

사람이 헤드셋을 움직였으면 `actor=human`, 사전 고정 동작이면 `scripted`, 비비가 실제로
선택하고 `policy_decision_id`로 추적되는 경우만 `bibi`다. human/scripted chain은 관측/행동
모델 데이터로 유효하지만 비비 agency evidence에는 포함되지 않는다.

pose의 `orientation_xyzw`는 장치 로컬 축을 공통 좌표계로 보내는 자세로 해석하고, 공통
좌표계에서의 관측 상대회전은 `q_outcome * inverse(q_source)`로 계산한다. 엄격 비교는 translation norm(m)과
shortest quaternion rotation(rad)을 별도로 계산한다. 동일한 회전을 나타내는 `q`와 `-q`는
같은 것으로 처리한다. `translation_error_m`은 실제 이동벡터와 명령 이동벡터의 residual norm,
`rotation_error_rad`는 실제 상대회전과 명령 axis-angle 회전 사이의 quaternion geodesic이다.
방향/회전축을 버린 magnitude 차이가 아니며 단일 혼합 delta를 만들지 않는다. 연속 pose의
coordinate frame이 바뀌고 transform이 없으면 비교하지 않고 insufficient evidence로 기록한다.

완전한 합성 예시는
[`claudedocs/research/sensor_contract_synthetic_fixture_v1.jsonl`](../claudedocs/research/sensor_contract_synthetic_fixture_v1.jsonl)에 있다.
이는 테스트용 가상 값이며 실제 Quest/카메라/로봇 capture나 physical validation이 아니다.

## 왜 필요한가 (근거)
`claudedocs/baseline/embodied_prediction.py`(2026-07-12): 기존 45프레임(정적 데스크 장면)에서
누적 그래프가 next-frame 객체를 **popularity baseline조차 못 이김**(R@10_new 0.51 vs 0.55).
정적·무동작 장면에선 next-frame≈current-frame 이라 구조적 예측의 여지가 없다. **머리 움직임
(pose delta)** 이 있어야 "왼쪽으로 돌리면 X가 보인다"는 진짜 감각운동 예측이 성립한다. 즉
pose/depth 없이는 embodied 자기학습을 **측정조차 할 수 없다.**

## 데이터 수집 요청 (사용자 액션) — **다양성 최우선**
> 근거: 합성 스케일링 연구(`claudedocs/research/SCALING_STUDY_2026-07-13.md`)가 정량화 —
> 자기학습 신호(RW 음성증거의 빈도 대비 우위)를 결정적으로 만드는 건 **프레임 수(밀도)가 아니라
> 서로 다른 장면 수(다양성)**. 우위: 단일장면 −0.5% → 4장면 +3.7% → 16장면 +4.7% → 32장면 **+9.5%**.
> 밀도만 늘리면(같은 장면 더 오래) 우위는 오히려 완만히 감소.

- **최우선 = 장면 다양성**: 한 데스크 장면 반복 ✗. **방·주방·거실·야외·사람·이동 등 서로 다른 맥락**을
  많이(수십 장면+) 수집 ✓. 각 장면 안에서 **머리를 움직이며**(pose delta) 촬영.
- 밀도(장면당 프레임 수)는 2차 — 각 장면 수백 프레임이면 충분, 그보다 **새 장면 추가**가 더 가치.
- 수집 후: `python scripts/baseline/embodied_prediction.py` 재측정 → graph_spread가 popularity를 넘고
  pose-조건부 예측이 성립하는지 = embodied 자기학습 신호. (`prequential_experiment.py`로 RW 우위도 재확인.)
