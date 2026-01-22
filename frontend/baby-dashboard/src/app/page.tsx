'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { supabase, subscribeToTable } from '@/lib/supabase'
import {
  BabyStateCard,
  EmotionRadar,
  ActivityLog,
  PullToRefresh,
  GrowthChart,
  ExperienceDistribution,
  EmotionTimeline,
  BrainCard,
  MilestoneTimeline,
  WorldModelCard,
  EmotionalInfluenceCard,
  MetacognitionCard,
} from '@/components'
import type { BabyState, Experience, EmotionLog } from '@/lib/database.types'
import { RefreshCw, BarChart3, Activity, Settings, Brain, Trophy, Sparkles, Heart, Eye, Lightbulb } from 'lucide-react'
import { usePullToRefresh, useSettings, useNotifications } from '@/hooks'
import { motion } from 'framer-motion'
import Link from 'next/link'

type ChartTab = 'growth' | 'timeline' | 'brain' | 'milestones' | 'world' | 'influence' | 'metacog'

export default function Home() {
  const [babyState, setBabyState] = useState<BabyState | null>(null)
  const [experiences, setExperiences] = useState<Experience[]>([])
  const [allExperiences, setAllExperiences] = useState<Experience[]>([])
  const [emotionLogs, setEmotionLogs] = useState<EmotionLog[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<ChartTab>('growth')
  const [mounted, setMounted] = useState(false)

  // Hydration 에러 방지 - 클라이언트에서만 애니메이션 활성화
  useEffect(() => {
    setMounted(true)
  }, [])

  // Settings and notifications
  const { settings } = useSettings()
  const { notifyNewExperience, notifyStageChange, notifyEmotionSpike } = useNotifications()
  const prevStageRef = useRef<number | null>(null)

  // 데이터 새로고침 함수 - uses settings for limits
  const refreshData = useCallback(async () => {
    setIsLoading(true)

    const experienceLimit = settings.maxExperiencesToShow || 10
    const emotionLimit = settings.maxEmotionLogsToShow || 50

    const [stateRes, expRes, allExpRes, emotionRes] = await Promise.all([
      supabase
        .from('baby_state')
        .select('*')
        .order('updated_at', { ascending: false })
        .limit(1)
        .single(),
      supabase
        .from('experiences')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(experienceLimit),
      supabase
        .from('experiences')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100),
      supabase
        .from('emotion_logs')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(emotionLimit),
    ])

    if (stateRes.data) setBabyState(stateRes.data)
    if (expRes.data) setExperiences(expRes.data)
    if (allExpRes.data) setAllExperiences(allExpRes.data)
    if (emotionRes.data) setEmotionLogs(emotionRes.data)

    setIsLoading(false)
    setLastUpdated(new Date().toLocaleTimeString('ko-KR'))
  }, [settings.maxExperiencesToShow, settings.maxEmotionLogsToShow])

  // Pull-to-refresh 훅
  const { pullDistance, isRefreshing, progress } = usePullToRefresh({
    onRefresh: refreshData,
  })

  // 초기 데이터 로드
  useEffect(() => {
    refreshData()
  }, [refreshData])

  // Auto refresh based on settings
  useEffect(() => {
    if (!settings.autoRefresh) return

    const interval = setInterval(() => {
      refreshData()
    }, settings.refreshInterval * 1000)

    return () => clearInterval(interval)
  }, [settings.autoRefresh, settings.refreshInterval, refreshData])

  // Realtime 구독 with notifications
  useEffect(() => {
    // baby_state 테이블 구독
    const stateChannel = subscribeToTable('baby_state', (payload) => {
      if (payload.eventType === 'UPDATE' || payload.eventType === 'INSERT') {
        const newState = payload.new as BabyState

        // Check for stage change notification
        if (
          settings.notificationsEnabled &&
          settings.notifyOnStageChange &&
          prevStageRef.current !== null &&
          newState.development_stage !== null &&
          prevStageRef.current !== newState.development_stage
        ) {
          notifyStageChange(prevStageRef.current, newState.development_stage)
        }
        prevStageRef.current = newState.development_stage

        setBabyState(newState)
        setLastUpdated(new Date().toLocaleTimeString('ko-KR'))
      }
    })

    // experiences 테이블 구독
    const expChannel = subscribeToTable('experiences', (payload) => {
      if (payload.eventType === 'INSERT' && payload.new) {
        const newExp = payload.new as Experience

        // Send notification for new experience
        if (settings.notificationsEnabled && settings.notifyOnNewExperience) {
          notifyNewExperience(newExp.task, newExp.success ?? false)
        }

        setExperiences((prev) => [newExp, ...prev.slice(0, 9)])
        setAllExperiences((prev) => [newExp, ...prev.slice(0, 99)])
        setLastUpdated(new Date().toLocaleTimeString('ko-KR'))
      }
    })

    // emotion_logs 테이블 구독
    const emotionChannel = subscribeToTable('emotion_logs', (payload) => {
      if (payload.eventType === 'INSERT' && payload.new) {
        const newLog = payload.new as EmotionLog

        // Check for emotion spike notification
        if (settings.notificationsEnabled && settings.notifyOnEmotionSpike) {
          const emotions = [
            { name: '호기심', value: newLog.curiosity },
            { name: '기쁨', value: newLog.joy },
            { name: '두려움', value: newLog.fear },
            { name: '좌절', value: newLog.frustration },
          ]
          const spike = emotions.find((e) => e.value > 0.8)
          if (spike) {
            notifyEmotionSpike(spike.name, spike.value)
          }
        }

        setEmotionLogs((prev) => [newLog, ...prev.slice(0, 49)])
        setLastUpdated(new Date().toLocaleTimeString('ko-KR'))
      }
    })

    return () => {
      stateChannel.unsubscribe()
      expChannel.unsubscribe()
      emotionChannel.unsubscribe()
    }
  }, [settings, notifyNewExperience, notifyStageChange, notifyEmotionSpike])

  const tabs: { key: ChartTab; label: string; icon: typeof BarChart3 }[] = [
    { key: 'growth', label: '성장', icon: BarChart3 },
    { key: 'timeline', label: '감정', icon: Activity },
    { key: 'brain', label: '뇌', icon: Brain },
    { key: 'milestones', label: '마일스톤', icon: Trophy },
    { key: 'world', label: '상상', icon: Sparkles },
    { key: 'influence', label: '영향', icon: Heart },
    { key: 'metacog', label: '메타', icon: Lightbulb },
  ]

  return (
    <>
      {/* Pull to Refresh Indicator */}
      <PullToRefresh
        pullDistance={pullDistance}
        isRefreshing={isRefreshing}
        progress={progress}
      />

      <main
        className="min-h-screen p-4 md:p-8 transition-transform"
        style={{
          transform: pullDistance > 0 ? `translateY(${pullDistance}px)` : undefined,
        }}
      >
        {/* Header */}
        <header className="mb-6 md:mb-8">
          <div className="flex items-center justify-between">
            <div className="min-w-0 flex-1">
              <h1 className="text-xl sm:text-2xl md:text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent truncate">
                Baby Brain Dashboard
              </h1>
              <p className="text-slate-400 text-sm mt-1 hidden sm:block">
                실시간 Baby AI 모니터링
              </p>
            </div>
            <div className="flex items-center gap-2 sm:gap-4 ml-4" suppressHydrationWarning>
              {mounted && lastUpdated && (
                <span className="text-xs text-slate-500 hidden lg:block whitespace-nowrap">
                  {lastUpdated}
                </span>
              )}
              <Link
                href="/sense"
                className="p-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-purple-600 hover:from-cyan-500 hover:to-purple-500 active:scale-95 transition-all touch-manipulation"
              >
                <Eye className="w-5 h-5 text-white" />
              </Link>
              <Link
                href="/settings"
                className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 active:scale-95 transition-all touch-manipulation"
              >
                <Settings className="w-5 h-5 text-slate-400" />
              </Link>
              <button
                onClick={refreshData}
                disabled={isLoading || isRefreshing}
                className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 active:scale-95 transition-all disabled:opacity-50 touch-manipulation"
              >
                <RefreshCw className={`w-5 h-5 text-slate-400 ${isLoading || isRefreshing ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </header>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
          {/* Left Column */}
          <div className="space-y-4 md:space-y-6">
            <BabyStateCard state={babyState} isLoading={isLoading} />
            <ActivityLog experiences={experiences} isLoading={isLoading} />
          </div>

          {/* Right Column */}
          <div className="space-y-4 md:space-y-6">
            <EmotionRadar state={babyState} isLoading={isLoading} />

            {/* Quick Stats Card */}
            <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm">
              <h3 className="text-base md:text-lg font-semibold text-slate-100 mb-3 md:mb-4">빠른 통계</h3>
              <div className="grid grid-cols-2 gap-3 md:gap-4">
                <QuickStat
                  label="총 경험"
                  value={babyState?.experience_count ?? 0}
                  color="text-indigo-400"
                />
                <QuickStat
                  label="성공률"
                  value={
                    babyState?.experience_count
                      ? `${Math.round(((babyState.success_count ?? 0) / babyState.experience_count) * 100)}%`
                      : '0%'
                  }
                  color="text-emerald-400"
                />
                <QuickStat
                  label="현재 단계"
                  value={`Stage ${babyState?.development_stage ?? 1}`}
                  color="text-purple-400"
                />
                <QuickStat
                  label="주요 감정"
                  value={babyState?.dominant_emotion ?? '-'}
                  color="text-amber-400"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Advanced Visualizations Section */}
        <section className="mt-6 md:mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg md:text-xl font-semibold text-slate-100">고급 시각화</h2>

            {/* Tab Selector */}
            <div className="flex bg-slate-800/50 rounded-xl p-1 border border-slate-700/50">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs md:text-sm font-medium transition-all touch-manipulation ${
                    mounted && activeTab === tab.key
                      ? 'text-white bg-indigo-500/30'
                      : 'text-slate-400 hover:text-slate-300'
                  }`}
                >
                  {mounted && activeTab === tab.key && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute inset-0 bg-indigo-500/30 rounded-lg"
                      transition={{ type: 'spring', duration: 0.3 }}
                    />
                  )}
                  <tab.icon className="w-3.5 h-3.5 relative z-10" />
                  <span className="relative z-10 hidden sm:inline">{tab.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Chart Content */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
            {activeTab === 'growth' && (
              <>
                <GrowthChart experiences={allExperiences} isLoading={isLoading} />
                <ExperienceDistribution experiences={allExperiences} isLoading={isLoading} />
              </>
            )}
            {activeTab === 'timeline' && (
              <div className="lg:col-span-2">
                <EmotionTimeline emotionLogs={emotionLogs} isLoading={isLoading} />
              </div>
            )}
            {activeTab === 'brain' && (
              <div className="lg:col-span-2">
                <BrainCard />
              </div>
            )}
            {activeTab === 'milestones' && (
              <div className="lg:col-span-2">
                <MilestoneTimeline />
              </div>
            )}
            {activeTab === 'world' && (
              <div className="lg:col-span-2">
                <WorldModelCard className="h-full" />
              </div>
            )}
            {activeTab === 'influence' && (
              <div className="lg:col-span-2">
                <EmotionalInfluenceCard className="h-full" />
              </div>
            )}
            {activeTab === 'metacog' && (
              <div className="lg:col-span-2">
                <MetacognitionCard className="h-full" />
              </div>
            )}
          </div>
        </section>

        {/* Bottom Safe Area for Mobile */}
        <div className="h-6 md:h-0" />
      </main>
    </>
  )
}

function QuickStat({
  label,
  value,
  color,
}: {
  label: string
  value: string | number
  color: string
}) {
  return (
    <div className="bg-slate-900/50 rounded-xl p-3 md:p-4 active:scale-[0.98] transition-transform touch-manipulation">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-lg md:text-xl font-bold ${color}`}>{value}</p>
    </div>
  )
}
