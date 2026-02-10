'use client'

import { Suspense, useState, useCallback, useEffect, Fragment } from 'react'
import { BrainVisualization } from '@/components/BrainVisualization'
import { RealisticBrain } from '@/components/RealisticBrain'
import { ImaginationPanel } from '@/components/ImaginationPanel'
import { PredictionVerifyPanel } from '@/components/PredictionVerifyPanel'
import { ArrowLeft, Brain, Sparkles, Target, Atom, Network, MessageCircle, ChevronDown, ChevronUp, ArrowRight } from 'lucide-react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { createClient } from '@supabase/supabase-js'
import type { DiscoveredConnection } from '@/hooks/useImaginationSessions'
import { useNeuronActivations, type ThoughtStep } from '@/hooks/useNeuronActivations'

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

  // Thought process data for abstract view overlay
  const { activeRegions, isReplaying, activationContext, thoughtProcess } = useNeuronActivations()

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
              title="뇌 구조도 (9개 영역 기반)"
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
              title="신경망 (뉴런 + 시냅스)"
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
          <div className="h-[calc(100vh-120px)] relative">
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

            {/* Thought Process overlay for abstract view (anatomical view has its own) */}
            {viewMode === 'abstract' && (
              <PageThoughtProcessPanel
                thoughtProcess={thoughtProcess}
                activationContext={activationContext}
                isActive={activeRegions.size > 0 || isReplaying}
              />
            )}
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

// ── Thought Process Panel (shared between views) ─────────

function PageThoughtProcessPanel({
  thoughtProcess,
  activationContext,
  isActive,
}: {
  thoughtProcess: ThoughtStep[]
  activationContext: { userMessage: string; aiResponse: string; emotion: string } | null
  isActive: boolean
}) {
  const [expanded, setExpanded] = useState(false)

  if (!isActive || !thoughtProcess || thoughtProcess.length === 0) return null

  const directSteps = thoughtProcess.filter(s => s.triggerType === 'conversation')
  const spreadSteps = thoughtProcess.filter(s => s.triggerType === 'spreading_activation')

  // Flow chain: sort direct steps by timestamp
  const sortedDirect = [...directSteps].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  )

  // Region groups: group spreading steps by region
  const regionGroups = new Map<string, ThoughtStep[]>()
  for (const step of spreadSteps) {
    const existing = regionGroups.get(step.regionName) || []
    existing.push(step)
    regionGroups.set(step.regionName, existing)
  }
  for (const [key, steps] of regionGroups) {
    regionGroups.set(key, steps.sort((a, b) => b.intensity - a.intensity))
  }
  const regionEntries = Array.from(regionGroups.entries())
  const displayRegions = expanded ? regionEntries : regionEntries.slice(0, 4)
  const hiddenRegionCount = regionEntries.length - displayRegions.length

  return (
    <div className="absolute bottom-4 left-4 max-w-[380px] bg-slate-900/95 backdrop-blur-md rounded-xl border border-violet-500/30 overflow-hidden z-20">
      {/* Header: conversation context */}
      {activationContext && (
        <div className="px-3 pt-2.5 pb-2 border-b border-slate-700/50">
          <div className="flex items-center gap-1.5 mb-1.5">
            <MessageCircle className="w-3 h-3 text-violet-400 flex-shrink-0" />
            <p className="text-[10px] text-violet-400 font-medium">파동의 원인</p>
            {activationContext.emotion && (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300">
                {activationContext.emotion}
              </span>
            )}
          </div>
          <div className="space-y-0.5">
            <p className="text-[11px] text-slate-300 line-clamp-1">
              <span className="text-slate-500">형아:</span> &quot;{activationContext.userMessage}&quot;
            </p>
            <p className="text-[11px] text-violet-300/80 line-clamp-1">
              <span className="text-slate-500">비비:</span> &quot;{activationContext.aiResponse}&quot;
            </p>
          </div>
        </div>
      )}

      {/* Flow chain: direct activations as connected path */}
      <div className="px-3 py-2">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-amber-400" />
            <p className="text-[10px] text-amber-400 font-medium">생각 경로</p>
            <span className="text-[9px] text-slate-500">{thoughtProcess.length}개 개념</span>
          </div>
        </div>

        {sortedDirect.length > 0 && (
          <div className="flex items-center gap-0.5 overflow-x-auto pb-1.5 scrollbar-thin">
            {sortedDirect.map((step, i) => (
              <Fragment key={`flow-${i}`}>
                {i > 0 && (
                  <ArrowRight className="w-3 h-3 text-amber-500/40 flex-shrink-0" />
                )}
                <div className="flex-shrink-0 text-center">
                  <div
                    className="px-1.5 py-0.5 rounded-md bg-amber-500/15 border border-amber-500/30 text-amber-300 text-[11px] font-medium whitespace-nowrap"
                    style={{ opacity: 0.5 + step.intensity * 0.5 }}
                  >
                    {step.conceptName}
                  </div>
                  <span className="text-[8px] text-slate-500 leading-none">{step.regionName}</span>
                </div>
              </Fragment>
            ))}
          </div>
        )}
      </div>

      {/* Region groups: spreading activations grouped by brain region */}
      {spreadSteps.length > 0 && (
        <div className="px-3 pb-2">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <div className="flex-1 h-px bg-slate-700/50" />
              <div className="flex items-center gap-1">
                <Brain className="w-2.5 h-2.5 text-violet-400" />
                <span className="text-[9px] text-violet-400 font-medium">연상 확산</span>
              </div>
              <div className="flex-1 h-px bg-slate-700/50" />
            </div>
            {regionEntries.length > 4 && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-[9px] text-slate-400 hover:text-slate-300 flex items-center gap-0.5 ml-2"
              >
                {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                {expanded ? '접기' : `+${hiddenRegionCount}개 영역`}
              </button>
            )}
          </div>

          <div className={`space-y-1 ${expanded ? 'max-h-[140px] overflow-y-auto' : ''}`}>
            {displayRegions.map(([region, steps]) => (
              <div key={region} className="flex items-start gap-1.5">
                <span className="text-[9px] text-violet-400/70 w-16 flex-shrink-0 text-right pt-0.5 truncate">
                  {region}
                </span>
                <div className="flex flex-wrap gap-1 flex-1 min-w-0">
                  {steps.slice(0, expanded ? 10 : 4).map((s, i) => (
                    <span
                      key={i}
                      className="text-[10px] text-slate-400 px-1 py-0.5 rounded bg-slate-800/80 whitespace-nowrap"
                      style={{ opacity: 0.4 + s.intensity * 0.6 }}
                    >
                      {s.conceptName}
                    </span>
                  ))}
                  {steps.length > (expanded ? 10 : 4) && (
                    <span className="text-[9px] text-slate-600 pt-0.5">
                      +{steps.length - (expanded ? 10 : 4)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
