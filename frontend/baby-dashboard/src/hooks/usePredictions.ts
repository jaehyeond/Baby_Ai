'use client'

import { useState, useEffect, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import type { Prediction, Json } from '@/lib/database.types'

// Parsed prediction for UI display
export interface ParsedPrediction {
  id: string
  scenario: string
  prediction: string
  confidence: number
  predictionType: string | null
  domain: string | null
  reasoning: string | null
  // Verification fields
  wasCorrect: boolean | null
  verifiedAt: Date | null
  actualOutcome: string | null
  predictionError: number | null
  insightGained: string | null
  // v18: Auto-verification fields
  verifiableAfter: string | null
  autoVerified: boolean
  // Metadata
  basedOnConcepts: string[]
  basedOnExperiences: string[]
  emotionalImpact: Record<string, number>
  developmentStage: number | null
  createdAt: Date | null
}

// Parse raw prediction row to typed prediction
function parsePrediction(raw: Prediction): ParsedPrediction {
  const emotionalImpact: Record<string, number> =
    typeof raw.emotional_impact === 'object' && raw.emotional_impact !== null
      ? Object.fromEntries(
          Object.entries(raw.emotional_impact as Record<string, unknown>)
            .filter(([, v]) => typeof v === 'number')
            .map(([k, v]) => [k, v as number])
        )
      : {}

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const rawAny = raw as any

  return {
    id: raw.id,
    scenario: raw.scenario,
    prediction: raw.prediction,
    confidence: raw.confidence ?? 0.5,
    predictionType: raw.prediction_type,
    domain: raw.domain,
    reasoning: raw.reasoning,
    wasCorrect: raw.was_correct,
    verifiedAt: raw.verified_at ? new Date(raw.verified_at) : null,
    actualOutcome: raw.actual_outcome,
    predictionError: raw.prediction_error,
    insightGained: raw.insight_gained,
    // v18: Auto-verification fields
    verifiableAfter: rawAny.verifiable_after ?? null,
    autoVerified: rawAny.auto_verified ?? false,
    basedOnConcepts: raw.based_on_concepts ?? [],
    basedOnExperiences: raw.based_on_experiences ?? [],
    emotionalImpact,
    developmentStage: raw.development_stage,
    createdAt: raw.created_at ? new Date(raw.created_at) : null,
  }
}

export interface VerifyPredictionData {
  wasCorrect: boolean
  actualOutcome?: string
  insightGained?: string
}

export interface PredictionStats {
  total: number
  verified: number
  pending: number
  correct: number
  incorrect: number
  accuracy: number
  avgConfidence: number
  avgConfidenceWhenCorrect: number
  avgConfidenceWhenIncorrect: number
  // v18: Auto-verification stats
  autoVerified: number
  manualVerified: number
}

interface UsePredictionsReturn {
  predictions: ParsedPrediction[]
  pendingPredictions: ParsedPrediction[]
  verifiedPredictions: ParsedPrediction[]
  autoVerifiedPredictions: ParsedPrediction[]
  manualPendingPredictions: ParsedPrediction[]
  isLoading: boolean
  error: string | null
  refetch: () => Promise<void>
  verifyPrediction: (predictionId: string, data: VerifyPredictionData) => Promise<boolean>
  stats: PredictionStats
}

export function usePredictions(limit: number = 50): UsePredictionsReturn {
  const [predictions, setPredictions] = useState<ParsedPrediction[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchPredictions = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error: fetchError } = await (supabase as any)
        .from('predictions')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(limit)

      if (fetchError) throw fetchError

      const parsedPredictions = (data || []).map(parsePrediction)
      setPredictions(parsedPredictions)
    } catch (err) {
      console.error('[usePredictions] Error:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch predictions')
    } finally {
      setIsLoading(false)
    }
  }, [limit])

  useEffect(() => {
    fetchPredictions()
  }, [fetchPredictions])

  // Verify a prediction (mark as correct/incorrect with feedback)
  const verifyPrediction = useCallback(
    async (predictionId: string, data: VerifyPredictionData): Promise<boolean> => {
      try {
        const prediction = predictions.find((p) => p.id === predictionId)
        if (!prediction) {
          console.error('[usePredictions] Prediction not found:', predictionId)
          return false
        }

        // Calculate prediction error (0 = correct, 1 = incorrect)
        const predictionError = data.wasCorrect ? 0 : 1

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const { error: updateError } = await (supabase as any)
          .from('predictions')
          .update({
            was_correct: data.wasCorrect,
            actual_outcome: data.actualOutcome || null,
            insight_gained: data.insightGained || null,
            prediction_error: predictionError,
            verified_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          })
          .eq('id', predictionId)

        if (updateError) throw updateError

        // Update local state
        setPredictions((prev) =>
          prev.map((p) =>
            p.id === predictionId
              ? {
                  ...p,
                  wasCorrect: data.wasCorrect,
                  actualOutcome: data.actualOutcome || null,
                  insightGained: data.insightGained || null,
                  predictionError,
                  verifiedAt: new Date(),
                }
              : p
          )
        )

        console.log('[usePredictions] Verified prediction:', predictionId, data.wasCorrect)
        return true
      } catch (err) {
        console.error('[usePredictions] Verify error:', err)
        return false
      }
    },
    [predictions]
  )

  // Filter predictions by verification status
  const pendingPredictions = predictions.filter((p) => p.wasCorrect === null)
  const verifiedPredictions = predictions.filter((p) => p.wasCorrect !== null)

  // v18: Filter by auto/manual verification
  const autoVerifiedPredictions = verifiedPredictions.filter((p) => p.autoVerified)
  const manualVerifiedPredictions = verifiedPredictions.filter((p) => !p.autoVerified)
  // Manual pending = predictions that need user verification (verifiable_after === 'manual' or null)
  const manualPendingPredictions = pendingPredictions.filter(
    (p) => p.verifiableAfter === 'manual' || p.verifiableAfter === null
  )

  // Calculate stats
  const correctPredictions = verifiedPredictions.filter((p) => p.wasCorrect === true)
  const incorrectPredictions = verifiedPredictions.filter((p) => p.wasCorrect === false)

  const stats: PredictionStats = {
    total: predictions.length,
    verified: verifiedPredictions.length,
    pending: pendingPredictions.length,
    correct: correctPredictions.length,
    incorrect: incorrectPredictions.length,
    accuracy:
      verifiedPredictions.length > 0
        ? correctPredictions.length / verifiedPredictions.length
        : 0,
    avgConfidence:
      predictions.length > 0
        ? predictions.reduce((sum, p) => sum + p.confidence, 0) / predictions.length
        : 0,
    avgConfidenceWhenCorrect:
      correctPredictions.length > 0
        ? correctPredictions.reduce((sum, p) => sum + p.confidence, 0) / correctPredictions.length
        : 0,
    avgConfidenceWhenIncorrect:
      incorrectPredictions.length > 0
        ? incorrectPredictions.reduce((sum, p) => sum + p.confidence, 0) / incorrectPredictions.length
        : 0,
    // v18: Auto-verification stats
    autoVerified: autoVerifiedPredictions.length,
    manualVerified: manualVerifiedPredictions.length,
  }

  return {
    predictions,
    pendingPredictions,
    verifiedPredictions,
    autoVerifiedPredictions,
    manualPendingPredictions,
    isLoading,
    error,
    refetch: fetchPredictions,
    verifyPrediction,
    stats,
  }
}

export default usePredictions
