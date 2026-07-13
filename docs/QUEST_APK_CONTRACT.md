# Quest APK → Brain 수신 계약 (POST /api/vision/quest-concepts)

> Phase 4 embodiment. 서버는 아래 필드를 **선택(optional)** 으로 이미 받는다(2026-07-12,
> `neural/baby/api_server.py`). **Quest APK가 이 필드를 채워 보내기 시작해야** 감각운동
> 신호가 기록된다. 안 채우면 기존 동작 그대로(하위호환) — 단 그럴 경우 pose/depth 는 영원히
> null 이라 embodied 예측이 성립하지 않는다(아래 §근거).

## 엔드포인트
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
