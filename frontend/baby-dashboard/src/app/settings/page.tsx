'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import {
  ArrowLeft,
  Bell,
  RefreshCw,
  Database,
  RotateCcw,
  Smartphone,
} from 'lucide-react'
import { useSettings, useNotifications } from '@/hooks'

export default function SettingsPage() {
  const { settings, saveSettings, resetSettings, isLoaded } = useSettings()
  const { permission, isSupported, requestPermission } = useNotifications()
  const [showResetConfirm, setShowResetConfirm] = useState(false)

  // Handle notification permission request
  const handleEnableNotifications = async () => {
    if (permission === 'granted') {
      saveSettings({ notificationsEnabled: !settings.notificationsEnabled })
    } else if (permission === 'default') {
      const result = await requestPermission()
      if (result === 'granted') {
        saveSettings({ notificationsEnabled: true })
      }
    }
  }

  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin" />
      </div>
    )
  }

  return (
    <main className="min-h-screen p-4 md:p-8 pb-safe">
      {/* Header */}
      <header className="mb-6 md:mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Link
            href="/"
            className="p-2 -ml-2 rounded-lg hover:bg-slate-800 active:scale-95 transition-all touch-manipulation"
          >
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </Link>
          <h1 className="text-xl md:text-2xl font-bold text-slate-100">설정</h1>
        </div>
        <p className="text-sm text-slate-400 ml-9">앱 환경설정 및 알림 관리</p>
      </header>

      <div className="space-y-6 max-w-2xl mx-auto">
        {/* Notifications Section */}
        <SettingsSection title="알림" icon={<Bell className="w-5 h-5" />}>
          {/* Permission Status */}
          {!isSupported ? (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 mb-4">
              <p className="text-sm text-amber-400">
                이 브라우저는 알림을 지원하지 않습니다.
              </p>
            </div>
          ) : permission === 'denied' ? (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4">
              <p className="text-sm text-red-400">
                알림 권한이 거부되었습니다. 브라우저 설정에서 권한을 허용해주세요.
              </p>
            </div>
          ) : null}

          {/* Master Toggle */}
          <SettingsToggle
            label="알림 활성화"
            description={
              permission === 'granted'
                ? '푸시 알림을 받습니다'
                : '알림 권한을 요청합니다'
            }
            checked={settings.notificationsEnabled && permission === 'granted'}
            onChange={handleEnableNotifications}
            disabled={!isSupported || permission === 'denied'}
          />

          {/* Individual Notification Settings */}
          {settings.notificationsEnabled && permission === 'granted' && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-4 space-y-3 pt-4 border-t border-slate-700/50"
            >
              <SettingsToggle
                label="새 경험 알림"
                description="Baby AI가 새로운 경험을 할 때"
                checked={settings.notifyOnNewExperience}
                onChange={(v) => saveSettings({ notifyOnNewExperience: v })}
              />
              <SettingsToggle
                label="발달 단계 변화"
                description="발달 단계가 변경될 때"
                checked={settings.notifyOnStageChange}
                onChange={(v) => saveSettings({ notifyOnStageChange: v })}
              />
              <SettingsToggle
                label="감정 변화 감지"
                description="급격한 감정 변화가 감지될 때"
                checked={settings.notifyOnEmotionSpike}
                onChange={(v) => saveSettings({ notifyOnEmotionSpike: v })}
              />
            </motion.div>
          )}
        </SettingsSection>

        {/* Display Section */}
        <SettingsSection title="디스플레이" icon={<Smartphone className="w-5 h-5" />}>
          <SettingsToggle
            label="애니메이션"
            description="UI 애니메이션 효과"
            checked={settings.showAnimations}
            onChange={(v) => saveSettings({ showAnimations: v })}
          />
          <SettingsToggle
            label="컴팩트 모드"
            description="더 많은 정보를 한 화면에"
            checked={settings.compactMode}
            onChange={(v) => saveSettings({ compactMode: v })}
          />
        </SettingsSection>

        {/* Data Section */}
        <SettingsSection title="데이터" icon={<Database className="w-5 h-5" />}>
          <SettingsToggle
            label="자동 새로고침"
            description="실시간 데이터 자동 업데이트"
            checked={settings.autoRefresh}
            onChange={(v) => saveSettings({ autoRefresh: v })}
          />

          {settings.autoRefresh && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-4"
            >
              <label className="text-sm text-slate-400 mb-2 block">
                새로고침 간격: {settings.refreshInterval}초
              </label>
              <input
                type="range"
                min={10}
                max={120}
                step={10}
                value={settings.refreshInterval}
                onChange={(e) =>
                  saveSettings({ refreshInterval: parseInt(e.target.value) })
                }
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>10초</span>
                <span>120초</span>
              </div>
            </motion.div>
          )}

          <div className="mt-4 pt-4 border-t border-slate-700/50">
            <SettingsRow
              label="표시할 경험 수"
              value={`${settings.maxExperiencesToShow}개`}
            >
              <select
                value={settings.maxExperiencesToShow}
                onChange={(e) =>
                  saveSettings({ maxExperiencesToShow: parseInt(e.target.value) })
                }
                className="bg-slate-700 border-none rounded-lg px-3 py-1.5 text-sm text-slate-200 focus:ring-2 focus:ring-indigo-500"
              >
                <option value={5}>5개</option>
                <option value={10}>10개</option>
                <option value={20}>20개</option>
                <option value={50}>50개</option>
              </select>
            </SettingsRow>
          </div>
        </SettingsSection>

        {/* Reset Section */}
        <SettingsSection title="초기화" icon={<RotateCcw className="w-5 h-5" />}>
          {!showResetConfirm ? (
            <button
              onClick={() => setShowResetConfirm(true)}
              className="w-full py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-medium hover:bg-red-500/20 active:scale-[0.98] transition-all touch-manipulation"
            >
              설정 초기화
            </button>
          ) : (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-red-500/10 border border-red-500/30 rounded-lg p-4"
            >
              <p className="text-sm text-red-400 mb-3">
                모든 설정이 기본값으로 초기화됩니다. 계속하시겠습니까?
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    resetSettings()
                    setShowResetConfirm(false)
                  }}
                  className="flex-1 py-2 rounded-lg bg-red-500 text-white text-sm font-medium hover:bg-red-600 active:scale-[0.98] transition-all touch-manipulation"
                >
                  초기화
                </button>
                <button
                  onClick={() => setShowResetConfirm(false)}
                  className="flex-1 py-2 rounded-lg bg-slate-700 text-slate-300 text-sm font-medium hover:bg-slate-600 active:scale-[0.98] transition-all touch-manipulation"
                >
                  취소
                </button>
              </div>
            </motion.div>
          )}
        </SettingsSection>

        {/* App Info */}
        <div className="text-center py-6 text-slate-500 text-xs">
          <p>Baby Brain Dashboard v1.0.0</p>
          <p className="mt-1">Made with Next.js & Supabase</p>
        </div>
      </div>
    </main>
  )
}

