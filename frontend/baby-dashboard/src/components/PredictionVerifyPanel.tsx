'use client'

import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Target,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronRight,
  ChevronLeft,
  TrendingUp,
  AlertCircle,
  Lightbulb,
  HelpCircle,
  Brain,
} from 'lucide-react'
import { usePredictions, ParsedPrediction, VerifyPredictionData } from '@/hooks/usePredictions'

// Domain colors
const DOMAIN_COLORS: Record<string, string> = {
  coding: '#3b82f6',
  emotion: '#ec4899',
  behavior: '#8b5cf6',
  learning: '#22c55e',
  social: '#f59e0b',
  감정: '#ec4899',
  대화: '#3b82f6',
  학습: '#22c55e',
}

// Prediction type labels
const PREDICTION_TYPE_LABELS: Record<string, { label: string; emoji: string }> = {
  outcome: { label: '결과 예측', emoji: '🎯' },
  behavior: { label: '행동 예측', emoji: '🤔' },
  emotion: { label: '감정 예측', emoji: '💜' },
  pattern: { label: '패턴 예측', emoji: '📊' },
  conversation: { label: '대화 예측', emoji: '💬' },
  learning: { label: '학습 예측', emoji: '📚' },
}

// Format relative time
function formatRelativeTime(date: Date | null): string {
  if (!date) return ''
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '방금 전'
  if (diffMins < 60) return `${diffMins}분 전`
  if (diffHours < 24) return `${diffHours}시간 전`
  if (diffDays < 7) return `${diffDays}일 전`
  return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
}

