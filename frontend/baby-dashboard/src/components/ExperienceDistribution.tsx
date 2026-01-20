'use client'

import { motion } from 'framer-motion'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { PieChartIcon, Layers } from 'lucide-react'
import type { Experience } from '@/lib/database.types'

interface ExperienceDistributionProps {
  experiences: Experience[]
  isLoading?: boolean
}

interface TypeStats {
  name: string
  value: number
  color: string
  [key: string]: string | number
}

const TYPE_COLORS: Record<string, string> = {
  // Original types
  learning: '#8b5cf6',
  exploration: '#10b981',
  problem_solving: '#f59e0b',
  creative: '#ec4899',
  communication: '#06b6d4',
  analysis: '#6366f1',
  // Additional types from database
  algorithm: '#f43f5e',
  class: '#14b8a6',
  function: '#a855f7',
  general: '#3b82f6',
  test: '#22c55e',
  debug: '#eab308',
  refactor: '#f97316',
  documentation: '#64748b',
  default: '#94a3b8',
}

const TYPE_LABELS: Record<string, string> = {
  learning: '학습',
  exploration: '탐험',
  problem_solving: '문제해결',
  creative: '창작',
  communication: '소통',
  analysis: '분석',
  algorithm: '알고리즘',
  class: '클래스',
  function: '함수',
  general: '일반',
  test: '테스트',
  debug: '디버깅',
  refactor: '리팩토링',
  documentation: '문서화',
}

// Fallback colors for unknown types
const FALLBACK_COLORS = [
  '#f43f5e', '#f97316', '#eab308', '#22c55e', '#14b8a6',
  '#06b6d4', '#3b82f6', '#6366f1', '#8b5cf6', '#a855f7',
  '#d946ef', '#ec4899',
]

export function ExperienceDistribution({ experiences, isLoading }: ExperienceDistributionProps) {
  if (isLoading) {
    return (
      <div className="bg-slate-800/50 rounded-2xl p-4 md:p-6 border border-slate-700/50 animate-pulse">
        <div className="h-8 bg-slate-700 rounded w-1/3 mb-4" />
        <div className="h-48 md:h-56 bg-slate-700 rounded" />
      </div>
    )
  }

  const typeStats = processExperienceTypes(experiences)

  if (typeStats.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm"
      >
        <div className="flex items-center gap-2 md:gap-3 mb-4">
          <div className="w-9 h-9 md:w-10 md:h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
            <PieChartIcon className="w-4 h-4 md:w-5 md:h-5 text-purple-400" />
          </div>
          <div>
            <h2 className="text-base md:text-lg font-semibold text-slate-100">경험 분포</h2>
            <p className="text-xs md:text-sm text-slate-400">유형별 분포</p>
          </div>
        </div>
        <div className="h-48 md:h-56 flex items-center justify-center text-slate-500">
          데이터가 충분하지 않습니다
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3 md:mb-4">
        <div className="flex items-center gap-2 md:gap-3">
          <div className="w-9 h-9 md:w-10 md:h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
            <PieChartIcon className="w-4 h-4 md:w-5 md:h-5 text-purple-400" />
          </div>
          <div>
            <h2 className="text-base md:text-lg font-semibold text-slate-100">경험 분포</h2>
            <p className="text-xs md:text-sm text-slate-400">유형별 분포</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Layers className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{typeStats.length}개 유형</span>
        </div>
      </div>

      {/* Chart */}
      <div className="h-48 md:h-56">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={typeStats}
              cx="50%"
              cy="50%"
              innerRadius="40%"
              outerRadius="70%"
              paddingAngle={2}
              dataKey="value"
              nameKey="name"
              animationBegin={0}
              animationDuration={800}
            >
              {typeStats.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color}
                  stroke="transparent"
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value) => [`${value}개`, '경험 수']}
            />
            <Legend
              layout="vertical"
              align="right"
              verticalAlign="middle"
              wrapperStyle={{ fontSize: '10px', paddingLeft: '10px' }}
              iconSize={8}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Type List (Mobile Friendly) */}
      <div className="grid grid-cols-2 gap-2 mt-3 md:hidden">
        {typeStats.slice(0, 4).map((type) => (
          <div
            key={type.name}
            className="flex items-center gap-2 bg-slate-900/50 rounded-lg p-2"
          >
            <div
              className="w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: type.color }}
            />
            <span className="text-xs text-slate-300 truncate">{type.name}</span>
            <span className="text-xs text-slate-500 ml-auto">{type.value}</span>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

function processExperienceTypes(experiences: Experience[]): TypeStats[] {
  const typeMap = new Map<string, number>()

  experiences.forEach((exp) => {
    const type = exp.task_type || 'default'
    typeMap.set(type, (typeMap.get(type) || 0) + 1)
  })

  const stats: TypeStats[] = []
  let fallbackColorIndex = 0

  typeMap.forEach((count, type) => {
    // Get color: try TYPE_COLORS first, then use fallback colors for unknown types
    let color = TYPE_COLORS[type]
    if (!color) {
      color = FALLBACK_COLORS[fallbackColorIndex % FALLBACK_COLORS.length]
      fallbackColorIndex++
    }

    stats.push({
      name: TYPE_LABELS[type] || type,
      value: count,
      color,
    })
  })

  // Sort by value descending
  return stats.sort((a, b) => b.value - a.value)
}
