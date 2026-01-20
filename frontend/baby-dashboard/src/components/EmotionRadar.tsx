'use client'

import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { Heart, Zap, Eye, Frown, Meh, AlertTriangle } from 'lucide-react'
import type { BabyState } from '@/lib/database.types'
import { EmotionParticles, AmbientParticles, useEmotionParticles } from './EmotionParticles'

// 감정별 색상 및 아이콘
const EMOTION_CONFIG: Record<string, { color: string; icon: typeof Heart; label: string }> = {
  curiosity: { color: '#8b5cf6', icon: Eye, label: '호기심' },
  joy: { color: '#10b981', icon: Heart, label: '기쁨' },
  fear: { color: '#ef4444', icon: AlertTriangle, label: '두려움' },
  surprise: { color: '#f59e0b', icon: Zap, label: '놀람' },
  frustration: { color: '#f97316', icon: Frown, label: '좌절' },
  boredom: { color: '#6b7280', icon: Meh, label: '지루함' },
}

interface EmotionRadarProps {
  state: BabyState | null
  isLoading?: boolean
}

export function EmotionRadar({ state, isLoading }: EmotionRadarProps) {
  const { currentEmotion, emotionIntensity, particleTrigger, onEmotionChange } = useEmotionParticles()
  const prevDominantRef = useRef<string | null>(null)

  // 감정 변화 감지 및 파티클 트리거
  useEffect(() => {
    if (state?.dominant_emotion && state.dominant_emotion !== prevDominantRef.current) {
      const intensity = state[state.dominant_emotion as keyof BabyState] as number ?? 0.5
      onEmotionChange(state.dominant_emotion, intensity)
      prevDominantRef.current = state.dominant_emotion
    }
  }, [state?.dominant_emotion, state, onEmotionChange])

  if (isLoading || !state) {
    return (
      <div className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50 animate-pulse">
        <div className="h-8 bg-slate-700 rounded w-1/3 mb-4" />
        <div className="h-64 bg-slate-700 rounded" />
      </div>
    )
  }

  const emotionData = [
    { emotion: '호기심', value: (state.curiosity ?? 0) * 100, fullMark: 100 },
    { emotion: '기쁨', value: (state.joy ?? 0) * 100, fullMark: 100 },
    { emotion: '두려움', value: (state.fear ?? 0) * 100, fullMark: 100 },
    { emotion: '놀람', value: (state.surprise ?? 0) * 100, fullMark: 100 },
    { emotion: '좌절', value: (state.frustration ?? 0) * 100, fullMark: 100 },
    { emotion: '지루함', value: (state.boredom ?? 0) * 100, fullMark: 100 },
  ]

  const dominantConfig = state.dominant_emotion
    ? EMOTION_CONFIG[state.dominant_emotion]
    : EMOTION_CONFIG.curiosity
  const DominantIcon = dominantConfig?.icon ?? Eye

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-6 border border-slate-700/50 backdrop-blur-sm relative overflow-hidden"
    >
      {/* Particle Effects */}
      <EmotionParticles
        emotion={currentEmotion}
        intensity={emotionIntensity}
        trigger={particleTrigger}
      />
      <AmbientParticles
        emotion={state.dominant_emotion}
        intensity={(state[state.dominant_emotion as keyof BabyState] as number ?? 0.3) * 0.5}
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ backgroundColor: `${dominantConfig?.color ?? '#8b5cf6'}20` }}
          >
            <DominantIcon
              className="w-5 h-5"
              style={{ color: dominantConfig?.color ?? '#8b5cf6' }}
            />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-100">감정 상태</h2>
            <p className="text-sm text-slate-400">
              현재:{' '}
              <span style={{ color: dominantConfig?.color }}>
                {dominantConfig?.label ?? state.dominant_emotion}
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* Radar Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={emotionData} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
            <PolarGrid stroke="#334155" />
            <PolarAngleAxis
              dataKey="emotion"
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              stroke="#334155"
            />
            <PolarRadiusAxis
              angle={30}
              domain={[0, 100]}
              tick={{ fill: '#64748b', fontSize: 10 }}
              stroke="#334155"
              tickCount={5}
            />
            <Radar
              name="감정"
              dataKey="value"
              stroke="#8b5cf6"
              fill="#8b5cf6"
              fillOpacity={0.3}
              strokeWidth={2}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#f1f5f9' }}
              formatter={(value) => value !== undefined ? [`${Number(value).toFixed(1)}%`, '강도'] : ['', '']}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Emotion Bars */}
      <div className="mt-4 space-y-2">
        {Object.entries(EMOTION_CONFIG).map(([key, config]) => {
          const value = (state[key as keyof BabyState] as number ?? 0) * 100
          return (
            <div key={key} className="flex items-center gap-2">
              <config.icon className="w-4 h-4" style={{ color: config.color }} />
              <span className="text-xs text-slate-400 w-12">{config.label}</span>
              <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: config.color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${value}%` }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                />
              </div>
              <span className="text-xs text-slate-500 w-10 text-right">{value.toFixed(0)}%</span>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}
