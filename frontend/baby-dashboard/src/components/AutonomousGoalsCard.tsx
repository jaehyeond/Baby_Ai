'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { createClient } from '@supabase/supabase-js'

// Types
interface Goal {
  id: string
  description: string
  goal_type: 'epistemic' | 'diversive' | 'empowerment'
  domain: string | null
  priority: number
  epistemic_score: number
  diversive_score: number
  empowerment_score: number
  combined_motivation: number
  status: string
  attempt_count: number
  success_count: number
  created_by_stage: number
  trigger_reason?: string
  created_at: string
}

interface GoalProgress {
  id: string
  goal_id: string
  attempt_number: number
  outcome: string
  learning_gain: number
  insight?: string
  created_at: string
}

interface AutonomyMetrics {
  id: string
  epistemic_curiosity: number
  diversive_curiosity: number
  empowerment_drive: number
  overall_autonomy: number
  active_goals_count: number
  completed_goals_count: number
  created_at: string
}

interface AutonomousGoalsCardProps {
  className?: string
}

// Supabase client
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// Goal type icons and colors
const goalTypeConfig: Record<string, { icon: string; color: string; label: string; bgColor: string }> = {
  epistemic: {
    icon: '🔬',
    color: 'text-blue-400',
    label: '지식 탐구',
    bgColor: 'bg-blue-500/20'
  },
  diversive: {
    icon: '🌈',
    color: 'text-purple-400',
    label: '다양성 추구',
    bgColor: 'bg-purple-500/20'
  },
  empowerment: {
    icon: '💪',
    color: 'text-orange-400',
    label: '능력 향상',
    bgColor: 'bg-orange-500/20'
  },
}

// Status colors
const statusConfig: Record<string, { color: string; label: string }> = {
  active: { color: 'bg-green-500', label: '진행 중' },
  completed: { color: 'bg-blue-500', label: '완료' },
  abandoned: { color: 'bg-red-500', label: '포기' },
  deferred: { color: 'bg-yellow-500', label: '보류' },
}

// Domain icons
const domainIcons: Record<string, string> = {
  programming: '💻',
  language: '📝',
  math: '🔢',
  science: '🔬',
  social: '👥',
  creative: '🎨',
  physical: '🏃',
}

