'use client'

import { useEffect, useRef } from 'react'

export interface WaveformVisualizerProps {
  analyserNode: AnalyserNode | null
  isActive: boolean
  className?: string
  barColor?: string
  barWidth?: number
  barGap?: number
}

export function WaveformVisualizer({
  analyserNode,
  isActive,
  className = '',
  barColor = '#22d3ee', // cyan-400
  barWidth = 3,
  barGap = 2,
}: WaveformVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationFrameRef = useRef<number | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size
    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect()
      const dpr = window.devicePixelRatio || 1
      canvas.width = rect.width * dpr
      canvas.height = rect.height * dpr
      ctx.scale(dpr, dpr)
    }

    resizeCanvas()
    window.addEventListener('resize', resizeCanvas)

    const draw = () => {
      const rect = canvas.getBoundingClientRect()
      ctx.clearRect(0, 0, rect.width, rect.height)

      if (!isActive || !analyserNode) {
        // Draw idle state - flat line
        ctx.fillStyle = barColor
        ctx.globalAlpha = 0.3
        const centerY = rect.height / 2
        const barCount = Math.floor(rect.width / (barWidth + barGap))

        for (let i = 0; i < barCount; i++) {
          const x = i * (barWidth + barGap)
          ctx.fillRect(x, centerY - 1, barWidth, 2)
        }

        animationFrameRef.current = requestAnimationFrame(draw)
        return
      }

      // Get frequency data
      const bufferLength = analyserNode.frequencyBinCount
      const dataArray = new Uint8Array(bufferLength)
      analyserNode.getByteFrequencyData(dataArray)

      ctx.globalAlpha = 1
      ctx.fillStyle = barColor

      const barCount = Math.floor(rect.width / (barWidth + barGap))
      const centerY = rect.height / 2
      const maxBarHeight = rect.height / 2 - 4

      // Sample the frequency data
      const step = Math.floor(bufferLength / barCount)

      for (let i = 0; i < barCount; i++) {
        // Get average of frequency range
        let sum = 0
        for (let j = 0; j < step; j++) {
          sum += dataArray[i * step + j] || 0
        }
        const average = sum / step

        // Calculate bar height with some minimum
        const normalizedHeight = average / 255
        const barHeight = Math.max(2, normalizedHeight * maxBarHeight)

        const x = i * (barWidth + barGap)

        // Draw bar centered vertically
        ctx.fillRect(x, centerY - barHeight, barWidth, barHeight * 2)
      }

      animationFrameRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      window.removeEventListener('resize', resizeCanvas)
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [analyserNode, isActive, barColor, barWidth, barGap])

  return (
    <canvas
      ref={canvasRef}
      className={`w-full h-full ${className}`}
      style={{ display: 'block' }}
    />
  )
}

// Compact audio level indicator (circular)
export interface AudioLevelIndicatorProps {
  level: number // 0-1
  isActive: boolean
  size?: number
  className?: string
}

export function AudioLevelIndicator({
  level,
  isActive,
  size = 48,
  className = '',
}: AudioLevelIndicatorProps) {
  const scale = isActive ? 1 + level * 0.3 : 1
  const opacity = isActive ? 0.5 + level * 0.5 : 0.3

  return (
    <div
      className={`relative flex items-center justify-center ${className}`}
      style={{ width: size, height: size }}
    >
      {/* Outer ring */}
      <div
        className="absolute inset-0 rounded-full bg-cyan-500 transition-all duration-75"
        style={{
          transform: `scale(${scale})`,
          opacity: opacity * 0.3,
        }}
      />
      {/* Middle ring */}
      <div
        className="absolute rounded-full bg-cyan-400 transition-all duration-75"
        style={{
          width: size * 0.7,
          height: size * 0.7,
          transform: `scale(${1 + level * 0.2})`,
          opacity: opacity * 0.5,
        }}
      />
      {/* Inner circle */}
      <div
        className="absolute rounded-full bg-cyan-300 transition-all duration-75"
        style={{
          width: size * 0.4,
          height: size * 0.4,
          opacity: opacity,
        }}
      />
    </div>
  )
}

// Recording time display
export interface RecordingTimerProps {
  duration: number // in seconds
  maxDuration?: number
  className?: string
}

export function RecordingTimer({
  duration,
  maxDuration,
  className = '',
}: RecordingTimerProps) {
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const progress = maxDuration ? (duration / maxDuration) * 100 : 0

  return (
    <div className={`flex flex-col items-center ${className}`}>
      <span className="text-2xl font-mono text-slate-100">
        {formatTime(duration)}
      </span>
      {maxDuration && (
        <div className="w-full mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-cyan-400 transition-all duration-100"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      )}
    </div>
  )
}
