# Embodiment 데이터 파이프라인 — 진행 보고 (2026-07-12)

> 최우선 레버(PHASE1_PLASTICITY_FINDINGS §5·§7): 데이터 밀도 = 모든 실험의 바인딩 제약.
> Quest passthrough를 밀집·시간적 감각운동 스트림으로 만드는 작업. measure-first로 진행.

## Step 1 — 현 파이프라인 측정 (measure-first)
`POST /api/vision/quest-concepts` (A4.3)가 **이미 존재하고 올바르게 작동**: 프레임당 Experience
1개(task_type='vision') → INVOLVES concepts → visual_cooc Hebbian. 측정 결과:
- **45 vision 프레임** (2026-04-24~05-12), 프레임당 **mean 5.44 객체**(대화 2.8보다 밀집),
  프레임간 gap 36/44이 **<10s** = 진짜 프레임 시퀀스. 69 시각객체, visual_cooc 엣지 173.
- **0 프레임이 depth/pose 보유** — 감각운동 신호 부재.
- **바인딩 제약 = 수량**: 2026-05-12 이후 스트리밍 없음. 밀집화는 Quest 세션(하드웨어) 필요.

## Step 2 — 프레임 시퀀스 구조 확인
주 세션 = 30프레임·193s 연속 데스크 장면(keyboard 36/45, bottle, monitor, liquid…).
next-frame **Jaccard 0.31**(지속성=예측가능성), 다음 프레임당 **3.1개 새 객체**(지속성이 못
얻는 진짜 예측 대상). → next-frame 예측이 측정 가능.

## Step 3 — embodied next-frame 예측 하니스 (`scripts/baseline/embodied_prediction.py`)
북극성 지표: 언어가 아니라 **세계(감각운동)를 예측하는가**. frame_t → frame_t+1 객체 예측.
36 transition, 예측기 비교:

| 예측기 | R@10_all | R@10_new(진짜 예측) |
|---|---:|---:|
| persistence(=현프레임) | 0.469 | 0.00 (정의상) |
| popularity(최빈객체) | 0.274 | **0.546** |
| graph_spread(누적 뇌) | 0.254 | 0.511 |

**결과(정직)**: 누적 그래프가 **popularity baseline조차 못 이김**(0.51 vs 0.55). 이유: (a) 36
transition·저검정력, (b) **정적 단일 장면**(keyboard 80% 프레임)이라 popularity가 천장, (c)
**움직임 신호 부재** — 정적 장면은 next-frame≈current라 구조적 예측 여지 없음.
→ **세 번째로 확인된 동일 결론**: 언어(256이벤트)·학습head(518노드)·embodiment(45프레임) 전부
바인딩 제약 = **데이터 수량+다양성+움직임**. 이 실험이 pose/depth 필요성의 **증거 기반 정당화**:
움직임 없이는 감각운동 예측 과제가 degenerate.

## Step 4 — 파이프라인 확장 (증거 기반, 비파괴·검증됨)
1. **pose/depth 캡처** (`api_server.py` `quest-concepts` 엔드포인트): `head_pose`, `depth_bins`
   선택 필드 추가 → Experience 1급 속성 + extras 저장 (하위호환). 계약: `docs/QUEST_APK_CONTRACT.md`.
2. **프레임 시퀀스** (`neo4j_db.link_vision_frame_sequence`): 직전 vision 프레임(≤30s)과
   `(:Experience)-[:NEXT_FRAME {dt_sec, pose_delta}]->(:Experience)` 연결. pose delta = head_pose
   L2 이동량. **synthetic 프레임으로 Cypher end-to-end 검증**(dt/pose_delta/멱등/정리 OK).
3. **기존 프레임 backfill** (`scripts/maintenance/backfill_frame_sequence.py`, 멱등·`--rollback`):
   45 고립 프레임 → **36 NEXT_FRAME 엣지, 9 시퀀스**. 신규 엣지 타입이 실데이터서 즉시 exercise
   (dead-code 방지). 기존 프레임은 pose 없어 pose_delta=null.
- 라이브 그래프 비파괴(신규 엣지·선택속성만), 프로덕션 규칙·conversation_handler 미변경.

## 결론 & 다음 (사용자 액션 필요)
- 파이프라인은 **준비 완료**: pose/depth 캡처 + 프레임 시퀀스 서버측 구현·검증. 이제 **다양한
  장면에서 머리를 움직이며 Quest 세션을 대량 스트리밍**하면 밀집·움직임 있는 감각운동 스트림이
  쌓인다. (계약: `docs/QUEST_APK_CONTRACT.md` — APK가 head_pose/depth_bins 전송하도록 업데이트 필요.)
- **막힌 지점(정직)**: Quest 프레임 생성은 하드웨어-인-더-루프 → 자율로 못 만듦. APK가
  head_pose/depth_bins 를 보내도록 업데이트 + 다양한 세션 수집 = **사용자/기기 의존**.
- 수집 후 `embodied_prediction.py` 재측정 → graph_spread가 popularity 초과 + pose-조건부 예측
  성립하면 = **embodied 자기학습 신호**. (그 전까진 파이프라인만 준비된 상태.)

## 산출물
- `scripts/baseline/embodied_prediction.py` (embodied next-frame 예측 하니스, 재사용)
- `scripts/maintenance/backfill_frame_sequence.py` (NEXT_FRAME backfill, 멱등·rollback)
- `neural/baby/{api_server.py, neo4j_db.py}` (pose/depth 캡처 + 시퀀스 링크, 검증됨)
- `docs/QUEST_APK_CONTRACT.md` (클라이언트 계약)
- `claudedocs/baseline/embodied_vision_v1_20260712.json`
