'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CameraCapture, AudioRecorder, ConversationView, WakeWordIndicator } from '@/components'
import type { ConversationMessage } from '@/components'
import { useWakeWord } from '@/hooks/useWakeWord'
import { useSettings } from '@/hooks/useSettings'
import {
  Camera,
  Mic,
  MessageSquare,
  ArrowLeft,
  Image as ImageIcon,
  Eye,
  Sparkles,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Volume2,
} from 'lucide-react'
import Link from 'next/link'

// Global audio context for unlocking audio playback
let audioContextUnlocked = false
let globalAudioElement: HTMLAudioElement | null = null

// Debug log for mobile (visible in UI)
const debugLogs: string[] = []
function debugLog(msg: string) {
  const timestamp = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  debugLogs.push(`[${timestamp}] ${msg}`)
  if (debugLogs.length > 10) debugLogs.shift()
  console.log('[DEBUG]', msg)
}

// Unlock audio on first user interaction
function unlockAudio() {
  if (audioContextUnlocked) {
    debugLog('Audio already unlocked')
    return
  }

  // Create a silent audio context to unlock audio
  try {
    const AudioContext = window.AudioContext || (window as unknown as { webkitAudioContext: typeof window.AudioContext }).webkitAudioContext
    if (AudioContext) {
      const ctx = new AudioContext()
      // Create a short silent buffer and play it
      const buffer = ctx.createBuffer(1, 1, 22050)
      const source = ctx.createBufferSource()
      source.buffer = buffer
      source.connect(ctx.destination)
      source.start(0)
      debugLog('AudioContext created & started')
    }
  } catch (e) {
    debugLog(`AudioContext failed: ${e}`)
  }

  // Also try to play a silent audio element
  try {
    globalAudioElement = new Audio()
    globalAudioElement.volume = 0.01
    // Play silent data URI (valid MP3)
    globalAudioElement.src = 'data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA/+M4wAAAAAAAAAAAAEluZm8AAAAPAAAAAgAAAbAAqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//////////////////////////////////////////////////////////////////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAAAAAAAAAAAAbD/ZAAAAAAAAAAAAAAAAAAAAP/jOMAAAM9JgB4AzACqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq'
    globalAudioElement.play()
      .then(() => debugLog('Silent audio played'))
      .catch(e => debugLog(`Silent audio failed: ${e.message}`))
  } catch (e) {
    debugLog(`Audio element failed: ${e}`)
  }

  audioContextUnlocked = true
  debugLog('Audio unlock complete')
}

// Audio playback helper - plays audio immediately when called
async function playAudioUrl(url: string): Promise<void> {
  debugLog(`playAudioUrl called: ${url.substring(0, 60)}...`)

  return new Promise((resolve, reject) => {
    const audio = new Audio()

    // Set up timeout
    const timeout = setTimeout(() => {
      debugLog('Audio timeout after 10s')
      cleanup()
      reject(new Error('timeout'))
    }, 10000)

    const cleanup = () => {
      clearTimeout(timeout)
      audio.onended = null
      audio.onerror = null
      audio.oncanplaythrough = null
      audio.onloadeddata = null
    }

    audio.onloadeddata = () => {
      debugLog(`Audio loaded, duration: ${audio.duration}s`)
    }

    audio.onended = () => {
      debugLog('Audio ended')
      cleanup()
      resolve()
    }

    audio.onerror = (e) => {
      debugLog(`Audio error: ${JSON.stringify(e)}`)
      cleanup()
      reject(e)
    }

    audio.oncanplaythrough = () => {
      debugLog('Audio canplaythrough, attempting play...')
      audio.play()
        .then(() => debugLog('Play promise resolved'))
        .catch((err) => {
          debugLog(`Play rejected: ${err.name} - ${err.message}`)
          cleanup()
          reject(err)
        })
    }

    // Set source and load
    audio.preload = 'auto'
    audio.src = url
    debugLog('Calling audio.load()')
    audio.load()
  })
}

type SenseTab = 'camera' | 'microphone' | 'conversation'

