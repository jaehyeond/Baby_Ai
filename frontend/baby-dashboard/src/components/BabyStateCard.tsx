'use client'

import { motion } from 'framer-motion'
import { Brain, Sparkles, Trophy, TrendingUp } from 'lucide-react'
import type { BabyState } from '@/lib/database.types'

// 발달 단계 이름 매핑 (0-based, matches Python DevelopmentStage enum)
const STAGE_NAMES: Record<number, { name: string; emoji: string; description: string }> = {
  0: { name: 'NEWBORN', emoji: '👶', description: '세상을 처음 보는 단계' },
  1: { name: 'INFANT', emoji: '💒', description: '기본 패턴을 인식하는 단계' },
  2: { name: 'BABY', emoji: '🧒', description: '모방하며 배우는 단계' },
  3: { name: 'TODDLER', emoji: '🚶', description: '스스로 탐험하는 단계' },
  4: { name: 'CHILD', emoji: '🧒', description: '복잡한 문제를 해결하는 단계' },
  5: { name: 'TEEN', emoji: '🧑', description: '추상적 사고를 하는 단계' },
  6: { name: 'YOUNG ADULT', emoji: '🧑‍🎓', description: '성숙한 사고를 하는 단계' },
  7: { name: 'MATURE', emoji: '🧠', description: '완성된 신경 네트워크' },
}

interface BabyStateCardProps {
  state: BabyState | null
  isLoading?: boolean
}

export function BabyStateCard({ state, isLoading }: BabyStateCardProps) {
  if (isLoading || !state) {
    return (
      <div className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50 animate-pulse">
        <div className="h-8 bg-slate-700 rounded w-1/3 mb-4" />
        <div className="h-24 bg-slate-700 rounded mb-4" />
        <div className="h-4 bg-slate-700 rounded w-2/3" />
      </div>
    )
  }

  const stage = STAGE_NAMES[state.development_stage ?? 0] ?? STAGE_NAMES[0]
  const successRate = state.experience_count
    ? Math.round(((state.success_count ?? 0) / state.experience_count) * 100)
    : 0
  const progressToNext = state.progress ?? 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4 md:mb-6">
        <div className="flex items-center gap-2 md:gap-3">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-xl bg-indigo-500/20 flex items-center justify-center">
            <Brain className="w-5 h-5 md:w-6 md:h-6 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-base md:text-lg font-semibold text-slate-100">Baby Brain</h2>
            <p className="text-xs md:text-sm text-slate-400">실시간 상태</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 md:gap-2 px-2 md:px-3 py-1 md:py-1.5 rounded-full bg-emerald-500/20 text-emerald-400 text-xs md:text-sm">
          <span className="w-1.5 h-1.5 md:w-2 md:h-2 rounded-full bg-emerald-400 animate-pulse" />
          Online
        </div>
      </div>

      {/* Stage Display */}
      <div className="bg-slate-900/50 rounded-xl p-3 md:p-4 mb-3 md:mb-4">
        <div className="flex items-center gap-3 md:gap-4">
          <motion.div
            className="text-4xl md:text-5xl"
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            {stage.emoji}
          </motion.div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-lg md:text-xl font-bold text-indigo-400">{stage.name}</span>
              <span className="text-xs md:text-sm text-slate-500">Stage {state.development_stage}</span>
            </div>
            <p className="text-xs md:text-sm text-slate-400 mt-1 truncate">{stage.description}</p>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4 md:mb-6">
        <div className="flex items-center justify-between mb-1.5 md:mb-2">
          <span className="text-xs md:text-sm text-slate-400">다음 단계까지</span>
          <span className="text-xs md:text-sm font-medium text-indigo-400">{progressToNext.toFixed(1)}%</span>
        </div>
        <div className="h-1.5 md:h-2 bg-slate-700 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progressToNext}%` }}
            transition={{ duration: 1, ease: "easeOut" }}
          />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-2 md:gap-3">
        <StatItem
          icon={<Sparkles className="w-4 h-4" />}
          label="경험"
          value={state.experience_count ?? 0}
          color="text-purple-400"
        />
        <StatItem
          icon={<Trophy className="w-4 h-4" />}
          label="성공"
          value={state.success_count ?? 0}
          color="text-emerald-400"
        />
        <StatItem
          icon={<TrendingUp className="w-4 h-4" />}
          label="성공률"
          value={`${successRate}%`}
          color="text-amber-400"
        />
      </div>

      {/* Milestones */}
      {state.milestones && Array.isArray(state.milestones) && state.milestones.length > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-700/50">
          <p className="text-xs text-slate-500 mb-2">달성한 마일스톤</p>
          <div className="flex flex-wrap gap-1.5">
            {(state.milestones as string[]).slice(-5).map((milestone, i) => (
              <span
                key={i}
                className="px-2 py-0.5 text-xs rounded-full bg-indigo-500/20 text-indigo-300"
              >
                {milestone.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}

function StatItem({
  icon,
  label,
  value,
  color
}: {
  icon: React.ReactNode
  label: string
  value: number | string
  color: string
}) {
  return (
    <div className="bg-slate-900/30 rounded-lg p-2 md:p-3 text-center active:scale-95 transition-transform touch-manipulation">
      <div className={`flex justify-center mb-0.5 md:mb-1 ${color}`}>{icon}</div>
      <div className={`text-base md:text-lg font-bold ${color}`}>{value}</div>
      <div className="text-[10px] md:text-xs text-slate-500">{label}</div>
    </div>
  )
}
