'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { supabase } from '@/lib/supabase'

interface NeuronActivation {
  concept_id: string
  brain_region_id: string
  intensity: number
  trigger_type: string
  created_at: string
}

export interface RegionHeatmap {
  brain_region_id: string
  activation_count: number
  avg_intensity: number
}

export function useNeuronActivations() {
  const [activeRegions, setActiveRegions] = useState<Map<string, number>>(new Map())
  const [activeNeurons, setActiveNeurons] = useState<Map<string, number>>(new Map())
  // v21: Track spreading activations separately for ripple visual effect
  const [spreadingRegions, setSpreadingRegions] = useState<Map<string, number>>(new Map())
  const [waveCount, setWaveCount] = useState(0)
  // A+C: Cumulative heatmap (persistent base glow)
  const [heatmapRegions, setHeatmapRegions] = useState<Map<string, number>>(new Map())
  const [isReplaying, setIsReplaying] = useState(false)
  const timeoutsRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())
  const replayTimeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([])

  const addActivation = useCallback((activation: NeuronActivation) => {
    const { concept_id, brain_region_id, intensity, trigger_type } = activation
    const isSpreading = trigger_type === 'spreading_activation'
    // Spreading activations decay slower (5s) for visible wave effect, direct activations 3s
    const decayMs = isSpreading ? 5000 : 3000

    // Activate region
    if (brain_region_id) {
      // For spreading activations, add to separate spreading map for ripple effect
      if (isSpreading) {
        setSpreadingRegions(prev => {
          const next = new Map(prev)
          const current = next.get(brain_region_id) || 0
          next.set(brain_region_id, Math.min(1.0, Math.max(current, intensity)))
          return next
        })

        const spreadKey = `spread_${brain_region_id}`
        const existingTimeout = timeoutsRef.current.get(spreadKey)
        if (existingTimeout) clearTimeout(existingTimeout)

        const timeout = setTimeout(() => {
          setSpreadingRegions(prev => {
            const next = new Map(prev)
            next.delete(brain_region_id)
            return next
          })
          timeoutsRef.current.delete(spreadKey)
        }, decayMs)
        timeoutsRef.current.set(spreadKey, timeout)
      }

      // Always update main active regions (combined intensity)
      setActiveRegions(prev => {
        const next = new Map(prev)
        const current = next.get(brain_region_id) || 0
        next.set(brain_region_id, Math.min(1.0, current + intensity))
        return next
      })

      const regionKey = `region_${brain_region_id}`
      const existingTimeout = timeoutsRef.current.get(regionKey)
      if (existingTimeout) clearTimeout(existingTimeout)

      const timeout = setTimeout(() => {
        setActiveRegions(prev => {
          const next = new Map(prev)
          next.delete(brain_region_id)
          return next
        })
        timeoutsRef.current.delete(regionKey)
      }, decayMs)
      timeoutsRef.current.set(regionKey, timeout)
    }

    // Activate neuron
    if (concept_id) {
      setActiveNeurons(prev => {
        const next = new Map(prev)
        // For spreading, use the propagated (lower) intensity
        const current = next.get(concept_id) || 0
        next.set(concept_id, Math.max(current, intensity))
        return next
      })

      const neuronKey = `neuron_${concept_id}`
      const existingTimeout = timeoutsRef.current.get(neuronKey)
      if (existingTimeout) clearTimeout(existingTimeout)

      const timeout = setTimeout(() => {
        setActiveNeurons(prev => {
          const next = new Map(prev)
          next.delete(concept_id)
          return next
        })
        timeoutsRef.current.delete(neuronKey)
      }, decayMs)
      timeoutsRef.current.set(neuronKey, timeout)
    }

    // v21: Track wave events
    if (isSpreading) {
      setWaveCount(prev => prev + 1)
    }
  }, [])

  // A+C: Load activation summary on mount (replay + heatmap)
  useEffect(() => {
    async function loadActivationSummary() {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await (supabase as any).rpc('get_brain_activation_summary')

      if (error || !data) {
        if (error) console.error('[useNeuronActivations] RPC error:', error)
        return
      }

      // 1. Heatmap: normalize activation counts to 0-1 range
      const heatmapRaw = data.heatmap as RegionHeatmap[]
      if (heatmapRaw.length > 0) {
        const maxCount = Math.max(...heatmapRaw.map((h: RegionHeatmap) => h.activation_count))
        const heatmap = new Map<string, number>()
        for (const h of heatmapRaw) {
          heatmap.set(h.brain_region_id, maxCount > 0 ? h.activation_count / maxCount : 0)
        }
        setHeatmapRegions(heatmap)
      }

      // 2. Replay: stagger activations over 3 seconds
      const replay = data.replay as NeuronActivation[]
      if (replay.length > 0) {
        setIsReplaying(true)
        const totalDuration = 3000
        const interval = Math.max(15, totalDuration / replay.length)

        replay.forEach((activation: NeuronActivation, i: number) => {
          const t = setTimeout(() => {
            addActivation(activation)
            if (i === replay.length - 1) {
              setIsReplaying(false)
            }
          }, i * interval)
          replayTimeoutsRef.current.push(t)
        })
      }
    }

    loadActivationSummary()

    return () => {
      replayTimeoutsRef.current.forEach(t => clearTimeout(t))
      replayTimeoutsRef.current = []
    }
  }, [addActivation])

  // Realtime subscription
  useEffect(() => {
    const channel = supabase
      .channel('brain-activity')
      .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'neuron_activations',
      }, (payload) => {
        addActivation(payload.new as NeuronActivation)
      })
      .subscribe()

    return () => {
      channel.unsubscribe()
      timeoutsRef.current.forEach(t => clearTimeout(t))
      timeoutsRef.current.clear()
    }
  }, [addActivation])

  return {
    activeRegions,
    activeNeurons,
    // v21: Spreading wave visualization
    spreadingRegions,
    waveCount,
    // A+C: Persistent data
    heatmapRegions,  // Normalized 0-1 per region (cumulative activation history)
    isReplaying,     // True during initial replay animation
  }
}