interface VisualExperience {
  id: string
  image_url: string
  description: string
  objects_detected: Array<{
    name: string
    category: string
    confidence: number
  }>
  scene_type: string
  emotional_response: Record<string, number>
  created_at: string
}

interface AudioConversation {
  id: string
  transcript: string
  response_text: string
  response_audio_url?: string
  emotion?: string
  is_question: boolean
  created_at: string
}

const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000'

function transformVisualExperience(row: Record<string, unknown>): VisualExperience {
  return {
    id: row.id as string,
    image_url: (row.image_url as string) || '',
    description: (row.description as string) || '',
    objects_detected: (row.objects_detected as VisualExperience['objects_detected']) || [],
    scene_type: (row.scene_type as string) || 'unknown',
    emotional_response: (row.emotional_response as Record<string, number>) || {},
    created_at: (row.created_at as string) || new Date().toISOString(),
  }
}

// E2-3 Speaker 편집용 인라인 컴포넌트
function SpeakerEditor({
  initialId,
  initialName,
  onSave,
  onCancel,
}: {
  initialId: string
  initialName: string
  onSave: (id: string, name: string) => void
  onCancel: () => void
}) {
  const [id, setId] = useState(initialId)
  const [name, setName] = useState(initialName)
  return (
    <div className="flex items-center gap-2 w-full">
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="이름 (예: 형아)"
        className="flex-1 px-2 py-1 bg-slate-900/60 border border-slate-700 rounded text-slate-100 text-xs focus:outline-none focus:ring-1 focus:ring-violet-400"
      />
      <input
        type="text"
        value={id}
        onChange={(e) => setId(e.target.value)}
        placeholder="ID (예: brother)"
        className="flex-1 px-2 py-1 bg-slate-900/60 border border-slate-700 rounded text-slate-100 text-xs focus:outline-none focus:ring-1 focus:ring-violet-400"
      />
      <button
        onClick={() => onSave(id, name)}
        className="px-2 py-1 bg-violet-500/20 text-violet-300 rounded text-xs hover:bg-violet-500/30 transition-colors"
      >
        저장
      </button>
      <button
        onClick={onCancel}
        className="px-2 py-1 text-slate-400 hover:text-slate-200 text-xs transition-colors"
      >
        취소
      </button>
    </div>
  )
}

