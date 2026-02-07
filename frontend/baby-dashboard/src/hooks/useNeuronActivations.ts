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

export function useNeuronActivations() {
  const [activeRegions, setActiveRegions] = useState<Map<string, number>>(new Map())
  const [activeNeurons, setActiveNeurons] = useState<Map<string, number>>(new Map())
  const timeoutsRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  const addActivation = useCallback((activation: NeuronActivation) => {
    const { concept_id, brain_region_id, intensity } = activation
    const decayMs = 3000 // Activation visible for 3 seconds

    // Activate region
    if (brain_region_id) {
      setActiveRegions(prev => {
        const next = new Map(prev)
        const current = next.get(brain_region_id) || 0
        next.set(brain_region_id, Math.min(1.0, current + intensity))
        return next
      })

      // Clear existing timeout for this region
      const regionKey = `region_${brain_region_id}`
      const existingTimeout = timeoutsRef.current.get(regionKey)
      if (existingTimeout) clearTimeout(existingTimeout)

      // Schedule deactivation
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
        next.set(concept_id, intensity)
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
  }, [])

  useEffect(() => {
    // Subscribe to realtime neuron activations
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
      // Clear all timeouts
      timeoutsRef.current.forEach(t => clearTimeout(t))
      timeoutsRef.current.clear()
    }
  }, [addActivation])

  return { activeRegions, activeNeurons }
}
