'use client'

import { useState, useEffect, useCallback } from 'react'

const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000'

// Local types replacing Supabase-generated database.types
export interface Prediction {
  id: string
  scenario: string
  prediction: string
  confidence: number | null
  prediction_type: string | null
  domain: string | null
  reasoning: string | null
  was_correct: boolean | null
  verified_at: string | null
  actual_outcome: string | null
  prediction_error: number | null
  insight_gained: string | null
  based_on_concepts: string[]
  based_on_experiences: string[]
  emotional_impact: Record<string, unknown> | null
  development_stage: number | null
  created_at: string | null
}

export interface Simulation {
  id: string
  goal: string | null
  simulation_type: string | null
  outcome: string | null
  reward_signal: number | null
  started_at: string | null
  ended_at: string | null
  created_at: string | null
}

export interface CausalModel {
  id: string
  cause_concept_id: string | null
  effect_concept_id: string | null
  relationship_type: string | null
  causal_strength: number | null
  confidence: number | null
  evidence_count: number | null
  cause_name?: string | null
  effect_name?: string | null
  cause_category?: string | null
  effect_category?: string | null
  created_at: string | null
}

export interface ImaginationSession {
  id: string
  topic: string
  trigger: string | null
  imagination_type: string | null
  thoughts: unknown[]
  connections_discovered: unknown[]
  insights: string[]
  predictions_made?: unknown[] | null
  emotional_state: Record<string, unknown> | null
  curiosity_level: number | null
  duration_ms: number | null
  started_at: string | null
  ended_at: string | null
}

export interface PredictionStats {
  total: number
  correct: number
  incorrect: number
  pending: number
  accuracy: number
  avgConfidence: number
}

export interface CausalNode {
  id: string
  name: string
  category: string | null
  type: 'cause' | 'effect' | 'both'
}

export interface CausalEdge {
  id: string
  from: string
  to: string
  strength: number
  relationshipType: string
  confidence: number
}

export interface CausalGraphData {
  nodes: CausalNode[]
  edges: CausalEdge[]
}

export interface WorldModelData {
  predictions: Prediction[]
  simulations: Simulation[]
  causalModels: CausalModel[]
  imaginationSessions: ImaginationSession[]
  predictionStats: PredictionStats
  causalGraph: CausalGraphData
}

// Build causal graph from causal model rows
function buildCausalGraph(models: CausalModel[]): CausalGraphData {
  const nodesMap = new Map<string, CausalNode>()
  const edges: CausalEdge[] = []

  models.forEach((row, index) => {
    const causeName = row.cause_name || row.cause_concept_id
    const effectName = row.effect_name || row.effect_concept_id
    if (!causeName || !effectName) return

    if (!nodesMap.has(causeName)) {
      nodesMap.set(causeName, { id: causeName, name: causeName, category: row.cause_category ?? null, type: 'cause' })
    } else {
      const existing = nodesMap.get(causeName)!
      if (existing.type === 'effect') existing.type = 'both'
    }

    if (!nodesMap.has(effectName)) {
      nodesMap.set(effectName, { id: effectName, name: effectName, category: row.effect_category ?? null, type: 'effect' })
    } else {
      const existing = nodesMap.get(effectName)!
      if (existing.type === 'cause') existing.type = 'both'
    }

    edges.push({
      id: `edge-${index}`,
      from: causeName,
      to: effectName,
      strength: row.causal_strength ?? 0.5,
      relationshipType: row.relationship_type ?? 'causes',
      confidence: row.confidence ?? 0.5,
    })
  })

  return { nodes: Array.from(nodesMap.values()), edges }
}

export function useWorldModel() {
  const [data, setData] = useState<WorldModelData>({
    predictions: [],
    simulations: [],
    causalModels: [],
    imaginationSessions: [],
    predictionStats: { total: 0, correct: 0, incorrect: 0, pending: 0, accuracy: 0, avgConfidence: 0 },
    causalGraph: { nodes: [], edges: [] },
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)

      const [predsRes, simsRes, causalRes, imagRes] = await Promise.all([
        fetch(`${FASTAPI_URL}/api/predictions?limit=50`).then(r => r.ok ? r.json() : null),
        fetch(`${FASTAPI_URL}/api/simulations?limit=20`).then(r => r.ok ? r.json() : null),
        fetch(`${FASTAPI_URL}/api/causal-models?limit=100`).then(r => r.ok ? r.json() : null),
        fetch(`${FASTAPI_URL}/api/imagination?limit=20`).then(r => r.ok ? r.json() : null),
      ])

      const predictions: Prediction[] = predsRes?.predictions || []
      const simulations: Simulation[] = simsRes?.simulations || []
      const causalModels: CausalModel[] = causalRes?.causal_models || []
      const imaginationSessions: ImaginationSession[] = imagRes?.sessions || []

      // Compute prediction stats from raw predictions
      const verified = predictions.filter(p => p.was_correct !== null)
      const correct = verified.filter(p => p.was_correct === true)
      const incorrect = verified.filter(p => p.was_correct === false)
      const pending = predictions.filter(p => p.was_correct === null)
      const avgConfidence = predictions.length > 0
        ? predictions.reduce((s, p) => s + (p.confidence ?? 0.5), 0) / predictions.length
        : 0

      const predictionStats: PredictionStats = {
        total: predictions.length,
        correct: correct.length,
        incorrect: incorrect.length,
        pending: pending.length,
        accuracy: verified.length > 0 ? (correct.length / verified.length) * 100 : 0,
        avgConfidence: avgConfidence * 100,
      }

      const causalGraph = buildCausalGraph(causalModels)

      setData({ predictions, simulations, causalModels, imaginationSessions, predictionStats, causalGraph })
      setError(null)
    } catch (err) {
      console.error('Error fetching world model data:', err)
      setError('Failed to load world model data')
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial fetch — no Realtime (tables now in Neo4j, not Supabase)
  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { ...data, loading, error, refresh: fetchData }
}

// Hook for recent predictions only
export function useRecentPredictions(limit = 10) {
  const [predictions, setPredictions] = useState<Prediction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${FASTAPI_URL}/api/predictions?limit=${limit}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        setPredictions(data?.predictions || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [limit])

  return { predictions, loading }
}

// Hook for active imagination session
export function useActiveImagination() {
  const [session, setSession] = useState<ImaginationSession | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${FASTAPI_URL}/api/imagination?limit=5`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        const sessions: ImaginationSession[] = data?.sessions || []
        // Active session = one without ended_at
        const active = sessions.find(s => !s.ended_at) ?? null
        setSession(active)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  return { session, loading }
}
