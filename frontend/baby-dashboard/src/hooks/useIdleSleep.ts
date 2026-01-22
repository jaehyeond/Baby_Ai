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
 *   idleTimeoutMs: 30 * 60 * 1000, // 30 minutes
 *   onSleepStart: () => console.log('Baby is going to sleep...'),
 *   onSleepComplete: (stats) => console.log('Sleep complete!', stats),
 * })
 * ```
 */
export function useIdleSleep(options: UseIdleSleepOptions = {}): UseIdleSleepReturn {
  const {
    idleTimeoutMs = 30 * 60 * 1000, // 30 minutes default
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

  // Trigger sleep (memory consolidation)
  const triggerSleep = useCallback(async () => {
    if (isSleeping || hasSleeptRef.current) return

    setIsSleeping(true)
    hasSleeptRef.current = true
    onSleepStart?.()

    try {
      console.log('[IdleSleep] Starting memory consolidation (idle trigger)...')

      const response = await fetch('/api/memory/consolidate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'consolidate',
          trigger_type: 'idle',
          hours_window: 24,
        }),
      })

      if (!response.ok) {
        throw new Error(`Consolidation failed: ${response.status}`)
      }

      const data = await response.json()

      if (data.success && data.stats) {
        console.log('[IdleSleep] Sleep complete:', data.stats)
        onSleepComplete?.(data.stats)
      } else {
        throw new Error(data.error || 'Unknown error')
      }
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

  // Reset idle timer
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
        triggerSleep()
      }, idleTimeoutMs)
    }
  }, [idleTimeoutMs, enabled, triggerSleep])

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

  // Listen for user activity
  useEffect(() => {
    if (!enabled) return

    const events = ['mousedown', 'mousemove', 'keydown', 'touchstart', 'scroll']

    const handleActivity = () => {
      resetIdleTimer()
    }

    // Add event listeners
    events.forEach(event => {
      window.addEventListener(event, handleActivity, { passive: true })
    })

    // Initialize timer
    resetIdleTimer()

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
  }, [enabled, resetIdleTimer])

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
