'use client'

import { useState, useEffect, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import type {
  Prediction,
  Simulation,
  CausalModel,
  ImaginationSession,
  PredictionStats,
  CausalGraphData,
  CausalNode,
  CausalEdge
} from '@/lib/database.types'

export interface WorldModelData {
  predictions: Prediction[]
  simulations: Simulation[]
  causalModels: CausalModel[]
  imaginationSessions: ImaginationSession[]
  predictionStats: PredictionStats
  causalGraph: CausalGraphData
}

export function useWorldModel() {
  const [data, setData] = useState<WorldModelData>({
    predictions: [],
    simulations: [],
    causalModels: [],
    imaginationSessions: [],
    predictionStats: {
      total: 0,
      correct: 0,
      incorrect: 0,
      pending: 0,
      accuracy: 0,
      avgConfidence: 0
    },
    causalGraph: { nodes: [], edges: [] }
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)

      // Fetch all world model data in parallel
      const [
        predictionsRes,
        simulationsRes,
        causalModelsRes,
        imaginationRes,
        statsRes,
        causalNetworkRes
      ] = await Promise.all([
        supabase
          .from('predictions')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(50),
        supabase
          .from('simulations')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(20),
        supabase
          .from('causal_models')
          .select('*')
          .order('causal_strength', { ascending: false })
          .limit(100),
        supabase
          .from('imagination_sessions')
          .select('*')
          .order('started_at', { ascending: false })
          .limit(20),
        supabase
          .from('prediction_accuracy_stats')
          .select('*'),
        supabase
          .from('causal_network_summary')
          .select('*')
      ])

      // Process prediction stats
      let stats: PredictionStats = {
        total: 0,
        correct: 0,
        incorrect: 0,
        pending: 0,
        accuracy: 0,
        avgConfidence: 0
      }

      if (statsRes.data && statsRes.data.length > 0) {
        const aggregated = statsRes.data.reduce((acc, row) => ({
          total: acc.total + (row.total_predictions || 0),
          correct: acc.correct + (row.correct_predictions || 0),
          incorrect: acc.incorrect + (row.incorrect_predictions || 0),
          pending: acc.pending + (row.pending_predictions || 0),
          avgConfidence: row.avg_confidence || 0
        }), { total: 0, correct: 0, incorrect: 0, pending: 0, avgConfidence: 0 })

        stats = {
          ...aggregated,
          accuracy: aggregated.total > 0
            ? (aggregated.correct / (aggregated.correct + aggregated.incorrect)) * 100
            : 0,
          avgConfidence: aggregated.avgConfidence * 100
        }
      }

      // Process causal graph
      const causalGraph = buildCausalGraph(causalNetworkRes.data || [])

      setData({
        predictions: predictionsRes.data || [],
        simulations: simulationsRes.data || [],
        causalModels: causalModelsRes.data || [],
        imaginationSessions: imaginationRes.data || [],
        predictionStats: stats,
        causalGraph
      })
      setError(null)
    } catch (err) {
      console.error('Error fetching world model data:', err)
      setError('Failed to load world model data')
    } finally {
      setLoading(false)
    }
  }, [])

  // Build causal graph from network summary
  const buildCausalGraph = (networkData: Array<{
    cause_name: string | null
    cause_category: string | null
    effect_name: string | null
    effect_category: string | null
    relationship_type: string | null
    causal_strength: number | null
    confidence: number | null
    evidence_count: number | null
  }>): CausalGraphData => {
    const nodesMap = new Map<string, CausalNode>()
    const edges: CausalEdge[] = []

    networkData.forEach((row, index) => {
      if (!row.cause_name || !row.effect_name) return

      // Add cause node
      if (!nodesMap.has(row.cause_name)) {
        nodesMap.set(row.cause_name, {
          id: row.cause_name,
          name: row.cause_name,
          category: row.cause_category,
          type: 'cause'
        })
      } else {
        const existing = nodesMap.get(row.cause_name)!
        if (existing.type === 'effect') {
          existing.type = 'both'
        }
      }

      // Add effect node
      if (!nodesMap.has(row.effect_name)) {
        nodesMap.set(row.effect_name, {
          id: row.effect_name,
          name: row.effect_name,
          category: row.effect_category,
          type: 'effect'
        })
      } else {
        const existing = nodesMap.get(row.effect_name)!
        if (existing.type === 'cause') {
          existing.type = 'both'
        }
      }

      // Add edge
      edges.push({
        id: `edge-${index}`,
        from: row.cause_name,
        to: row.effect_name,
        strength: row.causal_strength || 0.5,
        relationshipType: row.relationship_type || 'causes',
        confidence: row.confidence || 0.5
      })
    })

    return {
      nodes: Array.from(nodesMap.values()),
      edges
    }
  }

  // Subscribe to real-time updates
  useEffect(() => {
    fetchData()

    const channel = supabase
      .channel('world-model-changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'predictions' },
        () => fetchData()
      )
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'simulations' },
        () => fetchData()
      )
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'imagination_sessions' },
        () => fetchData()
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [fetchData])

  return {
    ...data,
    loading,
    error,
    refresh: fetchData
  }
}

// Hook for recent predictions only
export function useRecentPredictions(limit = 10) {
  const [predictions, setPredictions] = useState<Prediction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchPredictions = async () => {
      const { data } = await supabase
        .from('predictions')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(limit)

      setPredictions(data || [])
      setLoading(false)
    }

    fetchPredictions()

    const channel = supabase
      .channel('predictions-recent')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'predictions' },
        (payload) => {
          setPredictions(prev => [payload.new as Prediction, ...prev.slice(0, limit - 1)])
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [limit])

  return { predictions, loading }
}

// Hook for active imagination session
export function useActiveImagination() {
  const [session, setSession] = useState<ImaginationSession | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchSession = async () => {
      const { data } = await supabase
        .from('imagination_sessions')
        .select('*')
        .is('ended_at', null)
        .order('started_at', { ascending: false })
        .limit(1)
        .single()

      setSession(data)
      setLoading(false)
    }

    fetchSession()

    const channel = supabase
      .channel('imagination-active')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'imagination_sessions' },
        fetchSession
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  return { session, loading }
}
