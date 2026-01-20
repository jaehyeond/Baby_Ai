'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

// 감정별 파티클 설정
const EMOTION_PARTICLE_CONFIG: Record<string, {
  color: string
  emoji: string
  count: number
  speed: number
  size: [number, number]
}> = {
  joy: {
    color: '#10b981',
    emoji: '✨',
    count: 12,
    speed: 1.5,
    size: [12, 20],
  },
  curiosity: {
    color: '#8b5cf6',
    emoji: '💡',
    count: 8,
    speed: 1.2,
    size: [14, 18],
  },
  surprise: {
    color: '#f59e0b',
    emoji: '⚡',
    count: 10,
    speed: 2,
    size: [12, 18],
  },
  fear: {
    color: '#ef4444',
    emoji: '💢',
    count: 6,
    speed: 1.8,
    size: [10, 16],
  },
  frustration: {
    color: '#f97316',
    emoji: '😤',
    count: 8,
    speed: 1.5,
    size: [14, 18],
  },
  boredom: {
    color: '#6b7280',
    emoji: '💤',
    count: 4,
    speed: 0.8,
    size: [12, 16],
  },
}

interface Particle {
  id: string
  x: number
  y: number
  emoji: string
  size: number
  duration: number
  delay: number
  direction: { x: number; y: number }
}

interface EmotionParticlesProps {
  emotion: string | null
  intensity?: number // 0-1, 감정 강도
  trigger?: number // 변경될 때마다 파티클 발생
  className?: string
}

