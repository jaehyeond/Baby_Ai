'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles,
  Brain,
  Lightbulb,
  Link2,
  ChevronRight,
  ChevronLeft,
  Clock,
  Zap,
  MessageCircle,
} from 'lucide-react'
import { useImaginationSessions, ParsedImaginationSession, DiscoveredConnection } from '@/hooks/useImaginationSessions'

// Emotion color mapping
const EMOTION_COLORS: Record<string, string> = {
  joy: '#22c55e',
  surprise: '#f59e0b',
  curiosity: '#8b5cf6',
  fear: '#ef4444',
  frustration: '#f97316',
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

// Session card component
function SessionCard({
  session,
  isSelected,
  onClick,
}: {
  session: ParsedImaginationSession
  isSelected: boolean
  onClick: () => void
}) {
  const dominantEmotion = Object.entries(session.emotionalState)
    .sort((a, b) => b[1] - a[1])[0]

  return (
    <motion.button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg border transition-all ${
        isSelected
          ? 'bg-violet-500/20 border-violet-500/50'
          : 'bg-slate-800/50 border-slate-700/50 hover:bg-slate-700/50'
      }`}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-white truncate">
            {session.topic}
          </h4>
          <div className="flex items-center gap-2 mt-1 text-xs text-slate-400">
            <Clock className="w-3 h-3" />
            <span>{formatRelativeTime(session.startedAt)}</span>
            {dominantEmotion && (
              <>
                <span className="text-slate-600">·</span>
                <span
                  className="capitalize"
                  style={{ color: EMOTION_COLORS[dominantEmotion[0]] || '#94a3b8' }}
                >
                  {dominantEmotion[0]}
                </span>
              </>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="text-xs text-violet-400">
            {session.connectionsDiscovered.length} 연결
          </span>
          {session.insights.length > 0 && (
            <span className="text-xs text-amber-400">
              {session.insights.length} 통찰
            </span>
          )}
        </div>
      </div>
    </motion.button>
  )
}

// Connection badge component
function ConnectionBadge({
  connection,
  isHighlighted,
  onHover,
}: {
  connection: DiscoveredConnection
  isHighlighted: boolean
  onHover: (connection: DiscoveredConnection | null) => void
}) {
  return (
    <motion.div
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs cursor-pointer transition-colors ${
        isHighlighted
          ? 'bg-emerald-500/30 text-emerald-300 border border-emerald-500/50'
          : 'bg-slate-700/50 text-slate-300 border border-slate-600/50 hover:bg-slate-600/50'
      }`}
      onMouseEnter={() => onHover(connection)}
      onMouseLeave={() => onHover(null)}
      whileHover={{ scale: 1.05 }}
    >
      <span className="font-medium">{connection.from}</span>
      <Link2 className="w-3 h-3 text-slate-500" />
      <span className="font-medium">{connection.to}</span>
    </motion.div>
  )
}

