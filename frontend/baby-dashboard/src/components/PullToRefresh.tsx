'use client'

import { RefreshCw } from 'lucide-react'
import { motion } from 'framer-motion'

interface PullToRefreshProps {
  pullDistance: number
  isRefreshing: boolean
  progress: number
}

export function PullToRefresh({ pullDistance, isRefreshing, progress }: PullToRefreshProps) {
  if (pullDistance === 0 && !isRefreshing) return null

  return (
    <motion.div
      className="fixed top-0 left-0 right-0 flex justify-center z-40 pointer-events-none"
      style={{ paddingTop: `${Math.max(pullDistance - 20, 0)}px` }}
    >
      <motion.div
        className={`p-3 rounded-full shadow-lg ${
          isRefreshing || progress >= 1
            ? 'bg-indigo-500'
            : 'bg-slate-700'
        }`}
        animate={{
          scale: isRefreshing ? [1, 1.1, 1] : 1,
        }}
        transition={{
          repeat: isRefreshing ? Infinity : 0,
          duration: 0.6,
        }}
      >
        <RefreshCw
          className={`w-6 h-6 text-white transition-transform ${
            isRefreshing ? 'animate-spin' : ''
          }`}
          style={{
            transform: isRefreshing ? undefined : `rotate(${progress * 360}deg)`,
            opacity: Math.max(progress, 0.3),
          }}
        />
      </motion.div>
    </motion.div>
  )
}
