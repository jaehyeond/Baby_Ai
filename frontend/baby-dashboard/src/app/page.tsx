'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
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
  CuriosityCard,
  TextualBackpropCard,
  QuestionNotification,
  QuestionBubble,
  QuestionList,
} from '@/components'
import type { PendingQuestion } from '@/lib/database.types'
import { RefreshCw, BarChart3, Activity, Settings, Brain, Trophy, Sparkles, Heart, Eye, Lightbulb, Search, Moon, Zap, MessageCircle } from 'lucide-react'
import { usePullToRefresh, useSettings, useNotifications, usePendingQuestions, useSSESubscription } from '@/hooks'
import type { SSEBabyStateData, SSEExperienceData } from '@/hooks'
import { motion } from 'framer-motion'
import Link from 'next/link'

const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000'

// FastAPI 응답 기반 로컬 타입 (Supabase 타입 대체)
interface BabyState {
  development_stage: number
  experience_count: number
  success_count?: number
  dominant_emotion?: string
  curiosity?: number
  joy?: number
  fear?: number
  surprise?: number
  frustration?: number
  boredom?: number
  emotional_state?: Record<string, number>
}

interface Experience {
  id: string
  task: string
  task_type: string
  output: string
  success: boolean
  emotional_salience?: number
  dominant_emotion?: string
  development_stage?: number
  created_at: string
}

interface EmotionLog {
  id: string
  curiosity: number
  joy: number
  fear: number
  surprise?: number
  frustration: number
  boredom?: number
  dominant_emotion: string
  created_at: string
}