// Verification modal component
function VerifyModal({
  prediction,
  onSubmit,
  onClose,
}: {
  prediction: ParsedPrediction
  onSubmit: (data: VerifyPredictionData) => void
  onClose: () => void
}) {
  const [wasCorrect, setWasCorrect] = useState<boolean | null>(null)
  const [actualOutcome, setActualOutcome] = useState('')
  const [insightGained, setInsightGained] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (wasCorrect === null) return

    setIsSubmitting(true)
    onSubmit({
      wasCorrect,
      actualOutcome: actualOutcome.trim() || undefined,
      insightGained: insightGained.trim() || undefined,
    })
    setIsSubmitting(false)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="relative w-full max-w-md bg-slate-900 rounded-2xl shadow-2xl border border-slate-700/50 overflow-hidden"
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-violet-600 px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-white" />
            <span className="font-semibold text-white">예측 검증</span>
          </div>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white transition-colors p-1"
          >
            <XCircle className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          {/* Prediction display */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center shrink-0">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1">
                <p className="text-xs text-slate-400 mb-1">비비의 예측</p>
                <p className="text-sm text-white font-medium">{prediction.scenario}</p>
                <p className="text-xs text-slate-300 mt-2 bg-slate-700/30 rounded-lg p-2 border-l-2 border-violet-500">
                  {prediction.prediction}
                </p>
                <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
                  <span>확신도: {Math.round(prediction.confidence * 100)}%</span>
                  <span>·</span>
                  <span>{formatRelativeTime(prediction.createdAt)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Verification question */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-3">
              이 예측이 맞았나요?
            </label>
            <div className="flex gap-3">
              <button
                onClick={() => setWasCorrect(true)}
                className={`flex-1 py-3 px-4 rounded-xl flex items-center justify-center gap-2 transition-all ${
                  wasCorrect === true
                    ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/25'
                    : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50 border border-slate-700'
                }`}
              >
                <CheckCircle2 className="w-5 h-5" />
                <span className="font-medium">맞았어요</span>
              </button>
              <button
                onClick={() => setWasCorrect(false)}
                className={`flex-1 py-3 px-4 rounded-xl flex items-center justify-center gap-2 transition-all ${
                  wasCorrect === false
                    ? 'bg-red-500 text-white shadow-lg shadow-red-500/25'
                    : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50 border border-slate-700'
                }`}
              >
                <XCircle className="w-5 h-5" />
                <span className="font-medium">틀렸어요</span>
              </button>
            </div>
          </div>

          {/* Optional: Actual outcome */}
          {wasCorrect === false && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
            >
              <label className="block text-sm font-medium text-slate-300 mb-2">
                실제로는 어땠나요? (선택)
              </label>
              <textarea
                value={actualOutcome}
                onChange={(e) => setActualOutcome(e.target.value)}
                placeholder="실제 결과를 알려주시면 비비가 더 잘 배울 수 있어요..."
                rows={2}
                className="w-full px-4 py-2 bg-slate-800/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent resize-none text-sm"
              />
            </motion.div>
          )}

          {/* Optional: Insight */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              배운 점이 있나요? (선택)
            </label>
            <textarea
              value={insightGained}
              onChange={(e) => setInsightGained(e.target.value)}
              placeholder="이 경험에서 배운 점을 적어주세요..."
              rows={2}
              className="w-full px-4 py-2 bg-slate-800/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent resize-none text-sm"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="px-5 pb-5 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-3 px-4 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-xl transition-colors font-medium"
          >
            나중에
          </button>
          <button
            onClick={handleSubmit}
            disabled={wasCorrect === null || isSubmitting}
            className="flex-1 py-3 px-4 text-white bg-gradient-to-r from-blue-500 to-violet-500 hover:opacity-90 rounded-xl transition-opacity font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                저장 중...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                검증 완료
              </>
            )}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

// Prediction card component
function PredictionCard({
  prediction,
  onVerify,
  showVerifyButton = true,
}: {
  prediction: ParsedPrediction
  onVerify: () => void
  showVerifyButton?: boolean
}) {
  const typeConfig = PREDICTION_TYPE_LABELS[prediction.predictionType || 'outcome'] || {
    label: '예측',
    emoji: '🎯',
  }
  const domainColor = DOMAIN_COLORS[prediction.domain || ''] || '#64748b'

  const isVerified = prediction.wasCorrect !== null
  const isAutoVerified = prediction.autoVerified

  return (
    <motion.div
      className={`p-3 rounded-xl border transition-all ${
        isVerified
          ? prediction.wasCorrect
            ? 'bg-emerald-500/10 border-emerald-500/30'
            : 'bg-red-500/10 border-red-500/30'
          : 'bg-slate-800/50 border-slate-700/50 hover:bg-slate-700/50'
      }`}
      whileHover={{ scale: isVerified ? 1 : 1.01 }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          {/* Type badge */}
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs">{typeConfig.emoji}</span>
            <span className="text-xs text-slate-400">{typeConfig.label}</span>
            {prediction.domain && (
              <span
                className="text-xs px-1.5 py-0.5 rounded-full"
                style={{ backgroundColor: `${domainColor}20`, color: domainColor }}
              >
                {prediction.domain}
              </span>
            )}
            {/* v18: Auto-verified badge */}
            {isVerified && isAutoVerified && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400">
                🤖 자동
              </span>
            )}
          </div>

          {/* Scenario */}
          <p className="text-xs text-white font-medium line-clamp-2 mb-1">
            {prediction.scenario}
          </p>

          {/* Prediction */}
          <p className="text-xs text-slate-400 line-clamp-2">
            → {prediction.prediction}
          </p>

          {/* Meta */}
          <div className="flex items-center gap-2 mt-2 text-[10px] text-slate-500">
            <span className="flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              {Math.round(prediction.confidence * 100)}%
            </span>
            <span>·</span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatRelativeTime(prediction.createdAt)}
            </span>
          </div>
        </div>

        {/* Verify button or status */}
        <div className="shrink-0">
          {isVerified ? (
            <div
              className={`p-1.5 rounded-full ${
                prediction.wasCorrect ? 'bg-emerald-500/20' : 'bg-red-500/20'
              }`}
            >
              {prediction.wasCorrect ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400" />
              )}
            </div>
          ) : showVerifyButton ? (
            <button
              onClick={onVerify}
              className="p-2 bg-violet-500/20 hover:bg-violet-500/30 rounded-lg transition-colors"
              title="검증하기"
            >
              <HelpCircle className="w-4 h-4 text-violet-400" />
            </button>
          ) : (
            <div className="p-1.5 rounded-full bg-cyan-500/20" title="자동 검증 대기">
              <Clock className="w-4 h-4 text-cyan-400" />
            </div>
          )}
        </div>
      </div>

      {/* Verified info */}
      {isVerified && prediction.insightGained && (
        <div className="mt-2 pt-2 border-t border-slate-700/50">
          <div className="flex items-center gap-1 text-[10px] text-amber-400 mb-1">
            <Lightbulb className="w-3 h-3" />
            배운 점
          </div>
          <p className="text-xs text-slate-400">{prediction.insightGained}</p>
        </div>
      )}
    </motion.div>
  )
}

// Main panel component
interface PredictionVerifyPanelProps {
  isCollapsed?: boolean
  onToggleCollapse?: () => void
}

