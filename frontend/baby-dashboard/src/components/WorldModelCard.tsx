'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { useWorldModel } from '@/hooks/useWorldModel'

interface WorldModelCardProps {
  className?: string
}

export function WorldModelCard({ className = '' }: WorldModelCardProps) {
  const { predictionStats, predictions, imaginationSessions, loading } = useWorldModel()

  const recentPrediction = predictions[0]
  const activeSession = imaginationSessions.find(s => !s.ended_at)

  return (
    <Link href="/imagination">
      <motion.div
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={`bg-gradient-to-br from-indigo-900/50 to-purple-900/50 backdrop-blur-sm rounded-xl p-4 border border-indigo-700/30 cursor-pointer group ${className}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              {activeSession && (
                <motion.div
                  animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-slate-900"
                />
              )}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">World Model</h3>
              <p className="text-xs text-indigo-300">Imagination & Prediction</p>
            </div>
          </div>

          <motion.div
            animate={{ x: [0, 5, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="text-indigo-300 group-hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </motion.div>
        </div>

        {loading ? (
          <div className="space-y-3 animate-pulse">
            <div className="h-12 bg-slate-700/50 rounded-lg" />
            <div className="grid grid-cols-3 gap-2">
              <div className="h-16 bg-slate-700/50 rounded-lg" />
              <div className="h-16 bg-slate-700/50 rounded-lg" />
              <div className="h-16 bg-slate-700/50 rounded-lg" />
            </div>
          </div>
        ) : (
          <>
            {/* Prediction Stats */}
            <div className="grid grid-cols-3 gap-2 mb-4">
              <div className="bg-slate-800/50 rounded-lg p-2 text-center">
                <p className="text-2xl font-bold text-white">{predictionStats.total}</p>
                <p className="text-xs text-slate-400">Predictions</p>
              </div>
              <div className="bg-slate-800/50 rounded-lg p-2 text-center">
                <p className="text-2xl font-bold text-green-400">
                  {predictionStats.accuracy.toFixed(0)}%
                </p>
                <p className="text-xs text-slate-400">Accuracy</p>
              </div>
              <div className="bg-slate-800/50 rounded-lg p-2 text-center">
                <p className="text-2xl font-bold text-purple-400">
                  {imaginationSessions.length}
                </p>
                <p className="text-xs text-slate-400">Sessions</p>
              </div>
            </div>

            {/* Recent Activity */}
            {recentPrediction && (
              <div className="bg-slate-800/30 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs text-purple-400">Latest prediction</span>
                  {recentPrediction.was_correct !== null && (
                    <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                      recentPrediction.was_correct
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {recentPrediction.was_correct ? 'Correct' : 'Wrong'}
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-300 line-clamp-2">
                  {recentPrediction.scenario}
                </p>
              </div>
            )}

            {/* Active imagination indicator */}
            {activeSession && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-3 flex items-center gap-2 text-xs text-green-400"
              >
                <motion.span
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  className="w-2 h-2 bg-green-400 rounded-full"
                />
                Imagining: {activeSession.topic.slice(0, 30)}...
              </motion.div>
            )}
          </>
        )}

        {/* Hover effect */}
        <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-indigo-500/10 to-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
      </motion.div>
    </Link>
  )
}
