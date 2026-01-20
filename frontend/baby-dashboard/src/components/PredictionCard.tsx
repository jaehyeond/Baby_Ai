'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useRecentPredictions } from '@/hooks/useWorldModel'
import type { Prediction } from '@/lib/database.types'

interface PredictionItemProps {
  prediction: Prediction
  index: number
}

function PredictionItem({ prediction, index }: PredictionItemProps) {
  const confidenceColor = prediction.confidence
    ? prediction.confidence > 0.7
      ? 'text-green-400'
      : prediction.confidence > 0.4
        ? 'text-yellow-400'
        : 'text-red-400'
    : 'text-gray-400'

  const statusIcon = prediction.was_correct === null
    ? '...' // pending
    : prediction.was_correct
      ? '...' // correct
      : '...' // incorrect

  const statusColor = prediction.was_correct === null
    ? 'bg-gray-500/20 text-gray-400'
    : prediction.was_correct
      ? 'bg-green-500/20 text-green-400'
      : 'bg-red-500/20 text-red-400'

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ delay: index * 0.05 }}
      className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50 hover:border-purple-500/30 transition-colors"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-300 truncate">
            {prediction.scenario}
          </p>
          <p className="text-xs text-purple-400 mt-1 line-clamp-2">
            {prediction.prediction}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor}`}>
            {statusIcon}
          </span>
          <span className={`text-xs ${confidenceColor}`}>
            {prediction.confidence ? `${Math.round(prediction.confidence * 100)}%` : '-'}
          </span>
        </div>
      </div>

      {prediction.reasoning && (
        <p className="text-xs text-slate-500 mt-2 italic line-clamp-1">
          {prediction.reasoning}
        </p>
      )}

      <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
        <span className="px-1.5 py-0.5 bg-slate-700/50 rounded">
          {prediction.prediction_type || 'outcome'}
        </span>
        <span>
          {prediction.created_at
            ? new Date(prediction.created_at).toLocaleTimeString('ko-KR', {
                hour: '2-digit',
                minute: '2-digit'
              })
            : ''}
        </span>
      </div>
    </motion.div>
  )
}

interface PredictionCardProps {
  className?: string
}

export function PredictionCard({ className = '' }: PredictionCardProps) {
  const { predictions, loading } = useRecentPredictions(5)

  return (
    <div className={`bg-slate-900/80 backdrop-blur-sm rounded-xl p-4 border border-slate-800 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Predictions</h3>
            <p className="text-xs text-slate-400">Baby AI's forecasts</p>
          </div>
        </div>
        <motion.div
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="text-2xl"
        >
          ...
        </motion.div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-slate-800/50 rounded-lg p-3 animate-pulse">
              <div className="h-4 bg-slate-700 rounded w-3/4 mb-2" />
              <div className="h-3 bg-slate-700 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : predictions.length === 0 ? (
        <div className="text-center py-8 text-slate-500">
          <p className="text-sm">No predictions yet</p>
          <p className="text-xs mt-1">Baby AI is learning to predict...</p>
        </div>
      ) : (
        <AnimatePresence mode="popLayout">
          <div className="space-y-2">
            {predictions.map((prediction, index) => (
              <PredictionItem
                key={prediction.id}
                prediction={prediction}
                index={index}
              />
            ))}
          </div>
        </AnimatePresence>
      )}
    </div>
  )
}