export function PredictionVerifyPanel({
  isCollapsed = false,
  onToggleCollapse,
}: PredictionVerifyPanelProps) {
  const {
    predictions,
    pendingPredictions,
    verifiedPredictions,
    manualPendingPredictions,
    autoVerifiedPredictions,
    isLoading,
    error,
    verifyPrediction,
    stats,
  } = usePredictions(50)

  const [verifyingPrediction, setVerifyingPrediction] = useState<ParsedPrediction | null>(null)
  const [showTab, setShowTab] = useState<'pending' | 'verified'>('pending')

  const handleVerify = useCallback(
    async (data: VerifyPredictionData) => {
      if (!verifyingPrediction) return
      await verifyPrediction(verifyingPrediction.id, data)
      setVerifyingPrediction(null)
    },
    [verifyingPrediction, verifyPrediction]
  )

  // Show manual pending + auto-waiting predictions in pending tab
  const displayedPredictions = showTab === 'pending' ? pendingPredictions : verifiedPredictions

  if (isCollapsed) {
    return (
      <motion.div
        initial={{ width: 0, opacity: 0 }}
        animate={{ width: 48, opacity: 1 }}
        exit={{ width: 0, opacity: 0 }}
        className="h-full bg-slate-900/80 backdrop-blur border-l border-slate-700/50 flex flex-col items-center py-4"
      >
        <button
          onClick={onToggleCollapse}
          className="p-2 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 transition-colors"
        >
          <ChevronLeft className="w-4 h-4 text-slate-400" />
        </button>
        <div className="mt-4 flex flex-col items-center gap-2">
          <Target className="w-5 h-5 text-blue-400" />
          <span className="text-xs text-slate-400 writing-vertical">예측</span>
        </div>
        <div className="mt-auto text-center">
          <div className="text-lg font-bold text-blue-400">{stats.pending}</div>
          <div className="text-[10px] text-slate-500">대기</div>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 320, opacity: 1 }}
      exit={{ width: 0, opacity: 0 }}
      className="h-full bg-slate-900/80 backdrop-blur border-l border-slate-700/50 flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-blue-500/20 rounded-lg">
            <Target className="w-4 h-4 text-blue-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">예측 검증</h2>
            <p className="text-[10px] text-slate-400">World Model Verification</p>
          </div>
        </div>
        <button
          onClick={onToggleCollapse}
          className="p-1.5 rounded-lg hover:bg-slate-700/50 transition-colors"
        >
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-4 gap-1 p-3 border-b border-slate-700/50 bg-slate-800/30">
        <div className="text-center">
          <div className="text-lg font-bold text-slate-400">{stats.total}</div>
          <div className="text-[10px] text-slate-500">전체</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-cyan-400">{stats.autoVerified}</div>
          <div className="text-[10px] text-slate-500">🤖 자동</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-emerald-400">{stats.correct}</div>
          <div className="text-[10px] text-slate-500">정답</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-blue-400">
            {stats.verified > 0 ? `${Math.round(stats.accuracy * 100)}%` : '-'}
          </div>
          <div className="text-[10px] text-slate-500">정확도</div>
        </div>
      </div>

      {/* Tab buttons */}
      <div className="flex p-2 gap-2 border-b border-slate-700/50">
        <button
          onClick={() => setShowTab('pending')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1 ${
            showTab === 'pending'
              ? 'bg-amber-500/20 text-amber-400'
              : 'text-slate-400 hover:bg-slate-700/50'
          }`}
        >
          <AlertCircle className="w-3 h-3" />
          검증 대기 ({pendingPredictions.length})
        </button>
        <button
          onClick={() => setShowTab('verified')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1 ${
            showTab === 'verified'
              ? 'bg-emerald-500/20 text-emerald-400'
              : 'text-slate-400 hover:bg-slate-700/50'
          }`}
        >
          <CheckCircle2 className="w-3 h-3" />
          검증 완료 ({verifiedPredictions.length})
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Target className="w-8 h-8 text-blue-400 animate-pulse mx-auto mb-2" />
              <p className="text-xs text-slate-400">예측 로딩 중...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center p-4">
            <p className="text-xs text-red-400 text-center">{error}</p>
          </div>
        ) : displayedPredictions.length === 0 ? (
          <div className="flex-1 flex items-center justify-center p-4">
            <div className="text-center">
              <Target className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400">
                {showTab === 'pending' ? '검증할 예측이 없어요' : '검증된 예측이 없어요'}
              </p>
              <p className="text-[10px] text-slate-500 mt-1">
                {showTab === 'pending'
                  ? '비비와 대화하면 예측이 자동 생성돼요'
                  : '대화 중 자동 검증 또는 수동 검증됩니다'}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar">
            {displayedPredictions.map((prediction) => (
              <PredictionCard
                key={prediction.id}
                prediction={prediction}
                onVerify={() => setVerifyingPrediction(prediction)}
                showVerifyButton={
                  prediction.wasCorrect === null &&
                  (prediction.verifiableAfter === 'manual' || prediction.verifiableAfter === null)
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Verify modal */}
      <AnimatePresence>
        {verifyingPrediction && (
          <VerifyModal
            prediction={verifyingPrediction}
            onSubmit={handleVerify}
            onClose={() => setVerifyingPrediction(null)}
          />
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default PredictionVerifyPanel
