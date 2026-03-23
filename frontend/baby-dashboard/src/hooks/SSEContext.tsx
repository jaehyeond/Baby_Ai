'use client'

import {
  createContext,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'

// ── 타입 정의 ────────────────────────────────────────────────────────────────

export interface SSEBabyStateData {
  development_stage: number
  curiosity: number
  joy: number
  fear: number
  surprise: number
  frustration: number
  boredom: number
  dominant_emotion: string
}

export interface SSEExperienceData {
  id: string
  task_type: string
  dominant_emotion: string
  development_stage: number
}

export interface SSENeuronActivationItem {
  concept_id: string | null
  brain_region_id: string | null
  intensity: number
  trigger_type: 'conversation' | 'spreading_activation'
  created_at?: string
}

export type SSEEventType = 'baby_state' | 'experience' | 'neuron_activation'

export interface SSEEvent {
  type: SSEEventType
  data: SSEBabyStateData | SSEExperienceData | SSENeuronActivationItem[]
}

export type SSEHandler = (event: SSEEvent) => void

// ── Context ───────────────────────────────────────────────────────────────────

interface SSEContextValue {
  isConnected: boolean
  subscribe: (handler: SSEHandler) => () => void
}

export const SSEContext = createContext<SSEContextValue | null>(null)

// ── SSEProvider ───────────────────────────────────────────────────────────────

export function SSEProvider({ children }: { children: ReactNode }) {
  const [isConnected, setIsConnected] = useState(false)
  const handlersRef = useRef<Set<SSEHandler>>(new Set())
  const esRef = useRef<EventSource | null>(null)
  const retryDelayRef = useRef(3000)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const unmountedRef = useRef(false)

  const notify = useCallback((event: SSEEvent) => {
    handlersRef.current.forEach(h => h(event))
  }, [])

  const connect = useCallback(() => {
    if (unmountedRef.current) return

    const fastapiUrl = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000'
    const url = `${fastapiUrl}/api/events`

    const es = new EventSource(url)
    esRef.current = es

    es.onopen = () => {
      if (unmountedRef.current) return
      setIsConnected(true)
      retryDelayRef.current = 3000
    }

    es.onmessage = (event) => {
      if (unmountedRef.current) return
      try {
        const parsed = JSON.parse(event.data) as { type: SSEEventType; data: unknown }
        if (parsed.type && parsed.data !== undefined) {
          notify({ type: parsed.type, data: parsed.data as SSEEvent['data'] })
        }
      } catch {
        // keep-alive ping 등 파싱 불가 메시지는 무시
      }
    }

    es.onerror = () => {
      if (unmountedRef.current) return
      setIsConnected(false)
      es.close()
      esRef.current = null

      // 지수 백오프 재연결 (max 60s)
      const delay = retryDelayRef.current
      retryDelayRef.current = Math.min(delay * 2, 60000)

      retryTimerRef.current = setTimeout(() => {
        if (!unmountedRef.current) connect()
      }, delay)
    }
  }, [notify])

  useEffect(() => {
    unmountedRef.current = false
    connect()

    return () => {
      unmountedRef.current = true
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current)
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
    }
  }, [connect])

  const subscribe = useCallback((handler: SSEHandler) => {
    handlersRef.current.add(handler)
    return () => {
      handlersRef.current.delete(handler)
    }
  }, [])

  return (
    <SSEContext.Provider value={{ isConnected, subscribe }}>
      {children}
    </SSEContext.Provider>
  )
}
