'use client'

import { motion } from 'framer-motion'
import { Brain, ArrowRight, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { useBrainData } from '@/hooks/useBrainData'

export function BrainCard() {
  const { brainData, isLoading, error } = useBrainData()

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
    >
      <Link href="/brain" className="block group">
        <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm hover:border-violet-500/50 transition-all duration-300 cursor-pointer">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center">
                <Brain className="w-5 h-5 text-violet-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-100">뉴런 네트워크</h3>
                <p className="text-xs text-slate-400">Baby AI의 뇌 구조</p>
              </div>
            </div>
            <div className="flex items-center gap-1 text-sm text-violet-400 group-hover:translate-x-1 transition-transform">
              <span className="hidden sm:inline">자세히 보기</span>
              <ArrowRight className="w-4 h-4" />
            </div>
          </div>

          {/* Content */}
          {isLoading ? (
            <div className="h-32 flex items-center justify-center">
              <Loader2 className="w-6 h-6 text-violet-400 animate-spin" />
            </div>
          ) : error ? (
            <div className="h-32 flex items-center justify-center text-slate-500 text-sm">
              데이터 로드 실패
            </div>
          ) : brainData ? (
            <>
              {/* Stats Grid */}
              <div className="grid grid-cols-3 gap-2 mb-4">
                <div className="bg-slate-900/50 rounded-xl p-3 text-center">
                  <p className="text-2xl font-bold text-violet-400">{brainData.neurons.length}</p>
                  <p className="text-xs text-slate-500">뉴런</p>
                </div>
                <div className="bg-slate-900/50 rounded-xl p-3 text-center">
                  <p className="text-2xl font-bold text-emerald-400">{brainData.synapses.length}</p>
                  <p className="text-xs text-slate-500">시냅스</p>
                </div>
                <div className="bg-slate-900/50 rounded-xl p-3 text-center">
                  <p className="text-2xl font-bold text-amber-400">{brainData.astrocytes?.length || 0}</p>
                  <p className="text-xs text-slate-500">클러스터</p>
                </div>
              </div>

              {/* Visual Preview - animated dots */}
              <div className="relative h-64 bg-slate-900/30 rounded-xl overflow-hidden">
                <div className="absolute inset-0 flex items-center justify-center">
                  {/* Animated brain network preview */}
                  <svg className="w-full h-full" viewBox="0 0 200 100">
                    {/* Connection lines */}
                    {[...Array(8)].map((_, i) => (
                      <motion.line
                        key={`line-${i}`}
                        x1={50 + Math.cos(i * 0.8) * 30}
                        y1={50 + Math.sin(i * 0.8) * 20}
                        x2={150 + Math.cos(i * 0.8 + Math.PI) * 30}
                        y2={50 + Math.sin(i * 0.8 + Math.PI) * 20}
                        stroke="#475569"
                        strokeWidth="1"
                        strokeOpacity={0.3}
                        initial={{ pathLength: 0 }}
                        animate={{ pathLength: 1 }}
                        transition={{ duration: 1.5, delay: i * 0.1 }}
                      />
                    ))}
                    {/* Neuron dots */}
                    {[...Array(12)].map((_, i) => {
                      const angle = (i / 12) * Math.PI * 2
                      const radius = 25 + (i % 3) * 10
                      const cx = 100 + Math.cos(angle) * radius
                      const cy = 50 + Math.sin(angle) * radius * 0.6
                      const colors = ['#f43f5e', '#a855f7', '#14b8a6', '#3b82f6', '#22c55e']
                      return (
                        <motion.circle
                          key={`neuron-${i}`}
                          cx={cx}
                          cy={cy}
                          r={3 + (i % 3)}
                          fill={colors[i % colors.length]}
                          initial={{ opacity: 0, scale: 0 }}
                          animate={{
                            opacity: [0.6, 1, 0.6],
                            scale: [1, 1.2, 1]
                          }}
                          transition={{
                            duration: 2,
                            delay: i * 0.1,
                            repeat: Infinity,
                            repeatType: 'reverse'
                          }}
                        />
                      )
                    })}
                  </svg>
                </div>
                {/* Overlay text */}
                <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-t from-slate-900/80 to-transparent">
                  <p className="text-xs text-slate-400 group-hover:text-violet-300 transition-colors">
                    클릭하여 3D로 탐색하기
                  </p>
                </div>
              </div>

              {/* Category breakdown */}
              <div className="mt-3 flex flex-wrap gap-1.5">
                {getCategoryBreakdown(brainData.neurons).map(({ category, count, color }) => (
                  <span
                    key={category}
                    className="px-2 py-0.5 rounded-full text-[10px] font-medium"
                    style={{ backgroundColor: color + '20', color }}
                  >
                    {category}: {count}
                  </span>
                ))}
              </div>
            </>
          ) : (
            <div className="h-32 flex items-center justify-center text-slate-500 text-sm">
              뉴런 데이터 없음
            </div>
          )}
        </div>
      </Link>
    </motion.div>
  )
}

// Helper to get category breakdown
function getCategoryBreakdown(neurons: Array<{ category: string }>) {
  const counts: Record<string, number> = {}
  neurons.forEach((n) => {
    counts[n.category] = (counts[n.category] || 0) + 1
  })

  const CATEGORY_COLORS: Record<string, string> = {
    frozen_knowledge: '#64748b',  // cold gray
    learned: '#d946ef',           // warm magenta
    감정: '#f97316',              // orange
    emotion: '#f97316',
    person: '#14b8a6',            // teal
    '추상적 개념': '#3b82f6',     // blue
    행위: '#22c55e',              // green
    identity: '#fbbf24',          // gold
    사물: '#a855f7',              // purple
  }

  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([category, count]) => ({
      category,
      count,
      color: CATEGORY_COLORS[category] || '#6366f1',
    }))
}
