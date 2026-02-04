'use client'

import { useEffect, useRef, useCallback, useState } from 'react'

interface UseIdleSleepOptions {
  /** Idle timeout in milliseconds (default: 30 minutes) */
  idleTimeoutMs?: number
  /** Whether the hook is enabled (default: true) */
  enabled?: boolean
  /** Callback when idle sleep is triggered */
  onSleepStart?: () => void
  /** Callback when idle sleep is completed */
  onSleepComplete?: (stats: SleepStats) => void
  /** Callback when idle sleep fails */
  onSleepError?: (error: Error) => void
}

interface SleepStats {
  experiences_processed: number
  memories_strengthened: number
  memories_decayed: number
  patterns_promoted: number
  concepts_consolidated: number
  semantic_links_created: number
  // Phase 8: Curiosity stats
  curiosities_generated?: number
  explorations_completed?: number
  new_knowledge_acquired?: number
  // World Model stats
  imagination_sessions?: number
  connections_discovered?: number
  predictions_made?: number
}

interface UseIdleSleepReturn {
  /** Time in ms until idle sleep triggers */
  timeUntilSleep: number
  /** Whether idle sleep is currently running */
  isSleeping: boolean
  /** Whether the system is currently idle */
  isIdle: boolean
  /** Last activity timestamp */
  lastActivityAt: Date | null
  /** Manually trigger sleep */
  triggerSleep: () => Promise<void>
  /** Reset idle timer (call on user activity) */
  resetIdleTimer: () => void
}

/**
 * Hook for automatic memory consolidation when the user is idle
 *
 * Monitors user activity and triggers "sleep" (memory consolidation)
 * after a period of inactivity. This mimics the human brain's sleep cycle
 * where memories are consolidated during rest.
 *
 * @example
 * ```tsx
 * const { timeUntilSleep, isSleeping, isIdle } = useIdleSleep({
 *   idleTimeoutMs: 10 * 60 * 1000, // 10 minutes
 *   onSleepStart: () => console.log('Baby is going to sleep...'),
 *   onSleepComplete: (stats) => console.log('Sleep complete!', stats),
 * })
 * ```
 */
