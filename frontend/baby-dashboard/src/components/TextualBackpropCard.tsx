'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { createClient } from '@supabase/supabase-js'
import {
  Brain,
  Star,
  TrendingUp,
  TrendingDown,
  History,
  BarChart3,
  Zap,
  RefreshCw,
  ChevronRight,
  MessageSquare,
} from 'lucide-react'

// Types
interface FeedbackStats {
  total_feedbacks: number
  average_rating: number
  concepts_affected: number
  strategies_affected: number
  total_propagations: number
  rating_distribution: Record<number, number>
}

interface FeedbackHistoryItem {
  id: string
  experience_id: string
  rating: number
  feedback_text: string | null
  is_helpful: boolean | null
  is_accurate: boolean | null
  created_at: string
  propagation_count: number
}

interface PropagationImpact {
  target_type: string
  target_name: string
  field_name: string
  value_before: number
  value_after: number
  delta: number
  propagation_reason: string
}

interface TextualBackpropCardProps {
  className?: string
}

// Initialize Supabase client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
const supabase = createClient(supabaseUrl, supabaseKey)

export function TextualBackpropCard({ className = '' }: TextualBackpropCardProps) {
  const [stats, setStats] = useState<FeedbackStats | null>(null)
  const [history, setHistory] = useState<FeedbackHistoryItem[]>([])
  const [selectedFeedback, setSelectedFeedback] = useState<string | null>(null)
  const [impacts, setImpacts] = useState<PropagationImpact[]>([])
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'impact'>('overview')
  const [loading, setLoading] = useState(true)

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      const [statsRes, historyRes] = await Promise.all([
        fetch('/api/conversation/feedback?action=stats'),
        fetch('/api/conversation/feedback?action=history&limit=10'),
      ])

      const [statsData, historyData] = await Promise.all([
        statsRes.json(),
        historyRes.json(),
      ])

      if (statsData.success) setStats(statsData.stats)
      if (historyData.success) setHistory(historyData.feedbacks || [])

    } catch (error) {
      console.error('[TextualBackpropCard] Fetch error:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch impact for selected feedback
  const fetchImpact = useCallback(async (feedbackId: string) => {
    try {
      const res = await fetch(`/api/conversation/feedback?action=impact&feedback_id=${feedbackId}`)
      const data = await res.json()
      if (data.success) {
        setImpacts(data.impacts || [])
        setActiveTab('impact')
      }
    } catch (error) {
      console.error('[TextualBackpropCard] Impact fetch error:', error)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Setup realtime subscription
  useEffect(() => {
    const channel = supabase
      .channel('feedback_changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'response_feedback' }, () => {
        fetchData()
      })
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [fetchData])

  const handleFeedbackClick = (feedbackId: string) => {
    setSelectedFeedback(feedbackId)
    fetchImpact(feedbackId)
  }

  // Render stars
  const renderStars = (rating: number, size: 'sm' | 'md' = 'sm') => {
    const sizeClass = size === 'sm' ? 'w-3 h-3' : 'w-4 h-4'
    return (
      <div className="flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`${sizeClass} ${
              star <= rating ? 'text-yellow-400 fill-yellow-400' : 'text-slate-600'
            }`}
          />
        ))}
      </div>
    )
  }

  // Format delta with arrow
  const formatDelta = (delta: number) => {
    if (delta > 0) {
      return (
        <span className="flex items-center gap-1 text-emerald-400">
          <TrendingUp className="w-3 h-3" />
          +{(delta * 100).toFixed(1)}%
        </span>
      )
    } else if (delta < 0) {
      return (
        <span className="flex items-center gap-1 text-rose-400">
          <TrendingDown className="w-3 h-3" />
          {(delta * 100).toFixed(1)}%
        </span>
      )
    }
    return <span className="text-slate-500">0%</span>
  }

  if (loading) {
    return (
      <div className={`bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-6 border border-slate-700/50 ${className}`}>
        <div className="flex items-center justify-center h-48">
          <RefreshCw className="w-6 h-6 text-slate-400 animate-spin" />
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl border border-slate-700/50 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-slate-700/50">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
            <Brain className="w-5 h-5 text-amber-400" />
            Textual Backprop
          </h3>
          <button
            onClick={fetchData}
            className="p-1.5 rounded-lg bg-slate-700/50 hover:bg-slate-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4 text-slate-400" />
          </button>
        </div>
        <p className="text-xs text-slate-500 mt-1">피드백 기반 학습</p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-700/50">
        {[
          { id: 'overview', label: '개요', icon: BarChart3 },
          { id: 'history', label: '기록', icon: History },
          { id: 'impact', label: '영향', icon: Zap },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'text-amber-400 bg-amber-500/10 border-b-2 border-amber-400'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4">
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-700/30 rounded-xl p-3">
                  <p className="text-xs text-slate-500">총 피드백</p>
                  <p className="text-2xl font-bold text-slate-100">{stats?.total_feedbacks ?? 0}</p>
                </div>
                <div className="bg-slate-700/30 rounded-xl p-3">
                  <p className="text-xs text-slate-500">평균 평점</p>
                  <div className="flex items-center gap-2">
                    <p className="text-2xl font-bold text-slate-100">
                      {(stats?.average_rating ?? 0).toFixed(1)}
                    </p>
                    {renderStars(Math.round(stats?.average_rating ?? 0), 'md')}
                  </div>
                </div>
                <div className="bg-slate-700/30 rounded-xl p-3">
                  <p className="text-xs text-slate-500">개념 영향</p>
                  <p className="text-2xl font-bold text-emerald-400">{stats?.concepts_affected ?? 0}</p>
                </div>
                <div className="bg-slate-700/30 rounded-xl p-3">
                  <p className="text-xs text-slate-500">총 전파</p>
                  <p className="text-2xl font-bold text-cyan-400">{stats?.total_propagations ?? 0}</p>
                </div>
              </div>

              {/* Rating Distribution */}
              {stats?.rating_distribution && (
                <div className="bg-slate-700/30 rounded-xl p-3">
                  <p className="text-xs text-slate-500 mb-2">평점 분포</p>
                  <div className="space-y-1.5">
                    {[5, 4, 3, 2, 1].map((rating) => {
                      const count = stats.rating_distribution[rating] || 0
                      const total = stats.total_feedbacks || 1
                      const percentage = (count / total) * 100
                      return (
                        <div key={rating} className="flex items-center gap-2">
                          <span className="text-xs text-slate-400 w-8">{rating}점</span>
                          <div className="flex-1 h-2 bg-slate-600 rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${percentage}%` }}
                              className={`h-full ${
                                rating >= 4 ? 'bg-emerald-400' : rating === 3 ? 'bg-yellow-400' : 'bg-rose-400'
                              }`}
                            />
                          </div>
                          <span className="text-xs text-slate-500 w-8">{count}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* How it works */}
              <div className="bg-slate-700/20 rounded-xl p-3 border border-slate-600/30">
                <p className="text-xs text-slate-400 mb-2">작동 원리</p>
                <ol className="text-xs text-slate-500 space-y-1">
                  <li>1. 사용자가 Baby의 응답에 평점 제공</li>
                  <li>2. 평점에 따라 delta 계산 (1점: -15%, 5점: +20%)</li>
                  <li>3. 관련 개념/전략/기억력에 delta 전파</li>
                  <li>4. 피드백 텍스트에서 새 개념 추출</li>
                </ol>
              </div>
            </motion.div>
          )}

          {activeTab === 'history' && (
            <motion.div
              key="history"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-2"
            >
              {history.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">아직 피드백이 없습니다</p>
                </div>
              ) : (
                history.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => handleFeedbackClick(item.id)}
                    className={`w-full text-left p-3 rounded-xl transition-colors ${
                      selectedFeedback === item.id
                        ? 'bg-amber-500/20 border border-amber-500/30'
                        : 'bg-slate-700/30 hover:bg-slate-700/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      {renderStars(item.rating)}
                      <span className="text-xs text-slate-500">
                        {new Date(item.created_at).toLocaleDateString('ko-KR')}
                      </span>
                    </div>
                    {item.feedback_text && (
                      <p className="text-xs text-slate-400 truncate mb-1">
                        &quot;{item.feedback_text}&quot;
                      </p>
                    )}
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500">
                        {item.propagation_count}개 항목 업데이트
                      </span>
                      <ChevronRight className="w-3 h-3 text-slate-500" />
                    </div>
                  </button>
                ))
              )}
            </motion.div>
          )}

          {activeTab === 'impact' && (
            <motion.div
              key="impact"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-2"
            >
              {impacts.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <Zap className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">피드백을 선택하면 영향을 볼 수 있습니다</p>
                </div>
              ) : (
                impacts.map((impact, index) => (
                  <div
                    key={index}
                    className="p-3 bg-slate-700/30 rounded-xl"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        impact.target_type === 'concept' ? 'bg-purple-500/20 text-purple-400' :
                        impact.target_type === 'strategy' ? 'bg-cyan-500/20 text-cyan-400' :
                        'bg-amber-500/20 text-amber-400'
                      }`}>
                        {impact.target_type === 'concept' ? '개념' :
                         impact.target_type === 'strategy' ? '전략' : '경험'}
                      </span>
                      {formatDelta(impact.delta)}
                    </div>
                    <p className="text-sm text-slate-200 mb-1">
                      {impact.target_name || impact.field_name}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span>{(impact.value_before * 100).toFixed(0)}%</span>
                      <span>→</span>
                      <span className={impact.delta > 0 ? 'text-emerald-400' : impact.delta < 0 ? 'text-rose-400' : ''}>
                        {(impact.value_after * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
