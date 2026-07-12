# Identity & Access-Control — Owner Recognition

> **목표**: 비비가 owner(박재현)를 다른 사람과 **구분·인식**하고, 기억에 대한 **접근 권한을 차등**한다.
> **작성**: 2026-07-10 · 근거: 신경과학 7기전(peer-reviewed) + AI/ML SOTA + 업계 9제품 + 코드 실측.
> **제1원칙 정합**: 사회뇌(social brain) 확장. 인식=연상 결합/패턴완성, 인가=별도 정책층.

---

## 1. 문제 정의 (코드 실측 2026-07-10)

| 발견 | 증거 |
|---|---|
| 정체성 = **자기신고 plaintext 문자열** | `speaker_id` localStorage `'self'`(sense/page.tsx:239) → route.ts:29 무검증 forward → conversation_handler.py:371 raw 소비. `/api/conversation` auth guard 없음 |
| owner **박재현 파편화** | 개발자/형/사용자/엄마 = 4개 별도 `:Concept`. identity 링크 없음. `:Person` 노드 타입 **부재**. 4개 중 직접 엣지는 `개발자-RELATES_TO-사용자` 하나(단순 공출현) |
| **음성 생체증거 낭비** | `/api/audio/transcribe`(api_server.py:2257)에 오디오 도착 → Gemini STT 후 **bytes 폐기**(2274,2311). speaker embedding/diarization 없음 |
| UserModel ↔ Concept 분리 | `UserModel{speaker_id=mom/brother}` 존재하나 `:Concept 엄마/형`과 disjoint (INTERESTED_IN 링크 0) |

**근본 원인**: 뇌의 CA2식 "인물 인식 게이트"가 없어, 사람 역할이 person이 아니라 **사물 개념**으로 저장됨.

---

## 2. 신경과학 근거 (접근계층의 청사진, 전부 peer-reviewed)

| 뇌 기전 | 논문 | 그래프 대응 |
|---|---|---|
| 개념/정체 세포 (불변·다감각 단일 노드) | Quiroga 2005 *Nature* (1931) | `(:Person)` 허브 1개/인물 |
| **CA2 사회기억** (아는 개인 vs 낯선 이 게이트) | Hitti & Siegelbaum 2014 *Nature* (902) | 입력마다 speaker/face를 기존 Person과 대조 |
| 친숙성 vs 회상 (이중처리) | Eichenbaum 2007 *Annu Rev Neurosci* (2594) | 친숙성=degree/interaction, 회상=INTERACTED_WITH 순회 |
| mPFC 자기참조 (owner 특권) | Kelley 2002 *J Cog Neurosci* (1600) | `(:Self)` + `[:IS_OWNER]` + salience↑ |
| ATL hub-and-spoke (amodal 결합) | Patterson 2007 *Nat Rev Neurosci* (2568) | 별칭 spoke → 하나의 Person 허브 |
| FFA 얼굴 / TVA 목소리 | 1997 *J Neurosci* / 2000 *Nature* | face/voice embedding 채널 |

---

## 3. 제안 아키텍처

**대원칙**: 인식(who is speaking, confidence-scored) ≠ 인가(what may they see, 별도 정책층). — Alexa/Google/Zep 공통.

| # | 작업 | 뇌/업계 근거 | 의존성 |
|---|---|---|---|
| **0** | **owner token** (env `OWNER_SECRET`, dashboard localStorage device-bound, /api/conversation 시 전송·대조) — honor-system 대체 최소 앵커 | Apple: owner는 앱 밖에서 선언 | 신규 dep 0 (문자열 비교) |
| **1** | `:Person {person_id UNIQUE, canonical_name, role∈{owner,family,stranger}, access_clearance}` | 개념/정체 세포·ATL 허브 | neo4j-patterns skill 준수 |
| **2** | entity resolution **seed** (owner 확인, **auto-merge 금지**): owner←개발자+사용자. mom/brother→각자 Person + `FAMILY_OF`. 비파괴 `ALIAS_OF`/`SAME_AS`, 원본 보존 | ATL 결합, 단 다른 사람=다른 허브 | ⚠️ §5 결정 필요 |
| **3** | WHO 인식 (layered): (a) speaker_id→Person + token; (b) **최고가치**: `/api/audio/transcribe`에서 폐기 전 **ECAPA/Resemblyzer voiceprint** 캡처→owner 대조; (c) 옵션: Quest jpeg→InsightFace | TVA 목소리·FFA 얼굴, 다중모달 corroboration | (b) speaker-embed 모델, mic 경로 |
| **4** | 접근계층 `access_tier∈{public,family,owner_private}` on Concept/Experience. **READ 시 v30 절차대로** loadRelevantConcepts/Experiences·formatMemoryContext를 clearance 필터 | mPFC 특권 + 친숙성/회상 이중처리 | v30 수정 절차 준수 |
| **5** | write guard: stranger/low-conf = public만 쓰기, owner_private 불가·tier 승격 불가 | default-deny | — |

---

## 4. 접근 계층 (업계 4단 — Alexa/Google/Apple/Letta/Zep 공통)

1. **OWNER** — 명시적 provision(생체는 재인증만). 전 영역 R/W.
2. **FAMILY/KNOWN** — 등록 인식된 개인, **각자 격리 메모리**(cross-read 차단, 키=speaker_id/Person).
3. **GUEST** — 저신뢰/미인증 → 공용·일반만(read-only).
4. **STRANGER** — 접근 0. 단 **라벨링은 함**(인식≠인가). Quest 헤드셋 촬영 시 consent 대상.

**복사할 primitive**: Zep *"검색 도구는 정확히 한 scope에만"* · Alexa *authenticationConfidenceLevel* ladder(voice-only <400 vs voice+PIN =400).

---

## 5. 냉정한 진실 & 미해결 결정

**진실**
- 인식은 **가능**(Alexa Voice ID/Google Voice Match/Apple 실배포)하나 **soft 개인화지 강한 인증 아님**. 음성/얼굴 spoofable — *"Breaking Security-Critical Voice Authentication"* IEEE S&P 2023이 은행 ASV+방어 우회. **최고 계층엔 2차 요소 필수.**
- 현 스택 **생체신호 없음**(SmolVLM=이름만, 음성 폐기). voiceprint가 첫 단추.
- `speaker_id` 기반 계층을 지금 켜면 = **security theater**(문자열 맞히면 owner).

**⚠️ 미해결 결정 (사용자)**: **mom/brother = 실제 타인 vs 박재현의 테스트 페르소나?**
- 실제 타인 → 별도 Person + FAMILY_OF (owner 병합 금지).
- 테스트 페르소나 → owner로 병합 가능.
- **잘못 병합 = 서로 다른 사람 기억 leak** → 정밀도 > 재현율, human-in-the-loop.

---

## 6. Hard problems (ML 리서치)
open-set 거부(낯선 이 reject) · few-shot 등록(owner 1명) · spoofing/liveness(비비 TTS가 역으로 위험) · 생체 PII 거버넌스(GDPR Art.9, Quest 촬영 bystander) · 템플릿 aging · 제1원칙 긴장(하드 분류기 vs 연상 결합).

## 참조
- 신경과학: `memory/brain_science_references.md`
- 상위: `memory/identity_access_control_2026-07.md`, `memory/first_principle.md`, `memory/architecture_brain_clients.md`
- 코드: neo4j_db.py(UserModel:154, get_or_create:1543), conversation_handler.py:371-515, api_server.py:2257(audio), :1239(quest vision)
