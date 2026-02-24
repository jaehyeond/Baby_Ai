# ISMAR 2026 투고 전략

**작성일**: 2026-02-19
**D-Day**: Abstract 3/9 (D-18) | Paper 3/16 (D-25)
**학회**: IEEE ISMAR 2026, Bari, Italy, Oct 4-9
**결과 게재**: IEEE TVCG (SCIE Q1, IF 6.55)

---

## 1. 핵심 판단: "시각화만으로 통과되나?"

**결론부터 말하면 — 단순 3D 시각화만으로는 안 된다.**

ISMAR 리뷰어는 소위 "AR Tax"를 적용한다. 모든 논문에 이 질문을 던진다:

> "이걸 일반 모니터에서 봐도 되는 거 아닌가? AR/MR이 왜 필요한가?"

대답이 "글쎄..."면 reject된다.

하지만 우리는 "단순 시각화"를 내는 게 아니다. 전략은 이렇다:

| 시나리오 | 통과 가능성 |
|---------|-----------|
| WebGL 3D만 (데스크탑 브라우저) | **0/5** — desk reject |
| Quest 3S VR 모드만 추가 | 2/5 — "VR은 디스플레이일 뿐"이라는 반론에 취약 |
| Quest 3S **MR 패스스루** + 공간 배치 | 3/5 — AR 요소 충족, 하지만 기여가 약함 |
| MR + **User Study (2D vs MR 비교)** | **4/5** — 연구 질문 자체가 AR-centric |

**따라서 논문의 Research Question을 AR-centric으로 설계한다:**

> *"Mixed Reality 시각화가 AI 인지 과정의 이해에 2D/3D 대안보다 효과적인가?"*

시각화 시스템은 "도구"이고, **MR의 효과를 실증하는 것**이 논문의 핵심 기여가 된다.

---

## 2. 논문의 정체성

### 2.1 제목 후보

1. **BrainXR: Real-time Mixed Reality Visualization of Cognitive Processes in a Developmental AI System**
2. BrainXR: Evaluating Mixed Reality for Understanding Spreading Activation in Artificial Cognitive Architectures
3. Visualizing a Growing Mind: An Empirical Study of Mixed Reality for AI Cognitive Process Understanding

→ 1번 추천. 시스템 이름 + 기술 키워드 + 도메인이 모두 제목에 들어간다.

### 2.2 Research Questions

| # | Research Question | 왜 ISMAR에 맞는가 |
|---|------------------|------------------|
| **RQ1** | MR 시각화가 2D 대시보드보다 AI 인지 과정 이해에 효과적인가? | MR vs non-MR 비교 — ISMAR의 핵심 관심사 |
| **RQ2** | 해부학적 뇌 메타포가 추상적 네트워크보다 직관적인가? | 시각화 기법 평가 — VIS/ISMAR 공통 관심사 |
| **RQ3** | 실시간 확산 활성화 시각화가 AI 추론 과정 추적에 도움이 되는가? | 인터랙티브 시각화 효과 — 몰입 분석 분야 |

### 2.3 핵심 기여 (Contributions)

1. **BrainXR 시스템**: 발달 인지 AI의 내부 과정을 실시간 MR로 시각화하는 최초의 시스템
2. **해부학적 메타포 매핑**: 인공 인지를 생물학적 뇌 구조로 매핑하는 새로운 시각화 접근
3. **실증 평가**: 2D vs 3D-desktop vs MR 3-condition within-subjects user study

### 2.4 한 줄 요약 (Elevator Pitch)

> "BrainXR은 발달 인지 AI의 내부 과정을 Mixed Reality로 실시간 시각화하는 최초의 시스템이다. 사용자가 Quest 3S를 쓰고 테이블 위에 AI의 뇌를 놓으면, 대화할 때마다 뉴런 활성화와 확산 과정을 3D로 관찰할 수 있다."

---

## 3. 선행연구 갭 — 왜 이 논문이 새로운가

문헌 조사 결과 (NeuroCave, CNN Explainer, BabyAI, ACT-R, HoloAnatomy 등 30+ 논문 분석), 다음 5개 교차점에 선행연구가 **0건**이다:

