'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles,
  Search,
  Brain,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Lightbulb,
  TrendingUp,
  Zap,
  Globe,
  Database,
  BookOpen,
} from 'lucide-react'
import { supabase } from '@/lib/supabase'

interface CuriosityItem {
  id: string
  query: string
  query_type: string
  source: string
  priority: number
  status: string
  exploration_count: number
  created_at: string
  satisfaction_after?: number
}

interface ExplorationLog {
  id: string
  query: string
  exploration_method: string
  success: boolean
  relevance_score?: number
  novelty_score?: number
  created_at: string
  new_concepts_created?: string[]
  concepts_strengthened?: string[]
}

interface QueueStats {
  total: number
  byStatus: Record<string, number>
  bySource: Record<string, number>
}

interface CuriosityCardProps {
  className?: string
}

type TabType = 'queue' | 'exploring' | 'learned'

export function CuriosityCard({ className = '' }: CuriosityCardProps) {
  const [activeTab, setActiveTab] = useState<TabType>('queue')
  const [queue, setQueue] = useState<CuriosityItem[]>([])
  const [explorationLogs, setExplorationLogs] = useState<ExplorationLog[]>([])
  const [stats, setStats] = useState<QueueStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isExploring, setIsExploring] = useState(false)

  // Fetch data
  const fetchData = useCallback(async () => {
    setIsLoading(true)

    try {
      // Fetch queue
      // Using 'as any' because these tables aren't in the generated TypeScript types
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data: queueData } = await (supabase as any)
        .from('curiosity_queue')
        .select('*')
        .order('priority', { ascending: false })
        .order('created_at', { ascending: false })
        .limit(20) as { data: CuriosityItem[] | null }

      if (queueData) setQueue(queueData)

      // Fetch exploration logs
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data: logsData } = await (supabase as any)
        .from('exploration_logs')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(10) as { data: ExplorationLog[] | null }

      if (logsData) setExplorationLogs(logsData)

      // Calculate stats
      if (queueData) {
        const byStatus: Record<string, number> = {}
        const bySource: Record<string, number> = {}

        for (const item of queueData) {
          byStatus[item.status] = (byStatus[item.status] || 0) + 1
          bySource[item.source] = (bySource[item.source] || 0) + 1
        }

        setStats({
          total: queueData.length,
          byStatus,
          bySource,
        })
      }
    } catch (error) {
      console.error('Error fetching curiosity data:', error)
    }

    setIsLoading(false)
  }, [])

  // Generate curiosities
  const generateCuriosities = async () => {
    setIsGenerating(true)

    try {
      const response = await fetch('/api/curiosity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'generate' }),
      })

      const data = await response.json()
      if (data.success) {
        await fetchData()
      }
    } catch (error) {
      console.error('Error generating curiosities:', error)
    }

    setIsGenerating(false)
  }

  // Explore curiosities
  const exploreCuriosities = async () => {
    setIsExploring(true)

    try {
      const response = await fetch('/api/curiosity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'explore_batch', batch_size: 3 }),
      })

      const data = await response.json()
      if (data.success) {
        await fetchData()
      }
    } catch (error) {
      console.error('Error exploring curiosities:', error)
    }

    setIsExploring(false)
  }

  // Initial fetch
  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Realtime subscription
  useEffect(() => {
    const channel = supabase
      .channel('curiosity_changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'curiosity_queue' },
        () => fetchData()
      )
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'exploration_logs' },
        () => fetchData()
      )
      .subscribe()

    return () => {
      channel.unsubscribe()
    }
  }, [fetchData])

  const tabs: { key: TabType; label: string; icon: typeof Sparkles }[] = [
    { key: 'queue', label: '대기열', icon: Clock },
    { key: 'exploring', label: '탐색 중', icon: Search },
    { key: 'learned', label: '학습 완료', icon: CheckCircle2 },
  ]

  const sourceIcons: Record<string, typeof Brain> = {
    concept_gap: Brain,
    failure: XCircle,
    pattern: TrendingUp,
    similarity: Sparkles,
    temporal: Clock,
    emotional: Lightbulb,
  }

  const methodIcons: Record<string, typeof Globe> = {
    web_search: Globe,
    internal_graph: Database,
    memory_recall: BookOpen,
    pattern_match: Zap,
  }

  const sourceLabels: Record<string, string> = {
    concept_gap: '개념 갭',
    failure: '실패 경험',
    pattern: '패턴 발견',
    similarity: '유사도',
    temporal: '시간 기반',
    emotional: '감정 기반',
  }

  const pendingCount = stats?.byStatus?.pending || 0
  const exploringCount = stats?.byStatus?.exploring || 0
  const learnedCount = stats?.byStatus?.learned || 0

  return (
    <div
      className={`bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-amber-400" />
          <h3 className="text-lg font-semibold text-slate-100">자율적 호기심</h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300">
            Phase 8
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={generateCuriosities}
            disabled={isGenerating}
            className="p-2 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 transition-all disabled:opacity-50"
            title="호기심 생성"
          >
            <Lightbulb className={`w-4 h-4 ${isGenerating ? 'animate-pulse' : ''}`} />
          </button>
          <button
            onClick={exploreCuriosities}
            disabled={isExploring || pendingCount === 0}
            className="p-2 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 transition-all disabled:opacity-50"
            title="탐색 실행"
          >
            <Search className={`w-4 h-4 ${isExploring ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={fetchData}
            disabled={isLoading}
            className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-400 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="bg-slate-900/50 rounded-lg p-2 text-center">
          <p className="text-xs text-slate-500">대기</p>
          <p className="text-lg font-bold text-amber-400">{pendingCount}</p>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-2 text-center">
          <p className="text-xs text-slate-500">탐색 중</p>
          <p className="text-lg font-bold text-purple-400">{exploringCount}</p>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-2 text-center">
          <p className="text-xs text-slate-500">완료</p>
          <p className="text-lg font-bold text-emerald-400">{learnedCount}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex bg-slate-900/50 rounded-lg p-1 mb-4">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === tab.key
                ? 'bg-amber-500/30 text-amber-300'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            <tab.icon className="w-3.5 h-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <AnimatePresence mode="wait">
        {activeTab === 'queue' && (
          <motion.div
            key="queue"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-2"
          >
            {queue.filter((q) => q.status === 'pending').length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>대기 중인 호기심이 없습니다</p>
                <button
                  onClick={generateCuriosities}
                  className="mt-2 text-sm text-amber-400 hover:text-amber-300"
                >
                  호기심 생성하기
                </button>
              </div>
            ) : (
              queue
                .filter((q) => q.status === 'pending')
                .slice(0, 5)
                .map((item) => {
                  const SourceIcon = sourceIcons[item.source] || Sparkles
                  return (
                    <div
                      key={item.id}
                      className="bg-slate-900/30 rounded-lg p-3 border border-slate-700/30"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <SourceIcon className="w-4 h-4 text-amber-400" />
                          <span className="text-sm text-slate-200 font-medium">
                            {item.query}
                          </span>
                        </div>
                        <span
                          className="text-xs px-2 py-0.5 rounded-full"
                          style={{
                            backgroundColor: `rgba(251, 191, 36, ${item.priority * 0.3})`,
                            color: '#fbbf24',
                          }}
                        >
                          {Math.round(item.priority * 100)}%
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
                        <span className="px-1.5 py-0.5 rounded bg-slate-800">
                          {sourceLabels[item.source] || item.source}
                        </span>
                        <span>{item.query_type}</span>
                      </div>
                    </div>
                  )
                })
            )}
          </motion.div>
        )}

        {activeTab === 'exploring' && (
          <motion.div
            key="exploring"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-2"
          >
            {queue.filter((q) => q.status === 'exploring').length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>현재 탐색 중인 항목이 없습니다</p>
              </div>
            ) : (
              queue
                .filter((q) => q.status === 'exploring')
                .map((item) => (
                  <div
                    key={item.id}
                    className="bg-purple-500/10 rounded-lg p-3 border border-purple-500/30"
                  >
                    <div className="flex items-center gap-2">
                      <Search className="w-4 h-4 text-purple-400 animate-pulse" />
                      <span className="text-sm text-slate-200 font-medium">
                        {item.query}
                      </span>
                    </div>
                    <div className="mt-2 flex items-center gap-2">
                      <div className="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-purple-500"
                          animate={{ width: ['0%', '100%'] }}
                          transition={{ duration: 2, repeat: Infinity }}
                        />
                      </div>
                      <span className="text-xs text-purple-400">탐색 중...</span>
                    </div>
                  </div>
                ))
            )}
          </motion.div>
        )}

        {activeTab === 'learned' && (
          <motion.div
            key="learned"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-2"
          >
            {explorationLogs.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>아직 학습 기록이 없습니다</p>
              </div>
            ) : (
              explorationLogs.slice(0, 5).map((log) => {
                const MethodIcon = methodIcons[log.exploration_method] || Globe
                return (
                  <div
                    key={log.id}
                    className={`rounded-lg p-3 border ${
                      log.success
                        ? 'bg-emerald-500/10 border-emerald-500/30'
                        : 'bg-red-500/10 border-red-500/30'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <MethodIcon
                          className={`w-4 h-4 ${
                            log.success ? 'text-emerald-400' : 'text-red-400'
                          }`}
                        />
                        <span className="text-sm text-slate-200 font-medium">
                          {log.query}
                        </span>
                      </div>
                      {log.success ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-400" />
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                      <span className="px-1.5 py-0.5 rounded bg-slate-800">
                        {log.exploration_method}
                      </span>
                      {log.new_concepts_created && log.new_concepts_created.length > 0 && (
                        <span className="text-emerald-400">
                          +{log.new_concepts_created.length} 개념
                        </span>
                      )}
                      {log.relevance_score && (
                        <span>관련성: {Math.round(log.relevance_score * 100)}%</span>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Source Distribution */}
      {stats && stats.total > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-700/50">
          <p className="text-xs text-slate-500 mb-2">출처별 분포</p>
          <div className="flex gap-1">
            {Object.entries(stats.bySource).map(([source, count]) => {
              const SourceIcon = sourceIcons[source] || Sparkles
              const percentage = (count / stats.total) * 100
              return (
                <div
                  key={source}
                  className="flex items-center gap-1 px-2 py-1 rounded bg-slate-800/50 text-xs"
                  title={sourceLabels[source] || source}
                >
                  <SourceIcon className="w-3 h-3 text-amber-400" />
                  <span className="text-slate-400">{Math.round(percentage)}%</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
