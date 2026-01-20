'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMicrophone } from '@/hooks/useMicrophone'
import {
  WaveformVisualizer,
  AudioLevelIndicator,
  RecordingTimer,
} from './WaveformVisualizer'
import {
  Mic,
  MicOff,
  Square,
  Play,
  Pause,
  Send,
  RefreshCw,
  AlertCircle,
  Trash2,
  Volume2,
} from 'lucide-react'

export interface AudioRecorderProps {
  onSubmit: (audioBlob: Blob, duration: number) => void
  onClose?: () => void
  className?: string
  maxDuration?: number
}

export function AudioRecorder({
  onSubmit,
  onClose,
  className = '',
  maxDuration = 60,
}: AudioRecorderProps) {
  const {
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
  } = useMicrophone({ maxDuration })

  // Playback state
  const [isPlaying, setIsPlaying] = useState(false)
  const [playbackProgress, setPlaybackProgress] = useState(0)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Handle playback
  const handlePlayPause = useCallback(() => {
    if (!audioRef.current || !audioUrl) return

    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play()
    }
  }, [isPlaying, audioUrl])

  // Setup audio element
  useEffect(() => {
    if (!audioUrl) {
      setIsPlaying(false)
      setPlaybackProgress(0)
      return
    }

    const audio = new Audio(audioUrl)
    audioRef.current = audio

    audio.onplay = () => setIsPlaying(true)
    audio.onpause = () => setIsPlaying(false)
    audio.onended = () => {
      setIsPlaying(false)
      setPlaybackProgress(0)
    }
    audio.ontimeupdate = () => {
      if (audio.duration) {
        setPlaybackProgress((audio.currentTime / audio.duration) * 100)
      }
    }

    return () => {
      audio.pause()
      audio.src = ''
    }
  }, [audioUrl])

  // Handle submit
  const handleSubmit = useCallback(() => {
    if (audioBlob) {
      onSubmit(audioBlob, duration)
      clearRecording()
    }
  }, [audioBlob, duration, onSubmit, clearRecording])

  // Handle record button
  const handleRecordButton = useCallback(async () => {
    if (isRecording) {
      if (isPaused) {
        resumeRecording()
      } else {
        pauseRecording()
      }
    } else if (audioBlob) {
      // Already have a recording, clear it and start new
      clearRecording()
      await startRecording()
    } else {
      await startRecording()
    }
  }, [isRecording, isPaused, audioBlob, startRecording, pauseRecording, resumeRecording, clearRecording])

  // Handle stop button
  const handleStopButton = useCallback(async () => {
    await stopRecording()
  }, [stopRecording])

  return (
    <div className={`bg-gradient-to-br from-slate-800/90 to-slate-900/90 rounded-2xl border border-slate-700/50 backdrop-blur-sm overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700/50">
        <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
          <Mic className="w-5 h-5 text-cyan-400" />
          마이크
        </h3>
        {onClose && (
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 transition-colors"
          >
            <MicOff className="w-5 h-5 text-slate-300" />
          </button>
        )}
      </div>

      {/* Visualizer Area */}
      <div className="relative h-32 bg-slate-900 flex items-center justify-center">
        <AnimatePresence mode="wait">
          {/* Error state */}
          {error && (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex flex-col items-center justify-center p-4"
            >
              <AlertCircle className="w-10 h-10 text-rose-400 mb-3" />
              <p className="text-slate-400 text-center text-sm">{error}</p>
              <button
                onClick={requestPermission}
                className="mt-3 px-4 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg hover:bg-cyan-500/30 transition-colors text-sm"
              >
                다시 시도
              </button>
            </motion.div>
          )}

          {/* Loading state */}
          {isLoading && !error && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex items-center justify-center"
            >
              <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
            </motion.div>
          )}

          {/* Not started state */}
          {!isRecording && !audioBlob && !isLoading && !error && (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex flex-col items-center justify-center p-4"
            >
              <MicOff className="w-10 h-10 text-slate-500 mb-3" />
              <p className="text-slate-400 text-center text-sm">
                마이크 버튼을 눌러 녹음을 시작하세요
              </p>
            </motion.div>
          )}

          {/* Recording state - waveform */}
          {isRecording && !error && (
            <motion.div
              key="recording"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 p-4"
            >
              <WaveformVisualizer
                analyserNode={analyserNode}
                isActive={isRecording && !isPaused}
              />
              {/* Recording indicator */}
              <div className="absolute top-2 left-2 flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${isPaused ? 'bg-amber-500' : 'bg-rose-500 animate-pulse'}`} />
                <span className="text-xs text-slate-400">
                  {isPaused ? '일시정지' : '녹음 중'}
                </span>
              </div>
            </motion.div>
          )}

          {/* Playback state */}
          {audioBlob && !isRecording && !error && (
            <motion.div
              key="playback"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex flex-col items-center justify-center p-4"
            >
              <Volume2 className={`w-10 h-10 mb-3 ${isPlaying ? 'text-cyan-400' : 'text-slate-500'}`} />
              <p className="text-slate-300 text-sm mb-2">녹음 완료</p>
              {/* Playback progress */}
              <div className="w-full max-w-[200px] h-1 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-cyan-400 transition-all duration-100"
                  style={{ width: `${playbackProgress}%` }}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Timer */}
      {(isRecording || audioBlob) && (
        <div className="px-4 py-3 border-t border-slate-700/50">
          <RecordingTimer
            duration={duration}
            maxDuration={isRecording ? maxDuration : undefined}
          />
        </div>
      )}

      {/* Controls */}
      <div className="p-4 flex items-center justify-center gap-4">
        {/* Recording controls */}
        {isRecording ? (
          <>
            {/* Pause/Resume */}
            <button
              onClick={handleRecordButton}
              className="p-3 rounded-full bg-slate-700/50 hover:bg-slate-700 transition-colors"
            >
              {isPaused ? (
                <Play className="w-6 h-6 text-slate-300" />
              ) : (
                <Pause className="w-6 h-6 text-slate-300" />
              )}
            </button>

            {/* Stop */}
            <button
              onClick={handleStopButton}
              className="p-5 rounded-full bg-rose-500 hover:bg-rose-600 transition-colors shadow-lg shadow-rose-500/30"
            >
              <Square className="w-8 h-8 text-white" />
            </button>

            {/* Level indicator placeholder */}
            <div className="w-[52px]">
              <AudioLevelIndicator
                level={audioLevel}
                isActive={isRecording && !isPaused}
                size={52}
              />
            </div>
          </>
        ) : audioBlob ? (
          <>
            {/* Delete */}
            <button
              onClick={clearRecording}
              className="p-3 rounded-full bg-slate-700/50 hover:bg-slate-700 transition-colors"
            >
              <Trash2 className="w-6 h-6 text-slate-300" />
            </button>

            {/* Play/Pause */}
            <button
              onClick={handlePlayPause}
              className="p-4 rounded-full bg-slate-700/50 hover:bg-slate-700 transition-colors"
            >
              {isPlaying ? (
                <Pause className="w-6 h-6 text-cyan-400" />
              ) : (
                <Play className="w-6 h-6 text-cyan-400" />
              )}
            </button>

            {/* Submit */}
            <button
              onClick={handleSubmit}
              className="p-5 rounded-full bg-emerald-500 hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/30"
            >
              <Send className="w-8 h-8 text-white" />
            </button>
          </>
        ) : (
          /* Start recording */
          <button
            onClick={startRecording}
            disabled={isLoading}
            className="p-5 rounded-full bg-cyan-500 hover:bg-cyan-600 disabled:opacity-50 transition-colors shadow-lg shadow-cyan-500/30"
          >
            <Mic className="w-8 h-8 text-white" />
          </button>
        )}
      </div>

      {/* Permission info */}
      {isPermissionGranted && !isRecording && !audioBlob && (
        <div className="px-4 pb-4">
          <div className="text-xs text-slate-500 text-center">
            마이크 권한이 허용되었습니다. 버튼을 눌러 녹음하세요.
          </div>
        </div>
      )}
    </div>
  )
}

