'use client'

import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import {
  Brain,
  Lightbulb,
  ShieldAlert,
  Compass,
  Gauge,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
} from 'lucide-react'

interface EmotionalInfluence {
  learning_rate_modifier: number
  exploration_rate: number
  memory_weight: number
  strategy_change_prob: number
  risk_tolerance: number
  attention_focus: {
    exploration: number
    exploitation: number
    avoidance: number
    change: number
    detail: number
  }
}

interface BabyStateWithInfluence {
  curiosity: number
  joy: number
  fear: number
  frustration: number
  boredom: number
  dominant_emotion: string
}

// Transform nullable Supabase data to required types
function transformBabyState(data: Record<string, unknown>): BabyStateWithInfluence {
  return {
    curiosity: (data.curiosity as number) ?? 0.5,
    joy: (data.joy as number) ?? 0.5,
    fear: (data.fear as number) ?? 0,
    frustration: (data.frustration as number) ?? 0,
    boredom: (data.boredom as number) ?? 0,
    dominant_emotion: (data.dominant_emotion as string) ?? 'neutral',
  }
}

interface EmotionalInfluenceCardProps {
  className?: string
}

// 감정 기반 영향도 계산 함수 (프론트엔드에서 시뮬레이션)
function calculateInfluence(state: BabyStateWithInfluence): EmotionalInfluence {
  // Learning Rate Modifier (0.5 ~ 1.5)
  let modifier = 1.0
  if (state.joy > 0.6) modifier += (state.joy - 0.5) * 0.5
  if (state.curiosity > 0.6) modifier += (state.curiosity - 0.5) * 0.3
  if (state.fear > 0.6) modifier -= (state.fear - 0.5) * 0.4
  if (state.boredom > 0.5) modifier -= (state.boredom - 0.5) * 0.3
  if (state.frustration > 0.5) modifier += (state.frustration - 0.5) * 0.2
  const learning_rate_modifier = Math.max(0.5, Math.min(1.5, modifier))

  // Exploration Rate
  let exploration = state.curiosity * (1 - state.fear * 0.5)
  if (state.boredom > 0.5) exploration += 0.2
  const exploration_rate = Math.min(1.0, exploration)

  // Memory Weight
  const emotional_intensity = (
    Math.abs(state.curiosity - 0.5) +
    Math.abs(state.joy - 0.5) +
    Math.abs(state.fear - 0.5) +
    Math.abs(state.frustration - 0.5)
  ) / 2
  const memory_weight = Math.min(1.0, 0.3 + emotional_intensity * 0.7)

  // Strategy Change Probability
  let strategy_change_prob = 0.1
  if (state.frustration > 0.5) strategy_change_prob += (state.frustration - 0.5) * 0.8
  if (state.boredom > 0.5) strategy_change_prob += (state.boredom - 0.5) * 0.6
  if (state.curiosity > 0.7) strategy_change_prob += (state.curiosity - 0.7) * 0.5
  if (state.joy > 0.7) strategy_change_prob -= 0.2
  strategy_change_prob = Math.max(0, Math.min(1, strategy_change_prob))

  // Risk Tolerance
  let risk_tolerance = 0.5
  if (state.fear > 0.3) risk_tolerance -= (state.fear - 0.3) * 0.7
  if (state.curiosity > 0.5) risk_tolerance += (state.curiosity - 0.5) * 0.5
  if (state.joy > 0.6) risk_tolerance += (state.joy - 0.6) * 0.3
  if (state.frustration > 0.6) risk_tolerance += (state.frustration - 0.6) * 0.4
  risk_tolerance = Math.max(0, Math.min(1, risk_tolerance))

  // Attention Focus
  const attention_focus = {
    exploration: state.curiosity,
    exploitation: state.joy * 0.8,
    avoidance: state.fear,
    change: state.frustration + state.boredom * 0.5,
    detail: 1.0 - state.boredom,
  }

  return {
    learning_rate_modifier,
    exploration_rate,
    memory_weight,
    strategy_change_prob,
    risk_tolerance,
    attention_focus,
  }
}

