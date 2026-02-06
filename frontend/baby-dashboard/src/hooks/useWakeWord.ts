'use client'

import { useState, useCallback, useRef, useEffect } from 'react'

// ── Types ──────────────────────────────────────────────────

export type WakeWordState =
  | 'OFF'
  | 'LISTENING'
  | 'CAPTURING'
  | 'PROCESSING'
  | 'SPEAKING'

export interface UseWakeWordOptions {
  onCommand: (text: string) => void | Promise<void>
  silenceTimeoutMs?: number
}

export interface UseWakeWordReturn {
  state: WakeWordState
  isSupported: boolean
  transcript: string
  error: string | null
  start: () => void
  stop: () => void
  pauseForSpeaking: () => void
  resumeAfterSpeaking: () => void
}

// ── Wake Word Detection ────────────────────────────────────

const WAKE_PATTERNS = [
  /비비야/, /비비아/, /베비야/, /베베야/,
  /비비얌/, /비비요/, /삐삐야/, /베비아/,
  /비비 야/, /비비 아/,
  // 추가 변형 (Samsung STT 대응)
  /BB야/, /bb야/, /비 비야/, /비 비아/,
  /빼비야/, /뻬비야/, /피비야/, /피피야/,
  /비비$/, // "비비"만 말한 경우 (뒤에 아무것도 없으면)
]

function detectWakeWord(text: string): { found: boolean; commandText: string } {
  const normalized = text.trim()
  for (const pattern of WAKE_PATTERNS) {
    const match = normalized.match(pattern)
    if (match) {
      const commandText = normalized.slice(match.index! + match[0].length).trim()
      console.log('[WakeWord] MATCHED:', pattern, '→ command:', commandText || '(empty)')
      return { found: true, commandText }
    }
  }
  return { found: false, commandText: '' }
}

// ── Hook ───────────────────────────────────────────────────