// Helper Components
function SettingsSection({
  title,
  icon,
  children,
}: {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-2xl p-4 md:p-6 border border-slate-700/50 backdrop-blur-sm"
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="text-indigo-400">{icon}</div>
        <h2 className="text-base md:text-lg font-semibold text-slate-100">{title}</h2>
      </div>
      {children}
    </motion.section>
  )
}

function SettingsToggle({
  label,
  description,
  checked,
  onChange,
  disabled,
}: {
  label: string
  description?: string
  checked: boolean
  onChange: (value: boolean) => void
  disabled?: boolean
}) {
  return (
    <div
      className={`flex items-center justify-between gap-4 py-3 ${disabled ? 'opacity-50' : ''}`}
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-200">{label}</p>
        {description && (
          <p className="text-xs text-slate-400 mt-0.5">{description}</p>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => !disabled && onChange(!checked)}
        disabled={disabled}
        style={{
          width: '52px',
          height: '28px',
          borderRadius: '14px',
          backgroundColor: checked ? '#22c55e' : '#6b7280',
          position: 'relative',
          border: 'none',
          cursor: disabled ? 'not-allowed' : 'pointer',
          transition: 'background-color 0.2s ease',
          flexShrink: 0,
        }}
      >
        <span
          style={{
            position: 'absolute',
            top: '2px',
            left: checked ? '26px' : '2px',
            width: '24px',
            height: '24px',
            borderRadius: '50%',
            backgroundColor: '#ffffff',
            boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
            transition: 'left 0.2s ease',
          }}
        />
      </button>
    </div>
  )
}

function SettingsRow({
  label,
  value,
  children,
}: {
  label: string
  value?: string
  children?: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex-1 min-w-0 mr-3">
        <p className="text-sm text-slate-200">{label}</p>
      </div>
      {children || <span className="text-sm text-slate-400">{value}</span>}
    </div>
  )
}

