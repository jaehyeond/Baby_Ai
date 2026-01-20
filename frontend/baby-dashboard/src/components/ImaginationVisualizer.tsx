'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useActiveImagination } from '@/hooks/useWorldModel'
import type { Json } from '@/lib/database.types'

interface ThoughtBubbleProps {
  content: string
  type: 'question' | 'insight' | 'prediction' | 'connection'
  delay: number
}

function ThoughtBubble({ content, type, delay }: ThoughtBubbleProps) {
  const typeConfig = {
    question: { icon: '?', color: 'from-blue-500 to-cyan-500', bg: 'bg-blue-500/10' },
    insight: { icon: '!', color: 'from-yellow-500 to-orange-500', bg: 'bg-yellow-500/10' },
    prediction: { icon: 'P', color: 'from-purple-500 to-pink-500', bg: 'bg-purple-500/10' },
    connection: { icon: 'C', color: 'from-green-500 to-emerald-500', bg: 'bg-green-500/10' }
  }

  const config = typeConfig[type]

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.8, y: -20 }}
      transition={{ delay, type: 'spring', stiffness: 200 }}
      className={`${config.bg} rounded-2xl p-4 pl-10 border border-slate-700/50 relative`}
    >
      <div className={`absolute top-3 left-2 w-6 h-6 rounded-full bg-gradient-to-br ${config.color} flex items-center justify-center text-xs font-bold text-white`}>
        {config.icon}
      </div>
      <p className="text-sm text-slate-300">{content}</p>
    </motion.div>
  )
}

interface FloatingParticle {
  id: number
  x: number
  y: number
  size: number
  duration: number
  delay: number
}

function ImaginationParticles() {
  const [particles, setParticles] = useState<FloatingParticle[]>([])

  useEffect(() => {
    const newParticles = Array.from({ length: 15 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 4 + 2,
      duration: Math.random() * 3 + 2,
      delay: Math.random() * 2
    }))
    setParticles(newParticles)
  }, [])

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map(particle => (
        <motion.div
          key={particle.id}
          className="absolute rounded-full bg-gradient-to-r from-purple-400 to-pink-400 opacity-30"
          style={{
            left: `${particle.x}%`,
            top: `${particle.y}%`,
            width: particle.size,
            height: particle.size
          }}
          animate={{
            y: [0, -30, 0],
            x: [0, 10, -10, 0],
            opacity: [0.3, 0.6, 0.3],
            scale: [1, 1.2, 1]
          }}
          transition={{
            duration: particle.duration,
            delay: particle.delay,
            repeat: Infinity,
            ease: 'easeInOut'
          }}
        />
      ))}
    </div>
  )
}

interface ImaginationVisualizerProps {
  className?: string
}

export function ImaginationVisualizer({ className = '' }: ImaginationVisualizerProps) {
  const { session, loading } = useActiveImagination()
  const [displayedThoughts, setDisplayedThoughts] = useState<Array<{ content: string; type: 'question' | 'insight' | 'prediction' | 'connection' }>>([])
  const thoughtsRef = useRef<HTMLDivElement>(null)

  // Process thoughts from session
  useEffect(() => {
    if (!session?.thoughts) {
      setDisplayedThoughts([])
      return
    }

    const thoughts = (session.thoughts as Json[]).map((t: Json) => {
      if (typeof t === 'object' && t !== null && 'content' in t && 'type' in t) {
        return {
          content: String((t as { content: unknown }).content),
          type: ((t as { type: unknown }).type as 'question' | 'insight' | 'prediction' | 'connection') || 'insight'
        }
      }
      return { content: String(t), type: 'insight' as const }
    })

    setDisplayedThoughts(thoughts.slice(-5)) // Show last 5 thoughts
  }, [session])

  // Auto-scroll to bottom
  useEffect(() => {
    if (thoughtsRef.current) {
      thoughtsRef.current.scrollTop = thoughtsRef.current.scrollHeight
    }
  }, [displayedThoughts])

  const isActive = session && !session.ended_at

  return (
    <div className={`bg-slate-900/80 backdrop-blur-sm rounded-xl p-4 border border-slate-800 relative overflow-hidden ${className}`}>
      {isActive && <ImaginationParticles />}

      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <motion.div
              animate={isActive ? {
                boxShadow: [
                  '0 0 0 0 rgba(168, 85, 247, 0.4)',
                  '0 0 0 10px rgba(168, 85, 247, 0)',
                  '0 0 0 0 rgba(168, 85, 247, 0)'
                ]
              } : {}}
              transition={{ duration: 2, repeat: Infinity }}
              className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center"
            >
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </motion.div>
            <div>
              <h3 className="text-lg font-semibold text-white">Imagination</h3>
              <p className="text-xs text-slate-400">
                {isActive ? 'Active session' : 'No active session'}
              </p>
            </div>
          </div>
          {isActive && (
            <motion.div
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="flex items-center gap-1 text-xs text-purple-400"
            >
              <span className="w-2 h-2 bg-purple-400 rounded-full" />
              Thinking...
            </motion.div>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-48">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full"
            />
          </div>
        ) : !session ? (
          <div className="flex flex-col items-center justify-center h-48 text-slate-500">
            <motion.div
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 3, repeat: Infinity }}
              className="text-4xl mb-4"
            >
              ...
            </motion.div>
            <p className="text-sm">Baby AI is resting</p>
            <p className="text-xs mt-1">Waiting for something to imagine...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Topic */}
            <div className="bg-slate-800/50 rounded-lg p-3">
              <p className="text-xs text-slate-500 mb-1">Topic</p>
              <p className="text-sm text-white font-medium">{session.topic}</p>
              {session.imagination_type && (
                <span className="inline-block mt-2 text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded-full">
                  {session.imagination_type}
                </span>
              )}
            </div>

            {/* Thoughts stream */}
            <div
              ref={thoughtsRef}
              className="space-y-3 max-h-48 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700"
            >
              <AnimatePresence mode="popLayout">
                {displayedThoughts.map((thought, index) => (
                  <ThoughtBubble
                    key={index}
                    content={thought.content}
                    type={thought.type}
                    delay={index * 0.1}
                  />
                ))}
              </AnimatePresence>
            </div>

            {/* Stats */}
            {session.insights && session.insights.length > 0 && (
              <div className="flex items-center gap-4 text-xs text-slate-500 pt-2 border-t border-slate-700/50">
                <span className="flex items-center gap-1">
                  <span className="text-yellow-400">!</span>
                  {session.insights.length} insights
                </span>
                {session.predictions_made && (
                  <span className="flex items-center gap-1">
                    <span className="text-purple-400">P</span>
                    {session.predictions_made.length} predictions
                  </span>
                )}
                {session.curiosity_level && (
                  <span className="flex items-center gap-1">
                    Curiosity: {Math.round(session.curiosity_level * 100)}%
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
