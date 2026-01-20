# Real-time Multimodal AI Research

**Date**: 2025-01-21
**Status**: Research Only (미구현)
**Purpose**: 실시간 멀티모달 AI 가능성 조사

---

## Executive Summary

**결론: 실시간 멀티모달 AI는 기술적으로 가능하다.**

2026년 현재, AI가 실시간으로 "보고, 듣고, 말하는" 것이 완전히 가능합니다.
다만 현재 아키텍처(Supabase Edge Function)를 넘어서는 추가 인프라가 필요합니다.

---

## 현재 구현 vs 실시간 구현

| 항목 | 현재 (녹음 → 전송) | 실시간 가능 |
|------|-------------------|-------------|
| 카메라 | 사진 찍고 업로드 | **연속 스트리밍** (1 FPS) |
| 마이크 | 녹음 완료 후 전송 | **실시간 음성 인식** |
| 응답 | 전체 처리 후 TTS | **스트리밍 응답** (말하면서 생성) |
| 지연 | 3-5초 | **300ms-800ms** |
| 대화 느낌 | "메시지 보내기" | **진짜 대화** |

---

## 주요 기술 옵션

### 1. Gemini Live API (Google) - 가장 유력

**특징:**
- 실시간 비디오 + 오디오 양방향 스트리밍
- 저지연 (low-latency)
- 비디오 1 FPS 처리 (빠른 움직임은 부적합)
- 세션 메모리 지원
- 감정 인식 대화 (affective dialogue)
- 능동적 응답 (proactive audio)
- WebSocket 기반 연결

**장점:**
- 이미 Gemini 사용 중이므로 통합 용이
- Google 생태계 일관성 유지

**단점:**
- Gemini 2.0 Flash/Flash-Lite는 2026년 3월 3일 퇴출 예정
- Gemini 2.5 Flash Live로 마이그레이션 필요