export function AutonomousGoalsCard({ className = '' }: AutonomousGoalsCardProps) {
  const [goals, setGoals] = useState<Goal[]>([])
  const [progress, setProgress] = useState<GoalProgress[]>([])
  const [metrics, setMetrics] = useState<AutonomyMetrics | null>(null)
  const [activeTab, setActiveTab] = useState<'goals' | 'metrics' | 'history'>('goals')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      const [goalsRes, progressRes, metricsRes] = await Promise.all([
        supabase
          .from('autonomous_goals')
          .select('*')
          .order('combined_motivation', { ascending: false })
          .limit(20),
        supabase
          .from('goal_progress')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(20),
        supabase
          .from('autonomy_metrics')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(1)
          .single(),
      ])

      if (goalsRes.data) setGoals(goalsRes.data)
      if (progressRes.data) setProgress(progressRes.data)
      if (metricsRes.data) setMetrics(metricsRes.data)
    } catch (error) {
      console.error('[AutonomousGoalsCard] Fetch error:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()

    // Subscribe to real-time updates
    const goalsChannel = supabase
      .channel('autonomous_goals_changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'autonomous_goals' }, () => {
        fetchData()
      })
      .subscribe()

    const metricsChannel = supabase
      .channel('autonomy_metrics_changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'autonomy_metrics' }, () => {
        fetchData()
      })
      .subscribe()

    return () => {
      supabase.removeChannel(goalsChannel)
      supabase.removeChannel(metricsChannel)
    }
  }, [fetchData])

  // Generate new goals
  const generateGoals = async () => {
    setGenerating(true)
    try {
      const response = await fetch('/api/goals/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'generate' }),
      })

      if (response.ok) {
        await fetchData()
      }
    } catch (error) {
      console.error('[AutonomousGoalsCard] Generate error:', error)
    } finally {
      setGenerating(false)
    }
  }

  // Calculate stats
  const stats = useMemo(() => {
    const activeGoals = goals.filter(g => g.status === 'active').length
    const completedGoals = goals.filter(g => g.status === 'completed').length
    const epistemicGoals = goals.filter(g => g.goal_type === 'epistemic').length
    const diversiveGoals = goals.filter(g => g.goal_type === 'diversive').length
    const empowermentGoals = goals.filter(g => g.goal_type === 'empowerment').length

    return {
      activeGoals,
      completedGoals,
      totalGoals: goals.length,
      epistemicGoals,
      diversiveGoals,
      empowermentGoals,
      completionRate: goals.length > 0 ? (completedGoals / goals.length) * 100 : 0,
    }
  }, [goals])

  if (loading) {
    return (
      <div className={`bg-slate-800 rounded-xl p-4 ${className}`}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-700 rounded w-1/3"></div>
          <div className="h-32 bg-slate-700 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-slate-800 rounded-xl overflow-hidden ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="text-2xl">🎯</span>
            자율 목표 설정
            <span className="text-xs bg-purple-500/30 text-purple-300 px-2 py-0.5 rounded-full">
              Phase 5
            </span>
          </h3>
          <button
            onClick={generateGoals}
            disabled={generating}
            className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 disabled:bg-slate-600
                       text-white text-sm rounded-lg transition-colors flex items-center gap-1"
          >
            {generating ? (
              <>
                <span className="animate-spin">⚙️</span>
                생성 중...
              </>
            ) : (
              <>
                <span>✨</span>
                새 목표 생성
              </>
            )}
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-slate-700/50 rounded-lg p-1">
          {[
            { id: 'goals', label: '목표', icon: '🎯' },
            { id: 'metrics', label: '지표', icon: '📊' },
            { id: 'history', label: '히스토리', icon: '📜' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors
                ${activeTab === tab.id
                  ? 'bg-slate-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                }`}
            >
              <span className="mr-1">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-4 max-h-[400px] overflow-y-auto">
        <AnimatePresence mode="wait">
          {activeTab === 'goals' && (
            <motion.div
              key="goals"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-3"
            >
              {/* Quick Stats */}
              <div className="grid grid-cols-3 gap-2 mb-4">
                <div className="bg-green-500/20 rounded-lg p-2 text-center">
                  <div className="text-2xl font-bold text-green-400">{stats.activeGoals}</div>
                  <div className="text-xs text-green-300">진행 중</div>
                </div>
                <div className="bg-blue-500/20 rounded-lg p-2 text-center">
                  <div className="text-2xl font-bold text-blue-400">{stats.completedGoals}</div>
                  <div className="text-xs text-blue-300">완료</div>
                </div>
                <div className="bg-purple-500/20 rounded-lg p-2 text-center">
                  <div className="text-2xl font-bold text-purple-400">{stats.completionRate.toFixed(0)}%</div>
                  <div className="text-xs text-purple-300">달성률</div>
                </div>
              </div>

              {/* Goals List */}
              {goals.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  <div className="text-4xl mb-2">🌱</div>
                  <p>아직 목표가 없어요</p>
                  <p className="text-sm">새 목표 생성 버튼을 눌러보세요!</p>
                </div>
              ) : (
                goals.filter(g => g.status === 'active').slice(0, 5).map((goal) => (
                  <motion.div
                    key={goal.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={`p-3 rounded-lg border border-slate-600 ${goalTypeConfig[goal.goal_type]?.bgColor || 'bg-slate-700/50'}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-lg">{goalTypeConfig[goal.goal_type]?.icon}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${goalTypeConfig[goal.goal_type]?.bgColor} ${goalTypeConfig[goal.goal_type]?.color}`}>
                            {goalTypeConfig[goal.goal_type]?.label}
                          </span>
                          {goal.domain && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-600 text-slate-300">
                              {domainIcons[goal.domain] || '📁'} {goal.domain}
                            </span>
                          )}
                        </div>
                        <p className="text-white text-sm">{goal.description}</p>
                        {goal.trigger_reason && (
                          <p className="text-slate-400 text-xs mt-1">💡 {goal.trigger_reason}</p>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-white">
                          {(goal.combined_motivation * 100).toFixed(0)}%
                        </div>
                        <div className="text-xs text-slate-400">동기</div>
                      </div>
                    </div>

                    {/* Motivation bars */}
                    <div className="mt-2 grid grid-cols-3 gap-1">
                      <div className="text-xs">
                        <div className="flex justify-between text-blue-400 mb-0.5">
                          <span>지식</span>
                          <span>{(goal.epistemic_score * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full transition-all"
                            style={{ width: `${goal.epistemic_score * 100}%` }}
                          />
                        </div>
                      </div>
                      <div className="text-xs">
                        <div className="flex justify-between text-purple-400 mb-0.5">
                          <span>다양성</span>
                          <span>{(goal.diversive_score * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-purple-500 rounded-full transition-all"
                            style={{ width: `${goal.diversive_score * 100}%` }}
                          />
                        </div>
                      </div>
                      <div className="text-xs">
                        <div className="flex justify-between text-orange-400 mb-0.5">
                          <span>능력</span>
                          <span>{(goal.empowerment_score * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-orange-500 rounded-full transition-all"
                            style={{ width: `${goal.empowerment_score * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))
              )}

              {/* Completed goals summary */}
              {stats.completedGoals > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-700">
                  <h4 className="text-sm font-medium text-slate-300 mb-2">
                    ✅ 완료된 목표 ({stats.completedGoals})
                  </h4>
                  <div className="space-y-1">
                    {goals.filter(g => g.status === 'completed').slice(0, 3).map((goal) => (
                      <div key={goal.id} className="text-xs text-slate-400 flex items-center gap-2">
                        <span>{goalTypeConfig[goal.goal_type]?.icon}</span>
                        <span className="line-through">{goal.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {activeTab === 'metrics' && (
            <motion.div
              key="metrics"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              {/* Curiosity Scores */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-slate-300">호기심 지표</h4>

                {/* Epistemic Curiosity */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-blue-400 flex items-center gap-2">
                      <span>🔬</span> 지식 탐구 (Epistemic)
                    </span>
                    <span className="text-white font-medium">
                      {((metrics?.epistemic_curiosity || 0.5) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(metrics?.epistemic_curiosity || 0.5) * 100}%` }}
                      className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full"
                    />
                  </div>
                  <p className="text-xs text-slate-500">무엇을 배울까? 지식에 대한 궁금증</p>
                </div>

                {/* Diversive Curiosity */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-purple-400 flex items-center gap-2">
                      <span>🌈</span> 다양성 추구 (Diversive)
                    </span>
                    <span className="text-white font-medium">
                      {((metrics?.diversive_curiosity || 0.5) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(metrics?.diversive_curiosity || 0.5) * 100}%` }}
                      className="h-full bg-gradient-to-r from-purple-600 to-purple-400 rounded-full"
                    />
                  </div>
                  <p className="text-xs text-slate-500">새로운 것을 시도할까? 변화에 대한 욕구</p>
                </div>

                {/* Empowerment Drive */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-orange-400 flex items-center gap-2">
                      <span>💪</span> 영향력 추구 (Empowerment)
                    </span>
                    <span className="text-white font-medium">
                      {((metrics?.empowerment_drive || 0.5) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(metrics?.empowerment_drive || 0.5) * 100}%` }}
                      className="h-full bg-gradient-to-r from-orange-600 to-orange-400 rounded-full"
                    />
                  </div>
                  <p className="text-xs text-slate-500">더 많은 것을 할 수 있게 될까? 능력 향상 욕구</p>
                </div>
              </div>

              {/* Overall Autonomy */}
              <div className="mt-6 p-4 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 rounded-lg border border-indigo-500/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-white font-medium">🚀 종합 자율성 점수</span>
                  <span className="text-2xl font-bold text-white">
                    {((metrics?.overall_autonomy || 0.5) * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-4 bg-slate-700 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(metrics?.overall_autonomy || 0.5) * 100}%` }}
                    className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-full"
                  />
                </div>
                <p className="text-xs text-slate-400 mt-2">
                  스스로 목표를 설정하고 학습을 주도하는 능력
                </p>
              </div>

              {/* Goal Distribution */}
              <div className="mt-4">
                <h4 className="text-sm font-medium text-slate-300 mb-3">목표 유형 분포</h4>
                <div className="flex gap-2">
                  <div className="flex-1 text-center p-3 bg-blue-500/20 rounded-lg">
                    <div className="text-2xl">🔬</div>
                    <div className="text-lg font-bold text-blue-400">{stats.epistemicGoals}</div>
                    <div className="text-xs text-blue-300">지식 탐구</div>
                  </div>
                  <div className="flex-1 text-center p-3 bg-purple-500/20 rounded-lg">
                    <div className="text-2xl">🌈</div>
                    <div className="text-lg font-bold text-purple-400">{stats.diversiveGoals}</div>
                    <div className="text-xs text-purple-300">다양성</div>
                  </div>
                  <div className="flex-1 text-center p-3 bg-orange-500/20 rounded-lg">
                    <div className="text-2xl">💪</div>
                    <div className="text-lg font-bold text-orange-400">{stats.empowermentGoals}</div>
                    <div className="text-xs text-orange-300">능력 향상</div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'history' && (
            <motion.div
              key="history"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-3"
            >
              <h4 className="text-sm font-medium text-slate-300 mb-3">최근 진행 기록</h4>

              {progress.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  <div className="text-4xl mb-2">📜</div>
                  <p>아직 진행 기록이 없어요</p>
                </div>
              ) : (
                progress.slice(0, 10).map((p) => (
                  <div
                    key={p.id}
                    className="p-3 bg-slate-700/50 rounded-lg border border-slate-600"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        p.outcome === 'success' ? 'bg-green-500/20 text-green-400' :
                        p.outcome === 'partial' ? 'bg-yellow-500/20 text-yellow-400' :
                        p.outcome === 'learning' ? 'bg-blue-500/20 text-blue-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        {p.outcome === 'success' ? '✅ 성공' :
                         p.outcome === 'partial' ? '🔄 부분 성공' :
                         p.outcome === 'learning' ? '📚 학습' : '❌ 실패'}
                      </span>
                      <span className="text-xs text-slate-500">
                        {new Date(p.created_at).toLocaleDateString('ko-KR')}
                      </span>
                    </div>
                    {p.insight && (
                      <p className="text-sm text-slate-300 mt-1">
                        💡 {p.insight}
                      </p>
                    )}
                    <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
                      <span>시도 #{p.attempt_number}</span>
                      <span>•</span>
                      <span>학습 +{(p.learning_gain * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Footer info */}
      <div className="px-4 py-2 bg-slate-900/50 border-t border-slate-700">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>CDALNs (2025) 기반 자율 학습</span>
          <span>총 {stats.totalGoals}개 목표</span>
        </div>
      </div>
    </div>
  )
}
