# AGENTS.md — Baby AI Brain (Claude Code · Codex 공용 마스터)

> **크로스툴 단일 진입점.** Codex는 이 파일을 자동 로드한다. Claude Code는 `CLAUDE.md` 최상단의 `@AGENTS.md`로 임포트한다.
> ⚠️ **Claude auto-memory(`C:\Users\SOGANG\.claude\projects\E--A2A\memory\`)는 Claude 전용 — Codex는 못 읽는다.** Codex는 아래 "상세 문서"의 경로를 직접 열어라. **세션 인계는 반드시 이 파일 + repo 공유 파일을 통해서만** 한다.

## 🔖 현재 상태 / 재개 (2026-07-13 체크포인트)
**"이어서 하자"면 여기부터.**
- **🔴 보안(2026-07-13 처리완료)**: `.env.bak-20260512`(실키) push 차단됨 → secret 있던 커밋 `40ed387`→`5cfe1a5`로 amend(unpushed라 안전) + `.gitignore` `.env.bak*` 보강. **키 원격 미도달, push 이제 통과.** 디스크 .env.bak은 gitignore됨(삭제/이동 권고). git 작업 전 `.env*` 백업이 안 딸려가는지 항상 확인.
- **Gap#6 모니터링 상시화 완료(2026-07-13)**: `scripts/monitoring/brain_health_monitor.py`(4지표: prediction/collapse/forgetting/plasticity → `claudedocs/monitoring/brain_health.jsonl` append + alert). **consolidate(수면) 훅**(`_spawn_health_monitor`)으로 자동 실행. baseline 🟢(lift 7.86, isolated 0.38, recall 0.70).
- **완료(검증)**: decay fix · identity/access-control · LLM 복구 · 자기학습 로드맵 · **Phase 1 가소성 실험(2026-07-12)** · embodiment 파이프라인 · Gap#6 모니터링.
- **Phase 1 결과 = 자기학습 신호 발견(정정본)**. 상세: `claudedocs/baseline/PHASE1_PLASTICITY_FINDINGS.md`, `RESEARCH_SYNTHESIS_2026-07-12.md`. 하니스: `scripts/baseline/{plasticity,prequential}_experiment.py`.
  - ① **정적 랜덤분할**: 순진한 가소성(STDP/항상성/양성전용 PE게이팅)이 가산빈도 baseline(lift 5.34)을 **못 이김**(정적지표는 빈도 보상 → 가산 Hebbian이 천장). = 초기 "반증".
  - ② **리서치 정정**(프런티어 6각 fan-out): 틀린 규칙×틀린 지표였음. 빠진 조각=**Rescorla-Wagner 음성증거**(a 켜지고 후보 b 안 켜지면 w_ab를 깎음 → w_ab=P(b|a) **보정확률**). 지표=**prequential(예측→채점→학습) + EdgeBank(암기) baseline**.
  - ③ **prequential 재실험**: RW가 빈도(additive 0.494)·암기(EdgeBank 0.426)를 **유의·강건**하게 이김(MRR **0.510**, paired 484/282 p≈0, 다중시드 최악도 초과), **보정됨**(ECE 0.038), 우위는 **time-shuffle서 붕괴 = 진짜 시간적 학습**(밀집화 artifact 아님).
- **④ 학습가능 head 리허설(gap#1)**: 방향성 임베딩+온라인 SGD head(`scripts/baseline/trainable_head_experiment.py`) = MRR 0.415 < 규칙(additive 0.494/rw 0.512) < EdgeBank(0.426), 곡선기울기 음수. **518노드/256이벤트 규모선 파라미터 코어가 손튜닝 스칼라를 못 이김**(리서치 scale caveat 실증).
- **⑤ embodiment 파이프라인 착수·준비완료(2026-07-12)** ([[embodiment_pipeline_2026-07]], `claudedocs/baseline/EMBODIMENT_PIPELINE_2026-07-12.md`): 3-실험 전부 "데이터 밀도+움직임=바인딩 제약" 실증 → **Phase 4를 Phase 2 앞으로 승격**. `quest-concepts` 엔드포인트 이미 작동(45프레임·밀집). `embodied_prediction.py`=정적장면서 graph가 popularity 못 이김(R@10_new 0.51<0.55)=움직임 필수 증거. **확장(비파괴·검증)**: `api_server.py`에 `head_pose`/`depth_bins` 선택캡처 + `neo4j_db.link_vision_frame_sequence`로 `NEXT_FRAME{dt_sec,pose_delta}` 시퀀스 링크(synthetic Cypher 검증) + `backfill_frame_sequence.py`로 기존 45프레임→36엣지·9시퀀스. 계약 `docs/QUEST_APK_CONTRACT.md`.
- **다음 스텝 (밀도 먼저 — 사용자·기기 의존)**:
  - **최우선 = Quest 데이터 수집**: APK가 `head_pose`/`depth_bins` 전송하도록 업데이트(`docs/QUEST_APK_CONTRACT.md`: Unity `InputTracking` pose + depth 히스토그램) + **다양한 장면서 머리 움직이며 대량 세션 스트리밍**(정적 반복 금물=popularity 천장). 수집 후 `python scripts/baseline/embodied_prediction.py` 재측정=embodied 신호 판정.
  - ✅ (완료 2026-07-13) Gap#6 모니터링 상시화 — `scripts/monitoring/brain_health_monitor.py` + consolidate 훅.
  - (보류) Gap#1 학습 head·Phase2 로컬코어 = 스트림 커진 뒤.
  - (비가역·**사용자 확인 후**) 방향성 엣지 마이그레이션 + RW 프로덕션 `hebbian_update` 반영.
- **전제**: Neo4j(Baby_Robotics, bolt 7687) 켜기. embodiment 확장은 라이브 그래프 비파괴(신규 엣지·선택속성만)·conversation_handler 미변경. 실 ingest 테스트엔 uvicorn 필요.

## 🧭 불변 원칙 (요약)
- **제1원칙**: 인간 뇌를 본떠 아기부터 키우는, 로봇 이식용 AI 뇌. **신경과학적 타당성 > 코드 최적화.** LLM = 교체 가능한 몸, 학습/기억/성장 = LLM-free 내부 그래프 알고리즘.
- **북극성**: 진짜 자기학습 = 경험이 코어 파라미터를 바꿈. frozen-LLM+graph는 자기학습 아님. **"API 탈피 = 자기학습 전환"은 같은 한 수**(→ 로컬 trainable 코어).
- **아키텍처**: Brain = FastAPI + Neo4j + Redis 백엔드; Quest/PC/로봇 = client. (구 Supabase/Edge Function 아님.)
- **프로그램**: 자기성장 아기 뇌 Phase 0~5, 장기 ~1.5~3년. 마일스톤 = 예측오차 곡선 하강(월 아님).

## ⚙️ 코드 컨벤션 (필수 — 상세는 CLAUDE.md)
- **"정의만 되고 호출 안 됨" 금지**: 새 함수 추가 시 호출 지점 grep 검증(이 프로젝트 5회+ 반복 실수).
- **`conversation_handler.py`(v30) 미변경**: 수정은 endpoint/db층에서(MVP 제약).
- 새 의존성 신중(분석 스크립트 예외). **git commit·push는 사용자 명시 시만.**
- 실행: `python -m neural.baby.api_server --port 8000`(상대 import). brain LLM = Gemini(gemini-flash-latest).

## 📍 상세 문서 (어디를 읽나)
| 무엇 | 경로 | 접근 |
|---|---|---|
| 세션 로그(최신) | `CHANGELOG.md` 최상단 | 공유 |
| 현재 상태 | `Task.md` 상단 배너 | 공유 |
| 상위 로드맵 | `ROADMAP.md` | 공유 |
| 설계문서 | `docs/IDENTITY_ACCESS_CONTROL.md` | 공유 |
| Claude 상세 규약(skills·subagents·세션프로토콜) | `CLAUDE.md` | 공유(Codex도 읽을 것) |
| **전략·프로그램(최상위/북극성)** | `C:\Users\SOGANG\.claude\projects\E--A2A\memory\` → `MEMORY.md`, `program_roadmap_2026-07.md`, `self_learning_architecture_2026-07.md`, `beyond_api_llm_strategy_2026-07.md`, `identity_access_control_2026-07.md` | **Claude 자동** / Codex는 경로로 직접 |
| 재사용 연구지식(자기학습 서베이) | `D:\Obsidian\Bandi\강화학습\자기학습 AI 프런티어 2026 (경험의 시대).md` | 공유(볼트) |

## 🤝 하이브리드 도구 규율 (Claude ↔ Codex)
- **동시 실행 금지**: 같은 프로젝트의 `.serena`·Claude auto-memory·MCP memory에 두 도구 **동시 쓰기 금지**(race condition). **순차 인계**: 한 도구 종료 → 공유 파일로 결과 남김 → 다른 도구 시작.
- **인계 매체 = 공유 파일**: 이 AGENTS.md("현재 상태/재개") + CHANGELOG/Task/ROADMAP/docs + Bandi 볼트. Claude auto-memory 요지는 이 파일에 반영해 둘 것(Codex가 볼 수 있도록).
- **세션 종료 시(양 도구 공통)**: `CHANGELOG.md` 갱신 + **이 파일의 "현재 상태/재개" 섹션 갱신**. (Claude는 추가로 auto-memory도 갱신.)

## 📂 어디서 열까
- **Codex**: `E:\A2A\our-a2a-project`에서 열면 이 AGENTS.md 자동 로드 → "이어서 하자" 작동.
- **Claude Code**: `E:\A2A`에서 열면 auto-memory 자동 로드(권장); `our-a2a-project`에서 열면 CLAUDE.md→`@AGENTS.md`로 이 체크포인트 로드. 어느 쪽이든 재개됨.
