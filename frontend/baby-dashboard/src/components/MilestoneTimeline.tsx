'use client'

import { useMilestones, MILESTONE_DEFINITIONS } from '@/hooks/useMilestones'
import { motion } from 'framer-motion'
import { Loader2, Trophy, Lock, Clock, Star, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'

// Stage names (0-based, matches Python DevelopmentStage enum)
const STAGE_NAMES: Record<number, string> = {
  0: 'NEWBORN',
  1: 'INFANT',
  2: 'BABY',
  3: 'TODDLER',
  4: 'CHILD',
  5: 'TEEN',
  6: 'YOUNG ADULT',
  7: 'MATURE',
}

export function MilestoneTimeline() {
  const { data, isLoading, error, refetch } = useMilestones()
  const [showAll, setShowAll] = useState(false)

  if (isLoading) {
    return (
      <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-6 border border-slate-700/50 backdrop-blur-sm">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-6 border border-slate-700/50 backdrop-blur-sm">
        <div className="text-center py-8">
          <p className="text-red-400 mb-3">{error}</p>
          <button
            onClick={refetch}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm text-white transition-colors"
          >
            다시 시도
          </button>
        </div>
      </div>
    )
  }

  if (!data) return null

  const achievedMilestones = data.milestones.filter((m) => m.achievedAt !== null)
  const pendingMilestones = data.milestones.filter((m) => m.achievedAt === null)
  const displayedMilestones = showAll ? data.milestones : achievedMilestones.slice(0, 5)

  return (
    <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-500/20 rounded-lg">
            <Trophy className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-100">발달 마일스톤</h3>
            <p className="text-xs text-slate-400">
              {data.achievedCount}/{data.totalCount} 달성 · Stage {data.currentStage} ({STAGE_NAMES[data.currentStage] || 'UNKNOWN'})
            </p>
          </div>
        </div>

        {/* Progress Ring */}
        <div className="relative w-14 h-14">
          <svg className="w-full h-full -rotate-90">
            <circle
              cx="28"
              cy="28"
              r="24"
              fill="none"
              stroke="currentColor"
              strokeWidth="4"
              className="text-slate-700"
            />
            <circle
              cx="28"
              cy="28"
              r="24"
              fill="none"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray={`${(data.achievedCount / data.totalCount) * 150.8} 150.8`}
              className="text-amber-400"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-sm font-bold text-amber-400">
              {Math.round((data.achievedCount / data.totalCount) * 100)}%
            </span>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gradient-to-b from-amber-400 via-indigo-500 to-slate-700" />

        <div className="space-y-4">
          {displayedMilestones.map((milestone, index) => {
            const isAchieved = milestone.achievedAt !== null
            const isLatest = isAchieved && index === achievedMilestones.length - 1

            return (
              <motion.div
                key={milestone.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`relative pl-14 ${!isAchieved ? 'opacity-50' : ''}`}
              >
                {/* Timeline dot */}
                <div
                  className={`absolute left-4 w-5 h-5 rounded-full border-2 flex items-center justify-center
                    ${isAchieved
                      ? isLatest
                        ? 'bg-amber-500 border-amber-400 animate-pulse'
                        : 'bg-slate-800'
                      : 'bg-slate-800 border-slate-600'
                    }`}
                  style={isAchieved ? { borderColor: milestone.info.color, backgroundColor: isLatest ? undefined : milestone.info.color + '30' } : undefined}
                >
                  {!isAchieved && (
                    <Lock className="w-2.5 h-2.5 text-slate-500" />
                  )}
                </div>

                {/* Milestone card */}
                <div
                  className={`p-3 rounded-xl border transition-all
                    ${isAchieved
                      ? 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600'
                      : 'bg-slate-900/30 border-slate-800/50'
                    }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4
                          className={`font-medium ${isAchieved ? 'text-slate-100' : 'text-slate-500'}`}
                          style={isAchieved ? { color: milestone.info.color } : undefined}
                        >
                          {milestone.info.name}
                        </h4>
                        {isLatest && (
                          <span className="px-1.5 py-0.5 bg-amber-500/20 rounded text-[10px] text-amber-400 font-medium">
                            최신
                          </span>
                        )}
                      </div>
                      <p className={`text-xs mt-0.5 ${isAchieved ? 'text-slate-400' : 'text-slate-600'}`}>
                        {milestone.info.description}
                      </p>
                    </div>

                    {/* Achievement info - 일관된 배치 */}
                    {isAchieved && (
                      <div className="text-right shrink-0 min-w-[70px]">
                        <div className="flex items-center justify-end gap-1 text-[10px] text-slate-500">
                          <Clock className="w-3 h-3" />
                          {milestone.achievedAt ? formatDate(milestone.achievedAt) : '-'}
                        </div>
                        <div className="flex items-center justify-end gap-1 text-[10px] text-indigo-400 mt-0.5">
                          <Star className="w-3 h-3" />
                          #{milestone.experienceNumber || '-'}
                        </div>
                      </div>
                    )}

                    {/* Locked indicator */}
                    {!isAchieved && (
                      <div className="text-[10px] text-slate-600">
                        Stage {milestone.info.stage}+
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>

        {/* Show more/less button */}
        {data.milestones.length > 5 && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="mt-4 w-full py-2 flex items-center justify-center gap-1 text-sm text-slate-400 hover:text-slate-300 transition-colors"
          >
            {showAll ? (
              <>
                <ChevronUp className="w-4 h-4" />
                접기
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                {pendingMilestones.length}개 더 보기
              </>
            )}
          </button>
        )}
      </div>

      {/* Stats footer */}
      <div className="mt-4 pt-4 border-t border-slate-700/50 grid grid-cols-3 gap-2">
        <div className="text-center">
          <p className="text-lg font-bold text-emerald-400">{achievedMilestones.length}</p>
          <p className="text-[10px] text-slate-500">달성</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-amber-400">{pendingMilestones.length}</p>
          <p className="text-[10px] text-slate-500">미달성</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-indigo-400">{data.experienceCount}</p>
          <p className="text-[10px] text-slate-500">총 경험</p>
        </div>
      </div>
    </div>
  )
}

// Format date for display
function formatDate(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    return '오늘'
  } else if (diffDays === 1) {
    return '어제'
  } else if (diffDays < 7) {
    return `${diffDays}일 전`
  } else {
    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
  }
}
