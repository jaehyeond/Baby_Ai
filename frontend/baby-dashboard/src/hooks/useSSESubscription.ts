'use client'

/**
 * useSSESubscription — FastAPI /api/events SSE 스트림 구독
 *
 * Phase 3: 브라우저 → FastAPI 직접 연결 (Next.js route 없음)
 * - FastAPI의 allow_origins=["*"] CORS 설정으로 직접 연결 가능
 * - 단일 EventSource를 SSEProvider Context에서 앱 전체 공유
 * - 재연결: 지수 백오프 (3s → 6s → 12s → max 60s)
 *
 * 수신 채널 (baby-ai:* prefix):
 *   baby_state, experience, neuron_activation
 *   (pending_question, imagination은 Phase 4에서 발행자 추가 후 활성화)
 */

import { useContext, useEffect, useRef } from 'react'
import { SSEContext } from './SSEContext'
import type { SSEHandler } from './SSEContext'

export type { SSEHandler, SSEEvent, SSEEventType, SSEBabyStateData, SSEExperienceData, SSENeuronActivationItem } from './SSEContext'

/**
 * SSE 이벤트 구독 hook
 *
 * @param handler - 이벤트 수신 콜백. useCallback으로 감싸서 전달 권장.
 *
 * @example
 * const { isConnected } = useSSESubscription(useCallback((event) => {
 *   if (event.type === 'baby_state') {
 *     const state = event.data as SSEBabyStateData
 *     setEmotions(state)
 *   }
 * }, []))
 */
export function useSSESubscription(handler: SSEHandler) {
  const ctx = useContext(SSEContext)

  if (!ctx) {
    throw new Error('useSSESubscription must be used within <SSEProvider>')
  }

  const { isConnected, subscribe } = ctx
  const handlerRef = useRef(handler)

  // handler가 바뀌어도 구독 재등록 없이 최신 handler 참조
  useEffect(() => {
    handlerRef.current = handler
  }, [handler])

  useEffect(() => {
    const stableHandler: SSEHandler = (event) => handlerRef.current(event)
    return subscribe(stableHandler)
  }, [subscribe])

  return { isConnected }
}
