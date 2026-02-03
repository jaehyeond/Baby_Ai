'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Volume2, VolumeX, Play, Pause, RefreshCw } from 'lucide-react'
import { QuickFeedback } from './FeedbackButtons'

export interface SpeechOutputProps {
  text: string
  audioUrl?: string
  isLoading?: boolean
  autoPlay?: boolean
  className?: string
  onPlayStart?: () => void
  onPlayEnd?: () => void
}

export function SpeechOutput({
  text,
  audioUrl,
  isLoading = false,
  autoPlay = false,
  className = '',
  onPlayStart,
  onPlayEnd,
}: SpeechOutputProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const [isMuted, setIsMuted] = useState(false)
  const [highlightIndex, setHighlightIndex] = useState(-1)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Split text into words for highlighting
  const words = text.split(/\s+/)

  // Setup audio element
  useEffect(() => {
    if (!audioUrl) return

    const audio = new Audio(audioUrl)
    audioRef.current = audio

    audio.onplay = () => {
      setIsPlaying(true)
      onPlayStart?.()
    }

    audio.onpause = () => {
      setIsPlaying(false)
    }

    audio.onended = () => {
      setIsPlaying(false)
      setProgress(0)
      setHighlightIndex(-1)
      onPlayEnd?.()
    }

    audio.ontimeupdate = () => {
      if (audio.duration) {
        const currentProgress = (audio.currentTime / audio.duration) * 100
        setProgress(currentProgress)

        // Estimate word highlighting based on progress
        const wordIndex = Math.floor((currentProgress / 100) * words.length)
        setHighlightIndex(wordIndex)
      }
    }

    // Autoplay if enabled
    if (autoPlay) {
      audio.play().catch(console.warn)
    }

    return () => {
      audio.pause()
      audio.src = ''
    }
  }, [audioUrl, autoPlay, words.length, onPlayStart, onPlayEnd])

  // Toggle play/pause
  const togglePlay = useCallback(() => {
    if (!audioRef.current) return

    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play().catch(console.warn)
    }
  }, [isPlaying])

  // Toggle mute
  const toggleMute = useCallback(() => {
    if (!audioRef.current) return

    audioRef.current.muted = !audioRef.current.muted
    setIsMuted(!isMuted)
  }, [isMuted])

  return (
    <div className={`bg-slate-800/50 rounded-xl p-4 ${className}`}>
      {/* Text with highlighting */}
      <div className="mb-4">
        <p className="text-slate-200 leading-relaxed">
          {words.map((word, index) => (
            <span
              key={index}
              className={`transition-colors duration-150 ${
                index === highlightIndex
                  ? 'text-cyan-400 font-medium'
                  : index < highlightIndex
                  ? 'text-slate-400'
                  : ''
              }`}
            >
              {word}{' '}
            </span>
          ))}
        </p>
      </div>

      {/* Audio controls */}
      {audioUrl && (
        <div className="flex items-center gap-3">
          {/* Play/Pause button */}
          <button
            onClick={togglePlay}
            disabled={isLoading}
            className="p-2 rounded-full bg-cyan-500/20 hover:bg-cyan-500/30 transition-colors disabled:opacity-50"
          >
            {isLoading ? (
              <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin" />
            ) : isPlaying ? (
              <Pause className="w-5 h-5 text-cyan-400" />
            ) : (
              <Play className="w-5 h-5 text-cyan-400" />
            )}
          </button>

          {/* Progress bar */}
          <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-cyan-400"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.1 }}
            />
          </div>

          {/* Mute button */}
          <button
            onClick={toggleMute}
            className="p-2 rounded-full bg-slate-700/50 hover:bg-slate-700 transition-colors"
          >
            {isMuted ? (
              <VolumeX className="w-5 h-5 text-slate-400" />
            ) : (
              <Volume2 className="w-5 h-5 text-slate-400" />
            )}
          </button>
        </div>
      )}

      {/* Loading state without audioUrl */}
      {isLoading && !audioUrl && (
        <div className="flex items-center gap-2 text-slate-400">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span className="text-sm">음성 생성 중...</span>
        </div>
      )}
    </div>
  )
}

