'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { createClient } from '@supabase/supabase-js'

// Types
interface Strategy {
  strategy_name: string
  description: string
  success_count: number
  failure_count: number
  partial_count: number
  effectiveness_score: number
  last_used_at: string | null
}

interface Evaluation {
  id: string
  experience_id: string
  outcome: 'success' | 'failure' | 'partial'
  strategy_used: string
  pattern_match_score: number
  expected_outcome: string
  prediction_correct: boolean
  concepts_strengthened: string[]
  concepts_weakened: string[]
  strength_delta: number
  created_at: string
  experiences?: {
    task: string
    task_type: string
  }
}

interface Stats {
  total_evaluations: number
  strategy_usage: Record<string, number>
  average_prediction_accuracy: number
  most_effective_strategy: string
  least_effective_strategy: string
}

interface MetacognitionCardProps {
  className?: string
}

// Initialize Supabase client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
const supabase = createClient(supabaseUrl, supabaseKey)

export function MetacognitionCard({ className = '' }: MetacognitionCardProps) {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [evaluations, setEvaluations] = useState<Evaluation[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [activeTab, setActiveTab] = useState<'strategies' | 'evaluations' | 'insights'>('strategies')
  const [loading, setLoading] = useState(true)

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      const [strategiesRes, evaluationsRes, statsRes] = await Promise.all([
        fetch('/api/metacognition', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'get_strategies' })
        }),
        fetch('/api/metacognition', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'get_evaluations', limit: 10 })
        }),
        fetch('/api/metacognition', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'get_stats' })
        })
      ])

      const [strategiesData, evaluationsData, statsData] = await Promise.all([
        strategiesRes.json(),
        evaluationsRes.json(),
        statsRes.json()
      ])

      if (strategiesData.success) setStrategies(strategiesData.strategies || [])
      if (evaluationsData.success) setEvaluations(evaluationsData.evaluations || [])
      if (statsData.success) setStats(statsData.stats || null)

    } catch (error) {
      console.error('[MetacognitionCard] Fetch error:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Subscribe to realtime updates
  useEffect(() => {
    const channel = supabase
      .channel('metacognition_changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'self_evaluation_logs' },
        () => {
          fetchData()
        }
      )
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'strategy_effectiveness' },
        () => {
          fetchData()
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [fetchData])

  // Format percentage
  const formatPercentage = (value: number): string => {
    return `${Math.round(value * 100)}%`
  }

  // Get strategy emoji
  const getStrategyEmoji = (name: string): string => {
    const emojis: Record<string, string> = {
      explore: '🔍',
      exploit: '🎯',
      cautious: '🛡️',
      creative: '🎨',
      analytical: '📊',
      imitative: '👀'
    }
    return emojis[name] || '❓'
  }

  // Get outcome color
  const getOutcomeColor = (outcome: string): string => {
    switch (outcome) {
      case 'success': return 'text-emerald-400'
      case 'failure': return 'text-red-400'
      case 'partial': return 'text-amber-400'
      default: return 'text-slate-400'
    }
  }

  // Get effectiveness bar color
  const getEffectivenessColor = (score: number): string => {
    if (score >= 0.7) return 'bg-emerald-500'
    if (score >= 0.4) return 'bg-amber-500'
    return 'bg-red-500'
  }

  if (loading) {
    return (
      <div className={`bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-6 border border-slate-700/50 ${className}`}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-700 rounded w-1/3" />
          <div className="h-32 bg-slate-700 rounded" />
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl border border-slate-700/50 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-violet-600/20 to-purple-600/20 border-b border-slate-700/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">🧠</span>
            <h3 className="font-semibold text-slate-100">Meta-cognition</h3>
            <span className="text-xs px-2 py-0.5 bg-violet-500/20 text-violet-300 rounded-full">
              Phase 7
            </span>
          </div>
          <button
            onClick={fetchData}
            className="p-1.5 rounded-lg hover:bg-slate-700/50 transition-colors"
            title="새로고침"
          >
            <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-700/50">
        {(['strategies', 'evaluations', 'insights'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'text-violet-300 border-b-2 border-violet-500 bg-violet-500/10'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            {tab === 'strategies' && '전략'}
            {tab === 'evaluations' && '평가'}
            {tab === 'insights' && '인사이트'}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4 max-h-[400px] overflow-y-auto">
        <AnimatePresence mode="wait">
          {/* Strategies Tab */}
          {activeTab === 'strategies' && (
            <motion.div
              key="strategies"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-3"
            >
              {strategies.length === 0 ? (
                <p className="text-slate-500 text-sm text-center py-4">
                  아직 전략 데이터가 없습니다
                </p>
              ) : (
                strategies.map((strategy) => {
                  const total = strategy.success_count + strategy.failure_count + strategy.partial_count
                  return (
                    <div
                      key={strategy.strategy_name}
                      className="bg-slate-800/50 rounded-xl p-3 border border-slate-700/30"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{getStrategyEmoji(strategy.strategy_name)}</span>
                          <span className="font-medium text-slate-200 capitalize">
                            {strategy.strategy_name}
                          </span>
                        </div>
                        <span className="text-sm text-slate-400">
                          {total > 0 ? formatPercentage(strategy.effectiveness_score) : 'N/A'}
                        </span>
                      </div>

                      <p className="text-xs text-slate-500 mb-2">{strategy.description}</p>

                      {/* Effectiveness bar */}
                      <div className="h-2 bg-slate-700 rounded-full overflow-hidden mb-2">
                        <div
                          className={`h-full ${getEffectivenessColor(strategy.effectiveness_score)} transition-all duration-500`}
                          style={{ width: `${strategy.effectiveness_score * 100}%` }}
                        />
                      </div>

                      {/* Stats */}
                      <div className="flex gap-3 text-xs">
                        <span className="text-emerald-400">✓ {strategy.success_count}</span>
                        <span className="text-red-400">✗ {strategy.failure_count}</span>
                        <span className="text-amber-400">◐ {strategy.partial_count}</span>
                      </div>
                    </div>
                  )
                })
              )}
            </motion.div>
          )}

          {/* Evaluations Tab */}
          {activeTab === 'evaluations' && (
            <motion.div
              key="evaluations"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-2"
            >
              {evaluations.length === 0 ? (
                <p className="text-slate-500 text-sm text-center py-4">
                  아직 평가 기록이 없습니다
                </p>
              ) : (
                evaluations.map((evaluation) => (
                  <div
                    key={evaluation.id}
                    className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/30"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className={`font-medium ${getOutcomeColor(evaluation.outcome)}`}>
                          {evaluation.outcome === 'success' && '✓'}
                          {evaluation.outcome === 'failure' && '✗'}
                          {evaluation.outcome === 'partial' && '◐'}
                        </span>
                        <span className="text-sm text-slate-300 truncate max-w-[200px]">
                          {evaluation.experiences?.task || evaluation.experience_id.slice(0, 8)}
                        </span>
                      </div>
                      <span className="text-xs text-slate-500">
                        {new Date(evaluation.created_at).toLocaleDateString('ko-KR')}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-400">
                      <span>
                        전략: {getStrategyEmoji(evaluation.strategy_used)} {evaluation.strategy_used}
                      </span>
                      <span>
                        매칭: {formatPercentage(evaluation.pattern_match_score || 0)}
                      </span>
                      {evaluation.prediction_correct !== null && (
                        <span className={evaluation.prediction_correct ? 'text-emerald-400' : 'text-red-400'}>
                          예측 {evaluation.prediction_correct ? '적중' : '실패'}
                        </span>
                      )}
                    </div>

                    {(evaluation.concepts_strengthened?.length > 0 || evaluation.concepts_weakened?.length > 0) && (
                      <div className="mt-2 text-xs">
                        {evaluation.concepts_strengthened?.length > 0 && (
                          <span className="text-emerald-400">
                            +{evaluation.concepts_strengthened.length} 강화
                          </span>
                        )}
                        {evaluation.concepts_weakened?.length > 0 && (
                          <span className="text-red-400 ml-2">
                            -{evaluation.concepts_weakened.length} 약화
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                ))
              )}
            </motion.div>
          )}

          {/* Insights Tab */}
          {activeTab === 'insights' && (
            <motion.div
              key="insights"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              {!stats ? (
                <p className="text-slate-500 text-sm text-center py-4">
                  통계 데이터를 불러오는 중...
                </p>
              ) : (
                <>
                  {/* Key Stats */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-slate-800/50 rounded-xl p-3 border border-slate-700/30">
                      <p className="text-xs text-slate-500 mb-1">총 평가 수</p>
                      <p className="text-xl font-bold text-violet-400">
                        {stats.total_evaluations}
                      </p>
                    </div>
                    <div className="bg-slate-800/50 rounded-xl p-3 border border-slate-700/30">
                      <p className="text-xs text-slate-500 mb-1">예측 정확도</p>
                      <p className="text-xl font-bold text-emerald-400">
                        {formatPercentage(stats.average_prediction_accuracy)}
                      </p>
                    </div>
                  </div>

                  {/* Best/Worst Strategy */}
                  <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                    <h4 className="text-sm font-medium text-slate-300 mb-3">전략 분석</h4>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-500">가장 효과적</span>
                        <span className="text-sm text-emerald-400">
                          {getStrategyEmoji(stats.most_effective_strategy)} {stats.most_effective_strategy || 'N/A'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-500">가장 비효과적</span>
                        <span className="text-sm text-red-400">
                          {getStrategyEmoji(stats.least_effective_strategy)} {stats.least_effective_strategy || 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Strategy Usage Distribution */}
                  <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                    <h4 className="text-sm font-medium text-slate-300 mb-3">전략 사용 분포</h4>

                    <div className="space-y-2">
                      {Object.entries(stats.strategy_usage || {}).map(([strategy, count]) => {
                        const total = Object.values(stats.strategy_usage || {}).reduce((a, b) => a + b, 0)
                        const percentage = total > 0 ? (count / total) * 100 : 0
                        return (
                          <div key={strategy} className="flex items-center gap-2">
                            <span className="w-16 text-xs text-slate-400 capitalize truncate">
                              {getStrategyEmoji(strategy)} {strategy}
                            </span>
                            <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-violet-500 transition-all duration-500"
                                style={{ width: `${percentage}%` }}
                              />
                            </div>
                            <span className="text-xs text-slate-500 w-8 text-right">{count}</span>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Philosophy Note */}
                  <div className="bg-violet-500/10 rounded-xl p-3 border border-violet-500/30">
                    <p className="text-xs text-violet-300 italic">
                      💡 "외부 LLM 없이 통계/규칙 기반으로 자기 사고를 분석합니다"
                    </p>
                  </div>
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Footer */}
      <div className="px-4 py-2 bg-slate-900/50 border-t border-slate-700">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>자기 사고에 대한 사고 (NO LLM)</span>
          <span>v1</span>
        </div>
      </div>
    </div>
  )
}
