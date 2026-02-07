'use client'

import { Suspense, useState, useCallback, useEffect } from 'react'
import { BrainVisualization } from '@/components/BrainVisualization'
import { RealisticBrain } from '@/components/RealisticBrain'
import { ImaginationPanel } from '@/components/ImaginationPanel'
import { PredictionVerifyPanel } from '@/components/PredictionVerifyPanel'
import { ArrowLeft, Brain, Sparkles, Target, Atom, Network } from 'lucide-react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { createClient } from '@supabase/supabase-js'
import type { DiscoveredConnection } from '@/hooks/useImaginationSessions'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://extbfhoktzozgqddjcps.supabase.co'
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

type PanelType = 'imagination' | 'prediction'
type BrainViewMode = 'abstract' | 'anatomical'

export default function BrainPage() {
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(false)
  const [activePanel, setActivePanel] = useState<PanelType>('imagination')
  const [highlightedConnection, setHighlightedConnection] = useState<DiscoveredConnection | null>(null)
  const [viewMode, setViewMode] = useState<BrainViewMode>('anatomical')
  const [developmentStage, setDevelopmentStage] = useState(2)

  // Fetch development stage
  useEffect(() => {
    supabase
      .from('baby_state')
      .select('development_stage')
      .single()
      .then(({ data }) => {
        if (data?.development_stage != null) {
          setDevelopmentStage(data.development_stage)
        }
      })
  }, [])

  const handleConnectionHover = useCallback((connection: DiscoveredConnection | null) => {
    setHighlightedConnection(connection)
  }, [])

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

        <div className="flex items-center gap-2">
          {/* Brain view mode toggle */}
          <div className="flex items-center gap-1 bg-slate-800/50 rounded-lg p-1">
            <button
              onClick={() => setViewMode('anatomical')}
              className={`p-2 rounded-lg transition-colors ${
                viewMode === 'anatomical'
                  ? 'bg-rose-500/20 text-rose-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
              title="해부학적 뇌 (영역 기반)"
            >
              <Atom className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('abstract')}
              className={`p-2 rounded-lg transition-colors ${
                viewMode === 'abstract'
                  ? 'bg-violet-500/20 text-violet-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
              title="추상 네트워크"
            >
              <Network className="w-4 h-4" />
            </button>
          </div>

          {/* Panel type toggle (desktop) */}
          <div className="hidden md:flex items-center gap-1 bg-slate-800/50 rounded-lg p-1">
            <button
              onClick={() => setActivePanel('imagination')}
              className={`p-2 rounded-lg transition-colors ${
                activePanel === 'imagination'
                  ? 'bg-violet-500/20 text-violet-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
              title="상상 세션"
            >
              <Sparkles className="w-4 h-4" />
            </button>
            <button
              onClick={() => setActivePanel('prediction')}
              className={`p-2 rounded-lg transition-colors ${
                activePanel === 'prediction'
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
              title="예측 검증"
            >
              <Target className="w-4 h-4" />
            </button>
          </div>

          {/* Panel open/close button (mobile) */}
          <button
            onClick={() => setIsPanelCollapsed(!isPanelCollapsed)}
            className="md:hidden p-2 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 transition-colors"
          >
            {activePanel === 'imagination' ? (
              <Sparkles className="w-5 h-5 text-violet-400" />
            ) : (
              <Target className="w-5 h-5 text-blue-400" />
            )}
          </button>
        </div>
      </header>

      {/* Main content with side panel */}
      <motion.main
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="flex-1 flex overflow-hidden"
      >
        {/* 3D Brain Visualization */}
        <div className="flex-1 p-4">
          <div className="h-[calc(100vh-120px)]">
            <Suspense fallback={
              <div className="h-full flex items-center justify-center">
                <div className="text-center">
                  <Brain className="w-12 h-12 text-violet-400 animate-pulse mx-auto mb-3" />
                  <p className="text-slate-400">뉴런 네트워크 로딩 중...</p>
                </div>
              </div>
            }>
              {viewMode === 'anatomical' ? (
                <RealisticBrain developmentStage={developmentStage} />
              ) : (
                <BrainVisualization
                  fullScreen
                  highlightedConnection={highlightedConnection}
                />
              )}
            </Suspense>
          </div>
        </div>

        {/* Side Panel (desktop) */}
        <AnimatePresence mode="wait">
          <div className="hidden md:block h-[calc(100vh-73px)]">
            {activePanel === 'imagination' ? (
              <ImaginationPanel
                isCollapsed={isPanelCollapsed}
                onToggleCollapse={() => setIsPanelCollapsed(!isPanelCollapsed)}
                onConnectionHover={handleConnectionHover}
                highlightedConnection={highlightedConnection}
              />
            ) : (
              <PredictionVerifyPanel
                isCollapsed={isPanelCollapsed}
                onToggleCollapse={() => setIsPanelCollapsed(!isPanelCollapsed)}
              />
            )}
          </div>
        </AnimatePresence>
      </motion.main>

      {/* Mobile panel overlay */}
      <AnimatePresence>
        {!isPanelCollapsed && (
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="md:hidden fixed inset-y-0 right-0 z-50 w-80 max-w-[90vw]"
          >
            {/* Mobile panel type toggle */}
            <div className="absolute top-4 left-4 flex items-center gap-1 bg-slate-800/80 backdrop-blur rounded-lg p-1 z-10">
              <button
                onClick={() => setActivePanel('imagination')}
                className={`p-2 rounded-lg transition-colors ${
                  activePanel === 'imagination'
                    ? 'bg-violet-500/20 text-violet-400'
                    : 'text-slate-400'
                }`}
              >
                <Sparkles className="w-4 h-4" />
              </button>
              <button
                onClick={() => setActivePanel('prediction')}
                className={`p-2 rounded-lg transition-colors ${
                  activePanel === 'prediction'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'text-slate-400'
                }`}
              >
                <Target className="w-4 h-4" />
              </button>
            </div>

            {activePanel === 'imagination' ? (
              <ImaginationPanel
                isCollapsed={false}
                onToggleCollapse={() => setIsPanelCollapsed(true)}
                onConnectionHover={handleConnectionHover}
                highlightedConnection={highlightedConnection}
              />
            ) : (
              <PredictionVerifyPanel
                isCollapsed={false}
                onToggleCollapse={() => setIsPanelCollapsed(true)}
              />
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mobile backdrop */}
      <AnimatePresence>
        {!isPanelCollapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="md:hidden fixed inset-0 bg-black/50 z-40"
            onClick={() => setIsPanelCollapsed(true)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