**참고:**
- [Gemini Live API Overview](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api)
- [Gemini Live API Reference](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live)
- [Gemini 2.0 Real-Time Multimodal](https://developers.googleblog.com/en/gemini-2-0-level-up-your-apps-with-real-time-multimodal-interactions/)

### 2. OpenAI Realtime API (GPT-4o)

**특징:**
- 오디오 + 이미지 지원 (비디오는 프레임 단위)
- **320ms** 응답 시간
- WebRTC 권장 (WebSocket보다 빠름)
- SIP 프로토콜 지원 (전화망 연결 가능)
- 네이티브 음성-음성 처리 (STT/TTS 체인 없이)

**가격:**
- 입력: $32/1M 오디오 토큰 ($0.40 캐시됨)
- 출력: $64/1M 오디오 토큰

**참고:**
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)
- [gpt-realtime Model](https://platform.openai.com/docs/models/gpt-realtime)

### 3. Pipecat (오픈소스 프레임워크)

**특징:**
- Python 기반 실시간 멀티모달 AI 프레임워크
- **500-800ms** 전체 왕복 지연
- Gemini, OpenAI, AWS 등 다양한 백엔드 지원
- WebRTC 통합 (Daily 파트너십)
- 로컬 macOS에서도 <800ms 달성 가능

**지원 서비스:**
- STT: AssemblyAI, AWS, Azure, Deepgram, Google, NVIDIA Riva
- LLM: OpenAI, Gemini, Groq, AWS Bedrock
- TTS: Cartesia, ElevenLabs, Google, NVIDIA Riva

**참고:**
- [Pipecat GitHub](https://github.com/pipecat-ai/pipecat)
- [Pipecat Documentation](https://docs.pipecat.ai/getting-started/introduction)
- [NVIDIA Voice Agent Examples](https://github.com/NVIDIA/voice-agent-examples)

---

## 기술 아키텍처 비교

### 현재 아키텍처 (Request-Response)

```
User → Record Audio → Upload → Supabase Edge Function → Gemini STT → LLM → TTS → Download → Play
       (2-3초)        (0.5초)     (1-2초)                (1초)        (1초)  (1초)   (0.5초)  (즉시)
                                                                               총: 3-5초
```

### 실시간 아키텍처 (Streaming)

```
User ←→ WebSocket/WebRTC ←→ Live API (Gemini/OpenAI)
        (실시간 양방향)          (300-800ms 지연)
```

---

## 구현에 필요한 요소

### Frontend (Next.js)

```typescript
// 필요한 기술
- WebRTC 또는 WebSocket 연결
- MediaStream API (카메라/마이크 스트림)
- 실시간 오디오 재생
- RTCPeerConnection (P2P 연결)
```

### Backend 옵션

**Option A: Gemini Live API 직접 연결**
```
Frontend → WebSocket → Gemini Live API
- 장점: 간단, 서버 불필요
- 단점: API 키 노출 위험, 세션 관리 제한
```

**Option B: Pipecat 백엔드**
```
Frontend → WebRTC (Daily) → Pipecat Server → Gemini/OpenAI
- 장점: 유연성, 다중 AI 서비스 통합, 세션 관리
- 단점: 별도 Python 서버 필요
```

**Option C: Supabase Realtime + Edge Function**
```
Frontend → Supabase Realtime → Edge Function → Gemini Live
- 장점: 기존 인프라 활용
- 단점: Supabase Realtime이 WebSocket 대비 지연 있음
```

---

## 비용 고려사항

### Gemini Live API
- 가격 정보 미확인 (일반 Gemini API보다 높을 것으로 예상)
- 실시간 스트리밍으로 토큰 사용량 증가

### OpenAI Realtime API
- 입력: $32/1M 오디오 토큰
- 출력: $64/1M 오디오 토큰
- 일반 텍스트 API 대비 비용 상승

### 인프라 비용
- Pipecat 사용 시 별도 서버 비용 (AWS/GCP/Vercel)
- Daily WebRTC: 무료 티어 있음, 이후 사용량 기반

---

## 제한사항

### 기술적 제한
1. **비디오 처리**: Gemini Live는 1 FPS → 빠른 움직임 분석 불가
2. **서버 필요**: 상시 WebSocket 연결 유지 필요
3. **모바일 배터리**: 실시간 스트리밍은 배터리 소모 큼
4. **네트워크**: 안정적인 인터넷 연결 필요

### 아키텍처 제한
- 현재 Supabase Edge Function만으로는 WebSocket 상시 연결 불가
- 별도 WebSocket 서버 또는 Pipecat 백엔드 필요

---

## 잠재적 사용 사례

1. **실시간 대화**: Baby AI와 자연스러운 음성 대화
2. **시각 동반자**: 카메라로 보이는 것에 대해 실시간 질문/설명
3. **학습 도우미**: 실시간 피드백을 주는 교육 AI
4. **접근성**: 시각/청각 장애인을 위한 실시간 지원

---

## 결론 및 권장사항

### 현재 단계
- **구현하지 않음** - 리서치 및 기록 목적
- 현재 "녹음 → 전송" 방식도 충분히 기능적

### 향후 구현 시 권장 경로

1. **단기 (쉬운 경로)**: Gemini Live API + 브라우저 WebSocket
   - 프론트엔드만 수정
   - API 키 관리 주의 필요

2. **중기 (권장 경로)**: Pipecat + Daily WebRTC
   - 별도 Python 백엔드 필요
   - 가장 유연하고 확장 가능

3. **장기 (완전 통합)**: 커스텀 WebRTC 서버 + 멀티 AI
   - 완전한 제어권
   - 가장 복잡하지만 최적화 가능

---

## References

1. [Gemini Live API - Google Cloud](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api)
2. [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)
3. [Pipecat Framework](https://github.com/pipecat-ai/pipecat)
4. [WebRTC Google Codelab](https://codelabs.developers.google.com/codelabs/webrtc-web)
5. [ZEGOCLOUD Multimodal AI](https://www.zegocloud.com/blog/multimodal-ai-agent-is-reshaping-real-time-experiences)
6. [NVIDIA Voice Agent Examples](https://github.com/NVIDIA/voice-agent-examples)

---

## Document Info

| 항목 | 값 |
|------|-----|
| Version | 1.0 |
| Created | 2025-01-21 |
| Status | Research Only |
| Implementation | Not Planned |