export function useWakeWord(options: UseWakeWordOptions): UseWakeWordReturn {
  const { silenceTimeoutMs = 2000 } = options

  const [state, setState] = useState<WakeWordState>('OFF')
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSupported, setIsSupported] = useState(false)

  // Stable refs
  const stateRef = useRef<WakeWordState>('OFF')
  const onCommandRef = useRef(options.onCommand)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const restartTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const wakeLockRef = useRef<WakeLockSentinel | null>(null)
  const capturedTextRef = useRef('')
  const failureCountRef = useRef(0)
  const shouldListenRef = useRef(false)

  // Keep refs in sync
  useEffect(() => { onCommandRef.current = options.onCommand }, [options.onCommand])
  useEffect(() => { stateRef.current = state }, [state])

  // Feature detection
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    setIsSupported(!!SR)
  }, [])

  // ── Internal helpers ───────────────────────────────────

  const clearTimers = useCallback(() => {
    if (restartTimeoutRef.current) {
      clearTimeout(restartTimeoutRef.current)
      restartTimeoutRef.current = null
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
  }, [])

  const resetSilenceTimer = useCallback((timeoutMs?: number) => {
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
    silenceTimerRef.current = setTimeout(() => {
      const text = capturedTextRef.current.trim()
      if (text.length > 0) {
        setState('PROCESSING')
        capturedTextRef.current = ''
        setTranscript('')
        // Call the command handler
        Promise.resolve(onCommandRef.current(text)).catch((err) => {
          console.error('[WakeWord] Command error:', err)
        })
      } else {
        // Empty command — go back to listening
        setState('LISTENING')
        capturedTextRef.current = ''
        setTranscript('')
      }
    }, timeoutMs ?? silenceTimeoutMs)
  }, [silenceTimeoutMs])

  const scheduleRestart = useCallback(() => {
    if (restartTimeoutRef.current) clearTimeout(restartTimeoutRef.current)
    restartTimeoutRef.current = setTimeout(() => {
      if (!shouldListenRef.current) return
      if (stateRef.current === 'OFF' || stateRef.current === 'SPEAKING') return

      try {
        recognitionRef.current?.start()
        failureCountRef.current = 0
      } catch (e) {
        failureCountRef.current++
        console.warn('[WakeWord] Restart failed:', e, `(attempt ${failureCountRef.current})`)
        if (failureCountRef.current >= 5) {
          setError('음성 인식 재시작 실패. 다시 켜주세요.')
          setState('OFF')
          shouldListenRef.current = false
        } else {
          // Try again with longer delay
          scheduleRestart()
        }
      }
    }, 300)
  }, [])

  // ── Wake Lock ──────────────────────────────────────────

  const requestWakeLock = useCallback(async () => {
    if (!('wakeLock' in navigator)) return
    try {
      wakeLockRef.current = await navigator.wakeLock.request('screen')
      wakeLockRef.current.addEventListener('release', () => {
        // Re-acquire if still listening
        if (shouldListenRef.current) requestWakeLock()
      })
    } catch (e) {
      console.warn('[WakeWord] Wake lock failed:', e)
    }
  }, [])

  const releaseWakeLock = useCallback(() => {
    wakeLockRef.current?.release()
    wakeLockRef.current = null
  }, [])

  // ── Recognition setup ──────────────────────────────────

  const setupRecognition = useCallback(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return null

    const recognition = new SR()
    recognition.lang = 'ko-KR'
    recognition.continuous = false // Android workaround
    recognition.interimResults = true
    recognition.maxAlternatives = 3

    recognition.onstart = () => {
      if (stateRef.current === 'OFF') return
      if (stateRef.current !== 'CAPTURING' && stateRef.current !== 'PROCESSING') {
        setState('LISTENING')
      }
    }

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      failureCountRef.current = 0

      // Debug: log all results
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const alts = []
        for (let j = 0; j < event.results[i].length; j++) {
          alts.push(event.results[i][j].transcript)
        }
        console.log(`[WakeWord] state=${stateRef.current} result[${i}] final=${event.results[i].isFinal}:`, alts.join(' | '))
      }

      if (stateRef.current === 'LISTENING') {
        // Check all results and alternatives for wake word
        for (let i = event.resultIndex; i < event.results.length; i++) {
          for (let j = 0; j < event.results[i].length; j++) {
            const { found, commandText } = detectWakeWord(event.results[i][j].transcript)
            if (found) {
              console.log('[WakeWord] ✅ Wake word detected! Command:', commandText || '(waiting for command)')
              capturedTextRef.current = commandText
              setTranscript(commandText)
              if (commandText.length > 0) {
                setState('CAPTURING')
                resetSilenceTimer()
              } else {
                // Wake word detected but no command yet
                setState('CAPTURING')
                resetSilenceTimer()
              }
              return
            }
          }
        }
        // No wake word found — update transcript for visual feedback but don't act
        const latestTranscript = event.results[event.results.length - 1][0].transcript
        setTranscript(latestTranscript)
      } else if (stateRef.current === 'CAPTURING') {
        // Accumulate command text
        let newText = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          newText += event.results[i][0].transcript
        }
        capturedTextRef.current += ' ' + newText
        setTranscript(capturedTextRef.current.trim())
        resetSilenceTimer(event.results[event.results.length - 1].isFinal ? 1500 : silenceTimeoutMs)
      }
    }

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error === 'not-allowed') {
        setError('마이크 권한이 거부되었습니다.')
        setState('OFF')
        shouldListenRef.current = false
        return
      }
      if (event.error === 'no-speech') {
        // Normal — no speech detected, will restart via onend
        return
      }
      if (event.error === 'aborted') {
        // Intentional stop
        return
      }
      console.warn('[WakeWord] Recognition error:', event.error)
    }

    recognition.onend = () => {
      if (!shouldListenRef.current) return
      if (stateRef.current === 'OFF' || stateRef.current === 'SPEAKING') return
      // Auto-restart for continuous listening
      scheduleRestart()
    }

    return recognition
  }, [resetSilenceTimer, scheduleRestart, silenceTimeoutMs])

  // ── Public API ─────────────────────────────────────────

  const start = useCallback(() => {
    if (!isSupported) {
      setError('이 브라우저에서 음성 인식을 지원하지 않습니다.')
      return
    }

    setError(null)
    shouldListenRef.current = true
    failureCountRef.current = 0
    capturedTextRef.current = ''
    setTranscript('')

    // Create recognition instance
    if (!recognitionRef.current) {
      recognitionRef.current = setupRecognition()
    }

    try {
      recognitionRef.current?.start()
      setState('LISTENING')
      requestWakeLock()
    } catch (e) {
      console.error('[WakeWord] Start failed:', e)
      setError('음성 인식 시작 실패')
    }
  }, [isSupported, setupRecognition, requestWakeLock])

  const stop = useCallback(() => {
    shouldListenRef.current = false
    clearTimers()
    capturedTextRef.current = ''
    setTranscript('')

    try {
      recognitionRef.current?.stop()
    } catch {
      // Already stopped
    }
    recognitionRef.current = null

    setState('OFF')
    setError(null)
    releaseWakeLock()
  }, [clearTimers, releaseWakeLock])

  const pauseForSpeaking = useCallback(() => {
    if (stateRef.current === 'OFF') return
    setState('SPEAKING')
    clearTimers()
    try {
      recognitionRef.current?.stop()
    } catch {
      // Already stopped
    }
  }, [clearTimers])

  const resumeAfterSpeaking = useCallback(() => {
    if (!shouldListenRef.current) return
    if (stateRef.current !== 'SPEAKING') return

    capturedTextRef.current = ''
    setTranscript('')

    // Small delay to avoid picking up tail-end of TTS audio
    setTimeout(() => {
      if (!shouldListenRef.current) return
      setState('LISTENING')
      try {
        recognitionRef.current?.start()
      } catch {
        scheduleRestart()
      }
    }, 500)
  }, [scheduleRestart])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      shouldListenRef.current = false
      clearTimers()
      try { recognitionRef.current?.stop() } catch { /* */ }
      recognitionRef.current = null
      releaseWakeLock()
    }
  }, [clearTimers, releaseWakeLock])

  return {
    state,
    isSupported,
    transcript,
    error,
    start,
    stop,
    pauseForSpeaking,
    resumeAfterSpeaking,
  }
}