export default function SensePage() {
  const [activeTab, setActiveTab] = useState<SenseTab>('camera')
  const [isProcessing, setIsProcessing] = useState(false)
  const [result, setResult] = useState<VisualExperience | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [recentVisuals, setRecentVisuals] = useState<VisualExperience[]>([])
  const [showDebug, setShowDebug] = useState(false)
  const [debugRefresh, setDebugRefresh] = useState(0)

  // Conversation state
  const [messages, setMessages] = useState<ConversationMessage[]>([])
  const [conversationLoading, setConversationLoading] = useState(false)
  const [conversationError, setConversationError] = useState<string | null>(null)

  // E2-3 (Theory of Mind): speaker 식별
  // localStorage에 저장되어 다음 방문에도 자동 로드. 기본값 'self' / '나'.
  // - speaker_id !== 'unknown' 이어야 Step 1.5에서 UserModel 생성됨
  // - 여러 사람(엄마/형아 등) 테스트는 UI에서 이름 바꿔 저장
  const [speakerId, setSpeakerId] = useState<string>('self')
  const [speakerName, setSpeakerName] = useState<string>('나')
  const [showSpeakerEdit, setShowSpeakerEdit] = useState(false)

  // localStorage에서 speaker 로드 (SSR 안전: useEffect 안에서만)
  useEffect(() => {
    try {
      const raw = localStorage.getItem('baby-ai:speaker')
      if (raw) {
        const parsed = JSON.parse(raw) as { id?: string; name?: string }
        if (parsed.id) setSpeakerId(parsed.id)
        if (parsed.name) setSpeakerName(parsed.name)
      }
    } catch {
      // localStorage 접근 실패 (프라이빗 모드 등) — 기본값 유지
    }
  }, [])

  const saveSpeaker = useCallback((id: string, name: string) => {
    const trimmedId = (id || '').trim() || 'self'
    const trimmedName = (name || '').trim() || '나'
    setSpeakerId(trimmedId)
    setSpeakerName(trimmedName)
    try {
      localStorage.setItem(
        'baby-ai:speaker',
        JSON.stringify({ id: trimmedId, name: trimmedName })
      )
    } catch {
      // ignore
    }
    setShowSpeakerEdit(false)
  }, [])

  // Fetch recent visual experiences
  useEffect(() => {
    async function fetchRecent() {
      try {
        const res = await fetch(`${FASTAPI_URL}/api/visual-experiences?limit=5`)
        if (res.ok) {
          const data = await res.json()
          if (data.experiences) {
            setRecentVisuals(data.experiences.map(transformVisualExperience))
          }
        }
      } catch (e) {
        console.error('Failed to fetch recent visuals:', e)
      }
    }

    fetchRecent()
  }, [])

  // Handle image capture
  const handleCapture = useCallback(async (imageBlob: Blob) => {
    setIsProcessing(true)
    setError(null)
    setResult(null)

    try {
      // Convert blob to base64
      const reader = new FileReader()
      const base64Promise = new Promise<string>((resolve) => {
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1]
          resolve(base64)
        }
      })
      reader.readAsDataURL(imageBlob)
      const base64Data = await base64Promise

      // Send to API for processing
      const response = await fetch('/api/vision/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image: base64Data,
          mime_type: imageBlob.type || 'image/jpeg',
        }),
      })

      if (!response.ok) {
        throw new Error('이미지 처리에 실패했습니다.')
      }

      const data = await response.json()
      setResult(data.visual_experience)

    } catch (err) {
      const message = err instanceof Error ? err.message : '처리 중 오류가 발생했습니다.'
      setError(message)
    } finally {
      setIsProcessing(false)
    }
  }, [])

  // Handle audio recording submit
  const handleAudioSubmit = useCallback(async (audioBlob: Blob, duration: number) => {
    // Unlock audio on user interaction (critical for autoplay)
    unlockAudio()

    setConversationLoading(true)
    setConversationError(null)

    // Create user message placeholder
    const userMessageId = `user-${Date.now()}`
    const userMessage: ConversationMessage = {
      id: userMessageId,
      text: '음성 메시지 처리 중...',
      isUser: true,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])

    try {
      // Create form data for audio upload
      const formData = new FormData()
      formData.append('audio', audioBlob)
      formData.append('duration', duration.toString())

      // First, transcribe the audio
      const transcribeResponse = await fetch('/api/audio/transcribe', {
        method: 'POST',
        body: formData,
      })

      if (!transcribeResponse.ok) {
        throw new Error('음성 인식에 실패했습니다.')
      }

      const transcribeData = await transcribeResponse.json()
      const transcript = transcribeData.transcript || '(음성 인식 실패)'

      // Update user message with transcript
      setMessages(prev => prev.map(msg =>
        msg.id === userMessageId
          ? { ...msg, text: transcript }
          : msg
      ))

      // Now send the transcript to conversation API
      // E2-3: speakerRef.current를 사용 (stale closure 우회)
      const { id: _sid, name: _sname } = speakerRef.current
      const conversationResponse = await fetch('/api/conversation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: transcript,
          context: { speaker_id: _sid, speaker_name: _sname },
        }),
      })

      if (!conversationResponse.ok) {
        throw new Error('대화 처리에 실패했습니다.')
      }

      const conversationData = await conversationResponse.json()

      // Validate audio_url before using
      const validAudioUrl = conversationData.audio_url &&
        (conversationData.audio_url.startsWith('http') || conversationData.audio_url.startsWith('data:'))
        ? conversationData.audio_url
        : undefined

      // Add AI response
      const aiMessage: ConversationMessage = {
        id: `ai-${Date.now()}`,
        text: conversationData.response || '응답을 생성할 수 없습니다.',
        audioUrl: validAudioUrl,
        isUser: false,
        timestamp: new Date(),
        emotion: conversationData.emotion,
        isQuestion: conversationData.is_question,
      }
      setMessages(prev => [...prev, aiMessage])

      // Play audio immediately after receiving response
      if (validAudioUrl) {
        console.log('[SensePage] Attempting to play TTS audio:', validAudioUrl.substring(0, 50))
        wakeWordRef.current.pauseForSpeaking()
        playAudioUrl(validAudioUrl)
          .catch((err) => { console.warn('[SensePage] TTS autoplay failed:', err) })
          .finally(() => wakeWordRef.current.resumeAfterSpeaking())
      }

    } catch (err) {
      const message = err instanceof Error ? err.message : '처리 중 오류가 발생했습니다.'
      setConversationError(message)

      // Update user message to show error
      setMessages(prev => prev.map(msg =>
        msg.id === userMessageId
          ? { ...msg, text: '(음성 처리 실패)' }
          : msg
      ))
    } finally {
      setConversationLoading(false)
    }
  }, [])

  // Handle text message send
  const handleSendText = useCallback(async (text: string) => {
    // Unlock audio on user interaction (critical for autoplay)
    unlockAudio()
    debugLog(`Sending text: ${text.substring(0, 30)}...`)

    setConversationLoading(true)
    setConversationError(null)

    // Add user message
    const userMessage: ConversationMessage = {
      id: `user-${Date.now()}`,
      text,
      isUser: true,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])

    try {
      // E2-3: speakerRef.current를 사용 (stale closure 우회)
      const { id: _sid, name: _sname } = speakerRef.current
      debugLog(`Calling /api/conversation as speaker="${_sname}" (${_sid})`)
      const response = await fetch('/api/conversation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: text,
          context: { speaker_id: _sid, speaker_name: _sname },
        }),
      })

      if (!response.ok) {
        throw new Error('대화 처리에 실패했습니다.')
      }

      const data = await response.json()
      debugLog(`API response: ${JSON.stringify(data).substring(0, 200)}`)

      // Log TTS debug info from backend
      if (data.tts_debug) {
        debugLog(`TTS debug: ${data.tts_debug}`)
      }

      // Validate audio_url before using
      const validAudioUrl = data.audio_url &&
        (data.audio_url.startsWith('http') || data.audio_url.startsWith('data:'))
        ? data.audio_url
        : undefined

      // Add AI response
      const aiMessage: ConversationMessage = {
        id: `ai-${Date.now()}`,
        text: data.response || '응답을 생성할 수 없습니다.',
        audioUrl: validAudioUrl,
        isUser: false,
        timestamp: new Date(),
        emotion: data.emotion,
        isQuestion: data.is_question,
      }
      setMessages(prev => [...prev, aiMessage])

      // Play audio immediately after receiving response (within user gesture context)
      if (validAudioUrl) {
        debugLog(`TTS audio URL received: ${validAudioUrl.substring(0, 80)}`)
        wakeWordRef.current.pauseForSpeaking()
        playAudioUrl(validAudioUrl)
          .catch((err) => { debugLog(`TTS playback failed: ${err.message || err}`) })
          .finally(() => wakeWordRef.current.resumeAfterSpeaking())
      } else {
        debugLog('No valid audio_url in response')
      }

    } catch (err) {
      const message = err instanceof Error ? err.message : '처리 중 오류가 발생했습니다.'
      setConversationError(message)
    } finally {
      setConversationLoading(false)
    }
  }, [])

  // Handle audio send from conversation view
  const handleSendAudio = useCallback(async (audioBlob: Blob, duration: number) => {
    await handleAudioSubmit(audioBlob, duration)
  }, [handleAudioSubmit])

  // Clear conversation
  const handleClearConversation = useCallback(() => {
    setMessages([])
    setConversationError(null)
  }, [])

  // Wake Word (Always Listening) - Phase W
  const { settings, saveSettings } = useSettings()

  // Track conversation mode for resumeAfterSpeaking
  const isConversationModeRef = useRef(false)

  const handleWakeWordCommand = useCallback(async (text: string) => {
    setActiveTab('conversation')
    await handleSendText(text)
  }, [handleSendText])

  const handleWakeWordGreeting = useCallback(async () => {
    unlockAudio()
    setActiveTab('conversation')
    debugLog('Wake word greeting triggered')

    try {
      const res = await fetch('/api/wake-greeting', { method: 'POST' })
      const data = await res.json()
      debugLog(`Greeting response: ${data.greeting_text}`)

      // Add greeting message to conversation
      const greetingMsg: ConversationMessage = {
        id: `greeting-${Date.now()}`,
        text: data.greeting_text,
        audioUrl: data.audio_url,
        isUser: false,
        timestamp: new Date(),
        emotion: data.emotion,
      }
      setMessages(prev => [...prev, greetingMsg])

      // Play TTS greeting
      if (data.audio_url) {
        wakeWordRef.current.pauseForSpeaking()
        isConversationModeRef.current = true
        try {
          await playAudioUrl(data.audio_url)
        } catch (err) {
          debugLog(`Greeting TTS failed: ${err}`)
        }
        // After greeting TTS, enter continuous conversation mode
        wakeWordRef.current.enterConversing()
      } else {
        // No audio, still enter conversation mode
        wakeWordRef.current.enterConversing()
      }
    } catch (err) {
      debugLog(`Greeting error: ${err}`)
      // On error, try to resume listening
      wakeWordRef.current.enterConversing()
    }
  }, [])

  const wakeWord = useWakeWord({
    onCommand: handleWakeWordCommand,
    onGreeting: handleWakeWordGreeting,
    silenceTimeoutMs: 2000,
    conversationTimeoutMs: 30000,
  })

  // Keep stable ref for use in stale closures (handleAudioSubmit, handleSendText have [] deps)
  const wakeWordRef = useRef(wakeWord)
  useEffect(() => { wakeWordRef.current = wakeWord }, [wakeWord])

  // E2-3: speaker state도 같은 이유로 ref 유지 필요
  // handleSendText, handleAudioSubmit이 [] deps라 초기 렌더링의 'self'/'나'에 갇힘 → ref로 우회
  const speakerRef = useRef({ id: speakerId, name: speakerName })
  useEffect(() => {
    speakerRef.current = { id: speakerId, name: speakerName }
  }, [speakerId, speakerName])

  const tabs: { key: SenseTab; label: string; icon: typeof Camera; disabled?: boolean }[] = [
    { key: 'camera', label: '카메라', icon: Camera },
    { key: 'microphone', label: '마이크', icon: Mic },
    { key: 'conversation', label: '대화', icon: MessageSquare },
  ]

  return (
    <main className="min-h-screen p-4 md:p-8">
      {/* Header */}
      <header className="mb-6 md:mb-8">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </Link>
          <div>
            <h1 className="text-xl sm:text-2xl md:text-3xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              Sense Input
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Phase 4: 멀티모달 입력으로 Baby AI와 상호작용
            </p>
          </div>
        </div>
      </header>

      {/* Wake Word (Always Listening) Indicator */}
      <WakeWordIndicator
        state={wakeWord.state}
        isSupported={wakeWord.isSupported}
        transcript={wakeWord.transcript}
        error={wakeWord.error}
        enabled={settings.alwaysListeningEnabled}
        onToggle={(enabled) => {
          saveSettings({ alwaysListeningEnabled: enabled })
          if (enabled) {
            unlockAudio()
            wakeWord.start()
          } else {
            wakeWord.stop()
          }
        }}
        className="mb-4"
      />

      {/* Tab Selector */}
      <div className="flex bg-slate-800/50 rounded-xl p-1 mb-6 border border-slate-700/50">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => {
              unlockAudio() // Unlock audio on any tab click
              if (!tab.disabled) setActiveTab(tab.key)
            }}
            disabled={tab.disabled}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.key
                ? 'text-white bg-cyan-500/30'
                : tab.disabled
                ? 'text-slate-600 cursor-not-allowed'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            <span>{tab.label}</span>
            {tab.disabled && (
              <span className="text-xs px-1.5 py-0.5 bg-slate-700 rounded">Soon</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Input Area */}
        <div className="lg:col-span-2">
          <AnimatePresence mode="wait">
            {activeTab === 'camera' && (
              <motion.div
                key="camera"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
              >
                <CameraCapture
                  onCapture={handleCapture}
                  className="w-full"
                />

                {/* Processing indicator */}
                {isProcessing && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-4 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50 flex items-center gap-3"
                  >
                    <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin" />
                    <div>
                      <p className="text-slate-200 font-medium">이미지 처리 중...</p>
                      <p className="text-slate-500 text-sm">Baby AI가 이미지를 분석하고 있습니다</p>
                    </div>
                  </motion.div>
                )}

                {/* Error */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-4 p-4 bg-rose-500/10 rounded-xl border border-rose-500/30 flex items-center gap-3"
                  >
                    <AlertCircle className="w-5 h-5 text-rose-400" />
                    <p className="text-rose-300">{error}</p>
                  </motion.div>
                )}

                {/* Result */}
                {result && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-4 p-6 bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl border border-slate-700/50"
                  >
                    <div className="flex items-center gap-2 mb-4">
                      <CheckCircle className="w-5 h-5 text-emerald-400" />
                      <h3 className="text-lg font-semibold text-slate-100">분석 완료</h3>
                    </div>

                    {/* Description */}
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-slate-400 mb-2">장면 설명</h4>
                      <p className="text-slate-200">{result.description}</p>
                    </div>

                    {/* Scene type */}
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-slate-400 mb-2">장면 유형</h4>
                      <span className="px-3 py-1 bg-cyan-500/20 text-cyan-400 rounded-full text-sm">
                        {result.scene_type}
                      </span>
                    </div>

                    {/* Detected objects */}
                    {result.objects_detected && result.objects_detected.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-sm font-medium text-slate-400 mb-2">감지된 객체</h4>
                        <div className="flex flex-wrap gap-2">
                          {result.objects_detected.map((obj, i) => (
                            <span
                              key={i}
                              className="px-3 py-1 bg-slate-700/50 text-slate-300 rounded-full text-sm"
                            >
                              {obj.name}
                              <span className="ml-1 text-slate-500">
                                ({Math.round(obj.confidence * 100)}%)
                              </span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Emotional response */}
                    {result.emotional_response && Object.keys(result.emotional_response).length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-slate-400 mb-2">감정 반응</h4>
                        <div className="flex gap-4">
                          {Object.entries(result.emotional_response).map(([key, value]) => (
                            <div key={key} className="text-center">
                              <div className="text-lg font-bold text-cyan-400">
                                {value > 0 ? '+' : ''}{((value as number) * 100).toFixed(0)}%
                              </div>
                              <div className="text-xs text-slate-500">{key.replace('_change', '')}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </motion.div>
            )}

            {activeTab === 'microphone' && (
              <motion.div
                key="microphone"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
              >
                <AudioRecorder
                  onSubmit={handleAudioSubmit}
                  className="w-full"
                  maxDuration={60}
                />

                {/* Recent Audio Conversations */}
                {messages.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-4 p-4 bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl border border-slate-700/50"
                  >
                    <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                      <Volume2 className="w-4 h-4" />
                      최근 대화
                    </h4>
                    <div className="space-y-2">
                      {messages.slice(-4).map((msg) => (
                        <div
                          key={msg.id}
                          className={`p-3 rounded-lg ${
                            msg.isUser
                              ? 'bg-cyan-500/10 border-l-2 border-cyan-500'
                              : 'bg-purple-500/10 border-l-2 border-purple-500'
                          }`}
                        >
                          <p className="text-sm text-slate-200 line-clamp-2">{msg.text}</p>
                          {msg.emotion && (
                            <span className="text-xs text-purple-400 mt-1 inline-block">
                              {msg.emotion}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </motion.div>
            )}

            {activeTab === 'conversation' && (
              <motion.div
                key="conversation"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="h-[600px] flex flex-col gap-2"
              >
                {/* E2-3 Speaker badge: 대화 상대 식별 */}
                <div className="flex items-center justify-between px-3 py-2 bg-slate-800/60 border border-slate-700/50 rounded-xl text-sm">
                  {!showSpeakerEdit ? (
                    <>
                      <div className="flex items-center gap-2 text-slate-300">
                        <span className="w-2 h-2 rounded-full bg-emerald-400" />
                        <span className="text-slate-400">대화 상대:</span>
                        <span className="font-medium text-slate-100">{speakerName}</span>
                        <span className="text-slate-500 text-xs">({speakerId})</span>
                      </div>
                      <button
                        onClick={() => setShowSpeakerEdit(true)}
                        className="text-xs text-violet-400 hover:text-violet-300 transition-colors"
                      >
                        변경
                      </button>
                    </>
                  ) : (
                    <SpeakerEditor
                      initialId={speakerId}
                      initialName={speakerName}
                      onSave={saveSpeaker}
                      onCancel={() => setShowSpeakerEdit(false)}
                    />
                  )}
                </div>
                <ConversationView
                  messages={messages}
                  isLoading={conversationLoading}
                  error={conversationError}
                  onSendText={handleSendText}
                  onSendAudio={handleSendAudio}
                  onClearConversation={handleClearConversation}
                  className="flex-1"
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Sidebar - Recent Visual Experiences */}
        <div className="lg:col-span-1">
          <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl border border-slate-700/50 p-4">
            <h3 className="text-lg font-semibold text-slate-100 mb-4 flex items-center gap-2">
              <Eye className="w-5 h-5 text-purple-400" />
              최근 시각 경험
            </h3>

            {recentVisuals.length === 0 ? (
              <div className="text-center py-8">
                <ImageIcon className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-500 text-sm">아직 시각 경험이 없습니다</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentVisuals.map((visual) => (
                  <motion.div
                    key={visual.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="p-3 bg-slate-800/50 rounded-xl border border-slate-700/30"
                  >
                    <div className="flex items-start gap-3">
                      {visual.image_url ? (
                        <img
                          src={visual.image_url}
                          alt={visual.scene_type}
                          className="w-16 h-16 rounded-lg object-cover"
                        />
                      ) : (
                        <div className="w-16 h-16 rounded-lg bg-slate-700 flex items-center justify-center">
                          <ImageIcon className="w-6 h-6 text-slate-500" />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-slate-200 line-clamp-2">
                          {visual.description}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs px-2 py-0.5 bg-slate-700 text-slate-400 rounded">
                            {visual.scene_type}
                          </span>
                          <span className="text-xs text-slate-500">
                            {new Date(visual.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          {/* Info Card */}
          <div className="mt-4 p-4 bg-gradient-to-br from-cyan-500/10 to-purple-500/10 rounded-xl border border-cyan-500/20">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-5 h-5 text-cyan-400" />
              <h4 className="font-medium text-slate-200">Phase 4 정보</h4>
            </div>
            <p className="text-sm text-slate-400">
              카메라로 이미지를 캡처하고, 마이크로 대화하세요.
              Baby AI가 분석하고 학습하며, 질문과 반응을 생성합니다.
            </p>
          </div>
        </div>
      </div>

      {/* Debug Panel - Toggle with triple tap on header */}
      <button
        onClick={() => {
          setShowDebug(!showDebug)
          setDebugRefresh(n => n + 1)
        }}
        className="fixed bottom-4 right-4 p-2 bg-slate-800 rounded-full text-xs text-slate-500 z-50"
      >
        🔧
      </button>

      {showDebug && (
        <div className="fixed bottom-16 right-4 left-4 max-w-md ml-auto bg-slate-900 border border-slate-700 rounded-lg p-3 z-50 max-h-64 overflow-auto">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-bold text-slate-400">Debug Log (refresh: {debugRefresh})</span>
            <button
              onClick={() => setDebugRefresh(n => n + 1)}
              className="text-xs text-cyan-400"
            >
              Refresh
            </button>
          </div>
          <div className="space-y-1 font-mono text-[10px]">
            {debugLogs.length === 0 ? (
              <p className="text-slate-500">No logs yet</p>
            ) : (
              debugLogs.map((log, i) => (
                <p key={i} className="text-slate-300 break-all">{log}</p>
              ))
            )}
          </div>
          <div className="mt-2 pt-2 border-t border-slate-700">
            <p className="text-[10px] text-slate-500">
              audioUnlocked: {audioContextUnlocked ? '✅' : '❌'}
            </p>
          </div>
        </div>
      )}
    </main>
  )
}
