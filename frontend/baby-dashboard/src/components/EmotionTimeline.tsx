'use client'

import { motion } from 'framer-motion'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Activity, Clock } from 'lucide-react'
import type { EmotionLog } from '@/lib/database.types'

interface EmotionTimelineProps {
  emotionLogs: EmotionLog[]
  isLoading?: boolean
}

interface TimelinePoint {
  time: string
  displayTime: string
  curiosity: number
  joy: number
  fear: number
  frustration: number
  surprise: number
  boredom: number
}

const EMOTION_COLORS = {
  curiosity: '#8b5cf6',
  joy: '#10b981',
  fear: '#ef4444',
  frustration: '#f97316',
  surprise: '#f59e0b',
  boredom: '#6b7280',
}

const EMOTION_LABELS = {
  curiosity: '호기심',
  joy: '기쁨',
  fear: '두려움',
  frustration: '좌절',
  surprise: '놀람',
  boredom: '지루함',
}

export function EmotionTimeline({ emotionLogs, isLoading }: EmotionTimelineProps) {
  if (isLoading) {
    return (
      <div className="bg-slate-800/50 rounded-2xl p-4 md:p-6 border border-slate-700/50 animate-pulse">
        <div className="h-8 bg-slate-700 rounded w-1/3 mb-4" />
        <div className="h-48 md:h-64 bg-slate-700 rounded" />
      </div>
    )
  }

  const timelineData = processEmotionLogs(emotionLogs)

  if (timelineData.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.5 }}
        className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm"
      >
        <div className="flex items-center gap-2 md:gap-3 mb-4">
          <div className="w-9 h-9 md:w-10 md:h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
            <Activity className="w-4 h-4 md:w-5 md:h-5 text-amber-400" />
          </div>
          <div>
            <h2 className="text-base md:text-lg font-semibold text-slate-100">감정 타임라인</h2>
            <p className="text-xs md:text-sm text-slate-400">시간별 감정 변화</p>
          </div>
        </div>
        <div className="h-48 md:h-64 flex items-center justify-center text-slate-500">
          감정 로그 데이터가 없습니다
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.5 }}
      className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3 md:mb-4">
        <div className="flex items-center gap-2 md:gap-3">
          <div className="w-9 h-9 md:w-10 md:h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
            <Activity className="w-4 h-4 md:w-5 md:h-5 text-amber-400" />
          </div>
          <div>
            <h2 className="text-base md:text-lg font-semibold text-slate-100">감정 타임라인</h2>
            <p className="text-xs md:text-sm text-slate-400">시간별 감정 변화</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Clock className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">최근 {timelineData.length}개 기록</span>
        </div>
      </div>

      {/* Chart */}
      <div className="h-48 md:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={timelineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              {Object.entries(EMOTION_COLORS).map(([key, color]) => (
                <linearGradient key={key} id={`color${key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis
              dataKey="displayTime"
              tick={{ fill: '#64748b', fontSize: 10 }}
              stroke="#334155"
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[0, 100]}
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
                fontSize: '11px',
              }}
              labelStyle={{ color: '#f1f5f9', marginBottom: '4px' }}
              formatter={(value, name) => [
                `${Number(value ?? 0).toFixed(0)}%`,
                EMOTION_LABELS[name as keyof typeof EMOTION_LABELS] || name,
              ]}
            />
            {/* Stacked area for main emotions */}
            <Area
              type="monotone"
              dataKey="curiosity"
              stackId="1"
              stroke={EMOTION_COLORS.curiosity}
              fill={`url(#colorcuriosity)`}
              strokeWidth={1.5}
            />
            <Area
              type="monotone"
              dataKey="joy"
              stackId="2"
              stroke={EMOTION_COLORS.joy}
              fill={`url(#colorjoy)`}
              strokeWidth={1.5}
            />
            <Area
              type="monotone"
              dataKey="frustration"
              stackId="3"
              stroke={EMOTION_COLORS.frustration}
              fill={`url(#colorfrustration)`}
              strokeWidth={1.5}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-3 md:gap-4 mt-3 md:mt-4 pt-3 md:pt-4 border-t border-slate-700/50">
        {Object.entries(EMOTION_LABELS).slice(0, 4).map(([key, label]) => (
          <div key={key} className="flex items-center gap-1.5">
            <div
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: EMOTION_COLORS[key as keyof typeof EMOTION_COLORS] }}
            />
            <span className="text-[10px] md:text-xs text-slate-400">{label}</span>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

function processEmotionLogs(logs: EmotionLog[]): TimelinePoint[] {
  // Sort by created_at and take last 20
  const sortedLogs = [...logs]
    .sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at).getTime() : 0
      const dateB = b.created_at ? new Date(b.created_at).getTime() : 0
      return dateA - dateB
    })
    .slice(-20)

  return sortedLogs.map((log) => ({
    time: log.created_at || '',
    displayTime: formatTime(log.created_at),
    curiosity: log.curiosity * 100,
    joy: log.joy * 100,
    fear: log.fear * 100,
    frustration: log.frustration * 100,
    surprise: log.surprise * 100,
    boredom: log.boredom * 100,
  }))
}

function formatTime(dateString: string | null): string {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