function InfluenceBar({
  label,
  value,
  icon: Icon,
  description,
  colorClass,
  showTrend = false,
  baseValue = 0.5,
}: {
  label: string
  value: number
  icon: typeof Brain
  description: string
  colorClass: string
  showTrend?: boolean
  baseValue?: number
}) {
  const percentage = Math.round(value * 100)
  const trend = value > baseValue + 0.1 ? 'up' : value < baseValue - 0.1 ? 'down' : 'neutral'

  return (
    <div className="bg-slate-800/50 rounded-xl p-4 hover:bg-slate-800/70 transition-colors">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`p-1.5 rounded-lg ${colorClass} bg-opacity-20`}>
            <Icon className={`w-4 h-4 ${colorClass}`} />
          </div>
          <span className="text-sm font-medium text-slate-200">{label}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className={`text-lg font-bold ${colorClass}`}>{percentage}%</span>
          {showTrend && (
            <span className="ml-1">
              {trend === 'up' && <TrendingUp className="w-3 h-3 text-emerald-400" />}
              {trend === 'down' && <TrendingDown className="w-3 h-3 text-rose-400" />}
              {trend === 'neutral' && <Minus className="w-3 h-3 text-slate-500" />}
            </span>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden mb-2">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className={`h-full rounded-full ${colorClass.replace('text-', 'bg-')}`}
        />
      </div>

      <p className="text-xs text-slate-500">{description}</p>
    </div>
  )
}

function AttentionFocusRadar({ focus }: { focus: EmotionalInfluence['attention_focus'] }) {
  const items = [
    { key: 'exploration', label: '탐험', color: 'text-cyan-400' },
    { key: 'exploitation', label: '활용', color: 'text-emerald-400' },
    { key: 'avoidance', label: '회피', color: 'text-rose-400' },
    { key: 'change', label: '변화', color: 'text-amber-400' },
    { key: 'detail', label: '세부', color: 'text-purple-400' },
  ]

  return (
    <div className="bg-slate-800/50 rounded-xl p-4">
      <h4 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
        <Compass className="w-4 h-4 text-indigo-400" />
        주의 집중 영역
      </h4>
      <div className="space-y-2">
        {items.map((item) => {
          const value = focus[item.key as keyof typeof focus]
          const percentage = Math.round(value * 100)
          return (
            <div key={item.key} className="flex items-center gap-2">
              <span className={`text-xs w-12 ${item.color}`}>{item.label}</span>
              <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${percentage}%` }}
                  transition={{ duration: 0.5, delay: 0.1 }}
                  className={`h-full rounded-full ${item.color.replace('text-', 'bg-')}`}
                />
              </div>
              <span className="text-xs text-slate-500 w-8 text-right">{percentage}%</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function EmotionalInfluenceCard({ className = '' }: EmotionalInfluenceCardProps) {
  const [babyState, setBabyState] = useState<BabyStateWithInfluence | null>(null)
  const [influence, setInfluence] = useState<EmotionalInfluence | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    setLoading(true)
    try {
      const { data } = await supabase
        .from('baby_state')
        .select('curiosity, joy, fear, frustration, boredom, dominant_emotion')
        .order('updated_at', { ascending: false })
        .limit(1)
        .single()

      if (data) {
        const transformed = transformBabyState(data as Record<string, unknown>)
        setBabyState(transformed)
        setInfluence(calculateInfluence(transformed))
      }
    } catch (error) {
      console.error('Failed to fetch baby state:', error)
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchData()

    // 실시간 구독
    const channel = supabase
      .channel('emotional_influence')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'baby_state' }, () => {
        fetchData()
      })
      .subscribe()

    return () => {
      channel.unsubscribe()
    }
  }, [])

  if (loading) {
    return (
      <div className={`bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-6 border border-slate-700/50 backdrop-blur-sm ${className}`}>
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-6 h-6 text-slate-500 animate-spin" />
        </div>
      </div>
    )
  }

  if (!influence || !babyState) {
    return (
      <div className={`bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-6 border border-slate-700/50 backdrop-blur-sm ${className}`}>
        <div className="flex items-center justify-center h-64 text-slate-500">
          데이터 없음
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-6 border border-slate-700/50 backdrop-blur-sm ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
            <Brain className="w-5 h-5 text-indigo-400" />
            감정 영향 분석
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Phase 3: 감정이 학습과 행동에 미치는 영향
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-1 bg-indigo-500/20 text-indigo-400 rounded-full">
            {babyState.dominant_emotion}
          </span>
        </div>
      </div>

      {/* Main Influence Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <InfluenceBar
          label="학습률 조절"
          value={(influence.learning_rate_modifier - 0.5) / 1}
          icon={Lightbulb}
          description={influence.learning_rate_modifier > 1 ? '감정이 학습을 촉진' : '감정이 학습을 억제'}
          colorClass="text-amber-400"
          showTrend
          baseValue={0.5}
        />
        <InfluenceBar
          label="탐험 비율"
          value={influence.exploration_rate}
          icon={Compass}
          description="새로운 방법을 시도할 확률"
          colorClass="text-cyan-400"
          showTrend
        />
        <InfluenceBar
          label="기억 가중치"
          value={influence.memory_weight}
          icon={Brain}
          description="이 경험을 기억할 강도"
          colorClass="text-purple-400"
        />
        <InfluenceBar
          label="전략 변경 확률"
          value={influence.strategy_change_prob}
          icon={RefreshCw}
          description="현재 접근법을 바꿀 확률"
          colorClass="text-rose-400"
          showTrend
          baseValue={0.1}
        />
        <InfluenceBar
          label="위험 감수"
          value={influence.risk_tolerance}
          icon={ShieldAlert}
          description="위험한 시도를 할 의향"
          colorClass="text-emerald-400"
          showTrend
        />
        <InfluenceBar
          label="전체 영향력"
          value={(influence.learning_rate_modifier + influence.exploration_rate + influence.memory_weight) / 3}
          icon={Gauge}
          description="감정이 의사결정에 미치는 총 영향"
          colorClass="text-indigo-400"
        />
      </div>

      {/* Attention Focus */}
      <AttentionFocusRadar focus={influence.attention_focus} />

      {/* Strategy Recommendation */}
      <div className="mt-4 p-3 bg-slate-900/50 rounded-xl border border-slate-700/30">
        <h4 className="text-xs font-medium text-slate-400 mb-2">현재 추천 전략</h4>
        <div className="flex items-center gap-2">
          {influence.strategy_change_prob > 0.5 ? (
            <>
              <span className="px-2 py-1 bg-rose-500/20 text-rose-400 text-xs rounded-full">ALTERNATIVE</span>
              <span className="text-xs text-slate-500">좌절/지루함으로 새로운 접근 필요</span>
            </>
          ) : influence.exploration_rate > 0.7 ? (
            <>
              <span className="px-2 py-1 bg-cyan-500/20 text-cyan-400 text-xs rounded-full">EXPLORE</span>
              <span className="text-xs text-slate-500">호기심이 높아 탐험 모드</span>
            </>
          ) : influence.risk_tolerance < 0.3 ? (
            <>
              <span className="px-2 py-1 bg-amber-500/20 text-amber-400 text-xs rounded-full">CAUTIOUS</span>
              <span className="text-xs text-slate-500">두려움으로 조심스러운 접근</span>
            </>
          ) : (
            <>
              <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded-full">EXPLOIT</span>
              <span className="text-xs text-slate-500">안정적인 성공 패턴 활용</span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
