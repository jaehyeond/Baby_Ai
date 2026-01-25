'use client'

import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Star,
  ThumbsUp,
  ThumbsDown,
  MessageSquarePlus,
  X,
  Check,
  Loader2,
} from 'lucide-react'

export interface FeedbackButtonsProps {
  experienceId: string
  onFeedbackSubmit?: (data: FeedbackData) => void
  className?: string
  compact?: boolean
}

export interface FeedbackData {
  experience_id: string
  rating: number
  feedback_text?: string
  is_helpful?: boolean
  is_accurate?: boolean
  is_appropriate?: boolean
}

export interface FeedbackResult {
  success: boolean
  feedback_id?: string
  propagation?: {
    concepts_adjusted: number
    strategy_adjusted: string | null
    memory_adjusted: boolean
    new_concepts_linked: number
  }
  error?: string
}

export function FeedbackButtons({
  experienceId,
  onFeedbackSubmit,
  className = '',
  compact = false,
}: FeedbackButtonsProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [selectedRating, setSelectedRating] = useState<number | null>(null)
  const [feedbackText, setFeedbackText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [result, setResult] = useState<FeedbackResult | null>(null)

  const handleRatingClick = useCallback((rating: number) => {
    setSelectedRating(rating)
    if (compact) {
      // In compact mode, submit immediately on rating
      submitFeedback(rating)
    }
  }, [compact])

  const submitFeedback = useCallback(async (rating?: number) => {
    const finalRating = rating ?? selectedRating
    if (!finalRating) return

    setIsSubmitting(true)

    try {
      const feedbackData: FeedbackData = {
        experience_id: experienceId,
        rating: finalRating,
        feedback_text: feedbackText || undefined,
      }

      const response = await fetch('/api/conversation/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedbackData),
      })

      const data: FeedbackResult = await response.json()
      setResult(data)

      if (data.success) {
        setSubmitted(true)
        onFeedbackSubmit?.(feedbackData)
      }
    } catch (error) {
      console.error('[FeedbackButtons] Error:', error)
      setResult({ success: false, error: 'Failed to submit feedback' })
    } finally {
      setIsSubmitting(false)
    }
  }, [experienceId, selectedRating, feedbackText, onFeedbackSubmit])

  const handleSubmit = useCallback(() => {
    submitFeedback()
  }, [submitFeedback])

  const handleReset = useCallback(() => {
    setSelectedRating(null)
    setFeedbackText('')
    setSubmitted(false)
    setResult(null)
    setIsExpanded(false)
  }, [])

  // Submitted state
  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`flex items-center gap-2 text-sm ${className}`}
      >
        <Check className="w-4 h-4 text-emerald-400" />
        <span className="text-emerald-400">
          피드백 감사합니다!
          {result?.propagation && (
            <span className="text-slate-500 ml-1">
              ({result.propagation.concepts_adjusted}개 개념 업데이트)
            </span>
          )}
        </span>
        <button
          onClick={handleReset}
          className="text-slate-500 hover:text-slate-400 ml-2"
        >
          <X className="w-3 h-3" />
        </button>
      </motion.div>
    )
  }

  // Compact mode - just stars
  if (compact) {
    return (
      <div className={`flex items-center gap-1 ${className}`}>
        {[1, 2, 3, 4, 5].map((rating) => (
          <button
            key={rating}
            onClick={() => handleRatingClick(rating)}
            disabled={isSubmitting}
            className="p-1 hover:scale-110 transition-transform disabled:opacity-50"
            title={`${rating}점`}
          >
            {isSubmitting && selectedRating === rating ? (
              <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />
            ) : (
              <Star
                className={`w-4 h-4 ${
                  selectedRating && rating <= selectedRating
                    ? 'text-yellow-400 fill-yellow-400'
                    : 'text-slate-600 hover:text-yellow-400'
                }`}
              />
            )}
          </button>
        ))}
      </div>
    )
  }

  // Full mode - expandable with text input
  return (
    <div className={`${className}`}>
      <AnimatePresence mode="wait">
        {!isExpanded ? (
          <motion.button
            key="expand-btn"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsExpanded(true)}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-400 transition-colors"
          >
            <MessageSquarePlus className="w-3.5 h-3.5" />
            <span>피드백</span>
          </motion.button>
        ) : (
          <motion.div
            key="feedback-panel"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50"
          >
            {/* Rating stars */}
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-slate-400">이 응답은 어땠나요?</span>
              <button
                onClick={() => setIsExpanded(false)}
                className="p-1 text-slate-500 hover:text-slate-400"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="flex items-center gap-1 mb-3">
              {[1, 2, 3, 4, 5].map((rating) => (
                <button
                  key={rating}
                  onClick={() => setSelectedRating(rating)}
                  className="p-1.5 hover:scale-110 transition-transform"
                  title={getRatingLabel(rating)}
                >
                  <Star
                    className={`w-5 h-5 ${
                      selectedRating && rating <= selectedRating
                        ? 'text-yellow-400 fill-yellow-400'
                        : 'text-slate-600 hover:text-yellow-400'
                    }`}
                  />
                </button>
              ))}
              {selectedRating && (
                <span className="text-xs text-slate-400 ml-2">
                  {getRatingLabel(selectedRating)}
                </span>
              )}
            </div>

            {/* Optional text feedback */}
            <div className="mb-3">
              <input
                type="text"
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                placeholder="추가 의견 (선택)"
                className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
              />
            </div>

            {/* Submit button */}
            <button
              onClick={handleSubmit}
              disabled={!selectedRating || isSubmitting}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 disabled:opacity-50 disabled:hover:bg-cyan-500/20 rounded-lg text-sm text-cyan-400 transition-colors"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  제출 중...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  피드백 보내기
                </>
              )}
            </button>

            {/* Error message */}
            {result?.error && (
              <p className="text-xs text-rose-400 mt-2">{result.error}</p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function getRatingLabel(rating: number): string {
  const labels: Record<number, string> = {
    1: '별로예요',
    2: '아쉬워요',
    3: '보통이에요',
    4: '좋아요',
    5: '최고예요!',
  }
  return labels[rating] || ''
}

// Quick thumbs up/down feedback (simpler alternative)
export interface QuickFeedbackProps {
  experienceId: string
  onFeedback?: (isPositive: boolean) => void
  className?: string
}

export function QuickFeedback({
  experienceId,
  onFeedback,
  className = '',
}: QuickFeedbackProps) {
  const [submitted, setSubmitted] = useState<'positive' | 'negative' | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleFeedback = useCallback(async (isPositive: boolean) => {
    setIsSubmitting(true)

    try {
      const response = await fetch('/api/conversation/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          experience_id: experienceId,
          rating: isPositive ? 5 : 2,
          is_helpful: isPositive,
        }),
      })

      const data = await response.json()

      if (data.success) {
        setSubmitted(isPositive ? 'positive' : 'negative')
        onFeedback?.(isPositive)
      }
    } catch (error) {
      console.error('[QuickFeedback] Error:', error)
    } finally {
      setIsSubmitting(false)
    }
  }, [experienceId, onFeedback])

  if (submitted) {
    return (
      <div className={`flex items-center gap-1 text-xs text-slate-500 ${className}`}>
        {submitted === 'positive' ? (
          <ThumbsUp className="w-3.5 h-3.5 text-emerald-400" />
        ) : (
          <ThumbsDown className="w-3.5 h-3.5 text-rose-400" />
        )}
        <span>감사합니다</span>
      </div>
    )
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <button
        onClick={() => handleFeedback(true)}
        disabled={isSubmitting}
        className="p-1 text-slate-500 hover:text-emerald-400 transition-colors disabled:opacity-50"
        title="좋아요"
      >
        {isSubmitting ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <ThumbsUp className="w-3.5 h-3.5" />
        )}
      </button>
      <button
        onClick={() => handleFeedback(false)}
        disabled={isSubmitting}
        className="p-1 text-slate-500 hover:text-rose-400 transition-colors disabled:opacity-50"
        title="별로예요"
      >
        <ThumbsDown className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}
