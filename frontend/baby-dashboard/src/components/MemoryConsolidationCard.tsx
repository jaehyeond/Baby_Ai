'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useIdleSleep } from '@/hooks'

const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000'

// Types
interface ConsolidationLog {
  id: string
  started_at: string
  completed_at: string | null
  trigger_type: 'scheduled' | 'idle' | 'manual'
  experiences_processed: number
  memories_strengthened: number
  memories_decayed: number
  patterns_promoted: number
  concepts_consolidated: number
  success: boolean
  processing_time_ms: number | null
  development_stage: number | null
  extras?: { semantic_links_created?: number }
}

interface ProceduralMemory {
  id: string
  pattern_name: string
  pattern_type: string
  pattern_description: string | null
  strength: number
  repetition_count: number
  success_rate: number
  activation_count: number
  last_activated_at: string | null
  created_at: string
}

interface ConsolidationStats {
  total_consolidations: number
  last_consolidation: string | null
  total_memories_strengthened: number
  total_memories_decayed: number
  total_patterns_promoted: number
  procedural_memory_count: number
  semantic_links_count: number
}

interface MemoryConsolidationCardProps {
  className?: string
}

// Pattern type icons
const patternTypeIcons: Record<string, string> = {
  conversation: '💬',
  action: '⚡',
  response: '💭',
}

