'use client'

import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Cell,
  ReferenceLine,
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

// 복합 감정 설정
const COMPOUND_EMOTION_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  pride: { label: '자부심', color: '#fbbf24', icon: '🏆' },
  anxiety: { label: '불안', color: '#ef4444', icon: '😰' },
  wonder: { label: '경이', color: '#a78bfa', icon: '✨' },
  melancholy: { label: '우울', color: '#6b7280', icon: '🌧️' },
  determination: { label: '결의', color: '#f97316', icon: '💪' },
}

// 목표 타입 설정
const GOAL_TYPE_CONFIG: Record<string, { label: string; icon: string; description: string }> = {
  skill_deepening: { label: '기술 심화', icon: '🎯', description: '배운 것을 더 깊이 연습하고 싶어요' },
  safety_seeking: { label: '안전 추구', icon: '🛡️', description: '안전한 환경에서 천천히 배우고 싶어요' },
  exploration: { label: '탐험', icon: '🔭', description: '새로운 것을 발견하고 싶어요' },
  social_connection: { label: '사회적 연결', icon: '🤝', description: '누군가와 함께하고 싶어요' },
  challenge_seeking: { label: '도전 추구', icon: '⚡', description: '어려운 것에 도전하고 싶어요' },
  novelty_seeking: { label: '새로움 추구', icon: '✨', description: '지금과 다른 새로운 것을 해보고 싶어요' },
}

// 감정→목표 매핑
const EMOTION_GOAL_MAP: Record<string, string> = {
  pride: 'skill_deepening',
  anxiety: 'safety_seeking',
  wonder: 'exploration',
  melancholy: 'social_connection',
  determination: 'challenge_seeking',
  curiosity: 'exploration',
  joy: 'skill_deepening',
  fear: 'safety_seeking',
  surprise: 'exploration',
  frustration: 'challenge_seeking',
  boredom: 'novelty_seeking',
}

interface EmotionRadarProps {
  state: BabyState | null
  isLoading?: boolean
}

export function EmotionRadar({ state, isLoading }: EmotionRadarProps) {
  const { currentEmotion, emotionIntensity, particleTrigger, onEmotionChange } = useEmotionParticles()
  const prevDominantRef = useRef<string | null>(null)
  const [activeTab, setActiveTab] = useState<'radar' | 'va'>('radar')

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

  // Valence-Arousal 계산
  const valence = state ? ((state.curiosity ?? 0) + (state.joy ?? 0)) / 2 - ((state.fear ?? 0) + (state.frustration ?? 0)) / 2 : 0
  const arousal = state ? ((state.curiosity ?? 0) + (state.surprise ?? 0) + (state.fear ?? 0)) / 3 - (state.boredom ?? 0) * 0.5 : 0

  // 복합 감정 감지
  const detectCompoundEmotion = (): string | null => {
    if (!state) return null
    const s = {
      joy: state.joy ?? 0, fear: state.fear ?? 0, curiosity: state.curiosity ?? 0,
      surprise: state.surprise ?? 0, frustration: state.frustration ?? 0, boredom: state.boredom ?? 0,
    }
    if (s.joy > 0.6 && s.fear < 0.3) return 'pride'
    if (s.fear > 0.4 && s.frustration > 0.4) return 'anxiety'
    if (s.curiosity > 0.5 && s.surprise > 0.4) return 'wonder'
    if (s.boredom > 0.5 && s.frustration > 0.3) return 'melancholy'
    if (s.frustration > 0.4 && s.curiosity > 0.5 && s.fear < 0.4) return 'determination'
    return null
  }
  const compoundEmotion = detectCompoundEmotion()

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
        {compoundEmotion && COMPOUND_EMOTION_CONFIG[compoundEmotion] && (
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
            style={{
              backgroundColor: `${COMPOUND_EMOTION_CONFIG[compoundEmotion].color}20`,
              color: COMPOUND_EMOTION_CONFIG[compoundEmotion].color
            }}
          >
            <span>{COMPOUND_EMOTION_CONFIG[compoundEmotion].icon}</span>
            <span>{COMPOUND_EMOTION_CONFIG[compoundEmotion].label}</span>
          </motion.div>
        )}
      </div>

      {/* Tab Buttons */}
      <div className="flex gap-1 mb-3">
        {(['radar', 'va'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === tab
                ? 'bg-violet-500/20 text-violet-300'
                : 'text-slate-400 hover:text-slate-300 hover:bg-slate-700/50'
            }`}
          >
            {tab === 'radar' ? '감정 레이더' : '감정 지도'}
          </button>
        ))}
      </div>

      {/* Radar Chart */}
      {activeTab === 'radar' && (
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
      )}

      {/* Valence-Arousal Plot */}
      {activeTab === 'va' && (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="valence"
                domain={[-1, 1]}
                name="감정가"
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                stroke="#334155"
                label={{ value: '감정가 (부정 ← → 긍정)', position: 'bottom', fill: '#64748b', fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="arousal"
                domain={[-0.5, 1]}
                name="각성"
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                stroke="#334155"
                label={{ value: '각성도', angle: -90, position: 'left', fill: '#64748b', fontSize: 11 }}
              />
              <ReferenceLine x={0} stroke="#475569" strokeDasharray="3 3" />
              <ReferenceLine y={0.25} stroke="#475569" strokeDasharray="3 3" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                }}
                formatter={(value) => value !== undefined ? [Number(value).toFixed(3), ''] : ['', '']}
              />
              <Scatter
                name="현재 감정"
                data={[{ valence, arousal, label: compoundEmotion || (state?.dominant_emotion ?? 'neutral') }]}
                fill="#8b5cf6"
              >
                <Cell fill={compoundEmotion ? (COMPOUND_EMOTION_CONFIG[compoundEmotion]?.color ?? '#8b5cf6') : '#8b5cf6'} />
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
          {/* VA 영역 레이블 */}
          <div className="flex justify-between text-[10px] text-slate-500 mt-1 px-4">
            <span>😰 불안/스트레스</span>
            <span>🔥 흥분/열정</span>
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 px-4">
            <span>😴 무기력</span>
            <span>😌 평온/만족</span>
          </div>
        </div>
      )}

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

      {/* v19: Emotion → Goal Suggestion */}
      {(() => {
        const emotionKey = compoundEmotion || state.dominant_emotion
        const goalType = emotionKey ? EMOTION_GOAL_MAP[emotionKey] : null
        const goalConfig = goalType ? GOAL_TYPE_CONFIG[goalType] : null
        if (!goalConfig) return null
        const confidence = compoundEmotion ? 70 : 50

        return (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className="mt-4 pt-3 border-t border-slate-700/50"
          >
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs text-slate-500">감정 기반 추천 목표</span>
            </div>
            <div className="flex items-center gap-3 bg-slate-700/30 rounded-lg px-3 py-2">
              <span className="text-lg">{goalConfig.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-200">{goalConfig.label}</span>
                  <span className="text-[10px] text-slate-500 px-1.5 py-0.5 bg-slate-700/50 rounded">
                    {confidence}%
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5 truncate">{goalConfig.description}</p>
              </div>
            </div>
          </motion.div>
        )
      })()}
    </motion.div>
  )
}