export function useIdleSleep(options: UseIdleSleepOptions = {}): UseIdleSleepReturn {
  const {
    idleTimeoutMs = 10 * 60 * 1000, // 10 minutes default (more frequent "thinking")
    enabled = true,
    onSleepStart,
    onSleepComplete,
    onSleepError,
  } = options

  const [timeUntilSleep, setTimeUntilSleep] = useState(idleTimeoutMs)
  const [isSleeping, setIsSleeping] = useState(false)
  const [isIdle, setIsIdle] = useState(false)
  const [lastActivityAt, setLastActivityAt] = useState<Date | null>(null)

  const idleTimerRef = useRef<NodeJS.Timeout | null>(null)
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const lastActivityRef = useRef<number>(Date.now())
  const hasSleeptRef = useRef(false)

  // Trigger sleep (memory consolidation + curiosity exploration)
  const triggerSleep = useCallback(async () => {
    if (isSleeping || hasSleeptRef.current) return

    setIsSleeping(true)
    hasSleeptRef.current = true
    onSleepStart?.()

    const combinedStats: SleepStats = {
      experiences_processed: 0,
      memories_strengthened: 0,
      memories_decayed: 0,
      patterns_promoted: 0,
      concepts_consolidated: 0,
      semantic_links_created: 0,
      curiosities_generated: 0,
      explorations_completed: 0,
      new_knowledge_acquired: 0,
      imagination_sessions: 0,
      connections_discovered: 0,
      predictions_made: 0,
    }

    try {
      console.log('[IdleSleep] Starting sleep cycle (memory + curiosity)...')

      // Phase 1: Memory Consolidation
      console.log('[IdleSleep] Phase 1: Memory consolidation...')
      const memoryResponse = await fetch('/api/memory/consolidate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'consolidate',
          trigger_type: 'idle',
          hours_window: 24,
        }),
      })

      if (memoryResponse.ok) {
        const memoryData = await memoryResponse.json()
        if (memoryData.success && memoryData.stats) {
          Object.assign(combinedStats, memoryData.stats)
          console.log('[IdleSleep] Memory consolidation done:', memoryData.stats)
        }
      }

      // Phase 2: Generate New Curiosities (based on gaps found during consolidation)
      console.log('[IdleSleep] Phase 2: Generating curiosities...')
      const curiosityResponse = await fetch('/api/curiosity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'generate',
          methods: ['concept_gap', 'failure', 'pattern', 'similarity'],
          limit: 5, // Generate up to 5 new curiosities during sleep
        }),
      })

      if (curiosityResponse.ok) {
        const curiosityData = await curiosityResponse.json()
        if (curiosityData.success) {
          combinedStats.curiosities_generated = curiosityData.generated?.length || 0
          console.log('[IdleSleep] Curiosities generated:', combinedStats.curiosities_generated)
        }
      }

      // Phase 3: Autonomous Exploration (explore pending curiosities)
      console.log('[IdleSleep] Phase 3: Autonomous exploration...')
      const exploreResponse = await fetch('/api/curiosity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'explore_batch',
          limit: 3, // Explore up to 3 curiosities during sleep
          methods: ['internal_graph', 'memory_recall', 'pattern_match'], // Prefer internal methods during sleep
        }),
      })

      if (exploreResponse.ok) {
        const exploreData = await exploreResponse.json()
        if (exploreData.success) {
          combinedStats.explorations_completed = exploreData.explored?.length || 0
          // Count new knowledge from explorations
          const newKnowledge = exploreData.explored?.reduce((sum: number, exp: { new_concepts?: number; new_relations?: number }) => {
            return sum + (exp.new_concepts || 0) + (exp.new_relations || 0)
          }, 0) || 0
          combinedStats.new_knowledge_acquired = newKnowledge
          console.log('[IdleSleep] Explorations done:', combinedStats.explorations_completed, 'new knowledge:', newKnowledge)
        }
      }

      // Phase 4: World Model - Imagination (dream-like exploration)
      console.log('[IdleSleep] Phase 4: World Model - Imagination...')
      try {
        // Pick a random topic from recent experiences or curiosities
        const topics = [
          '오늘 배운 것들의 연결고리',
          '새로운 개념들 사이의 관계',
          '내가 궁금했던 것들',
        ]
        const randomTopic = topics[Math.floor(Math.random() * topics.length)]

        const imagineResponse = await fetch('/api/imagination', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'imagine',
            topic: randomTopic,
            trigger: 'idle_sleep',
          }),
        })

        if (imagineResponse.ok) {
          const imagineData = await imagineResponse.json()
          if (imagineData.success && imagineData.session) {
            combinedStats.imagination_sessions = 1
            combinedStats.connections_discovered = imagineData.session.connections_discovered?.length || 0
            console.log('[IdleSleep] Imagination session complete:', {
              topic: imagineData.session.topic,
              thoughts: imagineData.session.thoughts?.length || 0,
              connections: combinedStats.connections_discovered,
              insights: imagineData.session.insights?.length || 0,
            })
          }
        }

        // Also generate a prediction based on recent patterns
        const predictResponse = await fetch('/api/imagination', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'predict',
            scenario: '다음에 사용자와 대화할 때 어떤 주제가 나올까?',
            prediction_type: 'behavior',
            domain: 'conversation',
          }),
        })

        if (predictResponse.ok) {
          const predictData = await predictResponse.json()
          if (predictData.success && predictData.prediction) {
            combinedStats.predictions_made = 1
            console.log('[IdleSleep] Prediction made:', {
              prediction: predictData.prediction.prediction?.substring(0, 100),
              confidence: predictData.prediction.confidence,
            })
          }
        }
      } catch (imaginationError) {
        console.warn('[IdleSleep] Imagination phase error (non-critical):', imaginationError)
        // Imagination errors are non-critical, continue with sleep completion
      }

      console.log('[IdleSleep] Sleep cycle complete:', combinedStats)
      onSleepComplete?.(combinedStats)

    } catch (error) {
      console.error('[IdleSleep] Sleep error:', error)
      onSleepError?.(error instanceof Error ? error : new Error(String(error)))
    } finally {
      setIsSleeping(false)
      // Reset the flag after some time to allow future sleeps
      setTimeout(() => {
        hasSleeptRef.current = false
      }, 60 * 60 * 1000) // Allow next sleep after 1 hour
    }
  }, [isSleeping, onSleepStart, onSleepComplete, onSleepError])

  // Stable ref for triggerSleep to avoid dependency cycles
  const triggerSleepRef = useRef(triggerSleep)
  useEffect(() => {
    triggerSleepRef.current = triggerSleep
  }, [triggerSleep])

  // Reset idle timer - stable callback without triggerSleep dependency
  const resetIdleTimer = useCallback(() => {
    lastActivityRef.current = Date.now()
    setLastActivityAt(new Date())
    setIsIdle(false)
    setTimeUntilSleep(idleTimeoutMs)
    hasSleeptRef.current = false

    // Clear existing timer
    if (idleTimerRef.current) {
      clearTimeout(idleTimerRef.current)
    }

    // Set new timer
    if (enabled) {
      idleTimerRef.current = setTimeout(() => {
        setIsIdle(true)
        triggerSleepRef.current()
      }, idleTimeoutMs)
    }
  }, [idleTimeoutMs, enabled])

  // Update countdown
  useEffect(() => {
    if (!enabled) return

    countdownIntervalRef.current = setInterval(() => {
      const elapsed = Date.now() - lastActivityRef.current
      const remaining = Math.max(0, idleTimeoutMs - elapsed)
      setTimeUntilSleep(remaining)

      if (remaining === 0 && !isIdle) {
        setIsIdle(true)
      }
    }, 1000)

    return () => {
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current)
      }
    }
  }, [enabled, idleTimeoutMs, isIdle])

  // Stable ref for resetIdleTimer to avoid useEffect re-runs
  const resetIdleTimerRef = useRef(resetIdleTimer)
  useEffect(() => {
    resetIdleTimerRef.current = resetIdleTimer
  }, [resetIdleTimer])

  // Listen for user activity - only re-run when enabled changes
  useEffect(() => {
    if (!enabled) return

    const events = ['mousedown', 'mousemove', 'keydown', 'touchstart', 'scroll']

    const handleActivity = () => {
      resetIdleTimerRef.current()
    }

    // Add event listeners
    events.forEach(event => {
      window.addEventListener(event, handleActivity, { passive: true })
    })

    // Initialize timer
    resetIdleTimerRef.current()

    return () => {
      // Remove event listeners
      events.forEach(event => {
        window.removeEventListener(event, handleActivity)
      })

      // Clear timers
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current)
      }
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current)
      }
    }
  }, [enabled])

  return {
    timeUntilSleep,
    isSleeping,
    isIdle,
    lastActivityAt,
    triggerSleep,
    resetIdleTimer,
  }
}

export default useIdleSleep
