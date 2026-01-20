'use client'

import { useState, useCallback, useRef, useEffect } from 'react'

export type CameraFacing = 'user' | 'environment'

export interface UseCameraReturn {
  // Stream state
  stream: MediaStream | null
  isPermissionGranted: boolean
  isLoading: boolean
  error: string | null

  // Video ref
  videoRef: React.RefObject<HTMLVideoElement | null>

  // Actions
  startCamera: () => Promise<void>
  stopCamera: () => void
  capturePhoto: () => Promise<Blob | null>
  switchCamera: () => Promise<void>

  // Camera info
  currentFacing: CameraFacing
  hasMultipleCameras: boolean
}

export interface UseCameraOptions {
  autoStart?: boolean
  initialFacing?: CameraFacing
  width?: number
  height?: number
}

export function useCamera(options: UseCameraOptions = {}): UseCameraReturn {
  const {
    autoStart = false,
    initialFacing = 'environment',
    width = 1280,
    height = 720,
  } = options

  // State
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [isPermissionGranted, setIsPermissionGranted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentFacing, setCurrentFacing] = useState<CameraFacing>(initialFacing)
  const [hasMultipleCameras, setHasMultipleCameras] = useState(false)

  // Refs
  const videoRef = useRef<HTMLVideoElement>(null)

  // Connect stream to video element when stream changes
  useEffect(() => {
    if (!stream) {
      return
    }

    let retryCount = 0
    const maxRetries = 30 // 약 500ms 동안 재시도

    // Wait for video element to be available
    const connectVideo = () => {
      const video = videoRef.current
      if (!video) {
        retryCount++
        if (retryCount < maxRetries) {
          requestAnimationFrame(connectVideo)
        }
        return
      }

      // 기존 srcObject가 있으면 먼저 정리
      if (video.srcObject && video.srcObject !== stream) {
        video.srcObject = null
      }

      // srcObject 할당
      video.srcObject = stream

      // 명시적으로 load 호출 (일부 모바일 브라우저에서 필요)
      video.load()

      const playVideo = async () => {
        try {
          // play() 호출 전에 약간의 지연
          await new Promise(resolve => setTimeout(resolve, 100))
          await video.play()
        } catch (e) {
          // NotAllowedError는 사용자 상호작용이 필요한 경우 - autoplay가 처리함
          if (e instanceof Error && e.name !== 'AbortError') {
            console.warn('[Camera] Play failed:', e.name)
          }
        }
      }

      // loadedmetadata 이벤트에서 play 시도
      const handleLoadedMetadata = () => {
        playVideo()
      }

      video.addEventListener('loadedmetadata', handleLoadedMetadata, { once: true })

      // 이미 메타데이터가 로드된 경우 바로 play
      if (video.readyState >= 1) {
        playVideo()
      }

      // Fallback: 500ms 후에도 재생되지 않으면 강제 play 시도
      const fallbackTimeout = setTimeout(() => {
        if (video.paused && video.srcObject) {
          playVideo()
        }
      }, 500)

      return () => {
        video.removeEventListener('loadedmetadata', handleLoadedMetadata)
        clearTimeout(fallbackTimeout)
      }
    }

    const cleanup = connectVideo()

    return () => {
      cleanup?.()
    }
  }, [stream])

  // Check for multiple cameras
  useEffect(() => {
    async function checkCameras() {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices()
        const videoDevices = devices.filter(device => device.kind === 'videoinput')
        setHasMultipleCameras(videoDevices.length > 1)
      } catch {
        setHasMultipleCameras(false)
      }
    }
    checkCameras()
  }, [])

  // Start camera
  const startCamera = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Check if getUserMedia is supported
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('카메라가 지원되지 않는 브라우저입니다.')
      }

      // Request camera permission
      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: currentFacing,
          width: { ideal: width },
          height: { ideal: height },
        },
        audio: false,
      }

      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints)
      setStream(mediaStream)
      setIsPermissionGranted(true)
      // Video connection is handled by useEffect
    } catch (err) {
      const message = err instanceof Error ? err.message : '카메라 접근에 실패했습니다.'

      // Handle specific errors
      if (err instanceof DOMException) {
        if (err.name === 'NotAllowedError') {
          setError('카메라 권한이 거부되었습니다. 설정에서 권한을 허용해주세요.')
        } else if (err.name === 'NotFoundError') {
          setError('카메라를 찾을 수 없습니다.')
        } else if (err.name === 'NotReadableError') {
          setError('카메라가 다른 앱에서 사용 중입니다.')
        } else {
          setError(message)
        }
      } else {
        setError(message)
      }

      setIsPermissionGranted(false)
    } finally {
      setIsLoading(false)
    }
  }, [currentFacing, width, height])

  // Stop camera
  const stopCamera = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
  }, [stream])

  // Switch camera (front/back)
  const switchCamera = useCallback(async () => {
    if (!hasMultipleCameras) return

    // Stop current stream
    stopCamera()

    // Switch facing mode
    const newFacing: CameraFacing = currentFacing === 'user' ? 'environment' : 'user'
    setCurrentFacing(newFacing)

    // Restart with new facing
    // Note: startCamera will use the updated currentFacing via closure
    // So we need to manually set constraints here
    setIsLoading(true)
    setError(null)

    try {
      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: newFacing,
          width: { ideal: width },
          height: { ideal: height },
        },
        audio: false,
      }

      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints)
      setStream(mediaStream)
      // Video connection is handled by useEffect
    } catch (err) {
      const message = err instanceof Error ? err.message : '카메라 전환에 실패했습니다.'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }, [currentFacing, hasMultipleCameras, stopCamera, width, height])

  // Capture photo
  const capturePhoto = useCallback(async (): Promise<Blob | null> => {
    if (!videoRef.current || !stream) {
      setError('카메라가 활성화되지 않았습니다.')
      return null
    }

    try {
      const video = videoRef.current
      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight

      const ctx = canvas.getContext('2d')
      if (!ctx) {
        throw new Error('Canvas context를 생성할 수 없습니다.')
      }

      // Draw current frame
      ctx.drawImage(video, 0, 0)

      // Convert to blob
      return new Promise((resolve, reject) => {
        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(blob)
            } else {
              reject(new Error('이미지 변환에 실패했습니다.'))
            }
          },
          'image/jpeg',
          0.9
        )
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : '사진 캡처에 실패했습니다.'
      setError(message)
      return null
    }
  }, [stream])

  // Auto start
  useEffect(() => {
    if (autoStart) {
      startCamera()
    }

    // Cleanup on unmount
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop())
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStart])

  return {
    stream,
    isPermissionGranted,
    isLoading,
    error,
    videoRef,
    startCamera,
    stopCamera,
    capturePhoto,
    switchCamera,
    currentFacing,
    hasMultipleCameras,
  }
}