### Gap 1: AI 인지과정의 XR 시각화

기존 AI 시각화(TensorBoard, GAN Lab, CNN Explainer, Distill.pub)는 **전부 2D 웹 기반**이다. AI 시스템의 내부 인지 과정을 VR/AR로 시각화한 연구는 없다.

### Gap 2: 발달적/시간적 AI 시각화

AI 시각화는 정적 스냅샷이거나 학습 커브(2D 그래프)뿐이다. AI가 "성장하면서" 지식 네트워크가 진화하는 과정을 시간축으로 시각화한 XR 시스템은 없다.

### Gap 3: 해부학적 메타포 + 인공 인지

의학 분야에서는 실제 뇌를 VR로 시각화한다(NeuroCave, SlicerVR). AI 분야에서는 추상적 다이어그램을 쓴다. **인공 인지를 해부학적 뇌 구조에 매핑**하는 시도는 없다.

### Gap 4: 감정-인지 결합 시각화

Affective Computing은 감정 "인식"에 집중한다. 감정이 학습률을 어떻게 조절하는지를 **3D로 실시간 표현**한 연구는 없다.

### Gap 5: 인지 아키텍처의 XR 인스펙션

ACT-R, SOAR, CLARION 같은 인지 아키텍처의 시각화 도구는 전부 원시적 2D이다. XR 기반 인지 아키텍처 인스펙션 시스템은 **존재하지 않는다**.

### Related Work 논문 목록

**반드시 인용 (Tier 1):**
- Hohman et al. (2019) "Visual Analytics in Deep Learning" — TVCG
- Fonnet & Prié (2021) "Survey of Immersive Analytics" — TVCG
- Keiriz et al. (2018) "NeuroCave" — Informatics
- Wang et al. (2021) "CNN Explainer" — VIS/TVCG
- Kwon et al. (2016) "Immersive Graph Visualization" — TVCG
- Dwyer et al. (2018) "Immersive Analytics" — Springer

**권장 인용 (Tier 2):**
- Chevalier-Boisvert et al. (2019) "BabyAI" — ICLR
- Anderson (2007) ACT-R cognitive architecture
- Collins & Loftus (1975) Spreading Activation theory
- Hart & Staveland (1988) NASA-TLX
- Brooke (1996) SUS

> [!warning] 인용 검증 필요
> 위 논문 목록은 학습 데이터 기반. 최종 논문 작성 전 Google Scholar에서 정확한 연도, 학회, DOI를 반드시 재확인할 것. 특히 ISMAR 2024-2025에 유사 논문이 나왔는지 확인 필수.

---

## 4. 기술 전략

### 4.1 현재 보유 자산

이미 작동하는 코드가 있다. 처음부터 만드는 게 아니다.

| 자산 | 파일 | 상태 |
|------|------|------|
| **RealisticBrain** 3D 렌더링 | `components/RealisticBrain.tsx` | 완성 — 9개 뇌영역, 구 좌표계, 활성화 파동(SpreadingRipple), 호버/선택 인터랙션 |
| **BrainVisualization** 추상 뷰 | `components/BrainVisualization.tsx` | 완성 — 500 뉴런 네트워크, Louvain 클러스터링, Astrocyte 메타노드 |
| **실시간 파이프라인** | `hooks/useNeuronActivations.ts` | 완성 — Supabase Realtime → neuron_activations INSERT → 3D 업데이트 |
| **사고 경로 패널** | ThoughtProcessPanel | 완성 — 직접 활성화 경로 + 확산 활성화 영역 표시 |
| **히트맵 모드** | RealisticBrain 내장 | 완성 — 누적 활성화 이력, emissive glow |
| **R3F + Three.js** | package.json | 설치됨 — R3F v9.5.0, Three.js v0.182.0, drei v10.7.7 |
| **/brain 페이지** | `app/brain/page.tsx` | 완성 — 해부학/추상 토글, 전체화면 3D |

### 4.2 아키텍처: Unity는 시각화 클라이언트

