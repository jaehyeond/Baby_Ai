'use client'

import { useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { supabase } from '@/lib/supabase'
import { CameraCapture } from '@/components'
import {
  Camera,
  Mic,
  MessageSquare,
  ArrowLeft,
  Send,
  Image as ImageIcon,
  Eye,
  Sparkles,
  RefreshCw,
  AlertCircle,
  CheckCircle,
} from 'lucide-react'
import Link from 'next/link'

type SenseTab = 'camera' | 'microphone' | 'conversation'

interface VisualExperience {
  id: string
  image_url: string
  description: string
  objects_detected: Array<{
    name: string
    category: string
    confidence: number
  }>
  scene_type: string
  emotional_response: Record<string, number>
  created_at: string
}

// Transform Supabase row to local type
function transformVisualExperience(row: Record<string, unknown>): VisualExperience {
  return {
    id: row.id as string,
    image_url: (row.image_url as string) || '',
    description: (row.description as string) || '',
    objects_detected: (row.objects_detected as VisualExperience['objects_detected']) || [],
    scene_type: (row.scene_type as string) || 'unknown',
    emotional_response: (row.emotional_response as Record<string, number>) || {},
    created_at: (row.created_at as string) || new Date().toISOString(),
  }
}

export default function SensePage() {
  const [activeTab, setActiveTab] = useState<SenseTab>('camera')
  const [isProcessing, setIsProcessing] = useState(false)
  const [result, setResult] = useState<VisualExperience | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [recentVisuals, setRecentVisuals] = useState<VisualExperience[]>([])

  // Fetch recent visual experiences
  useEffect(() => {
    async function fetchRecent() {
      try {
        const { data } = await supabase
          .from('visual_experiences')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(5)

        if (data) {
          setRecentVisuals(data.map(transformVisualExperience))
        }
      } catch (e) {
        console.error('Failed to fetch recent visuals:', e)
      }
    }

    fetchRecent()

    // Subscribe to changes
    const channel = supabase
      .channel('visual_experiences')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'visual_experiences' }, (payload) => {
        setRecentVisuals((prev) => [transformVisualExperience(payload.new as Record<string, unknown>), ...prev.slice(0, 4)])
      })
      .subscribe()

    return () => {
      channel.unsubscribe()
    }
  }, [])

  // Handle image capture
  const handleCapture = useCallback(async (imageBlob: Blob) => {
    setIsProcessing(true)
    setError(null)
    setResult(null)

    try {
      // Convert blob to base64
      const reader = new FileReader()
      const base64Promise = new Promise<string>((resolve) => {
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1]
          resolve(base64)
        }
      })
      reader.readAsDataURL(imageBlob)
      const base64Data = await base64Promise

      // Send to API for processing
      const response = await fetch('/api/vision/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image: base64Data,
          mime_type: imageBlob.type || 'image/jpeg',
        }),
      })

      if (!response.ok) {
        throw new Error('이미지 처리에 실패했습니다.')
      }

      const data = await response.json()
      setResult(data.visual_experience)

    } catch (err) {
      const message = err instanceof Error ? err.message : '처리 중 오류가 발생했습니다.'
      setError(message)
    } finally {
      setIsProcessing(false)
    }
  }, [])

  const tabs: { key: SenseTab; label: string; icon: typeof Camera; disabled?: boolean }[] = [
    { key: 'camera', label: '카메라', icon: Camera },
    { key: 'microphone', label: '마이크', icon: Mic, disabled: true },
    { key: 'conversation', label: '대화', icon: MessageSquare, disabled: true },
  ]

  return (
    <main className="min-h-screen p-4 md:p-8">
      {/* Header */}
      <header className="mb-6 md:mb-8">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </Link>
          <div>
            <h1 className="text-xl sm:text-2xl md:text-3xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              Sense Input
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Phase 4: 멀티모달 입력으로 Baby AI와 상호작용
            </p>
          </div>
        </div>
      </header>

      {/* Tab Selector */}
      <div className="flex bg-slate-800/50 rounded-xl p-1 mb-6 border border-slate-700/50">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => !tab.disabled && setActiveTab(tab.key)}
            disabled={tab.disabled}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.key
                ? 'text-white bg-cyan-500/30'
                : tab.disabled
                ? 'text-slate-600 cursor-not-allowed'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            <span>{tab.label}</span>
            {tab.disabled && (
              <span className="text-xs px-1.5 py-0.5 bg-slate-700 rounded">Soon</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Input Area */}
        <div className="lg:col-span-2">
          <AnimatePresence mode="wait">
            {activeTab === 'camera' && (
              <motion.div
                key="camera"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
              >
                <CameraCapture
                  onCapture={handleCapture}
                  className="w-full"
                />

                {/* Processing indicator */}
                {isProcessing && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-4 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50 flex items-center gap-3"
                  >
                    <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin" />
                    <div>
                      <p className="text-slate-200 font-medium">이미지 처리 중...</p>
                      <p className="text-slate-500 text-sm">Baby AI가 이미지를 분석하고 있습니다</p>
                    </div>
                  </motion.div>
                )}

                {/* Error */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-4 p-4 bg-rose-500/10 rounded-xl border border-rose-500/30 flex items-center gap-3"
                  >
                    <AlertCircle className="w-5 h-5 text-rose-400" />
                    <p className="text-rose-300">{error}</p>
                  </motion.div>
                )}

                {/* Result */}
                {result && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-4 p-6 bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl border border-slate-700/50"
                  >
                    <div className="flex items-center gap-2 mb-4">
                      <CheckCircle className="w-5 h-5 text-emerald-400" />
                      <h3 className="text-lg font-semibold text-slate-100">분석 완료</h3>
                    </div>

                    {/* Description */}
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-slate-400 mb-2">장면 설명</h4>
                      <p className="text-slate-200">{result.description}</p>
                    </div>

                    {/* Scene type */}
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-slate-400 mb-2">장면 유형</h4>
                      <span className="px-3 py-1 bg-cyan-500/20 text-cyan-400 rounded-full text-sm">
                        {result.scene_type}
                      </span>
                    </div>

                    {/* Detected objects */}
                    {result.objects_detected && result.objects_detected.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-sm font-medium text-slate-400 mb-2">감지된 객체</h4>
                        <div className="flex flex-wrap gap-2">
                          {result.objects_detected.map((obj, i) => (
                            <span
                              key={i}
                              className="px-3 py-1 bg-slate-700/50 text-slate-300 rounded-full text-sm"
                            >
                              {obj.name}
                              <span className="ml-1 text-slate-500">
                                ({Math.round(obj.confidence * 100)}%)
                              </span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Emotional response */}
                    {result.emotional_response && Object.keys(result.emotional_response).length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-slate-400 mb-2">감정 반응</h4>
                        <div className="flex gap-4">
                          {Object.entries(result.emotional_response).map(([key, value]) => (
                            <div key={key} className="text-center">
                              <div className="text-lg font-bold text-cyan-400">
                                {value > 0 ? '+' : ''}{(value as number * 100).toFixed(0)}%
                              </div>
                              <div className="text-xs text-slate-500">{key.replace('_change', '')}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </motion.div>
            )}

            {activeTab === 'microphone' && (
              <motion.div
                key="microphone"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="p-8 bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl border border-slate-700/50 text-center"
              >
                <Mic className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-slate-300 mb-2">음성 입력</h3>
                <p className="text-slate-500">Phase 4.2에서 구현 예정</p>
              </motion.div>
            )}

            {activeTab === 'conversation' && (
              <motion.div
                key="conversation"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="p-8 bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl border border-slate-700/50 text-center"
              >
                <MessageSquare className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-slate-300 mb-2">대화</h3>
                <p className="text-slate-500">Phase 4.3에서 구현 예정</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Sidebar - Recent Visual Experiences */}
        <div className="lg:col-span-1">
          <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl border border-slate-700/50 p-4">
            <h3 className="text-lg font-semibold text-slate-100 mb-4 flex items-center gap-2">
              <Eye className="w-5 h-5 text-purple-400" />
              최근 시각 경험
            </h3>

            {recentVisuals.length === 0 ? (
              <div className="text-center py-8">
                <ImageIcon className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-500 text-sm">아직 시각 경험이 없습니다</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentVisuals.map((visual) => (
                  <motion.div
                    key={visual.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="p-3 bg-slate-800/50 rounded-xl border border-slate-700/30"
                  >
                    <div className="flex items-start gap-3">
                      {visual.image_url ? (
                        <img
                          src={visual.image_url}
                          alt={visual.scene_type}
                          className="w-16 h-16 rounded-lg object-cover"
                        />
                      ) : (
                        <div className="w-16 h-16 rounded-lg bg-slate-700 flex items-center justify-center">
                          <ImageIcon className="w-6 h-6 text-slate-500" />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-slate-200 line-clamp-2">
                          {visual.description}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs px-2 py-0.5 bg-slate-700 text-slate-400 rounded">
                            {visual.scene_type}
                          </span>
                          <span className="text-xs text-slate-500">
                            {new Date(visual.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          {/* Info Card */}
          <div className="mt-4 p-4 bg-gradient-to-br from-cyan-500/10 to-purple-500/10 rounded-xl border border-cyan-500/20">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-5 h-5 text-cyan-400" />
              <h4 className="font-medium text-slate-200">Phase 4 정보</h4>
            </div>
            <p className="text-sm text-slate-400">
              카메라로 이미지를 캡처하면 Baby AI가 분석하고 학습합니다.
              감지된 객체와 장면 유형이 기억에 저장됩니다.
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
