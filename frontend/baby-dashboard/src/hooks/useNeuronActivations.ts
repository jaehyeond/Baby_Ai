'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useSSESubscription } from './useSSESubscription'
import type { SSEEvent, SSENeuronActivationItem } from './useSSESubscription'

interface NeuronActivation {
  concept_id: string | null
  brain_region_id: string | null
  intensity: number
  trigger_type: string
  created_at?: string
}

export interface RegionHeatmap {
  brain_region_id: string
  activation_count: number
  avg_intensity: number
}

// v22: Conversation context that caused activations
export interface ActivationContext {
  experienceId: string
  userMessage: string
  aiResponse: string
  emotion: string
  timestamp: string
}

// v23: Thought process step
export interface ThoughtStep {
  conceptName: string
  conceptCategory: string
  regionName: string
  triggerType: 'conversation' | 'spreading_activation'
  intensity: number
  timestamp: string
}

export function useNeuronActivations() {
  const [activeRegions, setActiveRegions] = useState<Map<string, number>>(new Map())
  const [activeNeurons, setActiveNeurons] = useState<Map<string, number>>(new Map())
  const [spreadingRegions, setSpreadingRegions] = useState<Map<string, number>>(new Map())
  const [waveCount, setWaveCount] = useState(0)
  const [heatmapRegions, setHeatmapRegions] = useState<Map<string, number>>(new Map())
  const [isReplaying, setIsReplaying] = useState(false)
  const [activationContext, setActivationContext] = useState<ActivationContext | null>(null)
  const [thoughtProcess, setThoughtProcess] = useState<ThoughtStep[]>([])
  const timeoutsRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())
  const replayTimeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([])

  const addActivation = useCallback((activation: NeuronActivation) => {
    const { concept_id, brain_region_id, intensity, trigger_type } = activation
    const isSpreading = trigger_type === 'spreading_activation'
    const decayMs = isSpreading ? 5000 : 3000

    if (brain_region_id) {
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

    if (concept_id) {
      setActiveNeurons(prev => {
        const next = new Map(prev)
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

    if (isSpreading) {
      setWaveCount(prev => prev + 1)
    }
  }, [])

  // 초기 heatmap + replay 로드 (FastAPI)
  useEffect(() => {
    async function loadActivationSummary() {
      try {
        const fastapiUrl = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000'
        const res = await fetch(`${fastapiUrl}/api/brain/activation-summary`)
        if (!res.ok) {
          console.error('[useNeuronActivations] activation-summary error:', res.status)
          return
        }
        const data = await res.json() as {
          heatmap: Array<{
            concept_id: string
            brain_region_id: string | null
            activation_count: number
            avg_intensity: number
          }>
          replay: Array<NeuronActivation>
        }

        // heatmap: brain_region_id 기준 집계 → 0~1 정규화
        const regionCounts = new Map<string, number>()
        for (const h of data.heatmap) {
          if (h.brain_region_id) {
            regionCounts.set(
              h.brain_region_id,
              (regionCounts.get(h.brain_region_id) || 0) + h.activation_count
            )
          }
        }
        if (regionCounts.size > 0) {
          const maxCount = Math.max(...regionCounts.values())
          const heatmap = new Map<string, number>()
          for (const [rid, count] of regionCounts) {
            heatmap.set(rid, maxCount > 0 ? count / maxCount : 0)
          }
          setHeatmapRegions(heatmap)
        }

        // replay: 최근 활성화 순차 재생
        if (data.replay.length > 0) {
          setIsReplaying(true)
          const totalDuration = 3000
          const interval = Math.max(15, totalDuration / data.replay.length)

          data.replay.forEach((activation, i) => {
            const t = setTimeout(() => {
              addActivation(activation)
              if (i === data.replay.length - 1) setIsReplaying(false)
            }, i * interval)
            replayTimeoutsRef.current.push(t)
          })
        }
      } catch (err) {
        console.error('[useNeuronActivations] loadActivationSummary error:', err)
      }
    }

    loadActivationSummary()

    return () => {
      replayTimeoutsRef.current.forEach(t => clearTimeout(t))
      replayTimeoutsRef.current = []
    }
  }, [addActivation])

  // SSE 실시간 구독 (Supabase Realtime 대체)
  const sseHandler = useCallback((event: SSEEvent) => {
    if (event.type !== 'neuron_activation') return
    const activations = event.data as SSENeuronActivationItem[]
    for (const activation of activations) {
      addActivation(activation)
    }
  }, [addActivation])

  useSSESubscription(sseHandler)

  // 클린업
  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach(t => clearTimeout(t))
      timeoutsRef.current.clear()
    }
  }, [])

  return {
    activeRegions,
    activeNeurons,
    spreadingRegions,
    waveCount,
    heatmapRegions,
    isReplaying,
    activationContext,
    thoughtProcess,
  }
}