export function MemoryConsolidationCard({ className = '' }: MemoryConsolidationCardProps) {
  const [logs, setLogs] = useState<ConsolidationLog[]>([])
  const [proceduralMemories, setProceduralMemories] = useState<ProceduralMemory[]>([])
  const [stats, setStats] = useState<ConsolidationStats | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'procedural' | 'history'>('overview')
  const [loading, setLoading] = useState(true)
  const [consolidating, setConsolidating] = useState(false)

  // Idle sleep hook - auto memory consolidation after 30 minutes of inactivity
  const { timeUntilSleep, isSleeping: isIdleSleeping, isIdle } = useIdleSleep({
    idleTimeoutMs: 30 * 60 * 1000, // 30 minutes
    enabled: true,
    onSleepStart: () => {
      console.log('[MemoryConsolidation] Idle sleep started')
    },
    onSleepComplete: (sleepStats) => {
      console.log('[MemoryConsolidation] Idle sleep complete:', sleepStats)
      fetchData() // Refresh data after sleep
    },
    onSleepError: (error) => {
      console.error('[MemoryConsolidation] Idle sleep error:', error)
    },
  })

  // Format time remaining
  const formatTimeRemaining = (ms: number): string => {
    const minutes = Math.floor(ms / 60000)
    const seconds = Math.floor((ms % 60000) / 1000)
    if (minutes > 0) {
      return `${minutes}분 ${seconds}초`
    }
    return `${seconds}초`
  }

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      const [logsRes, procRes, statsRes] = await Promise.all([
        fetch(`${FASTAPI_URL}/api/sleep-logs?limit=10`).then(r => r.ok ? r.json() : null),
        fetch(`${FASTAPI_URL}/api/procedural-memory?limit=10`).then(r => r.ok ? r.json() : null),
        fetch('/api/memory/consolidate').then(r => r.json()),
      ])

      if (logsRes?.logs) setLogs(logsRes.logs as ConsolidationLog[])
      if (procRes?.procedural_memories) setProceduralMemories(procRes.procedural_memories as ProceduralMemory[])
      if (statsRes?.stats) setStats(statsRes.stats)
    } catch (error) {
      console.error('[MemoryConsolidationCard] Fetch error:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Run consolidation
  const runConsolidation = async () => {
    setConsolidating(true)
    try {
      const response = await fetch('/api/memory/consolidate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'consolidate',
          trigger_type: 'manual',
        }),
      })

      if (response.ok) {
        await fetchData()
      }
    } catch (error) {
      console.error('[MemoryConsolidationCard] Consolidation error:', error)
    } finally {
      setConsolidating(false)
    }
  }

  // Format time
  const formatTime = (ms: number | null): string => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  // Format date
  const formatDate = (date: string | null): string => {
    if (!date) return '없음'
    const d = new Date(date)
    return d.toLocaleDateString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

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
            <span className="text-2xl">🌙</span>
            기억 통합
            <span className="text-xs bg-indigo-500/30 text-indigo-300 px-2 py-0.5 rounded-full">
              Phase 6
            </span>
          </h3>
          <button
            onClick={runConsolidation}
            disabled={consolidating}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-600
                       text-white text-sm rounded-lg transition-colors flex items-center gap-1"
          >
            {consolidating ? (
              <>
                <span className="animate-pulse">🌙</span>
                수면 중...
              </>
            ) : (
              <>
                <span>😴</span>
                수면 시작
              </>
            )}
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-slate-700/50 rounded-lg p-1">
          {[
            { id: 'overview', label: '개요', icon: '📊' },
            { id: 'procedural', label: '절차 기억', icon: '⚡' },
            { id: 'history', label: '기록', icon: '📜' },
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
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              {/* Quick Stats */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gradient-to-br from-indigo-500/20 to-purple-500/20 rounded-lg p-3 border border-indigo-500/30">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xl">🧠</span>
                    <span className="text-sm text-slate-300">총 통합 횟수</span>
                  </div>
                  <div className="text-3xl font-bold text-white">
                    {stats?.total_consolidations || 0}
                  </div>
                </div>
                <div className="bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-lg p-3 border border-blue-500/30">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xl">⚡</span>
                    <span className="text-sm text-slate-300">절차 기억</span>
                  </div>
                  <div className="text-3xl font-bold text-white">
                    {stats?.procedural_memory_count || 0}
                  </div>
                </div>
              </div>

              {/* Detailed Stats */}
              <div className="bg-slate-700/50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-slate-300 mb-3">통합 효과</h4>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400 flex items-center gap-2">
                      <span className="text-green-400">✨</span> 강화된 기억
                    </span>
                    <span className="text-white font-medium">
                      {stats?.total_memories_strengthened || 0}개
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400 flex items-center gap-2">
                      <span className="text-red-400">💨</span> 감쇠된 기억
                    </span>
                    <span className="text-white font-medium">
                      {stats?.total_memories_decayed || 0}개
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400 flex items-center gap-2">
                      <span className="text-purple-400">⬆️</span> 승격된 패턴
                    </span>
                    <span className="text-white font-medium">
                      {stats?.total_patterns_promoted || 0}개
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400 flex items-center gap-2">
                      <span className="text-blue-400">🔗</span> 의미 연결
                    </span>
                    <span className="text-white font-medium">
                      {stats?.semantic_links_count || 0}개
                    </span>
                  </div>
                </div>
              </div>

              {/* Last Consolidation Info */}
              <div className="bg-slate-700/30 rounded-lg p-3 border border-slate-600">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">마지막 수면</span>
                  <span className="text-sm text-white">
                    {formatDate(stats?.last_consolidation || null)}
                  </span>
                </div>
              </div>

              {/* How it works */}
              <div className="mt-4 p-3 bg-slate-700/30 rounded-lg border border-slate-600">
                <h4 className="text-sm font-medium text-slate-300 mb-2">💡 어떻게 작동하나요?</h4>
                <ul className="text-xs text-slate-400 space-y-1">
                  <li>• 감정이 강렬했던 경험 → 기억 강화</li>
                  <li>• 오래되고 안 쓰는 기억 → 점진적 감쇠</li>
                  <li>• 반복 패턴 → 절차적 기억으로 승격</li>
                  <li>• 유사 경험들 → 의미적 연결 생성</li>
                </ul>
              </div>
            </motion.div>
          )}

          {activeTab === 'procedural' && (
            <motion.div
              key="procedural"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-3"
            >
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-slate-300">학습된 패턴</h4>
                <span className="text-xs text-slate-500">
                  {proceduralMemories.length}개
                </span>
              </div>

              {proceduralMemories.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  <div className="text-4xl mb-2">⚡</div>
                  <p>아직 절차 기억이 없어요</p>
                  <p className="text-sm">반복되는 패턴이 발견되면 자동으로 학습돼요</p>
                </div>
              ) : (
                proceduralMemories.map((memory) => (
                  <motion.div
                    key={memory.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="p-3 bg-slate-700/50 rounded-lg border border-slate-600"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-lg">
                            {patternTypeIcons[memory.pattern_type] || '⚡'}
                          </span>
                          <span className="text-white font-medium text-sm">
                            {memory.pattern_name}
                          </span>
                          <span className="text-xs px-1.5 py-0.5 rounded bg-slate-600 text-slate-300">
                            {memory.pattern_type}
                          </span>
                        </div>
                        {memory.pattern_description && (
                          <p className="text-slate-400 text-xs mb-2">
                            {memory.pattern_description}
                          </p>
                        )}
                        <div className="flex items-center gap-3 text-xs text-slate-500">
                          <span>반복 {memory.repetition_count}회</span>
                          <span>•</span>
                          <span>활성화 {memory.activation_count}회</span>
                          <span>•</span>
                          <span>성공률 {(memory.success_rate * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-purple-400">
                          {(memory.strength * 100).toFixed(0)}%
                        </div>
                        <div className="text-xs text-slate-500">강도</div>
                      </div>
                    </div>

                    {/* Strength bar */}
                    <div className="mt-2 h-1.5 bg-slate-600 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${memory.strength * 100}%` }}
                        className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                      />
                    </div>
                  </motion.div>
                ))
              )}
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
              <h4 className="text-sm font-medium text-slate-300 mb-3">통합 기록</h4>

              {logs.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  <div className="text-4xl mb-2">📜</div>
                  <p>아직 통합 기록이 없어요</p>
                  <p className="text-sm">수면 시작 버튼을 눌러보세요!</p>
                </div>
              ) : (
                logs.map((log) => (
                  <div
                    key={log.id}
                    className={`p-3 rounded-lg border ${
                      log.success
                        ? 'bg-green-500/10 border-green-500/30'
                        : 'bg-red-500/10 border-red-500/30'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className={log.success ? 'text-green-400' : 'text-red-400'}>
                          {log.success ? '✅' : '❌'}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-600 text-slate-300">
                          {log.trigger_type === 'scheduled' ? '⏰ 예약' :
                           log.trigger_type === 'idle' ? '💤 유휴' : '👆 수동'}
                        </span>
                      </div>
                      <span className="text-xs text-slate-500">
                        {formatDate(log.completed_at)}
                      </span>
                    </div>

                    <div className="grid grid-cols-4 gap-2 text-xs">
                      <div className="text-center">
                        <div className="text-white font-medium">
                          {log.experiences_processed}
                        </div>
                        <div className="text-slate-500">처리</div>
                      </div>
                      <div className="text-center">
                        <div className="text-green-400 font-medium">
                          +{log.memories_strengthened}
                        </div>
                        <div className="text-slate-500">강화</div>
                      </div>
                      <div className="text-center">
                        <div className="text-red-400 font-medium">
                          -{log.memories_decayed}
                        </div>
                        <div className="text-slate-500">감쇠</div>
                      </div>
                      <div className="text-center">
                        <div className="text-purple-400 font-medium">
                          {log.patterns_promoted}
                        </div>
                        <div className="text-slate-500">패턴</div>
                      </div>
                    </div>

                    {log.processing_time_ms && (
                      <div className="mt-2 text-xs text-slate-500 text-right">
                        처리 시간: {formatTime(log.processing_time_ms)}
                      </div>
                    )}
                  </div>
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Idle Sleep Status */}
      <div className="px-4 py-2 bg-slate-800/50 border-t border-slate-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isIdleSleeping ? (
              <>
                <span className="animate-pulse text-lg">💤</span>
                <span className="text-sm text-indigo-300">자동 수면 중...</span>
              </>
            ) : isIdle ? (
              <>
                <span className="text-lg">😪</span>
                <span className="text-sm text-amber-300">유휴 상태 감지됨</span>
              </>
            ) : (
              <>
                <span className="text-lg">👀</span>
                <span className="text-sm text-slate-400">
                  자동 수면까지 {formatTimeRemaining(timeUntilSleep)}
                </span>
              </>
            )}
          </div>
          <div className="text-xs text-slate-500">
            {isIdle ? '⏰ idle' : '🟢 active'}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-2 bg-slate-900/50 border-t border-slate-700">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>인간 뇌의 수면 중 기억 통합 모방</span>
          <span>v2 (NO LLM)</span>
        </div>
      </div>
    </div>
  )
}
