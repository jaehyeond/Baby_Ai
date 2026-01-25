'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { SpeechBubble } from './SpeechOutput'
import { AudioRecorderCompact } from './AudioRecorder'
import {
  MessageSquare,
  Send,
  RefreshCw,
  Sparkles,
  AlertCircle,
  Mic,
  Type,
  Volume2,
  Trash2,
} from 'lucide-react'

export interface ConversationMessage {
  id: string
  text: string
  audioUrl?: string
  isUser: boolean
  timestamp: Date
  emotion?: string
  isQuestion?: boolean
  experienceId?: string  // For feedback (AI responses)
}

export interface ConversationViewProps {
  messages: ConversationMessage[]
  isLoading?: boolean
  error?: string | null
  onSendText: (text: string) => Promise<void>
  onSendAudio: (audioBlob: Blob, duration: number) => Promise<void>
  onClearConversation?: () => void
  className?: string
}

type InputMode = 'text' | 'audio'

export function ConversationView({
  messages,
  isLoading = false,
  error,
  onSendText,
  onSendAudio,
  onClearConversation,
  className = '',
}: ConversationViewProps) {
  const [inputMode, setInputMode] = useState<InputMode>('text')
  const [textInput, setTextInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Handle text submit
  const handleTextSubmit = useCallback(async (e?: React.FormEvent) => {
    e?.preventDefault()

    if (!textInput.trim() || isSending) return

    const text = textInput.trim()
    setTextInput('')
    setIsSending(true)

    try {
      await onSendText(text)
    } finally {
      setIsSending(false)
    }
  }, [textInput, isSending, onSendText])

  // Handle audio submit
  const handleAudioSubmit = useCallback(async (audioBlob: Blob, duration: number) => {
    setIsSending(true)

    try {
      await onSendAudio(audioBlob, duration)
    } finally {
      setIsSending(false)
    }
  }, [onSendAudio])

  // Handle key press
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleTextSubmit()
    }
  }, [handleTextSubmit])

  // Format timestamp
  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className={`flex flex-col h-full bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl border border-slate-700/50 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700/50">
        <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-purple-400" />
          대화
        </h3>
        <div className="flex items-center gap-2">
          {onClearConversation && messages.length > 0 && (
            <button
              onClick={onClearConversation}
              className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 transition-colors"
              title="대화 기록 삭제"
            >
              <Trash2 className="w-4 h-4 text-slate-400" />
            </button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Sparkles className="w-12 h-12 text-slate-600 mb-4" />
            <p className="text-slate-400 mb-2">Baby AI와 대화를 시작하세요</p>
            <p className="text-slate-500 text-sm">
              텍스트를 입력하거나 음성으로 말해보세요
            </p>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <SpeechBubble
                key={message.id}
                text={message.text}
                audioUrl={message.audioUrl}
                isUser={message.isUser}
                timestamp={formatTime(message.timestamp)}
                emotion={message.emotion}
                autoPlay={!message.isUser && index === messages.length - 1 && !!message.audioUrl}
                experienceId={message.experienceId}
                showFeedback={!message.isUser && !!message.experienceId}
              />
            ))}

            {/* Loading indicator */}
            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-2 px-4 py-3 bg-slate-700/30 rounded-2xl rounded-bl-md max-w-[80%]"
              >
                <RefreshCw className="w-4 h-4 text-purple-400 animate-spin" />
                <span className="text-sm text-slate-400">생각하는 중...</span>
              </motion.div>
            )}

            {/* Error message */}
            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-2 px-4 py-3 bg-rose-500/10 rounded-xl border border-rose-500/30"
              >
                <AlertCircle className="w-4 h-4 text-rose-400" />
                <span className="text-sm text-rose-300">{error}</span>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-slate-700/50">
        {/* Input Mode Toggle */}
        <div className="flex items-center gap-2 mb-3">
          <button
            onClick={() => setInputMode('text')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              inputMode === 'text'
                ? 'bg-cyan-500/20 text-cyan-400'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            <Type className="w-4 h-4" />
            텍스트
          </button>
          <button
            onClick={() => setInputMode('audio')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              inputMode === 'audio'
                ? 'bg-cyan-500/20 text-cyan-400'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            <Mic className="w-4 h-4" />
            음성
          </button>
        </div>

        {/* Input */}
        <AnimatePresence mode="wait">
          {inputMode === 'text' ? (
            <motion.form
              key="text-input"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              onSubmit={handleTextSubmit}
              className="flex items-center gap-2"
            >
              <input
                ref={inputRef}
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="메시지를 입력하세요..."
                disabled={isSending}
                className="flex-1 px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!textInput.trim() || isSending}
                className="p-3 rounded-xl bg-cyan-500 hover:bg-cyan-600 disabled:opacity-50 disabled:hover:bg-cyan-500 transition-colors"
              >
                {isSending ? (
                  <RefreshCw className="w-5 h-5 text-white animate-spin" />
                ) : (
                  <Send className="w-5 h-5 text-white" />
                )}
              </button>
            </motion.form>
          ) : (
            <motion.div
              key="audio-input"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <AudioRecorderCompact
                onSubmit={handleAudioSubmit}
                className="w-full"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

// Compact conversation bubble for displaying recent interactions
export interface RecentConversationProps {
  messages: ConversationMessage[]
  maxMessages?: number
  className?: string
}

export function RecentConversation({
  messages,
  maxMessages = 3,
  className = '',
}: RecentConversationProps) {
  const recentMessages = messages.slice(-maxMessages)

  if (recentMessages.length === 0) {
    return (
      <div className={`p-4 bg-slate-800/50 rounded-xl ${className}`}>
        <div className="flex items-center gap-2 text-slate-500">
          <MessageSquare className="w-4 h-4" />
          <span className="text-sm">아직 대화가 없습니다</span>
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {recentMessages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[85%] px-3 py-2 rounded-xl text-sm ${
              message.isUser
                ? 'bg-cyan-500/20 text-cyan-100'
                : 'bg-slate-700/50 text-slate-200'
            }`}
          >
            <p className="line-clamp-2">{message.text}</p>
            {message.audioUrl && (
              <Volume2 className="w-3 h-3 mt-1 text-slate-500" />
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
