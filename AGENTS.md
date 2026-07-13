# AGENTS.md — Baby AI Brain (Claude Code · Codex 공용 마스터)

> **크로스툴 단일 진입점.** Codex는 이 파일을 자동 로드한다. Claude Code는 `CLAUDE.md` 최상단의 `@AGENTS.md`로 임포트한다.
> ⚠️ **Claude auto-memory(`C:\Users\SOGANG\.claude\projects\E--A2A\memory\`)는 Claude 전용 — Codex는 못 읽는다.** Codex는 아래 "상세 문서"의 경로를 직접 열어라. **세션 인계는 반드시 이 파일 + repo 공유 파일을 통해서만** 한다.

## 🔖 현재 상태 / 재개 (2026-07-14 체크포인트)
**"이어서 하자"면 여기부터.** 상세 이력·수치는 `CHANGELOG.md` 최상단 + `claudedocs/**/2026-07*.md`.

### 어디까지 왔나 (한눈에)
**자기학습 체인 end-to-end 검증 + 살아있는 시스템 전환 완료** (커밋 `d7f1b32` push됨).
- Phase 0 기반 ✅ · **Phase 1 가소성 ✅**: RW 음성증거(w_ab→P(b|a))=자기학습 신호, **다양성 주도**(prequential서 빈도·암기 초과, time-shuffle서 붕괴=진짜 시간학습). `PHASE1_PLASTICITY_FINDINGS.md`.
- **Phase 2 코어 내재학습 ✅ 이번 세션 완주** (`PHASE2_SLEEP_DISTILL_2026-07-13.md`): ① 학습코어가 그래프 역전(N≈2~4천, **weight-homeostasis 필수**·causal 확인; 없으면 발산해 짐) ② CLS 안티망각(순차태스크서 online −0.32 vs replay +0.03) ③ **실 LLM+LoRA(Qwen2.5-0.5B)가 실 Neo4j 아기 특이연상(비비·형) 학습**(identity MRR 0.081→0.176, 3시드) ④ **살아있는 로컬 코어**: 어댑터 디스크 영속(`models/local_core_adapter/`), 누적성장 0.089→0.123→0.152 ⑤ **라이브 트리거**: consolidate 훅서 야간 자동학습, env `LOCAL_CORE_DISTILL=1` opt-in, 프로덕션 하드닝(게이팅+락+OOM/backoff, adversarial review).
- **Phase 4 embodiment**: 파이프라인 준비됨(pose/depth 캡처·`NEXT_FRAME` 시퀀스)이나 **Quest 데이터 없음=병목**. `EMBODIMENT_PIPELINE_2026-07-12.md`.
- 인프라: Gap#6 brain health 모니터링 상시화 · 보안 fix(.env.bak) · torch(cu124)/transformers/peft `.venv` 설치 · RTX 4070 12GB.

### 핵심 진단 (정직)
1. **뇌가 "배우지만 무기력"**: 로컬 코어가 밤마다 학습하나 **wake에서 아무도 안 씀**(대화=Gemini 도구, 회상=그래프). 자기학습은 진짜지만 아직 **행동에 영향 X** — 북극성의 (1)"grounded 예측오차가 행동을 이끈다"가 빠짐.
2. **모든 병목=데이터 밀도** (언어256·노드518·프레임45·실그래프2241, 4번 확인). Quest 다양장면 수집이 근본 레버(하드웨어·사용자 의존).

### 다음 작업 플랜 (2-트랙)
- **[A] 사용자 몫(근본 레버)**: Quest **다양장면** 수집(방·주방·야외·사람, 머리 움직이며; 스케일링연구=다양성>밀도) + 살아있는 코어 **켜기**(`LOCAL_CORE_DISTILL=1` + Neo4j 상시). 계약 `docs/QUEST_APK_CONTRACT.md`.
- **[B] 자율·최우선 추천 = Phase 3 예측오차 루프 닫기**: 코어/그래프의 예측오차(surprise)를 **wake에서 살아있는 신호로** → 무엇을 통합·탐색(호기심)·주의할지 이끌고, 코어 예측이 Gemini 응답에 관련개념 prime. "무기력한 학습자"→"자기동기적 학습자". 데이터 흐르면 자기증폭.
- **[C] 자율·대안**: 운영화(실제 켜서 며칠 성장추적) + collapse(effective rank≈2) 장기감시.
- **⚠️ 메타**: 과학은 검증됨. [B]도 데이터 얇으면 신호 약할 수 있음 → "[C]/실사용으로 데이터 먼저, [B] 나중"도 합리. **사용자 판단 대기.**
- (보류·비가역, 사용자 확인 후) 방향성 엣지 마이그레이션 + RW 프로덕션 `hebbian_update` 반영.

### 전제
Neo4j(Baby_Robotics, bolt 7687) 켜기 **(현재 다운)**. Phase 2 실행엔 GPU(RTX 4070)+`.venv`. 살아있는 코어 켜려면 `LOCAL_CORE_DISTILL=1`. 라이브 그래프 비파괴·conversation_handler(v30) 미변경 원칙 유지.

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
