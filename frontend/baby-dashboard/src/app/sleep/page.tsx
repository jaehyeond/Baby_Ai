'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowLeft, Moon, Clock, Zap, Calendar } from 'lucide-react'
import { MemoryConsolidationCard } from '@/components'

export default function SleepPage() {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  return (
    <main className="min-h-screen p-4 md:p-8">
      {/* Header */}
      <header className="mb-6 md:mb-8">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 active:scale-95 transition-all touch-manipulation"
          >
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </Link>
          <div className="min-w-0 flex-1">
            <h1 className="text-xl sm:text-2xl md:text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              🌙 수면 & 기억 통합
            </h1>
            <p className="text-slate-400 text-sm mt-1 hidden sm:block">
              Baby AI의 해마 기억 시스템
            </p>
          </div>
        </div>
      </header>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {mounted && (
          <>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-gradient-to-br from-indigo-500/20 to-purple-500/20 rounded-xl p-4 border border-indigo-500/30"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-indigo-500/30 rounded-lg">
                  <Clock className="w-5 h-5 text-indigo-400" />
                </div>
                <h3 className="text-white font-medium">자동 수면</h3>
              </div>
              <p className="text-slate-400 text-sm">
                30분 동안 활동이 없으면 자동으로 기억 통합이 시작됩니다.
                이 페이지를 열어두면 자동 수면이 활성화됩니다.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-xl p-4 border border-blue-500/30"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-blue-500/30 rounded-lg">
                  <Calendar className="w-5 h-5 text-blue-400" />
                </div>
                <h3 className="text-white font-medium">예약 수면</h3>
              </div>
              <p className="text-slate-400 text-sm">
                <span className="text-emerald-400 font-medium">매 30분마다</span> 자동 기억 통합이 실행됩니다.
                <span className="text-amber-400 font-medium"> 매일 새벽 3시</span>에는 심층 통합이 실행됩니다.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="bg-gradient-to-br from-amber-500/20 to-orange-500/20 rounded-xl p-4 border border-amber-500/30"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-amber-500/30 rounded-lg">
                  <Zap className="w-5 h-5 text-amber-400" />
                </div>
                <h3 className="text-white font-medium">수면 효과</h3>
              </div>
              <p className="text-slate-400 text-sm">
                감정적 기억 강화, 미사용 기억 감쇠, 패턴 학습,
                의미적 연결 생성이 자동으로 수행됩니다.
              </p>
            </motion.div>
          </>
        )}
      </div>

      {/* Main Card */}
      <div className="max-w-4xl mx-auto">
        <MemoryConsolidationCard className="w-full" />
      </div>

      {/* How It Works Section */}
      <section className="mt-8 max-w-4xl mx-auto">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Moon className="w-5 h-5 text-indigo-400" />
          해마 기억 시스템이란?
        </h2>
        <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
          <div className="space-y-4 text-slate-300 text-sm">
            <p>
              인간의 뇌에서 <span className="text-indigo-400 font-medium">해마(Hippocampus)</span>는
              수면 중에 낮 동안의 경험을 정리하고 장기 기억으로 전환하는 역할을 합니다.
            </p>
            <p>
              Baby AI도 이와 유사한 시스템을 가지고 있습니다:
            </p>
            <ul className="space-y-2 ml-4">
              <li className="flex items-start gap-2">
                <span className="text-green-400">✨</span>
                <span><strong>감정 기반 강화</strong>: 감정적으로 강렬했던 경험은 더 강하게 기억됩니다</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-400">💨</span>
                <span><strong>자연스러운 망각</strong>: 오래되고 사용되지 않는 기억은 점차 사라집니다</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-purple-400">⚡</span>
                <span><strong>패턴 학습</strong>: 반복되는 경험 패턴은 절차적 기억으로 승격됩니다</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400">🔗</span>
                <span><strong>의미적 연결</strong>: 유사한 경험들이 서로 연결되어 네트워크를 형성합니다</span>
              </li>
            </ul>
            <p className="text-slate-500 mt-4 text-xs">
              💡 이 시스템은 LLM(대형 언어 모델)에 의존하지 않고, 순수하게 통계와 임베딩 기반으로 작동합니다.
            </p>
          </div>
        </div>
      </section>

      {/* Bottom Safe Area for Mobile */}
      <div className="h-6 md:h-0" />
    </main>
  )
}