type ChartTab = 'growth' | 'timeline' | 'brain' | 'milestones' | 'world' | 'influence' | 'metacog' | 'curiosity' | 'backprop' | 'questions'

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
  const { notifyNewExperience, notifyStageChange, notifyEmotionSpike, sendNotification } = useNotifications()
  const prevStageRef = useRef<number | null>(null)

  // Pending questions with realtime subscription (Phase A)
  const {
    questions: pendingQuestions,
    newQuestionAlert,
    clearAlert: clearQuestionAlert,
    submitAnswer,
    skipQuestion,
    isLoading: isQuestionsLoading,
  } = usePendingQuestions({ enableRealtime: true })

  // State for QuestionBubble modal
  const [selectedQuestion, setSelectedQuestion] = useState<PendingQuestion | null>(null)
  const [isQuestionModalOpen, setIsQuestionModalOpen] = useState(false)

  // Handle opening question modal from notification
  const handleAnswerQuestion = useCallback((question: PendingQuestion) => {
    setSelectedQuestion(question)
    setIsQuestionModalOpen(true)
    clearQuestionAlert()
  }, [clearQuestionAlert])

  // Handle selecting a question from the list
  const handleSelectQuestion = useCallback((question: PendingQuestion) => {
    setSelectedQuestion(question)
    setIsQuestionModalOpen(true)
  }, [])

  // Handle closing question modal
  const handleCloseQuestionModal = useCallback(() => {
    setIsQuestionModalOpen(false)
    setSelectedQuestion(null)
  }, [])

  // Handle answer submission
  const handleSubmitAnswer = useCallback(
    async (questionId: string, answer: string, confidence?: number) => {
      await submitAnswer(questionId, answer, confidence)
      console.log('[Page] Question answered:', questionId)
    },
    [submitAnswer]
  )

  // Handle skip question
  const handleSkipQuestion = useCallback(
    async (questionId: string) => {
      await skipQuestion(questionId)
      console.log('[Page] Question skipped:', questionId)
    },
    [skipQuestion]
  )

  // Send browser notification when new question arrives
  useEffect(() => {
    if (newQuestionAlert && settings.notificationsEnabled) {
      sendNotification('비비가 궁금해해요!', {
        body: newQuestionAlert.question,
        tag: 'pending-question',
      })
    }
  }, [newQuestionAlert, settings.notificationsEnabled, sendNotification])

  // 데이터 새로고침 함수 - FastAPI 병렬 fetch
  const refreshData = useCallback(async () => {
    setIsLoading(true)

    const experienceLimit = settings.maxExperiencesToShow || 10
    const emotionLimit = settings.maxEmotionLogsToShow || 50

    try {
      const [stateRes, expRes, allExpRes, emotionRes] = await Promise.all([
        fetch(`${FASTAPI_URL}/api/state`).then(r => r.ok ? r.json() : null),
        fetch(`${FASTAPI_URL}/api/experiences?limit=${experienceLimit}`).then(r => r.ok ? r.json() : null),
        fetch(`${FASTAPI_URL}/api/experiences?limit=100`).then(r => r.ok ? r.json() : null),
        fetch(`${FASTAPI_URL}/api/emotion-logs?limit=${emotionLimit}`).then(r => r.ok ? r.json() : null),
      ])

      if (stateRes) {
        // FastAPI /api/state → {emotional_state, development_stage, experience_count, capabilities}
        const emotState = stateRes.emotional_state || {}
        setBabyState({
          development_stage: stateRes.development_stage ?? 0,
          experience_count: stateRes.experience_count ?? 0,
          dominant_emotion: emotState.dominant_emotion ||
            Object.entries(emotState as Record<string, number>)
              .reduce((max: [string, number], [k, v]) =>
                (v as number) > max[1] ? [k, v as number] : max, ['joy', 0])[0],
          ...emotState,
        })
      }
      if (expRes?.experiences) setExperiences(expRes.experiences)
      if (allExpRes?.experiences) setAllExperiences(allExpRes.experiences)
      if (emotionRes?.emotion_logs) setEmotionLogs(emotionRes.emotion_logs)
    } catch (err) {
      console.error('[Page] refreshData error:', err)
    }

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

  // SSE 구독 (FastAPI Redis Pub/Sub → baby_state, experience 이벤트)
  useSSESubscription(useCallback((event) => {
    if (event.type === 'baby_state') {
      const newState = event.data as SSEBabyStateData

      // Stage change notification
      if (
        settings.notificationsEnabled &&
        settings.notifyOnStageChange &&
        prevStageRef.current !== null &&
        prevStageRef.current !== newState.development_stage
      ) {
        notifyStageChange(prevStageRef.current, newState.development_stage)
      }
      prevStageRef.current = newState.development_stage

      setBabyState({
        development_stage: newState.development_stage,
        experience_count: 0,        // SSE에는 experience_count 없음 → poll 유지
        dominant_emotion: newState.dominant_emotion,
        curiosity: newState.curiosity,
        joy: newState.joy,
        fear: newState.fear,
        surprise: newState.surprise,
        frustration: newState.frustration,
        boredom: newState.boredom,
      })
      setLastUpdated(new Date().toLocaleTimeString('ko-KR'))
    }

    if (event.type === 'experience') {
      const newExpPartial = event.data as SSEExperienceData

      // New experience notification
      if (settings.notificationsEnabled && settings.notifyOnNewExperience) {
        notifyNewExperience(newExpPartial.task_type || 'conversation', true)
      }

      // SSE experience에는 전체 필드가 없으므로 refreshData로 최신 데이터 로드
      refreshData()
    }
  }, [settings, notifyStageChange, notifyNewExperience, refreshData]))

  const tabs: { key: ChartTab; label: string; icon: typeof BarChart3; badge?: number }[] = [
    { key: 'growth', label: '성장', icon: BarChart3 },
    { key: 'timeline', label: '감정', icon: Activity },
    { key: 'brain', label: '뇌', icon: Brain },
    { key: 'milestones', label: '마일스톤', icon: Trophy },
    { key: 'world', label: '상상', icon: Sparkles },
    { key: 'influence', label: '영향', icon: Heart },
    { key: 'metacog', label: '메타', icon: Lightbulb },
    { key: 'curiosity', label: '호기심', icon: Search },
    { key: 'backprop', label: '피드백', icon: Zap },
    { key: 'questions', label: '질문', icon: MessageCircle, badge: pendingQuestions.length > 0 ? pendingQuestions.length : undefined },
  ]

  return (
    <>
      {/* Question Notification Toast (Phase A) */}
      <QuestionNotification
        question={newQuestionAlert}
        onDismiss={clearQuestionAlert}
        onAnswer={handleAnswerQuestion}
        autoDismissMs={15000}
      />

      {/* Question Answer Modal (Phase A Day 4) */}
      <QuestionBubble
        question={selectedQuestion}
        isOpen={isQuestionModalOpen}
        onClose={handleCloseQuestionModal}
        onSubmit={handleSubmitAnswer}
        onSkip={handleSkipQuestion}
      />

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
                title="감각 페이지"
              >
                <Eye className="w-5 h-5 text-white" />
              </Link>
              <Link
                href="/sleep"
                className="p-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 active:scale-95 transition-all touch-manipulation"
                title="수면 & 기억 통합"
              >
                <Moon className="w-5 h-5 text-white" />
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
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            <BabyStateCard state={babyState as any} isLoading={isLoading} />
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            <ActivityLog experiences={experiences as any} isLoading={isLoading} />
          </div>

          {/* Right Column */}
          <div className="space-y-4 md:space-y-6">
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            <EmotionRadar state={babyState as any} isLoading={isLoading} />

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
            <div className="flex bg-slate-800/50 rounded-xl p-1 border border-slate-700/50 overflow-x-auto">
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
                  {tab.badge && (
                    <span className="relative z-10 ml-1 min-w-[1.25rem] h-5 flex items-center justify-center text-xs bg-pink-500 text-white rounded-full px-1">
                      {tab.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Chart Content */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
            {activeTab === 'growth' && (
              <>
                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                <GrowthChart experiences={allExperiences as any} isLoading={isLoading} />
                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                <ExperienceDistribution experiences={allExperiences as any} isLoading={isLoading} />
              </>
            )}
            {activeTab === 'timeline' && (
              <div className="lg:col-span-2">
                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                <EmotionTimeline emotionLogs={emotionLogs as any} isLoading={isLoading} />
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
            {activeTab === 'curiosity' && (
              <div className="lg:col-span-2">
                <CuriosityCard className="h-full" />
              </div>
            )}
            {activeTab === 'backprop' && (
              <div className="lg:col-span-2">
                <TextualBackpropCard className="h-full" />
              </div>
            )}
            {activeTab === 'questions' && (
              <div className="lg:col-span-2">
                <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm">
                  <QuestionList
                    questions={pendingQuestions}
                    isLoading={isQuestionsLoading}
                    onSelectQuestion={handleSelectQuestion}
                    onSkipQuestion={handleSkipQuestion}
                  />
                </div>
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