핵심 포인트 — **백엔드는 건드리지 않는다.** 기존 Supabase DB + Edge Functions는 그대로 두고, Unity는 **읽기 전용 시각화 클라이언트**로만 동작한다.

```
[사용자 대화] → [Edge Functions (대화 처리)] → [Supabase DB]
                                                    ↓ (읽기 전용)
                                              [Unity 시각화 클라이언트]
                                              Quest 3S에서 실행
```

### 4.3 Unity ↔ Supabase 통신

Unity에서 공식 Supabase SDK (`supabase-csharp`)는 Quest 3S (Android/IL2CPP)에서 WebSocket이 깨진다. 따라서:

| 용도 | 방식 | 라이브러리 |
|------|------|-----------|
| **초기 데이터 로드** | REST API (PostgREST) | `UnityWebRequest` (내장) |
| **실시간 뉴런 발화** | WebSocket (Phoenix Channel) | `NativeWebSocket` (endel/NativeWebSocket) |

**초기 로드 시 가져오는 데이터:**

| 요청 | 테이블/RPC | 데이터량 | 용도 |
|------|-----------|---------|------|
| 발달 단계 | `baby_state` → `development_stage` | 1 row | 뇌 크기, 활성 영역 결정 |
| 뇌 영역 | `brain_regions` | 9 rows | 구 좌표, 색상, 이름 |
| 뉴런 | `semantic_concepts` (LIMIT 500, ORDER BY usage_count DESC) | ~486 rows | 3D 뉴런 노드 |
| 직접 시냅스 | `concept_relations` (LIMIT 500, ORDER BY evidence_count DESC) | ~500 rows | 연결선 |
| 공활성화 | `experience_concepts` (LIMIT 500) | ~500 rows | 간접 시냅스 보강 |
| 활성화 히스토리 | RPC `get_brain_activation_summary` | heatmap + replay | 히트맵 + 초기 리플레이 |

**실시간 구독:**

`neuron_activations` 테이블의 INSERT 이벤트만 구독. 발화 이벤트 하나 올 때마다 `semantic_concepts`, `brain_regions`에서 이름/영역 매핑을 REST로 추가 조회.

### 4.4 추가 구현 필요 (ISMAR용)

| Step | 작업 | 기술 | 예상 시간 |
|------|------|------|----------|
| 1 | Unity 프로젝트 생성 + URP + Meta XR SDK | Unity 2022.3 LTS | 2h |
| 2 | `SupabaseRestClient` — 6개 테이블 REST 로드 | UnityWebRequest + PostgREST | 4h |
| 3 | `BrainDataManager` — 피보나치 배치 + Louvain 클러스터링 포트 | C# 재구현 | 4h |
| 4 | `NeuronRenderer` — GPU Instancing 500개 구체 | `Graphics.DrawMeshInstanced` | 3h |
| 5 | `ConnectionRenderer` — 프로시저럴 메시 시냅스 | 단일 Mesh, billboard quad | 3h |
| 6 | `RegionRenderer` — 9개 투명 구체 + 히트맵 | URP Transparent | 2h |
| 7 | `SupabaseRealtimeClient` — WebSocket + Phoenix 프로토콜 | NativeWebSocket | 6h |
| 8 | 활성화 이펙트 — 발광, 감쇠(3s/5s), 리플 | Emissive + 타이머 | 4h |
| 9 | VR/MR 인터랙션 — 레이캐스트 선택, 정보 패널 | Meta XR Interaction SDK | 4h |
| 10 | MR 패스스루 + 공간 배치 | OVRPassthroughLayer | 3h |
| **합계** | | | **~35h** |

### 4.5 클라이언트 측 재구현 항목

기존 R3F에서 JavaScript로 돌아가는 로직을 C#로 포트해야 한다:

1. **피보나치 구 배치** (`fibonacciSphere`) — 뉴런 3D 좌표 계산 (golden ratio spiral)
2. **간이 Louvain 클러스터링** — 시냅스 그래프 기반 뉴런 그룹핑 (max 10 iterations)
3. **Astrocyte 메타노드** — 클러스터당 1개, 중심점 + 멤버 목록
4. **시냅스 빌딩** — `concept_relations` 직접 연결 + `experience_concepts` 공활성화 합산
5. **활성화 감쇠 타이머** — direct 3초, spreading 5초
6. **히트맵 정규화** — activation_count / max_count

