'use client'

import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { createClient } from '@supabase/supabase-js'

// Types
interface PhysicalObject {
  id: string
  name: string
  category: string
  description?: string
  typical_size?: string
  can_move?: boolean
  is_animate?: boolean
  familiarity: number
  permanence_learned: boolean
  times_disappeared: number
  times_reappeared: number
  interaction_count: number
  created_at: string
}

interface SpatialRelation {
  id: string
  relation_type: string
  relation_description: string
  estimated_distance?: string
  confidence: number
  created_at: string
}

interface PhysicsIntuition {
  id: string
  principle_name: string
  principle_type: string
  description: string
  understanding_level: string
  confidence: number
  predictions_made: number
  predictions_correct: number
  prediction_accuracy: number
}

interface ObjectTrackingEvent {
  id: string
  event_type: string
  surprise_level: number
  created_at: string
  object?: PhysicalObject
}

interface PhysicalWorldCardProps {
  className?: string
}

// Supabase client
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// Category icons
const categoryIcons: Record<string, string> = {
  person: '👤',
  animal: '🐾',
  furniture: '🪑',
  toy: '🧸',
  food: '🍎',
  vehicle: '🚗',
  nature: '🌿',
  tool: '🔧',
  object: '📦',
  other: '❓',
}

// Physics principle icons
const physicsIcons: Record<string, string> = {
  solidity: '🧱',
  continuity: '➡️',
  gravity: '⬇️',
  support: '🏗️',
  containment: '📦',
  occlusion: '👁️',
  inertia: '🎱',
  collision: '💥',
}

// Understanding level colors
const understandingColors: Record<string, string> = {
  none: 'bg-slate-500',
  implicit: 'bg-yellow-500',
  developing: 'bg-blue-500',
  stable: 'bg-green-500',
  explicit: 'bg-purple-500',
}

