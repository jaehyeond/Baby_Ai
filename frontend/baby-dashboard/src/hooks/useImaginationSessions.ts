'use client'

import { useState, useEffect, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import type { ImaginationSession, Json } from '@/lib/database.types'

// Parsed connection structure from imagination session
export interface DiscoveredConnection {
  from: string
  to: string
  relation: string
}

// Parsed thought structure
export interface ImaginationThought {
  content: string
  type?: 'exploration' | 'question' | 'insight' | 'prediction' | 'connection'
  timestamp?: string
  connections?: string[]
}

// Parsed imagination session with typed fields
export interface ParsedImaginationSession {
  id: string
  topic: string
  trigger: string | null
  imaginationType: string | null
  thoughts: ImaginationThought[]
  connectionsDiscovered: DiscoveredConnection[]
  insights: string[]
  emotionalState: Record<string, number>
  curiosityLevel: number
  durationMs: number | null
  startedAt: Date | null
  endedAt: Date | null
}

// Parse raw thought data
function parseThought(raw: Json): ImaginationThought {
  if (typeof raw === 'string') {
    return { content: raw }
  }
  if (typeof raw === 'object' && raw !== null && !Array.isArray(raw)) {
    const obj = raw as Record<string, Json>
    return {
      content: String(obj.content || obj.text || ''),
      type: obj.type as ImaginationThought['type'],
      timestamp: obj.timestamp ? String(obj.timestamp) : undefined,
      connections: Array.isArray(obj.connections)
        ? obj.connections.map(c => String(c))
        : undefined
    }
  }
  return { content: String(raw) }
}

// Parse raw connection data
function parseConnection(raw: Json): DiscoveredConnection | null {
  if (typeof raw === 'object' && raw !== null && !Array.isArray(raw)) {
    const obj = raw as Record<string, Json>
    if (obj.from && obj.to) {
      return {
        from: String(obj.from),
        to: String(obj.to),
        relation: String(obj.relation || 'related')
      }
    }
  }
  return null
}

// Parse raw session to typed session
function parseSession(raw: ImaginationSession): ParsedImaginationSession {
  const thoughts: ImaginationThought[] = Array.isArray(raw.thoughts)
    ? raw.thoughts.map(parseThought)
    : []

  const connectionsDiscovered: DiscoveredConnection[] = Array.isArray(raw.connections_discovered)
    ? raw.connections_discovered.map(parseConnection).filter((c): c is DiscoveredConnection => c !== null)
    : []

  const insights: string[] = Array.isArray(raw.insights)
    ? raw.insights.map(i => String(i))
    : []

  const emotionalState: Record<string, number> = typeof raw.emotional_state === 'object' && raw.emotional_state !== null
    ? Object.fromEntries(
        Object.entries(raw.emotional_state as Record<string, unknown>)
          .filter(([, v]) => typeof v === 'number')
          .map(([k, v]) => [k, v as number])
      )
    : {}

  return {
    id: raw.id,
    topic: raw.topic,
    trigger: raw.trigger,
    imaginationType: raw.imagination_type,
    thoughts,
    connectionsDiscovered,
    insights,
    emotionalState,
    curiosityLevel: raw.curiosity_level ?? 0,
    durationMs: raw.duration_ms,
    startedAt: raw.started_at ? new Date(raw.started_at) : null,
    endedAt: raw.ended_at ? new Date(raw.ended_at) : null,
  }
}

interface UseImaginationSessionsReturn {
  sessions: ParsedImaginationSession[]
  isLoading: boolean
  error: string | null
  refetch: () => Promise<void>
  selectedSession: ParsedImaginationSession | null
  setSelectedSession: (session: ParsedImaginationSession | null) => void
  stats: {
    totalSessions: number
    totalConnections: number
    totalInsights: number
    avgCuriosity: number
  }
}

export function useImaginationSessions(limit: number = 20): UseImaginationSessionsReturn {
  const [sessions, setSessions] = useState<ParsedImaginationSession[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedSession, setSelectedSession] = useState<ParsedImaginationSession | null>(null)

  const fetchSessions = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error: fetchError } = await (supabase as any)
        .from('imagination_sessions')
        .select('*')
        .order('started_at', { ascending: false })
        .limit(limit)

      if (fetchError) throw fetchError

      const parsedSessions = (data || []).map(parseSession)
      setSessions(parsedSessions)

      // Auto-select the most recent session
      if (parsedSessions.length > 0 && !selectedSession) {
        setSelectedSession(parsedSessions[0])
      }
    } catch (err) {
      console.error('[useImaginationSessions] Error:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch imagination sessions')
    } finally {
      setIsLoading(false)
    }
  }, [limit, selectedSession])

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  // Calculate stats
  const stats = {
    totalSessions: sessions.length,
    totalConnections: sessions.reduce((sum, s) => sum + s.connectionsDiscovered.length, 0),
    totalInsights: sessions.reduce((sum, s) => sum + s.insights.length, 0),
    avgCuriosity: sessions.length > 0
      ? sessions.reduce((sum, s) => sum + s.curiosityLevel, 0) / sessions.length
      : 0,
  }

  return {
    sessions,
    isLoading,
    error,
    refetch: fetchSessions,
    selectedSession,
    setSelectedSession,
    stats,
  }
}

export default useImaginationSessions