// Compact version for embedding
export function AudioRecorderCompact({
  onSubmit,
  className = '',
}: Omit<AudioRecorderProps, 'onClose'>) {
  const {
    isRecording,
    audioBlob,
    duration,
    audioLevel,
    startRecording,
    stopRecording,
    clearRecording,
  } = useMicrophone({ maxDuration: 30 })

  const [isSending, setIsSending] = useState(false)

  const handleSubmit = useCallback(async () => {
    if (audioBlob) {
      setIsSending(true)
      onSubmit(audioBlob, duration)
      clearRecording()
      setIsSending(false)
    }
  }, [audioBlob, duration, onSubmit, clearRecording])

  return (
    <div className={`relative rounded-xl overflow-hidden bg-slate-800 ${className}`}>
      <div className="flex items-center justify-center gap-3 p-4">
        {isRecording ? (
          <>
            <AudioLevelIndicator level={audioLevel} isActive={true} size={40} />
            <span className="text-sm text-slate-300 font-mono">
              {Math.floor(duration)}s
            </span>
            <button
              onClick={stopRecording}
              className="p-2 rounded-full bg-rose-500 hover:bg-rose-600 transition-colors"
            >
              <Square className="w-5 h-5 text-white" />
            </button>
          </>
        ) : audioBlob ? (
          <>
            <button
              onClick={clearRecording}
              className="p-2 rounded-full bg-slate-700 hover:bg-slate-600 transition-colors"
            >
              <Trash2 className="w-5 h-5 text-slate-300" />
            </button>
            <span className="text-sm text-slate-300">{Math.floor(duration)}s</span>
            <button
              onClick={handleSubmit}
              disabled={isSending}
              className="p-2 rounded-full bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 transition-colors"
            >
              {isSending ? (
                <RefreshCw className="w-5 h-5 text-white animate-spin" />
              ) : (
                <Send className="w-5 h-5 text-white" />
              )}
            </button>
          </>
        ) : (
          <button
            onClick={startRecording}
            className="p-3 rounded-full bg-cyan-500 hover:bg-cyan-600 transition-colors"
          >
            <Mic className="w-6 h-6 text-white" />
          </button>
        )}
      </div>
    </div>
  )
}
