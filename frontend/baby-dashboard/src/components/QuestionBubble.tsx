'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import type { PendingQuestion } from '@/lib/database.types'

interface QuestionBubbleProps {
  /** The question to display */
  question: PendingQuestion | null
  /** Whether the modal is open */
  isOpen: boolean
  /** Callback when modal is closed */
  onClose: () => void
  /** Callback when answer is submitted */
  onSubmit: (questionId: string, answer: string, confidence?: number) => void
  /** Callback when question is skipped */
  onSkip: (questionId: string) => void
}

// Question type display configuration
const QUESTION_TYPE_CONFIG: Record<string, { label: string; emoji: string; color: string; bgGradient: string }> = {
  personal: {
    label: '개인 정보',
    emoji: '👤',
    color: 'bg-blue-500',
    bgGradient: 'from-blue-500/20 to-blue-600/20'
  },
  preference: {
    label: '취향/선호',
    emoji: '💜',
    color: 'bg-purple-500',
    bgGradient: 'from-purple-500/20 to-purple-600/20'
  },
  experience: {
    label: '경험/추억',
    emoji: '📚',
    color: 'bg-amber-500',
    bgGradient: 'from-amber-500/20 to-amber-600/20'
  },
  relationship: {
    label: '관계/감정',
    emoji: '💕',
    color: 'bg-pink-500',
    bgGradient: 'from-pink-500/20 to-pink-600/20'
  },
}

// Confidence level options
const CONFIDENCE_OPTIONS = [
  { value: 1.0, label: '확실해요', emoji: '💯' },
  { value: 0.7, label: '대체로 그래요', emoji: '👍' },
  { value: 0.5, label: '잘 모르겠어요', emoji: '🤔' },
]

/**
 * QuestionBubble - Modal dialog for answering Baby AI's questions
 *
 * Features:
 * - Full-screen modal overlay
 * - Textarea for answer input
 * - Confidence level selection
 * - Skip option for later
 */
export function QuestionBubble({
  question,
  isOpen,
  onClose,
  onSubmit,
  onSkip,
}: QuestionBubbleProps) {
  const [answer, setAnswer] = useState('')
  const [confidence, setConfidence] = useState<number>(1.0)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Reset state when question changes
  useEffect(() => {
    if (question) {
      setAnswer('')
      setConfidence(1.0)
      setIsSubmitting(false)
    }
  }, [question?.id])

  // Focus textarea when modal opens
  useEffect(() => {
    if (isOpen && textareaRef.current) {
      setTimeout(() => textareaRef.current?.focus(), 100)
    }
  }, [isOpen])

  // Handle keyboard shortcuts
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      // Escape to close
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
      // Cmd/Ctrl + Enter to submit
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && answer.trim()) {
        e.preventDefault()
        handleSubmit()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, answer, onClose])

  const handleSubmit = useCallback(async () => {
    if (!question || !answer.trim() || isSubmitting) return

    setIsSubmitting(true)
    try {
      await onSubmit(question.id, answer.trim(), confidence)
      onClose()
    } catch (error) {
      console.error('[QuestionBubble] Submit error:', error)
      setIsSubmitting(false)
    }
  }, [question, answer, confidence, isSubmitting, onSubmit, onClose])

  const handleSkip = useCallback(() => {
    if (!question) return
    onSkip(question.id)
    onClose()
  }, [question, onSkip, onClose])

  if (!isOpen || !question) {
    return null
  }

  const config = QUESTION_TYPE_CONFIG[question.question_type] || {
    label: question.question_type,
    emoji: '❓',
    color: 'bg-gray-500',
    bgGradient: 'from-gray-500/20 to-gray-600/20',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className={`relative w-full max-w-md bg-gradient-to-br ${config.bgGradient} bg-slate-900 rounded-2xl shadow-2xl border border-slate-700/50 overflow-hidden animate-in fade-in zoom-in-95 duration-200`}
      >
        {/* Header */}
        <div className={`${config.color} px-5 py-3 flex items-center justify-between`}>
          <div className="flex items-center gap-2">
            <span className="text-xl">{config.emoji}</span>
            <span className="font-semibold text-white">{config.label}</span>
          </div>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white transition-colors p-1"
            aria-label="닫기"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Question Section */}
        <div className="p-5">
          <div className="flex items-start gap-4 mb-5">
            <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gradient-to-br from-pink-400 to-purple-500 flex items-center justify-center shadow-lg">
              <span className="text-2xl">🐣</span>
            </div>
            <div className="flex-1 pt-1">
              <p className="text-sm text-slate-400 mb-1">
                비비가 궁금해해요
              </p>
              <p className="text-lg text-white font-medium leading-relaxed">
                {question.question}
              </p>
              {question.context && (
                <p className="text-sm text-slate-400 mt-2 italic border-l-2 border-slate-600 pl-3">
                  &quot;{question.context}&quot;
                </p>
              )}
            </div>
          </div>

          {/* Answer Input */}
          <div className="space-y-4">
            <div>
              <label htmlFor="answer" className="block text-sm font-medium text-slate-300 mb-2">
                답변
              </label>
              <textarea
                ref={textareaRef}
                id="answer"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="비비에게 알려주세요..."
                rows={4}
                className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
              />
              <p className="text-xs text-slate-500 mt-1">
                Ctrl+Enter로 빠르게 제출
              </p>
            </div>

            {/* Confidence Selection */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                확신도
              </label>
              <div className="flex gap-2">
                {CONFIDENCE_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setConfidence(option.value)}
                    className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                      confidence === option.value
                        ? `${config.color} text-white shadow-md`
                        : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50'
                    }`}
                  >
                    <span className="mr-1">{option.emoji}</span>
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="px-5 pb-5 flex gap-3">
          <button
            onClick={handleSkip}
            disabled={isSubmitting}
            className="flex-1 py-3 px-4 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-xl transition-colors font-medium disabled:opacity-50"
          >
            나중에 답변할게요
          </button>
          <button
            onClick={handleSubmit}
            disabled={!answer.trim() || isSubmitting}
            className={`flex-1 py-3 px-4 text-white ${config.color} hover:opacity-90 rounded-xl transition-opacity font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2`}
          >
            {isSubmitting ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                저장 중...
              </>
            ) : (
              '답변 보내기'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
