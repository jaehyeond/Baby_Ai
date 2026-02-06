'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { Ear, EarOff, Loader2, Volume2 } from 'lucide-react'
import type { WakeWordState } from '@/hooks/useWakeWord'

interface WakeWordIndicatorProps {
  state: WakeWordState
  isSupported: boolean
  transcript: string
  error: string | null
  enabled: boolean
  onToggle: (enabled: boolean) => void
  className?: string
}

const STATE_CONFIG: Record<WakeWordState, { color: string; label: string; pulse: boolean }> = {
  OFF: { color: 'slate', label: '항상 듣기', pulse: false },
  LISTENING: { color: 'green', label: '듣고 있어요...', pulse: true },
  CAPTURING: { color: 'cyan', label: '', pulse: true },
  PROCESSING: { color: 'yellow', label: '처리 중...', pulse: false },
  SPEAKING: { color: 'orange', label: '말하는 중...', pulse: false },
}

function StateIcon({ state }: { state: WakeWordState }) {
  const className = 'w-4 h-4'
  switch (state) {
    case 'PROCESSING':
      return <Loader2 className={`${className} animate-spin`} />
    case 'SPEAKING':
      return <Volume2 className={className} />
    case 'OFF':
      return <EarOff className={className} />
    default:
      return <Ear className={className} />
  }
}

export function WakeWordIndicator({
  state,
  isSupported,
  transcript,
  error,
  enabled,
  onToggle,
  className = '',
}: WakeWordIndicatorProps) {
  const config = STATE_CONFIG[state]
  const isActive = state !== 'OFF'

  // Color classes
  const colorMap: Record<string, { bg: string; border: string; text: string; ring: string }> = {
    slate: { bg: 'bg-slate-800/50', border: 'border-slate-700/50', text: 'text-slate-400', ring: '' },
    green: { bg: 'bg-green-950/30', border: 'border-green-700/50', text: 'text-green-400', ring: 'ring-green-500/30' },
    cyan: { bg: 'bg-cyan-950/30', border: 'border-cyan-700/50', text: 'text-cyan-400', ring: 'ring-cyan-500/30' },
    yellow: { bg: 'bg-yellow-950/30', border: 'border-yellow-700/50', text: 'text-yellow-400', ring: '' },
    orange: { bg: 'bg-orange-950/30', border: 'border-orange-700/50', text: 'text-orange-400', ring: '' },
  }
  const colors = colorMap[config.color] || colorMap.slate

  if (!isSupported) {
    return (
      <div className={`flex items-center gap-3 px-4 py-2.5 rounded-xl bg-slate-800/30 border border-slate-700/30 ${className}`}>
        <EarOff className="w-4 h-4 text-slate-600" />
        <span className="text-xs text-slate-600 flex-1">이 브라우저에서 음성 인식을 지원하지 않습니다</span>
      </div>
    )
  }

  return (
    <div className={`flex items-center gap-3 px-4 py-2.5 rounded-xl border transition-all duration-300 ${colors.bg} ${colors.border} ${className}`}>
      {/* Icon with pulse */}
      <div className="relative">
        {config.pulse && (
          <motion.div
            className={`absolute inset-0 rounded-full ${colors.ring} ring-2`}
            animate={{ scale: [1, 1.8, 1], opacity: [0.6, 0, 0.6] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        )}
        <div className={colors.text}>
          <StateIcon state={state} />
        </div>
      </div>

      {/* Label / Transcript */}
      <div className="flex-1 min-w-0">
        <AnimatePresence mode="wait">
          {error ? (
            <motion.p
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-xs text-red-400 truncate"
            >
              {error}
            </motion.p>
          ) : state === 'CAPTURING' && transcript ? (
            <motion.p
              key="transcript"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-xs text-cyan-300 truncate font-medium"
            >
              &ldquo;{transcript}&rdquo;
            </motion.p>
          ) : (
            <motion.p
              key="label"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className={`text-xs ${isActive ? colors.text : 'text-slate-500'}`}
            >
              {config.label || '항상 듣기'}
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      {/* Toggle */}
      <button
        onClick={() => onToggle(!enabled)}
        className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${
          enabled ? 'bg-green-600' : 'bg-slate-700'
        }`}
        aria-label={enabled ? '항상 듣기 끄기' : '항상 듣기 켜기'}
      >
        <motion.div
          className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm"
          animate={{ x: enabled ? 20 : 0 }}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        />
      </button>
    </div>
  )
}