### 4.6 Quest 3S 스펙 + Unity 빌드 설정

| 항목 | 스펙/설정 |
|------|----------|
| SoC | Snapdragon XR2 Gen 2 |
| RAM | 8GB LPDDR5 |
| 디스플레이 | 1832×1920/eye, 72-120Hz |
| 패스스루 | **풀 컬러 RGB** (MR 지원) |
| 손 추적 | v2.2, 25-joint skeleton/hand |
| Scripting Backend | **IL2CPP** (Mono 불가) |
| Architecture | **ARM64 only** |
| Graphics API | **Vulkan** |
| Render Pipeline | **URP** (Built-in RP 불가) |
| Stereo Rendering | **Multiview** (single-pass, 양안 1회 렌더) |
| 배포 | **APK 사이드로드** (USB 연결 5분, 앱스토어 불필요) |

**필요 패키지:**
- `com.meta.xr.sdk.core` — 필수
- `com.meta.xr.sdk.interaction` — 컨트롤러/손 인터랙션
- `com.unity.nuget.newtonsoft-json` — Supabase JSON 파싱 (JsonUtility는 배열/중첩 객체 불가)
- `com.endel.nativewebsocket` — 실시간 WebSocket (Android/IL2CPP 호환)

### 4.7 렌더링 성능 예측

| 요소 | 기법 | Draw Calls | 삼각형 |
|------|------|-----------|--------|
| 뉴런 500개 | GPU Instancing (아이코스피어 80-320 tris) | **1-2** | 40K-160K |
| 시냅스 600개 | 단일 프로시저럴 메시 (billboard quad) | **1** | 1,200 |
| 뇌 영역 9개 | URP 투명 구체 | **9** | ~7K |
| UI/라벨 | TextMeshPro | 5-10 | minimal |
| **총계** | | **~16-22** | **~170K** |

Quest 3S 예산: ~200 draw calls, 1M 삼각형 (72Hz 기준). **예산의 10-15%만 사용. 72fps 여유.**

> [!important] 금지 사항
> - `LineRenderer` 사용 금지 — 600개 = 600 draw calls
> - Unity 기본 Sphere 메시 금지 — 768 tris, 아이코스피어(80-320 tris)로 교체
> - Built-in RP 금지 — URP만 사용
> - 뉴런/시냅스에 그림자(shadow) 금지 — 불필요한 GPU 비용

### 4.8 플랫폼 전략

| 플랫폼 | 지원 | 비고 |
|--------|------|------|
| **Quest 3S (VR/MR)** | **핵심 타겟** | APK 사이드로드, MR 패스스루 |
| Desktop (Unity Editor) | 개발/디버깅용 | 마우스+키보드 인터랙션 |
| 기존 웹 대시보드 | 그대로 유지 | 2D 조건 비교용으로 User Study에서 활용 |

User Study의 3개 조건:
- **2D**: 기존 웹 대시보드 (`/brain` 페이지)
- **3D Desktop**: Unity Editor 빌드 (모니터, 마우스)
- **MR**: Unity Quest 3S 빌드 (패스스루, 손/컨트롤러)

---

## 5. User Study 설계

### 5.1 실험 설계: Within-subjects 3-condition

| 조건 | 설명 | 인터랙션 |
|------|------|---------|
| **C1: 2D Dashboard** | 기존 웹 대시보드 (`/brain` 페이지) | 마우스 클릭 |
| **C2: 3D Desktop** | Unity Desktop 빌드 (모니터) | 마우스 회전/줌 |
| **C3: MR (Quest 3S)** | Unity Quest 빌드, 패스스루 MR | 손 추적 / 컨트롤러 |

- 순서 효과 제거: Latin Square counterbalancing
- 각 조건에서 동일 4개 과제 수행

### 5.2 참여자

