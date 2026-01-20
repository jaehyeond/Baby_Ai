'use client'

import { motion } from 'framer-motion'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Area,
  AreaChart,
} from 'recharts'
import { TrendingUp, Calendar } from 'lucide-react'
import type { Experience } from '@/lib/database.types'

interface GrowthChartProps {
  experiences: Experience[]
  isLoading?: boolean
}

interface DailyStats {
  date: string
  displayDate: string
  totalExperiences: number
  successCount: number
  successRate: number
  avgMemoryStrength: number
}

export function GrowthChart({ experiences, isLoading }: GrowthChartProps) {
  if (isLoading) {
    return (
      <div className="bg-slate-800/50 rounded-2xl p-4 md:p-6 border border-slate-700/50 animate-pulse">
        <div className="h-8 bg-slate-700 rounded w-1/3 mb-4" />
        <div className="h-48 md:h-64 bg-slate-700 rounded" />
      </div>
    )
  }

  // Process experiences into daily stats
  const dailyStats = processExperiencesToDaily(experiences)

  if (dailyStats.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
        className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm"
      >
        <div className="flex items-center gap-2 md:gap-3 mb-4">
          <div className="w-9 h-9 md:w-10 md:h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 md:w-5 md:h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-base md:text-lg font-semibold text-slate-100">성장 추이</h2>
            <p className="text-xs md:text-sm text-slate-400">일별 학습 현황</p>
          </div>
        </div>
        <div className="h-48 md:h-64 flex items-center justify-center text-slate-500">
          데이터가 충분하지 않습니다
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3 md:mb-4">
        <div className="flex items-center gap-2 md:gap-3">
          <div className="w-9 h-9 md:w-10 md:h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 md:w-5 md:h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-base md:text-lg font-semibold text-slate-100">성장 추이</h2>
            <p className="text-xs md:text-sm text-slate-400">일별 학습 현황</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Calendar className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">최근 {dailyStats.length}일</span>
        </div>
      </div>

      {/* Chart */}
      <div className="h-48 md:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={dailyStats} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorExperiences" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorSuccess" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis
              dataKey="displayDate"
              tick={{ fill: '#64748b', fontSize: 10 }}
              stroke="#334155"
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fill: '#64748b', fontSize: 10 }}
              stroke="#334155"
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              labelStyle={{ color: '#f1f5f9' }}
            />
            <Legend
              wrapperStyle={{ fontSize: '10px', paddingTop: '10px' }}
              iconSize={8}
            />
            <Area
              type="monotone"
              dataKey="totalExperiences"
              name="총 경험"
              stroke="#10b981"
              fillOpacity={1}
              fill="url(#colorExperiences)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="successCount"
              name="성공"
              stroke="#6366f1"
              fillOpacity={1}
              fill="url(#colorSuccess)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-2 md:gap-3 mt-3 md:mt-4 pt-3 md:pt-4 border-t border-slate-700/50">
        <div className="text-center">
          <p className="text-lg md:text-xl font-bold text-emerald-400">
            {dailyStats.reduce((sum, d) => sum + d.totalExperiences, 0)}
          </p>
          <p className="text-[10px] md:text-xs text-slate-500">총 경험</p>
        </div>
        <div className="text-center">
          <p className="text-lg md:text-xl font-bold text-indigo-400">
            {Math.round(
              dailyStats.reduce((sum, d) => sum + d.successRate, 0) / dailyStats.length
            )}%
          </p>
          <p className="text-[10px] md:text-xs text-slate-500">평균 성공률</p>
        </div>
        <div className="text-center">
          <p className="text-lg md:text-xl font-bold text-purple-400">
            {Math.round(
              dailyStats.reduce((sum, d) => sum + d.avgMemoryStrength, 0) / dailyStats.length
            )}%
          </p>
          <p className="text-[10px] md:text-xs text-slate-500">평균 기억력</p>
        </div>
      </div>
    </motion.div>
  )
}

function processExperiencesToDaily(experiences: Experience[]): DailyStats[] {
  const dailyMap = new Map<string, Experience[]>()

  // Group experiences by date
  experiences.forEach((exp) => {
    if (!exp.created_at) return
    const date = new Date(exp.created_at).toISOString().split('T')[0]
    const existing = dailyMap.get(date) || []
    dailyMap.set(date, [...existing, exp])
  })

  // Convert to stats array
  const stats: DailyStats[] = []
  dailyMap.forEach((exps, date) => {
    const successExps = exps.filter((e) => e.success)
    const memoryStrengths = exps
      .filter((e) => e.memory_strength !== null)
      .map((e) => e.memory_strength ?? 0)

    stats.push({
      date,
      displayDate: formatDate(date),
      totalExperiences: exps.length,
      successCount: successExps.length,
      successRate: exps.length > 0 ? Math.round((successExps.length / exps.length) * 100) : 0,
      avgMemoryStrength:
        memoryStrengths.length > 0
          ? Math.round(
              (memoryStrengths.reduce((a, b) => a + b, 0) / memoryStrengths.length) * 100
            )
          : 0,
    })
  })

  // Sort by date and return last 7 days
  return stats.sort((a, b) => a.date.localeCompare(b.date)).slice(-7)
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}/${date.getDate()}`
}
