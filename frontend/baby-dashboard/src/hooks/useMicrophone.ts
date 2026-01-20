'use client'

import { useState, useCallback, useRef, useEffect } from 'react'

export interface UseMicrophoneReturn {
  // Recording state
  isRecording: boolean
  isPaused: boolean
  isPermissionGranted: boolean
  isLoading: boolean
  error: string | null

  // Audio data
  audioBlob: Blob | null
  audioUrl: string | null
  duration: number

  // Real-time data
  audioLevel: number
  analyserNode: AnalyserNode | null

  // Actions
  startRecording: () => Promise<void>
  stopRecording: () => Promise<Blob | null>
  pauseRecording: () => void
  resumeRecording: () => void
  clearRecording: () => void

  // Permissions
  requestPermission: () => Promise<boolean>
}

export interface UseMicrophoneOptions {
  maxDuration?: number // in seconds
  sampleRate?: number
  channelCount?: number
  mimeType?: string
}

export function useMicrophone(options: UseMicrophoneOptions = {}): UseMicrophoneReturn {
  const {
    maxDuration = 60, // 1 minute default
    sampleRate = 44100,
    channelCount = 1,
    mimeType = 'audio/webm;codecs=opus',
  } = options

  // State
  const [isRecording, setIsRecording] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [isPermissionGranted, setIsPermissionGranted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [duration, setDuration] = useState(0)
  const [audioLevel, setAudioLevel] = useState(0)
  const [analyserNode, setAnalyserNode] = useState<AnalyserNode | null>(null)

  // Refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const durationIntervalRef = useRef<number | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const startTimeRef = useRef<number>(0)
  const pausedDurationRef = useRef<number>(0)

  // Cleanup function
  const cleanup = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }
    if (durationIntervalRef.current) {
      clearInterval(durationIntervalRef.current)
      durationIntervalRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    analyserRef.current = null
    setAnalyserNode(null)
  }, [])

  // Request microphone permission
  const requestPermission = useCallback(async (): Promise<boolean> => {
    try {
      setIsLoading(true)
      setError(null)

      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('마이크가 지원되지 않는 브라우저입니다.')
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate,
          channelCount,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })

      // Permission granted, stop the stream immediately
      stream.getTracks().forEach(track => track.stop())
      setIsPermissionGranted(true)
      return true
    } catch (err) {
      if (err instanceof DOMException) {
        if (err.name === 'NotAllowedError') {
          setError('마이크 권한이 거부되었습니다. 설정에서 권한을 허용해주세요.')
        } else if (err.name === 'NotFoundError') {
          setError('마이크를 찾을 수 없습니다.')
        } else if (err.name === 'NotReadableError') {
          setError('마이크가 다른 앱에서 사용 중입니다.')
        } else {
          setError(err.message)
        }
      } else {
        const message = err instanceof Error ? err.message : '마이크 접근에 실패했습니다.'
        setError(message)
      }
      setIsPermissionGranted(false)
      return false
    } finally {
      setIsLoading(false)
    }
  }, [sampleRate, channelCount])

  // Audio level monitoring
  const monitorAudioLevel = useCallback(() => {
    if (!analyserRef.current) return

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)

    const updateLevel = () => {
      if (!analyserRef.current) return

      analyserRef.current.getByteFrequencyData(dataArray)

      // Calculate average level
      const sum = dataArray.reduce((acc, val) => acc + val, 0)
      const average = sum / dataArray.length
      const normalizedLevel = average / 255

      setAudioLevel(normalizedLevel)

      animationFrameRef.current = requestAnimationFrame(updateLevel)
    }

    updateLevel()
  }, [])

  // Start recording
  const startRecording = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    cleanup()

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('마이크가 지원되지 않는 브라우저입니다.')
      }

      // Get microphone stream
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate,
          channelCount,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })

      streamRef.current = stream
      setIsPermissionGranted(true)

      // Setup audio context for visualization
      const audioContext = new AudioContext()
      audioContextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.8
      source.connect(analyser)

      analyserRef.current = analyser
      setAnalyserNode(analyser)

      // Start audio level monitoring
      monitorAudioLevel()

      // Setup MediaRecorder
      // Check for supported mimeType
      let selectedMimeType = mimeType
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        // Fallback options
        const fallbacks = ['audio/webm', 'audio/mp4', 'audio/ogg']
        selectedMimeType = fallbacks.find(type => MediaRecorder.isTypeSupported(type)) || ''
      }

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: selectedMimeType || undefined,
      })

      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onerror = (event) => {
        console.error('[Microphone] Recording error:', event)
        setError('녹음 중 오류가 발생했습니다.')
      }

      // Start recording
      mediaRecorder.start(100) // Collect data every 100ms
      setIsRecording(true)
      setIsPaused(false)
      startTimeRef.current = Date.now()
      pausedDurationRef.current = 0

      // Duration tracking
      durationIntervalRef.current = window.setInterval(() => {
        if (!isPaused) {
          const elapsed = (Date.now() - startTimeRef.current - pausedDurationRef.current) / 1000
          setDuration(Math.min(elapsed, maxDuration))

          // Auto-stop at max duration
          if (elapsed >= maxDuration) {
            stopRecording()
          }
        }
      }, 100)

    } catch (err) {
      if (err instanceof DOMException) {
        if (err.name === 'NotAllowedError') {
          setError('마이크 권한이 거부되었습니다. 설정에서 권한을 허용해주세요.')
        } else if (err.name === 'NotFoundError') {
          setError('마이크를 찾을 수 없습니다.')
        } else if (err.name === 'NotReadableError') {
          setError('마이크가 다른 앱에서 사용 중입니다.')
        } else {
          setError(err.message)
        }
      } else {
        const message = err instanceof Error ? err.message : '녹음을 시작할 수 없습니다.'
        setError(message)
      }
      cleanup()
    } finally {
      setIsLoading(false)
    }
  }, [cleanup, monitorAudioLevel, sampleRate, channelCount, mimeType, maxDuration, isPaused])

  // Stop recording
  const stopRecording = useCallback(async (): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const mediaRecorder = mediaRecorderRef.current

      if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        cleanup()
        setIsRecording(false)
        resolve(null)
        return
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: mediaRecorder.mimeType || 'audio/webm'
        })

        // Cleanup old URL
        if (audioUrl) {
          URL.revokeObjectURL(audioUrl)
        }

        const url = URL.createObjectURL(blob)
        setAudioBlob(blob)
        setAudioUrl(url)
        setIsRecording(false)
        setIsPaused(false)

        cleanup()
        resolve(blob)
      }

      mediaRecorder.stop()
    })
  }, [cleanup, audioUrl])

  // Pause recording
  const pauseRecording = useCallback(() => {
    const mediaRecorder = mediaRecorderRef.current

    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.pause()
      setIsPaused(true)

      // Track pause time for accurate duration
      pausedDurationRef.current += Date.now() - startTimeRef.current
    }
  }, [])

  // Resume recording
  const resumeRecording = useCallback(() => {
    const mediaRecorder = mediaRecorderRef.current

    if (mediaRecorder && mediaRecorder.state === 'paused') {
      mediaRecorder.resume()
      setIsPaused(false)
      startTimeRef.current = Date.now()
    }
  }, [])

  // Clear recording
  const clearRecording = useCallback(() => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
    }
    setAudioBlob(null)
    setAudioUrl(null)
    setDuration(0)
    chunksRef.current = []
  }, [audioUrl])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup()
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl)
      }
    }
  }, [cleanup, audioUrl])

  return {
    isRecording,
    isPaused,
    isPermissionGranted,
    isLoading,
    error,
    audioBlob,
    audioUrl,
    duration,
    audioLevel,
    analyserNode,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    clearRecording,
    requestPermission,
  }
}