- **N = 16-24** (within-subjects)
- large effect size (d=0.8) 기준 power=0.80 달성에 ~15명
- ISMAR 표준: 12-24명
- **IRB 승인 필요** — 최소 위험 연구로 신속 심사 가능

### 5.3 과제 (Tasks)

| Task | 내용 | 측정 변수 |
|------|------|----------|
| T1: 영역 식별 | "가장 활성화된 뇌 영역은?" | 정확도 (%), 반응시간 (s) |
| T2: 경로 추적 | "활성화 확산 경로를 추적하세요" | 경로 정확도, 시간 |
| T3: 패턴 비교 | "두 대화의 활성화 패턴 차이는?" | 정성적 코딩 (완전성) |
| T4: 발달 추정 | "AI의 현재 발달 단계는?" | 추정 오차 |

### 5.4 측정 도구

| 설문 | 측정 대상 | 시점 | 필수 여부 |
|------|----------|------|----------|
| **SSQ** | 사이버 멀미 | 실험 전 + MR 조건 후 | **필수** — VR 논문에 없으면 리뷰어가 지적 |
| **NASA-TLX** | 인지 부하 (6 subscale) | 각 조건 후 | 필수 |
| **SUS** | 사용성 (10 item) | 전체 실험 후 | 필수 |
| **IPQ** | 현존감/몰입감 | MR 조건 후 | 권장 |
| **Custom Likert** | AI 이해도, 직관성, 선호도 | 각 조건 후 | 권장 |

### 5.5 통계 분석

- 3조건 비교: **Friedman test** + Wilcoxon signed-rank post-hoc (Bonferroni 보정)
- 효과 크기: **Cliff's δ** (ICDL ablation과 동일 방법론으로 일관성 확보)
- 정성 분석: 반구조화 인터뷰 → 주제 분석(thematic analysis)

### 5.6 참여자당 소요 시간

| 단계 | 시간 |
|------|------|
| 동의서 + 인구통계 | 5-10분 |
| 사전 SSQ | 2분 |
| 튜토리얼 | 5-10분 |
| 3개 조건 × 과제 수행 | 30-45분 |
| 조건별 설문 (NASA-TLX 등) | 10-15분 |
| 사후 SSQ + 전체 설문 | 5-10분 |
| 인터뷰 (선택) | 5-10분 |
| **합계** | **60-90분/명** |

---

## 6. 논문 구조 (9+2 pages, IEEE TVCG format)

| Section | 내용 | 분량 |
|---------|------|------|
| Abstract | RQ + BrainXR 시스템 + 평가 결과 요약 | 0.3p |
| **1. Introduction** | AI XAI 필요성 → MR의 기회 → RQ 3개 → 기여 3개 | 1.0p |
| **2. Related Work** | 2.1 뇌 시각화 (NeuroCave, SlicerVR, HoloAnatomy) / 2.2 AI 시각화 (TensorBoard, CNN Explainer — 2D) / 2.3 몰입 분석 (Dwyer, Kwon) / 2.4 인지 아키텍처 시각화 (ACT-R, SOAR — 원시적 2D) → **Gap 명시** | 1.5p |
| **3. BrainXR System** | 3.1 인지 아키텍처 요약 (ICDL 논문 참조) / 3.2 뇌 영역 매핑 (9 regions, 구 좌표계) / 3.3 확산 활성화 시각화 (BFS + ripple) / 3.4 실시간 파이프라인 (Supabase → WebXR) / 3.5 MR 인터랙션 (패스스루, 손 추적, 공간 배치) | 2.0p |
| **4. User Study** | 4.1 설계 (3-condition within-subjects) / 4.2 참여자 / 4.3 과제 (T1-T4) / 4.4 측정 도구 / 4.5 절차 | 1.0p |
| **5. Results** | 5.1 과제 수행 (정확도, 시간) / 5.2 인지 부하 (NASA-TLX) / 5.3 사용성 (SUS) / 5.4 현존감 (IPQ) / 5.5 정성 분석 | 1.5p |
| **6. Discussion** | MR의 효과 해석, 해부학적 메타포의 의의, 한계점 (iOS 미지원, N 크기, 학습 효과), 미래 작업 | 1.0p |
| **7. Conclusion** | 기여 재정리, 의의 | 0.2p |
| References | | 2.0p |

