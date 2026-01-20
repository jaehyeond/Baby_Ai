'use client'

import { useState, useEffect, useCallback } from 'react'

export interface Settings {
  // Theme
  theme: 'dark' | 'light' | 'system'

  // Notifications
  notificationsEnabled: boolean
  notifyOnNewExperience: boolean
  notifyOnStageChange: boolean
  notifyOnEmotionSpike: boolean

  // Display
  compactMode: boolean
  showAnimations: boolean
  autoRefresh: boolean
  refreshInterval: number // seconds

  // Data
  maxExperiencesToShow: number
  maxEmotionLogsToShow: number
}

const DEFAULT_SETTINGS: Settings = {
  theme: 'dark',
  notificationsEnabled: false,
  notifyOnNewExperience: true,
  notifyOnStageChange: true,
  notifyOnEmotionSpike: true,
  compactMode: false,
  showAnimations: true,
  autoRefresh: true,
  refreshInterval: 30,
  maxExperiencesToShow: 10,
  maxEmotionLogsToShow: 50,
}

const STORAGE_KEY = 'baby-dashboard-settings'

export function useSettings() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS)
  const [isLoaded, setIsLoaded] = useState(false)

  // Load settings from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        setSettings({ ...DEFAULT_SETTINGS, ...parsed })
      }
    } catch (e) {
      console.error('Failed to load settings:', e)
    }
    setIsLoaded(true)
  }, [])

  // Save settings to localStorage
  const saveSettings = useCallback((newSettings: Partial<Settings>) => {
    setSettings((prev) => {
      const updated = { ...prev, ...newSettings }
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
      } catch (e) {
        console.error('Failed to save settings:', e)
      }
      return updated
    })
  }, [])

  // Reset to defaults
  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_SETTINGS)
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch (e) {
      console.error('Failed to reset settings:', e)
    }
  }, [])

  return {
    settings,
    saveSettings,
    resetSettings,
    isLoaded,
  }
}
