'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Link from 'next/link'
import { useWorldModel } from '@/hooks/useWorldModel'
import {
  PredictionCard,
  ImaginationVisualizer,
  CausalGraph
} from '@/components'

type TabType = 'overview' | 'predictions' | 'simulations' | 'causal'

export default function ImaginationPage() {
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const {
    predictions,
    simulations,
    predictionStats,
    causalGraph,
    imaginationSessions,
    loading,
    error,
    refresh
  } = useWorldModel()

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'overview', label: 'Overview', icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z' },
    { id: 'predictions', label: 'Predictions', icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z' },
    { id: 'simulations', label: 'Simulations', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
    { id: 'causal', label: 'Causal Graph', icon: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1' }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950/30 to-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-lg border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-4 pt-8 pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="text-slate-400 hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </Link>
              <div className="flex items-center gap-3">
                <motion.div
                  animate={{ rotate: [0, 360] }}
                  transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
                  className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center"
                >
                  <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </motion.div>
                <div>
                  <h1 className="text-xl font-bold text-white">World Model</h1>
                  <p className="text-xs text-indigo-300">Baby AI's Imagination & Prediction</p>
                </div>
              </div>
            </div>

            <button
              onClick={refresh}
              className="p-2 rounded-lg bg-slate-800/50 text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mt-4 overflow-x-auto pb-2">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-800/50 text-slate-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={tab.icon} />
                </svg>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
            {error}
          </div>
        )}

        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-6"
            >
              {/* Stats Row */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  title="Total Predictions"
                  value={predictionStats.total}
                  icon="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  color="purple"
                />
                <StatCard
                  title="Accuracy"
                  value={`${predictionStats.accuracy.toFixed(1)}%`}
                  icon="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  color="green"
                />
                <StatCard
                  title="Simulations"
                  value={simulations.length}
                  icon="M13 10V3L4 14h7v7l9-11h-7z"
                  color="yellow"
                />
                <StatCard
                  title="Imagination Sessions"
                  value={imaginationSessions.length}
                  icon="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  color="blue"
                />
              </div>

              {/* Main Content */}
              <div className="grid lg:grid-cols-2 gap-6">
                <PredictionCard />
                <ImaginationVisualizer />
              </div>

              {/* Causal Graph Preview */}
              <div className="bg-slate-900/80 backdrop-blur-sm rounded-xl p-6 border border-slate-800">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white">Causal Network</h3>
                  <button
                    onClick={() => setActiveTab('causal')}
                    className="text-sm text-indigo-400 hover:text-indigo-300"
                  >
                    View full graph
                  </button>
                </div>
                <div className="h-[300px]">
                  <CausalGraph data={causalGraph} height={280} />
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'predictions' && (
            <motion.div
              key="predictions"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4"
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white">All Predictions</h2>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-green-400">{predictionStats.correct} correct</span>
                  <span className="text-red-400">{predictionStats.incorrect} incorrect</span>
                  <span className="text-slate-400">{predictionStats.pending} pending</span>
                </div>
              </div>

              {loading ? (
                <div className="grid gap-4">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="bg-slate-800/50 rounded-lg p-4 animate-pulse">
                      <div className="h-4 bg-slate-700 rounded w-3/4 mb-2" />
                      <div className="h-3 bg-slate-700 rounded w-1/2" />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid gap-4">
                  {predictions.map((prediction, index) => (
                    <PredictionDetailCard key={prediction.id} prediction={prediction} index={index} />
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {activeTab === 'simulations' && (
            <motion.div
              key="simulations"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4"
            >
              <h2 className="text-xl font-semibold text-white mb-4">Simulations</h2>

              {simulations.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-500">
                  <motion.div
                    animate={{ y: [0, -10, 0] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="text-5xl mb-4"
                  >
                    ...
                  </motion.div>
                  <p className="text-lg">No simulations yet</p>
                  <p className="text-sm mt-1">Baby AI hasn't run any what-if scenarios</p>
                </div>
              ) : (
                <div className="grid gap-4">
                  {simulations.map((sim, index) => (
                    <SimulationCard key={sim.id} simulation={sim} index={index} />
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {activeTab === 'causal' && (
            <motion.div
              key="causal"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="bg-slate-900/80 backdrop-blur-sm rounded-xl p-6 border border-slate-800"
            >
              <h2 className="text-xl font-semibold text-white mb-4">Causal Relationship Graph</h2>
              <p className="text-sm text-slate-400 mb-6">
                Discovered cause-and-effect relationships between concepts
              </p>
              <div className="h-[500px]">
                <CausalGraph data={causalGraph} height={480} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}

// Helper components
function StatCard({ title, value, icon, color }: {
  title: string
  value: string | number
  icon: string
  color: 'purple' | 'green' | 'yellow' | 'blue'
}) {
  const colorClasses = {
    purple: 'from-purple-500 to-indigo-500 text-purple-400',
    green: 'from-green-500 to-emerald-500 text-green-400',
    yellow: 'from-yellow-500 to-orange-500 text-yellow-400',
    blue: 'from-blue-500 to-cyan-500 text-blue-400'
  }

  return (
    <div className="bg-slate-900/80 backdrop-blur-sm rounded-xl p-4 border border-slate-800">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${colorClasses[color].split(' ').slice(0, 2).join(' ')} flex items-center justify-center`}>
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={icon} />
          </svg>
        </div>
        <div>
          <p className={`text-2xl font-bold ${colorClasses[color].split(' ').pop()}`}>{value}</p>
          <p className="text-xs text-slate-500">{title}</p>
        </div>
      </div>
    </div>
  )
}

function PredictionDetailCard({ prediction, index }: { prediction: any; index: number }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="bg-slate-900/80 backdrop-blur-sm rounded-xl p-4 border border-slate-800 cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <p className="text-white font-medium">{prediction.scenario}</p>
          <p className="text-sm text-purple-400 mt-1">{prediction.prediction}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`text-xs px-2 py-0.5 rounded-full ${
            prediction.was_correct === null
              ? 'bg-gray-500/20 text-gray-400'
              : prediction.was_correct
                ? 'bg-green-500/20 text-green-400'
                : 'bg-red-500/20 text-red-400'
          }`}>
            {prediction.was_correct === null ? 'Pending' : prediction.was_correct ? 'Correct' : 'Wrong'}
          </span>
          <span className="text-xs text-slate-500">
            {Math.round((prediction.confidence || 0) * 100)}% confidence
          </span>
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-4 pt-4 border-t border-slate-700/50 space-y-2 text-sm">
              {prediction.reasoning && (
                <div>
                  <span className="text-slate-500">Reasoning: </span>
                  <span className="text-slate-300">{prediction.reasoning}</span>
                </div>
              )}
              {prediction.actual_outcome && (
                <div>
                  <span className="text-slate-500">Actual outcome: </span>
                  <span className="text-slate-300">{prediction.actual_outcome}</span>
                </div>
              )}
              {prediction.insight_gained && (
                <div>
                  <span className="text-slate-500">Insight: </span>
                  <span className="text-yellow-400">{prediction.insight_gained}</span>
                </div>
              )}
              <div className="flex items-center gap-4 text-xs text-slate-500 mt-2">
                <span>Type: {prediction.prediction_type || 'outcome'}</span>
                {prediction.domain && <span>Domain: {prediction.domain}</span>}
                <span>{new Date(prediction.created_at).toLocaleString('ko-KR')}</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function SimulationCard({ simulation, index }: { simulation: any; index: number }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="bg-slate-900/80 backdrop-blur-sm rounded-xl p-4 border border-slate-800 cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded text-xs">
              {simulation.simulation_type || 'what_if'}
            </span>
            {simulation.was_validated && (
              <span className="px-2 py-0.5 bg-green-500/20 text-green-400 rounded text-xs">
                Validated
              </span>
            )}
          </div>
          <p className="text-white font-medium">{simulation.target_goal || 'Exploration'}</p>
        </div>
        <div className="text-right">
          {simulation.success_probability && (
            <p className="text-lg font-bold text-green-400">
              {Math.round(simulation.success_probability * 100)}%
            </p>
          )}
          <p className="text-xs text-slate-500">success prob.</p>
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-4 pt-4 border-t border-slate-700/50 space-y-3 text-sm">
              <div>
                <span className="text-slate-500">Initial state: </span>
                <pre className="text-slate-300 text-xs mt-1 bg-slate-800/50 p-2 rounded overflow-auto">
                  {JSON.stringify(simulation.initial_state, null, 2)}
                </pre>
              </div>
              {simulation.predicted_outcome && (
                <div>
                  <span className="text-slate-500">Predicted outcome: </span>
                  <pre className="text-slate-300 text-xs mt-1 bg-slate-800/50 p-2 rounded overflow-auto">
                    {JSON.stringify(simulation.predicted_outcome, null, 2)}
                  </pre>
                </div>
              )}
              <div className="flex items-center gap-4 text-xs text-slate-500">
                <span>Complexity: {simulation.complexity_level || 1}</span>
                <span>Steps: {simulation.compute_steps || 0}</span>
                <span>{new Date(simulation.created_at).toLocaleString('ko-KR')}</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
