'use client'

import { useState, useEffect, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import type { NeuronNode, Synapse, BrainData, Astrocyte, BrainDataWithAstrocytes } from '@/lib/database.types'

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

// Type for direct concept relations (synapses stored in concept_relations table)
interface RawConceptRelation {
  id: string
  from_concept_id: string
  to_concept_id: string
  relation_type: string
  strength: number
  evidence_count: number
}

// Category colors for neurons (Temperature-based: frozen=cold, active=warm)
const CATEGORY_COLORS: Record<string, string> = {
  // Frozen knowledge - cold gray/blue (LLM already knows)
  frozen_knowledge: '#64748b',  // slate-500

  // Learned concepts - warm magenta/purple (Baby learned)
  learned: '#d946ef',           // fuchsia-500

  // Emotions - hot colors (feelings are warm)
  감정: '#f97316',              // orange-500
  emotion: '#f97316',

  // People/Relations - teal (relationships)
  person: '#14b8a6',            // teal-500
  관계: '#06b6d4',              // cyan-500
  사람: '#14b8a6',
  인물: '#14b8a6',

  // Abstract concepts - blue (thinking)
  '추상적 개념': '#3b82f6',     // blue-500
  'abstract concept': '#3b82f6',
  인지: '#60a5fa',              // blue-400

  // Actions/Behaviors - green (doing)
  행위: '#22c55e',              // green-500
  action: '#22c55e',
  활동: '#22c55e',
  행동: '#22c55e',

  // Identity - gold (special, core)
  identity: '#fbbf24',          // amber-400
  이름: '#fbbf24',

  // Objects/Things - purple
  사물: '#a855f7',              // violet-500
  thing: '#a855f7',
  물체: '#a855f7',

  // Locations - emerald
  장소: '#10b981',              // emerald-500
  location: '#10b981',
  지리: '#10b981',

  // Communication - pink
  communication: '#ec4899',     // pink-500
  인사말: '#ec4899',

  // Default fallback
  default: '#6366f1',           // indigo-500
}

// Generate 3D position using fibonacci sphere for even distribution
function fibonacciSphere(index: number, total: number, radius: number): [number, number, number] {
  if (total <= 0) return [0, 0, 0]
  const goldenRatio = (1 + Math.sqrt(5)) / 2
  const theta = 2 * Math.PI * index / goldenRatio
  const phi = Math.acos(1 - 2 * (index + 0.5) / total)

  const x = radius * Math.sin(phi) * Math.cos(theta)
  const y = radius * Math.sin(phi) * Math.sin(theta)
  const z = radius * Math.cos(phi)

  return [x, y, z]
}

// Simplified Louvain-style clustering algorithm (no external dependencies)
function clusterNeurons(
  neurons: NeuronNode[],
  synapses: Synapse[]
): { clusters: Map<string, string>; clusterMembers: Map<string, string[]> } {
  // Build adjacency map with weights
  const adjacency = new Map<string, Map<string, number>>()

  neurons.forEach(n => {
    adjacency.set(n.id, new Map())
  })

  synapses.forEach(s => {
    if (adjacency.has(s.fromId) && adjacency.has(s.toId)) {
      adjacency.get(s.fromId)!.set(s.toId, s.strength)
      adjacency.get(s.toId)!.set(s.fromId, s.strength)
    }
  })

  // Initialize: each neuron is its own cluster
  const clusters = new Map<string, string>()
  neurons.forEach(n => clusters.set(n.id, n.id))

  // Iteratively optimize (simplified Louvain)
  let changed = true
  let iterations = 0
  const maxIterations = 10 // Prevent infinite loops

  while (changed && iterations < maxIterations) {
    changed = false
    iterations++

    for (const neuron of neurons) {
      const currentCluster = clusters.get(neuron.id)!
      const neighbors = adjacency.get(neuron.id) || new Map()

      if (neighbors.size === 0) continue

      // Calculate strength to each neighboring cluster
      const clusterStrengths = new Map<string, number>()
      for (const [neighborId, strength] of neighbors) {
        const neighborCluster = clusters.get(neighborId)!
        clusterStrengths.set(
          neighborCluster,
          (clusterStrengths.get(neighborCluster) || 0) + strength
        )
      }

      // Also consider staying in current cluster
      if (!clusterStrengths.has(currentCluster)) {
        clusterStrengths.set(currentCluster, 0)
      }

      // Find best cluster (highest total strength)
      let bestCluster = currentCluster
      let bestStrength = clusterStrengths.get(currentCluster) || 0

      for (const [cluster, strength] of clusterStrengths) {
        if (strength > bestStrength) {
          bestStrength = strength
          bestCluster = cluster
        }
      }

      if (bestCluster !== currentCluster) {
        clusters.set(neuron.id, bestCluster)
        changed = true
      }
    }
  }

  // Build cluster members map
  const clusterMembers = new Map<string, string[]>()
  for (const [neuronId, clusterId] of clusters) {
    if (!clusterMembers.has(clusterId)) {
      clusterMembers.set(clusterId, [])
    }
    clusterMembers.get(clusterId)!.push(neuronId)
  }

  console.log('[useBrainData] Clustering completed:', clusterMembers.size, 'clusters after', iterations, 'iterations')

  return { clusters, clusterMembers }
}

// Create Astrocyte meta-nodes from clusters
function createAstrocytes(
  neurons: NeuronNode[],
  synapses: Synapse[],
  clusterMembers: Map<string, string[]>
): { astrocytes: Astrocyte[]; neuronToAstrocyte: Record<string, string> } {
  const neuronMap = new Map(neurons.map(n => [n.id, n]))
  const astrocytes: Astrocyte[] = []
  const neuronToAstrocyte: Record<string, string> = {}

  let astrocyteIndex = 0

  for (const [clusterId, memberIds] of clusterMembers) {
    // Skip very small clusters (merge into "misc")
    if (memberIds.length < 2) continue

    const members = memberIds.map(id => neuronMap.get(id)!).filter(Boolean)
    if (members.length === 0) continue

    // Calculate dominant category
    const categoryCounts = new Map<string, number>()
    members.forEach(m => {
      categoryCounts.set(m.category, (categoryCounts.get(m.category) || 0) + 1)
    })

    let dominantCategory = 'default'
    let maxCount = 0
    for (const [cat, count] of categoryCounts) {
      if (count > maxCount) {
        maxCount = count
        dominantCategory = cat
      }
    }

    // Calculate average strength of intra-cluster synapses
    const memberSet = new Set(memberIds)
    let totalStrength = 0
    let synapseCount = 0
    synapses.forEach(s => {
      if (memberSet.has(s.fromId) && memberSet.has(s.toId)) {
        totalStrength += s.strength
        synapseCount++
      }
    })
    const avgStrength = synapseCount > 0 ? totalStrength / synapseCount : 0.5

    // Create astrocyte
    const astrocyteId = `astrocyte-${astrocyteIndex}`
    const astrocyte: Astrocyte = {
      id: astrocyteId,
      name: `${dominantCategory} 클러스터`,
      color: CATEGORY_COLORS[dominantCategory] || CATEGORY_COLORS.default,
      position: fibonacciSphere(astrocyteIndex, clusterMembers.size, 6),
      neuronIds: memberIds,
      strength: avgStrength,
      size: Math.min(0.5 + members.length * 0.1, 2), // Size based on member count
    }

    astrocytes.push(astrocyte)

    // Map neurons to this astrocyte
    memberIds.forEach(id => {
      neuronToAstrocyte[id] = astrocyteId
    })

    astrocyteIndex++
  }

  console.log('[useBrainData] Created', astrocytes.length, 'astrocytes')

  return { astrocytes, neuronToAstrocyte }
}

// Position neurons around their astrocyte
function positionNeuronsWithAstrocytes(
  neurons: NeuronNode[],
  astrocytes: Astrocyte[],
  neuronToAstrocyte: Record<string, string>
): void {
  const astrocyteMap = new Map(astrocytes.map(a => [a.id, a]))

  // Neurons without astrocyte get placed in center
  const orphanNeurons: NeuronNode[] = []

  neurons.forEach(neuron => {
    const astrocyteId = neuronToAstrocyte[neuron.id]
    const astrocyte = astrocyteId ? astrocyteMap.get(astrocyteId) : null

    if (astrocyte) {
      // Find position within cluster
      const memberIndex = astrocyte.neuronIds.indexOf(neuron.id)
      const localRadius = 1 + astrocyte.neuronIds.length * 0.05 // Radius scales with cluster size
      const localPos = fibonacciSphere(memberIndex, astrocyte.neuronIds.length, localRadius)

      // Position around astrocyte center
      neuron.position = [
        astrocyte.position[0] + localPos[0],
        astrocyte.position[1] + localPos[1],
        astrocyte.position[2] + localPos[2],
      ]
    } else {
      orphanNeurons.push(neuron)
    }
  })

  // Position orphan neurons at center
  orphanNeurons.forEach((neuron, index) => {
    neuron.position = fibonacciSphere(index, orphanNeurons.length, 2)
  })
}

export function useBrainData() {
  const [brainData, setBrainData] = useState<BrainDataWithAstrocytes | null>(null)
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
        .limit(500) as { data: RawConcept[] | null; error: Error | null }

      if (conceptsError) throw conceptsError

      // Fetch direct concept relations (synapses from concept_relations table)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data: conceptRelations, error: crError } = await (supabase as any)
        .from('concept_relations')
        .select('id, from_concept_id, to_concept_id, relation_type, strength, evidence_count')
        .order('evidence_count', { ascending: false })
        .limit(500) as { data: RawConceptRelation[] | null; error: Error | null }

      if (crError) {
        console.warn('Failed to fetch concept_relations:', crError)
      }

      // DEBUG: Log fetched data
      console.log('[useBrainData] concepts:', concepts?.length, 'conceptRelations:', conceptRelations?.length, 'crError:', crError)

      // DEBUG: Log first 3 concept IDs and first 3 relation IDs
      if (concepts && concepts.length > 0) {
        console.log('[useBrainData] First 3 concept IDs:', concepts.slice(0, 3).map(c => c.id))
      }
      if (conceptRelations && conceptRelations.length > 0) {
        console.log('[useBrainData] First 3 relation pairs:', conceptRelations.slice(0, 3).map(cr => `${cr.from_concept_id} -> ${cr.to_concept_id}`))
      }

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

      // Build synapse map from direct concept_relations first
      const synapseMap = new Map<string, { count: number; totalRelevance: number; relationType?: string }>()

      // Add synapses from concept_relations table (direct relations)
      conceptRelations?.forEach((cr) => {
        const [id1, id2] = [cr.from_concept_id, cr.to_concept_id].sort()
        const key = `${id1}|${id2}`
        const existing = synapseMap.get(key)
        if (existing) {
          // Merge with existing
          synapseMap.set(key, {
            count: existing.count + cr.evidence_count,
            totalRelevance: existing.totalRelevance + cr.strength * cr.evidence_count,
            relationType: cr.relation_type,
          })
        } else {
          synapseMap.set(key, {
            count: cr.evidence_count,
            totalRelevance: cr.strength * cr.evidence_count,
            relationType: cr.relation_type,
          })
        }
      })

      // Group by experience to find co-occurrences
      const experienceGroups = new Map<string, { conceptId: string; relevance: number }[]>()
      experienceConcepts?.forEach((ec) => {
        const group = experienceGroups.get(ec.experience_id) || []
        group.push({ conceptId: ec.concept_id, relevance: ec.relevance || 0.5 })
        experienceGroups.set(ec.experience_id, group)
      })

      // Add synapses from experience co-occurrences (indirect relations)
      experienceGroups.forEach((group) => {
        for (let i = 0; i < group.length; i++) {
          for (let j = i + 1; j < group.length; j++) {
            const [id1, id2] = [group[i].conceptId, group[j].conceptId].sort()
            const key = `${id1}|${id2}`
            const existing = synapseMap.get(key) || { count: 0, totalRelevance: 0 }
            synapseMap.set(key, {
              count: existing.count + 1,
              totalRelevance: existing.totalRelevance + group[i].relevance + group[j].relevance,
              relationType: existing.relationType,
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

      // DEBUG: Check first few synapseMap keys against conceptMap
      let debugCount = 0
      synapseMap.forEach((data, key) => {
        const [fromId, toId] = key.split('|')
        if (debugCount < 3) {
          console.log('[useBrainData] synapse key:', key, 'fromId:', fromId, 'toId:', toId,
            'fromInMap:', conceptMap.has(fromId), 'toInMap:', conceptMap.has(toId))
          debugCount++
        }
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

      // DEBUG: Log final counts
      console.log('[useBrainData] Final: neurons:', neurons.length, 'synapses:', synapses.length, 'synapseMap size:', synapseMap.size)

      // Perform clustering to create astrocytes
      const { clusterMembers } = clusterNeurons(neurons, synapses)
      const { astrocytes, neuronToAstrocyte } = createAstrocytes(neurons, synapses, clusterMembers)

      // Reposition neurons around their astrocytes
      positionNeuronsWithAstrocytes(neurons, astrocytes, neuronToAstrocyte)

      console.log('[useBrainData] Astrocytes:', astrocytes.length, 'clusters created')

      setBrainData({ neurons, synapses, astrocytes, neuronToAstrocyte })
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