### 필요한 Figure 목록 (5-7개)

1. **시스템 아키텍처 다이어그램** — Baby AI → Supabase (REST + Realtime WSS) → Unity → Quest 3S 파이프라인
2. **MR 시연 사진** — Quest 3S 패스스루에서 테이블 위 뇌 (가장 중요한 figure)
3. **확산 활성화 시퀀스** — t=0 (직접 활성화) → t=1 (1-hop 확산) → t=2 (2-hop 확산)
4. **3개 조건 비교** — 동일 데이터의 2D / 3D-desktop / MR 스크린샷
5. **과제 결과 차트** — 정확도/시간 bar chart (3조건 비교)
6. **NASA-TLX 결과** — 6 subscale radar 또는 bar chart

### 보충 자료

- **데모 영상 (30초-3분)** — Quest 3S에서 실제 사용 영상. ISMAR에서 AR 논문은 영상이 사실상 필수.
- **보충 PDF** — 전체 설문지, 추가 통계 테이블

---

## 7. ICDL 논문과의 분리

두 논문은 **완전히 다른 연구**다. 같은 프로젝트에서 나왔을 뿐이다.

| 구분 | ICDL | ISMAR |
|------|------|-------|
| **RQ** | 발달 메커니즘이 인지 능력에 영향을 주는가? | MR이 AI 인지과정 이해에 효과적인가? |
| **IV** | 아키텍처 ablation 조건 | 시각화 모달리티 (2D/3D/MR) |
| **DV** | 개념 수, 강도, 관계 수 | 과제 정확도, 반응시간, 인지부하 |
| **실험** | Ablation study (20 runs, 자동) | User study (16-24명, within-subjects) |
| **데이터** | Supabase DB 통계 | 설문지 + 과제 수행 |
| **커뮤니티** | 발달 로보틱스 / 인지과학 | 혼합현실 / 시각화 |
| **핵심** | 알고리즘 + 아키텍처 | 시각화 시스템 + HCI 평가 |

### 듀얼 제출 시 필수 조치

1. **상호 참조**: 각 논문에서 다른 논문을 anonymous으로 인용 ("Anonymous (2026) presents the underlying cognitive architecture [anonymized]")
2. **커버레터**: 두 논문의 관계와 차이를 편집장에게 명시
3. **텍스트 중복 15% 이하**: IEEE CrossCheck(iThenticate)로 자동 스캔됨
4. **시스템 설명 최소화**: ISMAR에서 인지 아키텍처는 0.5 page 요약 + ICDL 참조

---

## 8. 3주 실행 계획

### Week 1 (2/20-2/26): Unity 프로젝트 셋업 + Supabase 연동

| 일 | 작업 | 산출물 |
|----|------|--------|
| 목-금 | Unity 프로젝트 생성, URP + Meta XR SDK 설치, Quest 빌드 확인 | 빈 씬이 Quest에서 실행됨 |
| 토-일 | `SupabaseRestClient` (6개 테이블 REST 로드) + `BrainDataManager` (피보나치+클러스터링 포트) | 데이터 로드 + 3D 좌표 계산 완료 |
| 월 | `NeuronRenderer` (GPU Instancing) + `ConnectionRenderer` (프로시저럴 메시) | 500 뉴런 + 600 시냅스 렌더링 |
| 화 | `RegionRenderer` (9개 투명 구) + 히트맵 색상 | 전체 뇌 시각화 Unity에서 동작 |
| 수 | Quest 3S 빌드 + 성능 확인 (72fps 타겟) | Quest에서 정적 뇌 시각화 |

→ **Week 1 마일스톤: Quest 3S에서 Supabase 데이터 기반 뇌 시각화 렌더링**

### Week 2 (2/27-3/5): 실시간 + MR + 인터랙션

