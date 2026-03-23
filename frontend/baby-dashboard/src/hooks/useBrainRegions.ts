'use client'

import { useState, useEffect, useMemo } from 'react'

export interface BrainRegion {
  id: string
  name: string
  display_name: string
  display_name_en: string
  color: string
  theta_min: number
  theta_max: number
  phi_min: number
  phi_max: number
  radius_min: number
  radius_max: number
  development_stage_min: number
  is_internal: boolean
  description: string | null
}

// Development stage growth parameters (0-based, matches Python DevelopmentStage enum)
// Synapse density peaks at TODDLER then decreases (synaptic pruning)
const STAGE_PARAMS: Record<number, { scale: number; synapseDensity: number; label: string }> = {
  0: { scale: 0.25, synapseDensity: 0.3, label: 'NEWBORN' },
  1: { scale: 0.48, synapseDensity: 0.6, label: 'INFANT' },
  2: { scale: 0.65, synapseDensity: 0.85, label: 'BABY' },
  3: { scale: 0.80, synapseDensity: 1.0, label: 'TODDLER' },
  4: { scale: 0.90, synapseDensity: 0.7, label: 'CHILD' },
  5: { scale: 0.95, synapseDensity: 0.55, label: 'TEEN' },
  6: { scale: 0.98, synapseDensity: 0.45, label: 'YOUNG_ADULT' },
  7: { scale: 1.00, synapseDensity: 0.40, label: 'MATURE' },
}

// Fallback for any stage beyond defined range
const MAX_DEFINED_STAGE = 7

export function useBrainRegions(developmentStage: number) {
  const [regions, setRegions] = useState<BrainRegion[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchRegions() {
      try {
        const fastapiUrl = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000'
        const res = await fetch(`${fastapiUrl}/api/brain/regions`)
        if (!res.ok) {
          console.error('[useBrainRegions] FastAPI error:', res.status)
          return
        }
        const json = await res.json() as { regions: BrainRegion[] }
        // development_stage_min 오름차순 정렬 (Supabase order 대체)
        const sorted = [...(json.regions || [])].sort(
          (a, b) => a.development_stage_min - b.development_stage_min
        )
        setRegions(sorted)
      } catch (err) {
        console.error('[useBrainRegions] Error:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchRegions()
  }, [])

  const stageParams = useMemo(() => {
    return STAGE_PARAMS[developmentStage] || STAGE_PARAMS[Math.min(developmentStage, MAX_DEFINED_STAGE)] || STAGE_PARAMS[MAX_DEFINED_STAGE]
  }, [developmentStage])

  const availableRegions = useMemo(() => {
    return regions.filter(r => developmentStage >= r.development_stage_min)
  }, [regions, developmentStage])

  const unavailableRegions = useMemo(() => {
    return regions.filter(r => developmentStage < r.development_stage_min)
  }, [regions, developmentStage])

  return {
    regions,
    availableRegions,
    unavailableRegions,
    stageParams,
    loading,
  }
}
