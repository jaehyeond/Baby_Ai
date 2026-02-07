'use client'

import { useState, useCallback, useRef, useEffect } from 'react'

// ── Types ──────────────────────────────────────────────────

export type WakeWordState =
  | 'OFF'
  | 'LISTENING'
  | 'GREETING'
  | 'CONVERSING'
  | 'CAPTURING'
  | 'PROCESSING'
  | 'SPEAKING'

export interface UseWakeWordOptions {
  onCommand: (text: string) => void | Promise<void>
  onGreeting: () => void | Promise<void>
  silenceTimeoutMs?: number
  conversationTimeoutMs?: number
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
  enterConversing: () => void
}

// ── Wake Word Detection ────────────────────────────────────

const WAKE_PATTERNS = [
  /비비야/, /비비아/, /베비야/, /베베야/,
  /비비얌/, /비비요/, /삐삐야/, /베비아/,
  /비비 야/, /비비 아/,
  /BB야/, /bb야/, /비 비야/, /비 비아/,
  /빼비야/, /뻬비야/, /피비야/, /피피야/,
  /비비$/, // "비비"만 말한 경우
]

// ── End Conversation Detection ─────────────────────────────

const END_PATTERNS = [
  /대화\s*끝/, /그만\s*할래/, /그만/, /잘\s*가/, /바이\s*바이/, /바이/,
  /끝\s*내자/, /이만/, /다음에/, /안녕/,
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

function detectEndConversation(text: string): boolean {
  const normalized = text.trim()
  return END_PATTERNS.some(p => p.test(normalized))
}

// ── Hook ───────────────────────────────────────────────────

export function useWakeWord(options: UseWakeWordOptions): UseWakeWordReturn {
  const { silenceTimeoutMs = 2000, conversationTimeoutMs = 30000 } = options

  const [state, setState] = useState<WakeWordState>('OFF')
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSupported, setIsSupported] = useState(false)

  // Stable refs
  const stateRef = useRef<WakeWordState>('OFF')
  const onCommandRef = useRef(options.onCommand)
  const onGreetingRef = useRef(options.onGreeting)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const restartTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const conversationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const wakeLockRef = useRef<WakeLockSentinel | null>(null)
  const capturedTextRef = useRef('')
  const failureCountRef = useRef(0)
  const shouldListenRef = useRef(false)

  // Keep refs in sync
  useEffect(() => { onCommandRef.current = options.onCommand }, [options.onCommand])
  useEffect(() => { onGreetingRef.current = options.onGreeting }, [options.onGreeting])
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
    if (conversationTimerRef.current) {
      clearTimeout(conversationTimerRef.current)
      conversationTimerRef.current = null
    }
  }, [])

  const resetConversationTimer = useCallback(() => {
    if (conversationTimerRef.current) clearTimeout(conversationTimerRef.current)
    conversationTimerRef.current = setTimeout(() => {
      // 30s silence in CONVERSING → back to LISTENING
      if (stateRef.current === 'CONVERSING') {
        console.log('[WakeWord] Conversation timeout, back to LISTENING')
        setState('LISTENING')
        capturedTextRef.current = ''
        setTranscript('')
      }
    }, conversationTimeoutMs)
  }, [conversationTimeoutMs])

  const resetSilenceTimer = useCallback((timeoutMs?: number) => {
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
    silenceTimerRef.current = setTimeout(() => {
      const currentState = stateRef.current
      const text = capturedTextRef.current.trim()

      if (currentState === 'CAPTURING') {
        if (text.length > 0) {
          setState('PROCESSING')
          capturedTextRef.current = ''
          setTranscript('')
          Promise.resolve(onCommandRef.current(text)).catch((err) => {
            console.error('[WakeWord] Command error:', err)
          })
        } else {
          // Empty command — go back to listening
          setState('LISTENING')
          capturedTextRef.current = ''
          setTranscript('')
        }
      } else if (currentState === 'CONVERSING') {
        if (text.length > 0) {
          // Check for end conversation phrases first
          if (detectEndConversation(text)) {
            console.log('[WakeWord] End conversation detected:', text)
            setState('LISTENING')
            capturedTextRef.current = ''
            setTranscript('')
            return
          }
          setState('PROCESSING')
          capturedTextRef.current = ''
          setTranscript('')
          // Reset conversation timer on activity
          resetConversationTimer()
          Promise.resolve(onCommandRef.current(text)).catch((err) => {
            console.error('[WakeWord] Conversation command error:', err)
          })
        }
        // If empty in CONVERSING, just keep waiting (conversation timer handles timeout)
      }
    }, timeoutMs ?? silenceTimeoutMs)
  }, [silenceTimeoutMs, resetConversationTimer])

  const scheduleRestart = useCallback(() => {
    if (restartTimeoutRef.current) clearTimeout(restartTimeoutRef.current)
    restartTimeoutRef.current = setTimeout(() => {
      if (!shouldListenRef.current) return
      if (stateRef.current === 'OFF' || stateRef.current === 'SPEAKING' || stateRef.current === 'GREETING') return

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
      // Don't override CONVERSING, GREETING, PROCESSING states
      if (stateRef.current !== 'CAPTURING' && stateRef.current !== 'PROCESSING' &&
          stateRef.current !== 'GREETING' && stateRef.current !== 'CONVERSING') {
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

      const currentState = stateRef.current

      if (currentState === 'LISTENING') {
        // Check all results and alternatives for wake word
        for (let i = event.resultIndex; i < event.results.length; i++) {
          for (let j = 0; j < event.results[i].length; j++) {
            const { found, commandText } = detectWakeWord(event.results[i][j].transcript)
            if (found) {
              if (commandText.length > 0) {
                // "비비야 안녕" → 즉시 커맨드 처리
                console.log('[WakeWord] Wake word + command detected:', commandText)
                capturedTextRef.current = commandText
                setTranscript(commandText)
                setState('CAPTURING')
                resetSilenceTimer()
              } else {
                // "비비야"만 → 인사 모드 진입
                console.log('[WakeWord] Wake word only → GREETING')
                capturedTextRef.current = ''
                setTranscript('')
                setState('GREETING')
                // Stop recognition during greeting
                try { recognitionRef.current?.stop() } catch { /* */ }
                Promise.resolve(onGreetingRef.current()).catch((err) => {
                  console.error('[WakeWord] Greeting error:', err)
                  // On error, go back to listening
                  setState('LISTENING')
                  scheduleRestart()
                })
              }
              return
            }
          }
        }
        // No wake word found — update transcript for visual feedback
        const latestTranscript = event.results[event.results.length - 1][0].transcript
        setTranscript(latestTranscript)

      } else if (currentState === 'CAPTURING') {
        // Accumulate command text
        let newText = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          newText += event.results[i][0].transcript
        }
        capturedTextRef.current += ' ' + newText
        setTranscript(capturedTextRef.current.trim())
        resetSilenceTimer(event.results[event.results.length - 1].isFinal ? 1500 : silenceTimeoutMs)

      } else if (currentState === 'CONVERSING') {
        // In conversation mode: no wake word needed, all speech is command
        let newText = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          newText += event.results[i][0].transcript
        }

        // Check for end conversation in real-time
        const fullText = (capturedTextRef.current + ' ' + newText).trim()
        if (event.results[event.results.length - 1].isFinal && detectEndConversation(fullText)) {
          console.log('[WakeWord] End conversation detected (realtime):', fullText)
          if (conversationTimerRef.current) clearTimeout(conversationTimerRef.current)
          if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
          capturedTextRef.current = ''
          setTranscript('')
          setState('LISTENING')
          return
        }

        capturedTextRef.current += ' ' + newText
        setTranscript(capturedTextRef.current.trim())
        resetSilenceTimer(event.results[event.results.length - 1].isFinal ? 1500 : silenceTimeoutMs)
        // Reset conversation timeout on activity
        resetConversationTimer()
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
        return
      }
      if (event.error === 'aborted') {
        return
      }
      console.warn('[WakeWord] Recognition error:', event.error)
    }

    recognition.onend = () => {
      if (!shouldListenRef.current) return
      if (stateRef.current === 'OFF' || stateRef.current === 'SPEAKING' || stateRef.current === 'GREETING') return
      // Auto-restart for continuous listening
      scheduleRestart()
    }

    return recognition
  }, [resetSilenceTimer, scheduleRestart, silenceTimeoutMs, resetConversationTimer])

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
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
    try {
      recognitionRef.current?.stop()
    } catch {
      // Already stopped
    }
  }, [])

  const resumeAfterSpeaking = useCallback(() => {
    if (!shouldListenRef.current) return
    if (stateRef.current !== 'SPEAKING') return

    capturedTextRef.current = ''
    setTranscript('')

    // Small delay to avoid picking up tail-end of TTS audio
    setTimeout(() => {
      if (!shouldListenRef.current) return
      // After speaking in conversation mode, stay in CONVERSING
      const wasConversing = stateRef.current === 'SPEAKING'
      // Check if we were in a conversation before speaking
      // We use conversation timer as indicator - if it's set, we were conversing
      if (conversationTimerRef.current) {
        setState('CONVERSING')
        resetConversationTimer()
      } else {
        setState('LISTENING')
      }
      try {
        recognitionRef.current?.start()
      } catch {
        scheduleRestart()
      }
    }, 500)
  }, [scheduleRestart, resetConversationTimer])

  // Called by page after greeting completes → enter continuous conversation mode
  const enterConversing = useCallback(() => {
    if (!shouldListenRef.current) return
    console.log('[WakeWord] Entering CONVERSING mode')
    capturedTextRef.current = ''
    setTranscript('')
    setState('CONVERSING')
    resetConversationTimer()

    // Restart recognition for conversation
    setTimeout(() => {
      if (!shouldListenRef.current) return
      if (stateRef.current !== 'CONVERSING') return
      try {
        recognitionRef.current?.start()
      } catch {
        scheduleRestart()
      }
    }, 300)
  }, [resetConversationTimer, scheduleRestart])

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
    enterConversing,
  }
}
