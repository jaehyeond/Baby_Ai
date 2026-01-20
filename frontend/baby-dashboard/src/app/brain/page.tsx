'use client'

import { Suspense } from 'react'
import { BrainVisualization } from '@/components/BrainVisualization'
import { ArrowLeft, Brain } from 'lucide-react'
import Link from 'next/link'
import { motion } from 'framer-motion'

export default function BrainPage() {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between p-4 border-b border-slate-800/50">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="p-2 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </Link>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-violet-500/20 rounded-lg">
              <Brain className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-slate-100">뉴런 네트워크</h1>
              <p className="text-xs text-slate-400">Baby AI의 뇌 구조 시각화</p>
            </div>
          </div>
        </div>
      </header>

      {/* Full-screen Brain Visualization */}
      <motion.main
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="flex-1 p-4"
      >
        <div className="h-full">
          <BrainVisualizationFullScreen />
        </div>
      </motion.main>
    </div>
  )
}

// Full-screen version of brain visualization
function BrainVisualizationFullScreen() {
  return (
    <div className="h-[calc(100vh-120px)]">
      <Suspense fallback={
        <div className="h-full flex items-center justify-center">
          <div className="text-center">
            <Brain className="w-12 h-12 text-violet-400 animate-pulse mx-auto mb-3" />
            <p className="text-slate-400">뉴런 네트워크 로딩 중...</p>
          </div>
        </div>
      }>
        <BrainVisualization fullScreen />
      </Suspense>
    </div>
  )
}
