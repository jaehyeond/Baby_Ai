'use client'

import { useState, useEffect, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import type { NeuronNode, Synapse, BrainData } from '@/lib/database.types'

// Type for raw concept data from Supabase
interface RawConcept {
  id: string
  name: string
  category: string | null
  strength: number
  usage_count: number
}

interface RawExperienceConcept {
  experience_id: string
  concept_id: string
  relevance: number | null
  co_activation_count: number
}

// Category colors for neurons
const CATEGORY_COLORS: Record<string, string> = {
  algorithm: '#f43f5e',
  function: '#a855f7',
  class: '#14b8a6',
  general: '#3b82f6',
  test: '#22c55e',
  default: '#6366f1',
}

// Generate 3D position using fibonacci sphere for even distribution
function fibonacciSphere(index: number, total: number, radius: number): [number, number, number] {
  const goldenRatio = (1 + Math.sqrt(5)) / 2
  const theta = 2 * Math.PI * index / goldenRatio
  const phi = Math.acos(1 - 2 * (index + 0.5) / total)

  const x = radius * Math.sin(phi) * Math.cos(theta)
  const y = radius * Math.sin(phi) * Math.sin(theta)
  const z = radius * Math.cos(phi)

  return [x, y, z]
}

export function useBrainData() {
  const [brainData, setBrainData] = useState<BrainData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchBrainData = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Fetch semantic concepts (neurons)
      // Using 'as any' because these tables aren't in the generated TypeScript types
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data: concepts, error: conceptsError } = await (supabase as any)
        .from('semantic_concepts')
        .select('id, name, category, strength, usage_count')
        .order('usage_count', { ascending: false })
        .limit(100) as { data: RawConcept[] | null; error: Error | null }

      if (conceptsError) throw conceptsError

      // Fetch co-occurrence data using raw SQL via RPC or direct query
      // Since we can't use raw SQL directly, we'll compute synapses from experience_concepts
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data: experienceConcepts, error: ecError } = await (supabase as any)
        .from('experience_concepts')
        .select('experience_id, concept_id, relevance, co_activation_count')
        .order('co_activation_count', { ascending: false })
        .limit(500) as { data: RawExperienceConcept[] | null; error: Error | null }

      if (ecError) throw ecError

      // Build concept ID to index map
      const conceptMap = new Map<string, number>()
      concepts?.forEach((c, i) => conceptMap.set(c.id, i))

      // Group by experience to find co-occurrences
      const experienceGroups = new Map<string, { conceptId: string; relevance: number }[]>()
      experienceConcepts?.forEach((ec) => {
        const group = experienceGroups.get(ec.experience_id) || []
        group.push({ conceptId: ec.concept_id, relevance: ec.relevance || 0.5 })
        experienceGroups.set(ec.experience_id, group)
      })

      // Build synapse map (concept pairs that co-occur)
      const synapseMap = new Map<string, { count: number; totalRelevance: number }>()
      experienceGroups.forEach((group) => {
        for (let i = 0; i < group.length; i++) {
          for (let j = i + 1; j < group.length; j++) {
            const [id1, id2] = [group[i].conceptId, group[j].conceptId].sort()
            const key = `${id1}-${id2}`
            const existing = synapseMap.get(key) || { count: 0, totalRelevance: 0 }
            synapseMap.set(key, {
              count: existing.count + 1,
              totalRelevance: existing.totalRelevance + group[i].relevance + group[j].relevance,
            })
          }
        }
      })

      // Convert to neurons with 3D positions
      const neurons: NeuronNode[] = (concepts || []).map((c, index) => ({
        id: c.id,
        name: c.name,
        category: c.category || 'default',
        strength: c.strength || 0.5,
        usageCount: c.usage_count || 0,
        position: fibonacciSphere(index, concepts?.length || 1, 5),
      }))

      // Convert synapse map to array
      const synapses: Synapse[] = []
      const conceptIdToName = new Map(concepts?.map((c) => [c.id, c.name]) || [])

      synapseMap.forEach((data, key) => {
        const [fromId, toId] = key.split('-')
        // Only include synapses where both concepts exist in our neuron list
        if (conceptMap.has(fromId) && conceptMap.has(toId)) {
          synapses.push({
            id: key,
            fromId,
            toId,
            fromConcept: conceptIdToName.get(fromId) || '',
            toConcept: conceptIdToName.get(toId) || '',
            strength: Math.min(data.totalRelevance / (data.count * 2), 1),
            coOccurrenceCount: data.count,
          })
        }
      })

      setBrainData({ neurons, synapses })
    } catch (err) {
      console.error('Error fetching brain data:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch brain data')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBrainData()
  }, [fetchBrainData])

  return { brainData, isLoading, error, refetch: fetchBrainData, CATEGORY_COLORS }
}
