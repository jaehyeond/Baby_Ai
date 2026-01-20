'use client'

import { useState, useEffect, useCallback } from 'react'

export type NotificationPermission = 'default' | 'granted' | 'denied'

export function useNotifications() {
  const [permission, setPermission] = useState<NotificationPermission>('default')
  const [isSupported, setIsSupported] = useState(false)

  useEffect(() => {
    // Check if notifications are supported
    const supported = 'Notification' in window
    setIsSupported(supported)

    if (supported) {
      setPermission(Notification.permission as NotificationPermission)
    }
  }, [])

  const requestPermission = useCallback(async () => {
    if (!isSupported) {
      return 'denied' as NotificationPermission
    }

    try {
      const result = await Notification.requestPermission()
      setPermission(result as NotificationPermission)
      return result as NotificationPermission
    } catch (e) {
      console.error('Failed to request notification permission:', e)
      return 'denied' as NotificationPermission
    }
  }, [isSupported])

  const sendNotification = useCallback(
    (title: string, options?: NotificationOptions) => {
      if (!isSupported || permission !== 'granted') {
        return null
      }

      try {
        const notification = new Notification(title, {
          icon: '/icons/icon-192x192.png',
          badge: '/icons/icon-72x72.png',
          ...options,
        })

        // Auto close after 5 seconds
        setTimeout(() => notification.close(), 5000)

        return notification
      } catch (e) {
        console.error('Failed to send notification:', e)
        return null
      }
    },
    [isSupported, permission]
  )

  // Notification helpers for specific events
  const notifyNewExperience = useCallback(
    (task: string, success: boolean) => {
      return sendNotification('새로운 경험', {
        body: `${task} - ${success ? '성공!' : '실패'}`,
        tag: 'new-experience',
      })
    },
    [sendNotification]
  )

  const notifyStageChange = useCallback(
    (oldStage: number, newStage: number) => {
      return sendNotification('발달 단계 변화!', {
        body: `Stage ${oldStage} → Stage ${newStage}`,
        tag: 'stage-change',
      })
    },
    [sendNotification]
  )

  const notifyEmotionSpike = useCallback(
    (emotion: string, value: number) => {
      return sendNotification('감정 변화 감지', {
        body: `${emotion}: ${(value * 100).toFixed(0)}%`,
        tag: 'emotion-spike',
      })
    },
    [sendNotification]
  )

  return {
    permission,
    isSupported,
    requestPermission,
    sendNotification,
    notifyNewExperience,
    notifyStageChange,
    notifyEmotionSpike,
  }
}