export function PhysicalWorldCard({ className = '' }: PhysicalWorldCardProps) {
  const [objects, setObjects] = useState<PhysicalObject[]>([])
  const [relations, setRelations] = useState<SpatialRelation[]>([])
  const [intuitions, setIntuitions] = useState<PhysicsIntuition[]>([])
  const [trackingEvents, setTrackingEvents] = useState<ObjectTrackingEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'objects' | 'physics' | 'permanence'>('objects')

  // Fetch data
  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      try {
        const [objectsRes, relationsRes, intuitionsRes, eventsRes] = await Promise.all([
          supabase
            .from('physical_objects')
            .select('*')
            .order('familiarity', { ascending: false })
            .limit(20),
          supabase
            .from('spatial_relations')
            .select('*')
            .eq('is_current', true)
            .order('created_at', { ascending: false })
            .limit(10),
          supabase
            .from('physics_intuitions')
            .select('*')
            .order('acquired_at_stage', { ascending: true }),
          supabase
            .from('object_tracking_events')
            .select('*, object:physical_objects(*)')
            .order('created_at', { ascending: false })
            .limit(10),
        ])

        if (objectsRes.data) setObjects(objectsRes.data)
        if (relationsRes.data) setRelations(relationsRes.data)
        if (intuitionsRes.data) setIntuitions(intuitionsRes.data)
        if (eventsRes.data) setTrackingEvents(eventsRes.data)
      } catch (error) {
        console.error('Failed to fetch physical world data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()

    // Subscribe to realtime updates
    const objectsChannel = supabase
      .channel('physical_objects_changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'physical_objects' }, () => {
        fetchData()
      })
      .subscribe()

    const eventsChannel = supabase
      .channel('tracking_events_changes')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'object_tracking_events' }, () => {
        fetchData()
      })
      .subscribe()

    return () => {
      objectsChannel.unsubscribe()
      eventsChannel.unsubscribe()
    }
  }, [])

  // Stats
  const stats = useMemo(() => {
    const familiarObjects = objects.filter(o => o.familiarity > 0.5).length
    const permanentObjects = objects.filter(o => o.permanence_learned).length
    const learnedIntuitions = intuitions.filter(i => i.understanding_level !== 'none').length
    const totalInteractions = objects.reduce((sum, o) => sum + (o.interaction_count || 0), 0)

    return {
      totalObjects: objects.length,
      familiarObjects,
      permanentObjects,
      learnedIntuitions,
      totalIntuitions: intuitions.length,
      totalInteractions,
      avgAccuracy: intuitions.length > 0
        ? intuitions.reduce((sum, i) => sum + (i.prediction_accuracy || 0), 0) / intuitions.length
        : 0,
    }
  }, [objects, intuitions])

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-gradient-to-br from-emerald-900/50 to-teal-900/50 backdrop-blur-sm rounded-xl border border-emerald-700/30 overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="p-4 border-b border-emerald-700/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
              <span className="text-xl">🌍</span>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Physical World</h3>
              <p className="text-xs text-emerald-300">Object Permanence & Physics</p>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="flex gap-2">
            <div className="bg-emerald-800/50 rounded-lg px-3 py-1 text-center">
              <p className="text-lg font-bold text-white">{stats.totalObjects}</p>
              <p className="text-[10px] text-emerald-300">Objects</p>
            </div>
            <div className="bg-emerald-800/50 rounded-lg px-3 py-1 text-center">
              <p className="text-lg font-bold text-teal-400">{stats.learnedIntuitions}/{stats.totalIntuitions}</p>
              <p className="text-[10px] text-emerald-300">Physics</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-emerald-700/30">
        {(['objects', 'physics', 'permanence'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2 px-4 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'text-white bg-emerald-700/30 border-b-2 border-emerald-400'
                : 'text-emerald-300 hover:text-white hover:bg-emerald-800/30'
            }`}
          >
            {tab === 'objects' && '📦 Objects'}
            {tab === 'physics' && '⚡ Physics'}
            {tab === 'permanence' && '👁️ Permanence'}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4 min-h-[300px]">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full"
            />
          </div>
        ) : (
          <AnimatePresence mode="wait">
            {/* Objects Tab */}
            {activeTab === 'objects' && (
              <motion.div
                key="objects"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="space-y-3"
              >
                {objects.length === 0 ? (
                  <div className="text-center py-8 text-emerald-300">
                    <span className="text-4xl block mb-2">👀</span>
                    <p>No objects discovered yet</p>
                    <p className="text-xs mt-1">Use the camera to explore the world!</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-2">
                    {objects.slice(0, 8).map(obj => (
                      <motion.div
                        key={obj.id}
                        whileHover={{ scale: 1.02 }}
                        className="bg-slate-800/50 rounded-lg p-3"
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xl">{categoryIcons[obj.category] || '📦'}</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-white truncate">{obj.name}</p>
                            <p className="text-[10px] text-slate-400">{obj.category}</p>
                          </div>
                        </div>

                        {/* Familiarity bar */}
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${(obj.familiarity || 0) * 100}%` }}
                              className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full"
                            />
                          </div>
                          <span className="text-[10px] text-slate-400">
                            {Math.round((obj.familiarity || 0) * 100)}%
                          </span>
                        </div>

                        {/* Permanence indicator */}
                        {obj.permanence_learned && (
                          <div className="mt-1 flex items-center gap-1 text-[10px] text-green-400">
                            <span>✓</span>
                            <span>Permanence learned</span>
                          </div>
                        )}
                      </motion.div>
                    ))}
                  </div>
                )}

                {/* Recent Relations */}
                {relations.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-xs font-medium text-emerald-300 mb-2">Recent Spatial Relations</h4>
                    <div className="space-y-1">
                      {relations.slice(0, 3).map(rel => (
                        <div key={rel.id} className="text-xs text-slate-300 bg-slate-800/30 rounded px-2 py-1">
                          {rel.relation_description}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}

            {/* Physics Tab */}
            {activeTab === 'physics' && (
              <motion.div
                key="physics"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="space-y-3"
              >
                {intuitions.map(intuition => (
                  <div
                    key={intuition.id}
                    className="bg-slate-800/50 rounded-lg p-3"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{physicsIcons[intuition.principle_name] || '🔬'}</span>
                        <div>
                          <p className="text-sm font-medium text-white capitalize">
                            {intuition.principle_name}
                          </p>
                          <p className="text-[10px] text-slate-400">
                            {intuition.principle_type === 'core_knowledge' ? 'Innate' : 'Learned'}
                          </p>
                        </div>
                      </div>

                      {/* Understanding level badge */}
                      <div className={`px-2 py-0.5 rounded-full text-[10px] text-white ${understandingColors[intuition.understanding_level]}`}>
                        {intuition.understanding_level}
                      </div>
                    </div>

                    <p className="text-xs text-slate-300 mb-2">{intuition.description}</p>

                    {/* Progress */}
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-slate-400">
                        Confidence: {Math.round((intuition.confidence || 0) * 100)}%
                      </span>
                      {intuition.predictions_made > 0 && (
                        <span className="text-emerald-400">
                          {intuition.predictions_correct}/{intuition.predictions_made} correct
                        </span>
                      )}
                    </div>

                    {/* Confidence bar */}
                    <div className="mt-1 h-1 bg-slate-700 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(intuition.confidence || 0) * 100}%` }}
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                      />
                    </div>
                  </div>
                ))}
              </motion.div>
            )}

            {/* Permanence Tab */}
            {activeTab === 'permanence' && (
              <motion.div
                key="permanence"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="space-y-4"
              >
                {/* Permanence Stats */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-white">{stats.permanentObjects}</p>
                    <p className="text-xs text-slate-400">Objects with Permanence</p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-emerald-400">
                      {objects.length > 0
                        ? Math.round((stats.permanentObjects / objects.length) * 100)
                        : 0}%
                    </p>
                    <p className="text-xs text-slate-400">Understanding Rate</p>
                  </div>
                </div>

                {/* Recent Tracking Events */}
                <div>
                  <h4 className="text-xs font-medium text-emerald-300 mb-2">Recent Object Tracking</h4>
                  {trackingEvents.length === 0 ? (
                    <div className="text-center py-4 text-emerald-300 text-sm">
                      <span className="text-2xl block mb-1">🎯</span>
                      No tracking events yet
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {trackingEvents.slice(0, 5).map(event => (
                        <motion.div
                          key={event.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="bg-slate-800/50 rounded-lg p-2 flex items-center gap-3"
                        >
                          <span className={`text-xl ${
                            event.event_type === 'appeared' ? '' :
                            event.event_type === 'disappeared' ? 'opacity-50' :
                            ''
                          }`}>
                            {event.event_type === 'appeared' && '👁️'}
                            {event.event_type === 'disappeared' && '👻'}
                            {event.event_type === 'reappeared' && '✨'}
                            {event.event_type === 'moved' && '➡️'}
                          </span>
                          <div className="flex-1">
                            <p className="text-sm text-white">
                              Object {event.event_type}
                            </p>
                            {event.surprise_level > 0 && (
                              <p className="text-[10px] text-yellow-400">
                                Surprise: {Math.round((event.surprise_level || 0) * 100)}%
                              </p>
                            )}
                          </div>
                          <span className="text-[10px] text-slate-500">
                            {new Date(event.created_at).toLocaleTimeString()}
                          </span>
                        </motion.div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Explanation */}
                <div className="bg-slate-800/30 rounded-lg p-3 text-xs text-slate-400">
                  <p className="font-medium text-emerald-300 mb-1">Object Permanence</p>
                  <p>
                    The understanding that objects continue to exist even when they cannot be seen.
                    Baby AI learns this through repeated experiences of objects disappearing and reappearing.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        )}
      </div>
    </motion.div>
  )
}
