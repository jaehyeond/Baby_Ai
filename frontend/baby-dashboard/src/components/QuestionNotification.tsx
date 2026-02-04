'use client'

import { useState, useEffect, useCallback } from 'react'
import type { PendingQuestion } from '@/lib/database.types'

interface QuestionNotificationProps {
  /** The new question to display */
  question: PendingQuestion | null
  /** Callback when notification is dismissed */
  onDismiss: () => void
  /** Callback when user wants to answer */
  onAnswer: (question: PendingQuestion) => void
  /** Auto-dismiss after this many milliseconds (0 = never) */
  autoDismissMs?: number
}

// Question type display configuration
const QUESTION_TYPE_CONFIG: Record<string, { label: string; emoji: string; color: string }> = {
  personal: { label: '개인 정보', emoji: '👤', color: 'bg-blue-500' },
  preference: { label: '취향/선호', emoji: '💜', color: 'bg-purple-500' },
  experience: { label: '경험/추억', emoji: '📚', color: 'bg-amber-500' },
  relationship: { label: '관계/감정', emoji: '💕', color: 'bg-pink-500' },
}

/**
 * QuestionNotification - Toast notification for new pending questions
 *
 * Shows a slide-in notification when a new question arrives via Realtime.
 * User can dismiss or click to answer the question.
 */
export function QuestionNotification({
  question,
  onDismiss,
  onAnswer,
  autoDismissMs = 10000,
}: QuestionNotificationProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [isExiting, setIsExiting] = useState(false)

  // Show/hide animation
  useEffect(() => {
    if (question) {
      setIsVisible(true)
      setIsExiting(false)
    }
  }, [question])

  // Auto-dismiss timer
  useEffect(() => {
    if (!question || autoDismissMs === 0) return

    const timer = setTimeout(() => {
      handleDismiss()
    }, autoDismissMs)

    return () => clearTimeout(timer)
  }, [question, autoDismissMs])

  const handleDismiss = useCallback(() => {
    setIsExiting(true)
    setTimeout(() => {
      setIsVisible(false)
      onDismiss()
    }, 300) // Match animation duration
  }, [onDismiss])

  const handleAnswer = useCallback(() => {
    if (question) {
      setIsExiting(true)
      setTimeout(() => {
        setIsVisible(false)
        onAnswer(question)
      }, 300)
    }
  }, [question, onAnswer])

  if (!question || !isVisible) {
    return null
  }

  const config = QUESTION_TYPE_CONFIG[question.question_type] || {
    label: question.question_type,
    emoji: '❓',
    color: 'bg-gray-500',
  }

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 max-w-sm transform transition-all duration-300 ease-out ${
        isExiting ? 'translate-x-full opacity-0' : 'translate-x-0 opacity-100'
      }`}
    >
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        {/* Header */}
        <div className={`${config.color} px-4 py-2 text-white flex items-center justify-between`}>
          <div className="flex items-center gap-2">
            <span className="text-lg">{config.emoji}</span>
            <span className="font-medium text-sm">{config.label}</span>
          </div>
          <button
            onClick={handleDismiss}
            className="text-white/80 hover:text-white transition-colors"
            aria-label="닫기"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-4">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-pink-400 to-purple-500 flex items-center justify-center">
              <span className="text-white text-lg">🐣</span>
            </div>
            <div className="flex-1">
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">
                비비가 궁금해해요
              </p>
              <p className="text-slate-800 dark:text-white font-medium">
                {question.question}
              </p>
              {question.context && (
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 italic">
                  &quot;{question.context}&quot;
                </p>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 mt-4">
            <button
              onClick={handleDismiss}
              className="flex-1 py-2 px-3 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              나중에
            </button>
            <button
              onClick={handleAnswer}
              className={`flex-1 py-2 px-3 text-sm text-white ${config.color} hover:opacity-90 rounded-lg transition-opacity font-medium`}
            >
              답변하기
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
