'use client'

import { useState, useCallback, useRef } from 'react'

const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000'

// Default ordering - defined outside component to maintain stable reference
const DEFAULT_ORDER_BY = [
  { column: 'priority', ascending: false },
  { column: 'created_at', ascending: false },
] as const

export interface PendingQuestion {
  id: string
  question: string
  question_type: string
  status: string | null
  priority: number | null
  context: string | null
  context_concept_ids: string[] | null
  source_curiosity_id: string | null
  answer: string | null
  answer_confidence: number | null
  asked_at: string | null
  answered_at: string | null
  learned_concept_id: string | null
  created_at: string | null
  updated_at: string | null
}

export interface UsePendingQuestionsOptions {
  /** Whether to enable realtime subscription */
  enableRealtime?: boolean
  /** Status filter (default: 'pending') */
  statusFilter?: string | string[]
  /** Limit (default: 10) */
  limit?: number
  /** Order by (default: priority DESC, created_at DESC) */
  orderBy?: readonly { column: string; ascending: boolean }[]
}

export interface UsePendingQuestionsReturn {
  /** List of pending questions */
  questions: PendingQuestion[]
  /** Currently displayed question (highest priority pending) */
  currentQuestion: PendingQuestion | null
  /** Loading state */
  isLoading: boolean
  /** Error message */
  error: string | null
  /** New question arrived via realtime */
  newQuestionAlert: PendingQuestion | null
  /** Clear the new question alert */
  clearAlert: () => void
  /** Mark question as asked */
  markAsAsked: (id: string) => Promise<void>
  /** Submit answer to a question */
  submitAnswer: (id: string, answer: string, confidence?: number) => Promise<void>
  /** Skip a question */
  skipQuestion: (id: string) => Promise<void>
  /** Refetch questions */
  refetch: () => Promise<void>
}

/**
 * Hook for managing pending questions
 *
 * NOTE: pending_questions table is not yet in Neo4j.
 * Baby AI now stores questions via FastAPI → Neo4j pipeline.
 * This hook fetches from FastAPI GET /api/pending-questions when available.
 * Until FastAPI implements pending_questions, returns empty data.
 */
export function usePendingQuestions(
  options: UsePendingQuestionsOptions = {}
): UsePendingQuestionsReturn {
  const {
    statusFilter = 'pending',
    limit = 10,
    orderBy = DEFAULT_ORDER_BY,
  } = options

  const [questions, setQuestions] = useState<PendingQuestion[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [newQuestionAlert, setNewQuestionAlert] = useState<PendingQuestion | null>(null)

  const fetchQuestions = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const statusParam = Array.isArray(statusFilter) ? statusFilter.join(',') : statusFilter
      const url = new URL(`${FASTAPI_URL}/api/pending-questions`)
      url.searchParams.set('status', statusParam)
      url.searchParams.set('limit', String(limit))
      for (const ord of orderBy) {
        url.searchParams.set('order_by', ord.column)
        url.searchParams.set('ascending', String(ord.ascending))
      }

      const res = await fetch(url.toString())
      if (res.ok) {
        const data = await res.json()
        setQuestions(data.questions || [])
      } else {
        // Endpoint not yet implemented — return empty gracefully
        setQuestions([])
      }
    } catch {
      // FastAPI endpoint not yet implemented — fail silently
      setQuestions([])
    } finally {
      setIsLoading(false)
    }
  }, [statusFilter, limit, orderBy])

  const clearAlert = useCallback(() => {
    setNewQuestionAlert(null)
  }, [])

  const markAsAsked = useCallback(async (id: string) => {
    try {
      await fetch(`${FASTAPI_URL}/api/pending-questions/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'asked', asked_at: new Date().toISOString() }),
      })
      setQuestions(prev => prev.map(q => q.id === id ? { ...q, status: 'asked', asked_at: new Date().toISOString() } : q))
    } catch (err) {
      console.error('[usePendingQuestions] markAsAsked error:', err)
      throw err
    }
  }, [])

  const submitAnswer = useCallback(async (id: string, answer: string, confidence?: number) => {
    try {
      const answerConfidence = confidence ?? 1.0
      await fetch(`${FASTAPI_URL}/api/pending-questions/${id}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer, answer_confidence: answerConfidence }),
      })
      setQuestions(prev => prev.filter(q => q.id !== id))
    } catch (err) {
      console.error('[usePendingQuestions] submitAnswer error:', err)
      throw err
    }
  }, [])

  const skipQuestion = useCallback(async (id: string) => {
    try {
      await fetch(`${FASTAPI_URL}/api/pending-questions/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'skipped' }),
      })
      setQuestions(prev => prev.filter(q => q.id !== id))
    } catch (err) {
      console.error('[usePendingQuestions] skipQuestion error:', err)
      throw err
    }
  }, [])

  const currentQuestion = questions.length > 0 ? questions[0] : null

  return {
    questions,
    currentQuestion,
    isLoading,
    error,
    newQuestionAlert,
    clearAlert,
    markAsAsked,
    submitAnswer,
    skipQuestion,
    refetch: fetchQuestions,
  }
}