// Compact version for message bubbles
export interface SpeechBubbleProps {
  text: string
  audioUrl?: string
  isUser?: boolean
  timestamp?: string
  emotion?: string
  autoPlay?: boolean
  className?: string
  experienceId?: string  // For feedback
  showFeedback?: boolean  // Show feedback UI for AI responses
}

export function SpeechBubble({
  text,
  audioUrl,
  isUser = false,
  timestamp,
  emotion,
  autoPlay = false,
  className = '',
  experienceId,
  showFeedback = false,
}: SpeechBubbleProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const hasAutoPlayed = useRef(false)

  const togglePlay = useCallback(() => {
    if (!audioRef.current || !audioUrl) return

    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play().catch(console.warn)
    }
  }, [isPlaying, audioUrl])

  useEffect(() => {
    // Skip if no audioUrl or if it's not a valid URL
    if (!audioUrl || (!audioUrl.startsWith('http') && !audioUrl.startsWith('data:'))) {
      return
    }

    const audio = new Audio(audioUrl)
    audioRef.current = audio

    audio.onplay = () => {
      console.log('[SpeechBubble] Audio playing:', audioUrl.substring(0, 50))
      setIsPlaying(true)
    }
    audio.onpause = () => setIsPlaying(false)
    audio.onended = () => setIsPlaying(false)
    audio.onerror = () => {
      const error = audio.error
      if (error) {
        // MediaError codes: 1=MEDIA_ERR_ABORTED, 2=MEDIA_ERR_NETWORK, 3=MEDIA_ERR_DECODE, 4=MEDIA_ERR_SRC_NOT_SUPPORTED
        const errorMessages: Record<number, string> = {
          1: 'Playback aborted',
          2: 'Network error',
          3: 'Decode error',
          4: 'Source not supported',
        }
        console.warn('[SpeechBubble] Audio error:', errorMessages[error.code] || `Unknown (${error.code})`, audioUrl?.substring(0, 50))
      }
      setIsPlaying(false)
    }

    // Auto-play for AI responses (only once)
    if (autoPlay && !hasAutoPlayed.current) {
      hasAutoPlayed.current = true
      console.log('[SpeechBubble] Attempting autoplay for:', audioUrl.substring(0, 50))

      // Wait for audio to be ready, then play
      audio.addEventListener('canplaythrough', () => {
        audio.play()
          .then(() => console.log('[SpeechBubble] Autoplay succeeded'))
          .catch((err) => {
            console.warn('[SpeechBubble] Autoplay blocked by browser:', err.message)
            // Show visual indicator that audio is ready to play
          })
      }, { once: true })

      // Fallback: try playing after a delay
      setTimeout(() => {
        if (!audio.paused) return // Already playing
        audio.play()
          .then(() => console.log('[SpeechBubble] Delayed autoplay succeeded'))
          .catch(() => {
            // Silent fail - user can click play manually
          })
      }, 500)
    }

    return () => {
      audio.pause()
      audio.src = ''
    }
  }, [audioUrl, autoPlay])

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} ${className}`}
    >
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-cyan-500/20 text-cyan-100 rounded-br-md'
            : 'bg-slate-700/50 text-slate-100 rounded-bl-md'
        }`}
      >
        {/* Emotion badge */}
        {emotion && !isUser && (
          <span className="inline-block text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded-full mb-2">
            {emotion}
          </span>
        )}

        {/* Text */}
        <p className="text-sm leading-relaxed">{text}</p>

        {/* Footer */}
        <div className="flex items-center justify-between mt-2 gap-2">
          {timestamp && (
            <span className="text-xs text-slate-500">{timestamp}</span>
          )}

          {audioUrl && (
            <button
              onClick={togglePlay}
              className={`p-1.5 rounded-full transition-colors ${
                isUser
                  ? 'bg-cyan-500/30 hover:bg-cyan-500/40'
                  : 'bg-slate-600/50 hover:bg-slate-600'
              }`}
            >
              {isPlaying ? (
                <Pause className="w-3.5 h-3.5" />
              ) : (
                <Play className="w-3.5 h-3.5" />
              )}
            </button>
          )}
        </div>

        {/* Feedback UI for AI responses */}
        {showFeedback && !isUser && experienceId && (
          <div className="mt-2 pt-2 border-t border-slate-600/30">
            <QuickFeedback experienceId={experienceId} />
          </div>
        )}
      </div>
    </motion.div>
  )
}