| 일 | 작업 | 산출물 |
|----|------|--------|
| 목-금 | `SupabaseRealtimeClient` (NativeWebSocket + Phoenix) + 활성화 이펙트(발광, 감쇠) | 실시간 뉴런 발화가 3D에서 표현됨 |
| 토-일 | MR 패스스루 (OVRPassthroughLayer) + 공간 배치 | 실제 테이블 위에 뇌 배치 |
| 월 | 레이캐스트 선택 + 정보 패널 (뉴런/영역 선택 시 이름, 카테고리, 강도 표시) | 인터랙션 동작 |
| 화 | 데모 영상 촬영 (Quest 3S MR) + pilot test (2-3명) | 30초-3분 영상 |
| 수 | 버그 수정 + User study 프로토콜/설문지 준비 | 안정화된 프로토타입 |

→ **Week 2 마일스톤: 실시간 MR 뇌 시각화 + 데모 영상 완성**

### Week 3 (3/6-3/12): 논문 작성 + Abstract 제출 + User study

| 일 | 작업 | 산출물 |
|----|------|--------|
| 목-금 | **3/7-8: 논문 초고 작성** (Introduction, Related Work, System) | 초고 5 pages |
| 토 | **3/8: Abstract 최종 수정** | |
| **일** | **3/9: Abstract 제출 (D-Day)** | Abstract 제출 완료 |
| 월-화 | User study 데이터 수집 시작 (4-5명/일) | 설문 + 과제 데이터 |
| 수-목 | 데이터 수집 계속 + Results 초안 | N=12-16 데이터 |
| 금 | 통계 분석, Discussion 작성 | |
| **토** | **3/15: 전체 논문 완성** | |
| **일** | **3/16: Paper 제출 (D-Day)** | 논문 제출 완료 |

> [!warning] 리스크
> - **IRB 승인**: 가장 큰 병목. 신속 심사도 2-4주. 교수님과 즉시 논의 필요.
> - **참여자 모집**: 16명 모집에 최소 1주. 연구실/학과 내부 모집이 현실적.
> - **타임라인 빡빡함**: ICDL (3/13)과 겹친다. 코드는 Week 1-2에 끝내고, Week 3는 글쓰기에 집중.

---

## 9. ISMAR 2026 CFP 정보

### 학회 개요

- **정식명**: IEEE International Symposium on Mixed and Augmented Reality
- **개최지**: Bari, Italy
- **일정**: 2026년 10월 4-9일
- **트랙**: Science & Technology (S&T), Journal (TVCG), Posters, Demos, Workshops
- **게재**: 수락 시 **IEEE TVCG** (SCIE Q1, IF 6.55)

### 주요 토픽

우리 논문이 해당하는 토픽:
- **Perception, Cognition, and Representation in AR/MR/VR** — 1순위
- **Applications of AR/MR/VR — Education and Training** — 2순위
- **Evaluation and User Studies for AR/MR** — 해당

주의: ISMAR의 "Perception & Cognition"은 **AR 사용 중 인간의 인지**를 의미한다. AI의 인지를 시각화하는 우리와는 미묘하게 다르다. 하지만 "MR이 AI 인지과정 이해에 미치는 영향"으로 프레이밍하면 부합한다.

### 리뷰 기준

| 기준 | 가중치 | 우리 논문 대응 |
|------|--------|---------------|
| **Novelty** | 높음 | 5개 갭 — 선행연구 0건 |
| **Technical Contribution** | 높음 | WebXR 실시간 파이프라인 + MR 인터랙션 |
| **AR/MR Relevance** | **결정적** | MR 패스스루 + 공간 배치 + user study |
| **Evaluation** | 높음 | 3-condition within-subjects, N=16-24 |
| **Significance** | 중간 | AI XAI + MR의 새로운 교차점 |
| **Presentation** | 중간 | 데모 영상 필수 |

### 포맷

- **분량**: 9 pages + 2 pages references (TVCG format)
- **리뷰**: Double-blind (저자 익명)
- **템플릿**: IEEE VGTC (LaTeX 또는 Word)
- **보충**: 영상 (강력 권장), 보충 PDF 가능

---

## 10. Abstract 초안 (English)

> **Abstract 제출일: 2026년 3월 9일 — 아래는 초안이며 수정 필요**

---

