'use client'

import { motion } from 'framer-motion'
import { Activity, CheckCircle, XCircle, Clock } from 'lucide-react'
import type { Experience } from '@/lib/database.types'

interface ActivityLogProps {
  experiences: Experience[]
  isLoading?: boolean
}

export function ActivityLog({ experiences, isLoading }: ActivityLogProps) {
  if (isLoading) {
    return (
      <div className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50 animate-pulse">
        <div className="h-8 bg-slate-700 rounded w-1/3 mb-4" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3 md:mb-4">
        <div className="flex items-center gap-2 md:gap-3">
          <div className="w-9 h-9 md:w-10 md:h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center">
            <Activity className="w-4 h-4 md:w-5 md:h-5 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-base md:text-lg font-semibold text-slate-100">최근 활동</h2>
            <p className="text-xs md:text-sm text-slate-400">최근 경험 {experiences.length}개</p>
          </div>
        </div>
      </div>

      {/* Activity List */}
      <div className="space-y-2 max-h-60 md:max-h-80 overflow-y-auto pr-1 md:pr-2 -mr-1 md:-mr-2 scrollbar-thin">
        {experiences.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            아직 활동이 없습니다
          </div>
        ) : (
          experiences.map((exp, index) => (
            <motion.div
              key={exp.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              className="bg-slate-900/50 rounded-lg p-2.5 md:p-3 hover:bg-slate-900/70 active:scale-[0.99] transition-all touch-manipulation"
            >
              <div className="flex items-start gap-2 md:gap-3">
                {/* Status Icon */}
                <div className="mt-0.5 flex-shrink-0">
                  {exp.success ? (
                    <CheckCircle className="w-4 h-4 md:w-5 md:h-5 text-emerald-400" />
                  ) : (
                    <XCircle className="w-4 h-4 md:w-5 md:h-5 text-red-400" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-xs md:text-sm text-slate-200 truncate">{exp.task}</p>
                  <div className="flex items-center gap-2 md:gap-3 mt-1 flex-wrap">
                    {exp.task_type && (
                      <span className="text-[10px] md:text-xs px-1.5 md:px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300">
                        {exp.task_type}
                      </span>
                    )}
                    <span className="text-[10px] md:text-xs text-slate-600 flex items-center gap-1">
                      <Clock className="w-2.5 h-2.5 md:w-3 md:h-3" />
                      {formatTime(exp.created_at)}
                    </span>
                  </div>
                </div>

                {/* Memory Strength - Hidden on small mobile */}
                {exp.memory_strength !== null && (
                  <div className="text-right hidden sm:block flex-shrink-0">
                    <div className="text-[10px] md:text-xs text-slate-500">기억</div>
                    <div className="text-xs md:text-sm font-medium text-purple-400">
                      {((exp.memory_strength ?? 0) * 100).toFixed(0)}%
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          ))
        )}
      </div>
    </motion.div>
  )
}

function formatTime(dateString: string | null): string {
  if (!dateString) return '-'
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '방금'
  if (minutes < 60) return `${minutes}분 전`
  if (hours < 24) return `${hours}시간 전`
  if (days < 7) return `${days}일 전`

  return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
}