export function EmotionParticles({
  emotion,
  intensity = 0.5,
  trigger,
  className = '',
}: EmotionParticlesProps) {
  const [particles, setParticles] = useState<Particle[]>([])
  const containerRef = useRef<HTMLDivElement>(null)

  const createParticles = useCallback(() => {
    if (!emotion || !EMOTION_PARTICLE_CONFIG[emotion]) return

    const config = EMOTION_PARTICLE_CONFIG[emotion]
    const particleCount = Math.ceil(config.count * intensity)

    const newParticles: Particle[] = Array.from({ length: particleCount }, (_, i) => {
      const angle = (Math.PI * 2 * i) / particleCount + Math.random() * 0.5
      const distance = 50 + Math.random() * 100

      return {
        id: `${Date.now()}-${i}`,
        x: 50 + (Math.random() - 0.5) * 20, // 중앙 근처에서 시작
        y: 50 + (Math.random() - 0.5) * 20,
        emoji: config.emoji,
        size: config.size[0] + Math.random() * (config.size[1] - config.size[0]),
        duration: (1 + Math.random()) / config.speed,
        delay: Math.random() * 0.3,
        direction: {
          x: Math.cos(angle) * distance,
          y: Math.sin(angle) * distance,
        },
      }
    })

    setParticles(newParticles)

    // 파티클 정리
    setTimeout(() => {
      setParticles([])
    }, 2000)
  }, [emotion, intensity])

  // trigger가 변경될 때마다 파티클 생성
  useEffect(() => {
    if (trigger !== undefined) {
      createParticles()
    }
  }, [trigger, createParticles])

  return (
    <div
      ref={containerRef}
      className={`absolute inset-0 pointer-events-none overflow-hidden ${className}`}
    >
      <AnimatePresence>
        {particles.map((particle) => (
          <motion.div
            key={particle.id}
            initial={{
              left: `${particle.x}%`,
              top: `${particle.y}%`,
              opacity: 1,
              scale: 0,
            }}
            animate={{
              left: `${particle.x + particle.direction.x}%`,
              top: `${particle.y + particle.direction.y}%`,
              opacity: 0,
              scale: 1,
            }}
            exit={{ opacity: 0 }}
            transition={{
              duration: particle.duration,
              delay: particle.delay,
              ease: 'easeOut',
            }}
            className="absolute"
            style={{
              fontSize: particle.size,
              transform: 'translate(-50%, -50%)',
            }}
          >
            {particle.emoji}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

// 지속적인 ambient 파티클 (배경 효과)
interface AmbientParticlesProps {
  emotion: string | null
  intensity?: number
  className?: string
}

export function AmbientParticles({
  emotion,
  intensity = 0.5,
  className = '',
}: AmbientParticlesProps) {
  const [particles, setParticles] = useState<Particle[]>([])

  useEffect(() => {
    if (!emotion || !EMOTION_PARTICLE_CONFIG[emotion]) {
      setParticles([])
      return
    }

    const config = EMOTION_PARTICLE_CONFIG[emotion]
    const count = Math.ceil(3 * intensity)

    // 초기 파티클 생성
    const createAmbientParticle = (id: number): Particle => ({
      id: `ambient-${Date.now()}-${id}`,
      x: Math.random() * 100,
      y: Math.random() * 100,
      emoji: config.emoji,
      size: config.size[0] * 0.7,
      duration: 3 + Math.random() * 2,
      delay: Math.random() * 2,
      direction: {
        x: (Math.random() - 0.5) * 30,
        y: -20 - Math.random() * 30, // 위로 떠오르는 효과
      },
    })

    setParticles(Array.from({ length: count }, (_, i) => createAmbientParticle(i)))

    // 주기적으로 새 파티클 추가
    const interval = setInterval(() => {
      setParticles((prev) => {
        if (prev.length >= count * 2) {
          return [...prev.slice(1), createAmbientParticle(Date.now())]
        }
        return [...prev, createAmbientParticle(Date.now())]
      })
    }, 2000 / intensity)

    return () => clearInterval(interval)
  }, [emotion, intensity])

  return (
    <div className={`absolute inset-0 pointer-events-none overflow-hidden ${className}`}>
      <AnimatePresence>
        {particles.map((particle) => (
          <motion.div
            key={particle.id}
            initial={{
              left: `${particle.x}%`,
              top: `${particle.y}%`,
              opacity: 0,
              scale: 0.5,
            }}
            animate={{
              left: `${particle.x + particle.direction.x}%`,
              top: `${particle.y + particle.direction.y}%`,
              opacity: [0, 0.6, 0],
              scale: [0.5, 1, 0.5],
            }}
            exit={{ opacity: 0 }}
            transition={{
              duration: particle.duration,
              delay: particle.delay,
              ease: 'easeInOut',
            }}
            className="absolute"
            style={{
              fontSize: particle.size,
              transform: 'translate(-50%, -50%)',
            }}
          >
            {particle.emoji}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

// Phase 3 연동을 위한 이벤트 기반 파티클 훅
export function useEmotionParticles() {
  const [particleTrigger, setParticleTrigger] = useState(0)
  const [currentEmotion, setCurrentEmotion] = useState<string | null>(null)
  const [emotionIntensity, setEmotionIntensity] = useState(0.5)
  const prevEmotionRef = useRef<string | null>(null)

  // 감정 변화 감지 및 파티클 트리거
  const onEmotionChange = useCallback((
    newEmotion: string | null,
    intensity: number = 0.5
  ) => {
    // 감정이 변경되었을 때만 파티클 발생
    if (newEmotion !== prevEmotionRef.current) {
      setCurrentEmotion(newEmotion)
      setEmotionIntensity(intensity)
      setParticleTrigger((prev) => prev + 1)
      prevEmotionRef.current = newEmotion
    }
  }, [])

  // 강제로 파티클 발생 (Phase 3에서 이벤트 수신 시 사용)
  const triggerParticles = useCallback((
    emotion: string,
    intensity: number = 0.5
  ) => {
    setCurrentEmotion(emotion)
    setEmotionIntensity(intensity)
    setParticleTrigger((prev) => prev + 1)
  }, [])

  return {
    currentEmotion,
    emotionIntensity,
    particleTrigger,
    onEmotionChange,
    triggerParticles,
  }
}