### BrainXR: Real-time Mixed Reality Visualization of Cognitive Processes in a Developmental AI System

Understanding the internal cognitive processes of AI systems remains a fundamental challenge in explainable AI (XAI). Current visualization tools are predominantly two-dimensional and static, limiting users' ability to comprehend complex dynamics such as spreading activation, emotion-modulated learning, and developmental progression. We present BrainXR, a mixed reality system that enables real-time visualization of cognitive processes in a developmental AI architecture. BrainXR maps 486 artificial semantic concepts onto nine anatomically-inspired brain regions using spherical coordinates, and renders spreading activation waves, emotion-driven modulation, and developmental growth in three dimensions. The system is built on WebXR, allowing deployment on Meta Quest 3S (with color passthrough for mixed reality), Android smartphones (AR mode), and desktop browsers from a single codebase.

To evaluate whether mixed reality improves comprehension of AI cognitive processes, we conducted a within-subjects user study (N=XX) comparing three visualization conditions: a 2D dashboard, a 3D desktop viewer, and a mixed reality experience on Quest 3S. Participants performed four tasks: identifying active brain regions, tracing activation spread paths, comparing activation patterns across conversations, and estimating developmental stage. We measured task accuracy, response time, cognitive workload (NASA-TLX), usability (SUS), and sense of presence (IPQ).

Results show that [결과 — 실험 후 작성]. Our work demonstrates that BrainXR is the first system to visualize a running AI's cognitive processes in mixed reality, and provides empirical evidence for [MR의 효과 — 실험 후 작성].

---

**길이**: ~230 words (제한 내)

**작성 노트:**
- `N=XX`와 결과 부분은 user study 완료 후 채워넣음
- Abstract 제출 시점(3/9)에 study가 안 끝났을 수 있음 → "we present a study design" 또는 preliminary results로 대체 가능
- ISMAR abstract은 full paper 심사의 기초가 되므로, RQ와 approach는 최대한 구체적으로

---

## 부록: 교수님/박사님 미팅 브리핑 포인트

### 30초 설명

> "Baby AI라는 발달 인지 아키텍처를 만들었는데, 이 AI의 뇌 활동을 Meta Quest 3S Mixed Reality로 실시간 시각화하는 시스템을 ISMAR 2026에 제출하려 합니다. 기존에 AI 인지과정을 XR로 본 연구가 아예 없어서, novelty가 확실합니다."

### 5분 설명 (순서대로)

1. **프로젝트 소개**: 9개 뇌 영역에 486개 개념이 매핑된 발달 인지 AI. 대화하면 뉴런이 활성화되고 확산된다.
2. **ISMAR 논문 핵심**: 이 과정을 MR로 보여주는 시스템 "BrainXR". 테이블 위에 AI의 뇌를 놓고 실시간으로 관찰.
3. **왜 새로운가**: AI 시각화는 전부 2D(TensorBoard 등). 뇌 VR은 실제 뇌만(NeuroCave 등). "인공 인지 + XR" 교차점에 논문 0건.
4. **기술**: 기존 Next.js + Three.js 코드에 WebXR 추가. Unity 아님. URL 접속으로 체험 가능.
5. **평가**: 16-24명 user study. 2D vs 3D vs MR 비교. NASA-TLX, SUS, SSQ 사용.
6. **ICDL과의 관계**: ICDL은 아키텍처 자체(ablation), ISMAR은 시각화 + HCI. RQ/IV/DV/데이터 모두 다름. salami slicing 아님.
7. **타임라인**: Abstract 3/9, Paper 3/16. 코드는 2주 내 완성 가능 (기존 자산 있음). User study가 병목.

### 교수님한테 꼭 확인받을 사항

1. **IRB 승인** — 신속 심사 가능한지, 절차가 어떻게 되는지
2. **참여자 모집** — 연구실/학과 내부 모집 가능한지
3. **Quest 3S 하드웨어** — 연구실에 있는지, 구매 필요한지
4. **듀얼 제출** — ICDL + ISMAR 동시 투고에 대한 의견
5. **공저** — 박사님 역할 분담 (논문 writing, user study 감독 등)