// Session detail component
function SessionDetail({
  session,
  onConnectionHover,
  highlightedConnection,
}: {
  session: ParsedImaginationSession
  onConnectionHover: (connection: DiscoveredConnection | null) => void
  highlightedConnection: DiscoveredConnection | null
}) {
  const [showAllThoughts, setShowAllThoughts] = useState(false)
  const displayedThoughts = showAllThoughts
    ? session.thoughts
    : session.thoughts.slice(0, 3)

  return (
    <div className="space-y-4">
      {/* Topic header */}
      <div className="flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-violet-400" />
        <h3 className="text-sm font-semibold text-white">{session.topic}</h3>
      </div>

      {/* Emotional state */}
      {Object.keys(session.emotionalState).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(session.emotionalState)
            .sort((a, b) => b[1] - a[1])
            .map(([emotion, value]) => (
              <div
                key={emotion}
                className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs"
                style={{
                  backgroundColor: `${EMOTION_COLORS[emotion] || '#64748b'}20`,
                  color: EMOTION_COLORS[emotion] || '#94a3b8',
                }}
              >
                <span className="capitalize">{emotion}</span>
                <span className="opacity-70">{Math.round(value * 100)}%</span>
              </div>
            ))}
        </div>
      )}

      {/* Thoughts */}
      {session.thoughts.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <MessageCircle className="w-3 h-3" />
            <span>생각의 흐름 ({session.thoughts.length})</span>
          </div>
          <div className="space-y-2 max-h-40 overflow-y-auto pr-2 custom-scrollbar">
            {displayedThoughts.map((thought, idx) => (
              <div
                key={idx}
                className="text-xs text-slate-300 bg-slate-800/50 rounded-lg p-2 border-l-2 border-violet-500/50"
              >
                {thought.content}
              </div>
            ))}
          </div>
          {session.thoughts.length > 3 && (
            <button
              onClick={() => setShowAllThoughts(!showAllThoughts)}
              className="text-xs text-violet-400 hover:text-violet-300"
            >
              {showAllThoughts ? '접기' : `+${session.thoughts.length - 3}개 더 보기`}
            </button>
          )}
        </div>
      )}

      {/* Connections */}
      {session.connectionsDiscovered.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Link2 className="w-3 h-3" />
            <span>발견한 연결 ({session.connectionsDiscovered.length})</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {session.connectionsDiscovered.map((conn, idx) => (
              <ConnectionBadge
                key={idx}
                connection={conn}
                isHighlighted={
                  highlightedConnection?.from === conn.from &&
                  highlightedConnection?.to === conn.to
                }
                onHover={onConnectionHover}
              />
            ))}
          </div>
        </div>
      )}

      {/* Insights */}
      {session.insights.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Lightbulb className="w-3 h-3" />
            <span>통찰 ({session.insights.length})</span>
          </div>
          <div className="space-y-2">
            {session.insights.map((insight, idx) => (
              <div
                key={idx}
                className="text-xs text-amber-200 bg-amber-500/10 rounded-lg p-2 border border-amber-500/20"
              >
                {insight}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Meta info */}
      <div className="flex items-center gap-4 text-xs text-slate-500 pt-2 border-t border-slate-700/50">
        {session.trigger && (
          <span className="flex items-center gap-1">
            <Zap className="w-3 h-3" />
            {session.trigger}
          </span>
        )}
        {session.durationMs && (
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {Math.round(session.durationMs / 1000)}초
          </span>
        )}
      </div>
    </div>
  )
}

// Main panel component
interface ImaginationPanelProps {
  isCollapsed?: boolean
  onToggleCollapse?: () => void
  onConnectionHover?: (connection: DiscoveredConnection | null) => void
  highlightedConnection?: DiscoveredConnection | null
}

export function ImaginationPanel({
  isCollapsed = false,
  onToggleCollapse,
  onConnectionHover,
  highlightedConnection = null,
}: ImaginationPanelProps) {
  const {
    sessions,
    isLoading,
    error,
    selectedSession,
    setSelectedSession,
    stats,
  } = useImaginationSessions(20)

  const handleConnectionHover = (connection: DiscoveredConnection | null) => {
    onConnectionHover?.(connection)
  }

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
          <Sparkles className="w-5 h-5 text-violet-400" />
          <span className="text-xs text-slate-400 writing-vertical">상상</span>
        </div>
        <div className="mt-auto text-center">
          <div className="text-lg font-bold text-violet-400">{stats.totalSessions}</div>
          <div className="text-[10px] text-slate-500">세션</div>
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
          <div className="p-1.5 bg-violet-500/20 rounded-lg">
            <Sparkles className="w-4 h-4 text-violet-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">상상 세션</h2>
            <p className="text-[10px] text-slate-400">World Model Imagination</p>
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
      <div className="grid grid-cols-3 gap-2 p-3 border-b border-slate-700/50 bg-slate-800/30">
        <div className="text-center">
          <div className="text-lg font-bold text-violet-400">{stats.totalSessions}</div>
          <div className="text-[10px] text-slate-500">세션</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-emerald-400">{stats.totalConnections}</div>
          <div className="text-[10px] text-slate-500">연결</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-amber-400">{stats.totalInsights}</div>
          <div className="text-[10px] text-slate-500">통찰</div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Brain className="w-8 h-8 text-violet-400 animate-pulse mx-auto mb-2" />
              <p className="text-xs text-slate-400">상상 세션 로딩 중...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center p-4">
            <p className="text-xs text-red-400 text-center">{error}</p>
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex-1 flex items-center justify-center p-4">
            <div className="text-center">
              <Sparkles className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400">아직 상상 세션이 없어요</p>
              <p className="text-[10px] text-slate-500 mt-1">
                비비가 쉴 때 상상을 시작해요
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Session list */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar">
              {sessions.map((session) => (
                <SessionCard
                  key={session.id}
                  session={session}
                  isSelected={selectedSession?.id === session.id}
                  onClick={() => setSelectedSession(session)}
                />
              ))}
            </div>

            {/* Selected session detail */}
            <AnimatePresence>
              {selectedSession && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-t border-slate-700/50 bg-slate-800/30 max-h-[40%] overflow-y-auto"
                >
                  <div className="p-3">
                    <SessionDetail
                      session={selectedSession}
                      onConnectionHover={handleConnectionHover}
                      highlightedConnection={highlightedConnection}
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </div>
    </motion.div>
  )
}

export default ImaginationPanel
