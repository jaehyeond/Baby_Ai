'use client'

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { supabase } from '@/lib/supabase'
import type { PendingQuestion, PendingQuestionUpdate } from '@/lib/database.types'
import type { RealtimeChannel } from '@supabase/supabase-js'

// Default ordering - defined outside component to maintain stable reference
const DEFAULT_ORDER_BY = [
  { column: 'priority', ascending: false },
  { column: 'created_at', ascending: false },
] as const

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
 * Hook for managing pending questions with Supabase Realtime support
 *
 * Features:
 * - Fetches pending questions sorted by priority
 * - Subscribes to INSERT events for real-time notifications
 * - Provides methods to answer/skip questions
 */
export function usePendingQuestions(
  options: UsePendingQuestionsOptions = {}
): UsePendingQuestionsReturn {
  const {
    enableRealtime = true,
    statusFilter = 'pending',
    limit = 10,
    orderBy = DEFAULT_ORDER_BY,
  } = options

  // Memoize statusFilter to prevent unnecessary re-renders
  const stableStatusFilter = useMemo(
    () => (Array.isArray(statusFilter) ? statusFilter.join(',') : statusFilter),
    [statusFilter]
  )

  const [questions, setQuestions] = useState<PendingQuestion[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [newQuestionAlert, setNewQuestionAlert] = useState<PendingQuestion | null>(null)

  const channelRef = useRef<RealtimeChannel | null>(null)

  // Fetch questions from database
  const fetchQuestions = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Build query
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let query = (supabase as any)
        .from('pending_questions')
        .select('*')

      // Apply status filter
      if (Array.isArray(statusFilter)) {
        query = query.in('status', statusFilter)
      } else {
        query = query.eq('status', statusFilter)
      }

      // Apply ordering
      for (const order of orderBy) {
        query = query.order(order.column, { ascending: order.ascending })
      }

      // Apply limit
      query = query.limit(limit)

      const { data, error: fetchError } = await query

      if (fetchError) throw fetchError

      setQuestions(data || [])
      console.log('[usePendingQuestions] Fetched', data?.length || 0, 'questions')
    } catch (err) {
      console.error('[usePendingQuestions] Fetch error:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch questions')
    } finally {
      setIsLoading(false)
    }
    // Use stableStatusFilter instead of statusFilter to prevent re-renders
    // orderBy uses DEFAULT_ORDER_BY which is a stable reference
  }, [stableStatusFilter, limit, orderBy, statusFilter])

  // Subscribe to realtime INSERT events
  useEffect(() => {
    if (!enableRealtime) return

    // Create channel for pending_questions INSERT events
    const channel = supabase
      .channel('pending_questions_inserts')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'pending_questions',
        },
        (payload) => {
          console.log('[usePendingQuestions] New question received:', payload.new)
          const newQuestion = payload.new as PendingQuestion

          // Set alert for UI notification
          setNewQuestionAlert(newQuestion)

          // Add to questions list if it matches the filter
          const matchesFilter = Array.isArray(statusFilter)
            ? statusFilter.includes(newQuestion.status || 'pending')
            : newQuestion.status === statusFilter

          if (matchesFilter) {
            setQuestions((prev) => {
              // Insert maintaining priority order
              const updated = [...prev, newQuestion]
              updated.sort((a, b) => {
                // Sort by priority DESC, then by created_at DESC
                const priorityDiff = (b.priority || 0.5) - (a.priority || 0.5)
                if (priorityDiff !== 0) return priorityDiff
                return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
              })
              return updated.slice(0, limit)
            })
          }
        }
      )
      .subscribe((status) => {
        console.log('[usePendingQuestions] Realtime subscription status:', status)
      })

    channelRef.current = channel

    // Cleanup on unmount
    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current)
        channelRef.current = null
      }
    }
  }, [enableRealtime, statusFilter, limit])

  // Initial fetch - only run once on mount, not when fetchQuestions changes
  const initialFetchDone = useRef(false)
  useEffect(() => {
    if (!initialFetchDone.current) {
      initialFetchDone.current = true
      fetchQuestions()
    }
  }, [fetchQuestions])

  // Clear the new question alert
  const clearAlert = useCallback(() => {
    setNewQuestionAlert(null)
  }, [])

  // Mark question as asked
  const markAsAsked = useCallback(async (id: string) => {
    try {
      const askedAt = new Date().toISOString()
      const update: PendingQuestionUpdate = {
        status: 'asked',
        asked_at: askedAt,
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { error: updateError } = await (supabase as any)
        .from('pending_questions')
        .update(update)
        .eq('id', id)

      if (updateError) throw updateError

      // Update local state - explicitly cast to maintain type consistency
      setQuestions((prev) =>
        prev.map((q): PendingQuestion =>
          q.id === id
            ? { ...q, status: 'asked', asked_at: askedAt }
            : q
        )
      )
      console.log('[usePendingQuestions] Marked as asked:', id)
    } catch (err) {
      console.error('[usePendingQuestions] markAsAsked error:', err)
      throw err
    }
  }, [])

  // Map question type to semantic concept category
  const getConceptCategory = (questionType: string): string => {
    const categoryMap: Record<string, string> = {
      personal: 'user_info',
      preference: 'user_preference',
      experience: 'user_experience',
      relationship: 'user_relationship',
    }
    return categoryMap[questionType] || 'user_knowledge'
  }

  // Save answer as a semantic concept
  const saveAnswerAsConcept = useCallback(
    async (question: PendingQuestion, answer: string, confidence: number) => {
      try {
        // Create concept name from question (extract key topic)
        const conceptName = `user_answer_${question.question_type}_${Date.now()}`
        const category = getConceptCategory(question.question_type)

        // Build concept data
        const conceptData = {
          name: conceptName,
          category,
          description: answer,
          strength: confidence,
          usage_count: 1,
          extras: {
            source: 'proactive_question',
            question_id: question.id,
            question_text: question.question,
            question_type: question.question_type,
            context: question.context,
            answered_at: new Date().toISOString(),
          },
        }

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const { data: concept, error: conceptError } = await (supabase as any)
          .from('semantic_concepts')
          .insert(conceptData)
          .select('id')
          .single()

        if (conceptError) {
          console.error('[usePendingQuestions] Failed to save concept:', conceptError)
          return null
        }

        console.log('[usePendingQuestions] Saved answer as concept:', concept?.id)
        return concept?.id || null
      } catch (err) {
        console.error('[usePendingQuestions] saveAnswerAsConcept error:', err)
        return null
      }
    },
    []
  )

  // Record answer as learning experience
  const recordAnswerExperience = useCallback(
    async (question: PendingQuestion, answer: string, conceptId: string | null, confidence: number) => {
      try {
        const experienceData = {
          task: `learned: ${question.question}`,
          task_type: 'learning',
          output: answer,
          success: true,
          emotional_salience: confidence,
          memory_strength: confidence,
          tags: ['proactive_question', question.question_type],
          extras: {
            source: 'proactive_question',
            question_id: question.id,
            question_type: question.question_type,
            learned_concept_id: conceptId,
          },
        }

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const { error: expError } = await (supabase as any)
          .from('experiences')
          .insert(experienceData)

        if (expError) {
          console.error('[usePendingQuestions] Failed to record experience:', expError)
        } else {
          console.log('[usePendingQuestions] Recorded learning experience')
        }
      } catch (err) {
        console.error('[usePendingQuestions] recordAnswerExperience error:', err)
      }
    },
    []
  )

  // Submit answer to a question
  const submitAnswer = useCallback(
    async (id: string, answer: string, confidence?: number) => {
      try {
        // Find the question in current list
        const question = questions.find((q) => q.id === id)
        const answerConfidence = confidence ?? 1.0

        // Save answer as semantic concept first
        let learnedConceptId: string | null = null
        if (question) {
          learnedConceptId = await saveAnswerAsConcept(question, answer, answerConfidence)
          // Also record as learning experience (for baby_state counting)
          await recordAnswerExperience(question, answer, learnedConceptId, answerConfidence)
        }

        const update: PendingQuestionUpdate = {
          status: 'answered',
          answer,
          answer_confidence: answerConfidence,
          answered_at: new Date().toISOString(),
          learned_concept_id: learnedConceptId,
        }

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const { error: updateError } = await (supabase as any)
          .from('pending_questions')
          .update(update)
          .eq('id', id)

        if (updateError) throw updateError

        // Remove from local state (since it's no longer pending)
        setQuestions((prev) => prev.filter((q) => q.id !== id))
        console.log('[usePendingQuestions] Answer submitted:', id, 'concept:', learnedConceptId)
      } catch (err) {
        console.error('[usePendingQuestions] submitAnswer error:', err)
        throw err
      }
    },
    [questions, saveAnswerAsConcept, recordAnswerExperience]
  )

  // Skip a question
  const skipQuestion = useCallback(async (id: string) => {
    try {
      const update: PendingQuestionUpdate = {
        status: 'skipped',
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { error: updateError } = await (supabase as any)
        .from('pending_questions')
        .update(update)
        .eq('id', id)

      if (updateError) throw updateError

      // Remove from local state
      setQuestions((prev) => prev.filter((q) => q.id !== id))
      console.log('[usePendingQuestions] Question skipped:', id)
    } catch (err) {
      console.error('[usePendingQuestions] skipQuestion error:', err)
      throw err
    }
  }, [])

  // Current question is the first one (highest priority)
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
