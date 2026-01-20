'use client'

import { useState, useEffect, useCallback } from 'react'
import { supabase } from '@/lib/supabase'

// Milestone definitions with metadata
export const MILESTONE_DEFINITIONS: Record<string, MilestoneInfo> = {
  first_success: {
    id: 'first_success',
    name: '첫 성공',
    description: '처음으로 작업을 성공적으로 완료했어요',
    icon: '🎉',
    color: '#22c55e',
    stage: 0,
    order: 1,
  },
  pattern_recognition: {
    id: 'pattern_recognition',
    name: '패턴 인식',
    description: '반복되는 패턴을 인식하기 시작했어요',
    icon: '🔍',
    color: '#3b82f6',
    stage: 0,
    order: 2,
  },
  consistent_success: {
    id: 'consistent_success',
    name: '일관된 성공',
    description: '여러 작업에서 꾸준히 성공하고 있어요',
    icon: '⭐',
    color: '#f59e0b',
    stage: 1,
    order: 3,
  },
  memory_formation: {
    id: 'memory_formation',
    name: '기억 형성',
    description: '경험을 기억하고 활용하기 시작했어요',
    icon: '🧠',
    color: '#8b5cf6',
    stage: 1,
    order: 4,
  },
  imitation_mastery: {
    id: 'imitation_mastery',
    name: '모방 마스터',
    description: '다양한 패턴을 모방할 수 있게 되었어요',
    icon: '🪞',
    color: '#ec4899',
    stage: 1,
    order: 5,
  },
  diverse_experience: {
    id: 'diverse_experience',
    name: '다양한 경험',
    description: '여러 유형의 작업을 경험했어요',
    icon: '🌈',
    color: '#14b8a6',
    stage: 2,
    order: 6,
  },
  self_reflection: {
    id: 'self_reflection',
    name: '자기 성찰',
    description: '자신의 행동을 돌아볼 수 있게 되었어요',
    icon: '🔮',
    color: '#6366f1',
    stage: 2,
    order: 7,
  },
  task_mastery: {
    id: 'task_mastery',
    name: '작업 숙달',
    description: '특정 작업 유형을 완벽히 숙달했어요',
    icon: '🏆',
    color: '#f43f5e',
    stage: 3,
    order: 8,
  },
  // Future milestones
  creative_solution: {
    id: 'creative_solution',
    name: '창의적 해결',
    description: '새로운 방법으로 문제를 해결했어요',
    icon: '💡',
    color: '#eab308',
    stage: 3,
    order: 9,
  },
  error_recovery: {
    id: 'error_recovery',
    name: '오류 회복',
    description: '실패에서 스스로 회복할 수 있게 되었어요',
    icon: '🔄',
    color: '#06b6d4',
    stage: 4,
    order: 10,
  },
}

export interface MilestoneInfo {
  id: string
  name: string
  description: string
  icon: string
  color: string
  stage: number
  order: number
}

export interface Milestone {
  id: string
  info: MilestoneInfo
  achievedAt: Date | null
  experienceNumber?: number
}

export interface MilestoneData {
  milestones: Milestone[]
  achievedCount: number
  totalCount: number
  currentStage: number
  experienceCount: number
}

export function useMilestones() {
  const [data, setData] = useState<MilestoneData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchMilestones = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Fetch baby state for milestones and stage
      const { data: stateData, error: stateError } = await supabase
        .from('baby_state')
        .select('milestones, development_stage, experience_count')
        .order('updated_at', { ascending: false })
        .limit(1)
        .single()

      if (stateError) throw stateError

      const achievedMilestones = (stateData?.milestones as string[]) || []
      const currentStage = stateData?.development_stage || 0
      const experienceCount = stateData?.experience_count || 0

      // Fetch experiences to estimate achievement times
      const { data: experiences, error: expError } = await supabase
        .from('experiences')
        .select('id, task, success, created_at')
        .order('created_at', { ascending: true })

      if (expError) throw expError

      // Estimate milestone achievement times based on experience patterns
      const milestoneAchievementTimes = estimateMilestoneAchievements(
        experiences || [],
        achievedMilestones
      )

      // Build milestone list with all definitions
      const milestones: Milestone[] = Object.values(MILESTONE_DEFINITIONS)
        .sort((a, b) => a.order - b.order)
        .map((info) => ({
          id: info.id,
          info,
          achievedAt: milestoneAchievementTimes[info.id] || null,
          experienceNumber: milestoneAchievementTimes[info.id]
            ? getExperienceNumberAtTime(experiences || [], milestoneAchievementTimes[info.id]!)
            : undefined,
        }))

      setData({
        milestones,
        achievedCount: achievedMilestones.length,
        totalCount: Object.keys(MILESTONE_DEFINITIONS).length,
        currentStage,
        experienceCount,
      })
    } catch (err) {
      console.error('Error fetching milestones:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch milestones')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMilestones()
  }, [fetchMilestones])

  return { data, isLoading, error, refetch: fetchMilestones }
}

// Estimate when each milestone was achieved based on experience patterns
function estimateMilestoneAchievements(
  experiences: Array<{ id: string; task: string; success: boolean | null; created_at: string | null }>,
  achievedMilestones: string[]
): Record<string, Date> {
  const achievements: Record<string, Date> = {}

  // Filter out experiences with null created_at
  const validExperiences = experiences.filter((e) => e.created_at !== null)
  if (validExperiences.length === 0) return achievements

  let successCount = 0
  let consecutiveSuccesses = 0
  const taskTypes = new Set<string>()

  for (let i = 0; i < validExperiences.length; i++) {
    const exp = validExperiences[i]
    const date = new Date(exp.created_at!)

    if (exp.success) {
      successCount++
      consecutiveSuccesses++
    } else {
      consecutiveSuccesses = 0
    }

    // Track task types for diversity
    const taskType = categorizeTask(exp.task)
    taskTypes.add(taskType)

    // first_success: First successful experience
    if (achievedMilestones.includes('first_success') && !achievements['first_success']) {
      if (exp.success) {
        achievements['first_success'] = date
      }
    }

    // pattern_recognition: After ~10 experiences
    if (achievedMilestones.includes('pattern_recognition') && !achievements['pattern_recognition']) {
      if (i >= 9) {
        achievements['pattern_recognition'] = date
      }
    }

    // consistent_success: After 5 consecutive successes
    if (achievedMilestones.includes('consistent_success') && !achievements['consistent_success']) {
      if (consecutiveSuccesses >= 5) {
        achievements['consistent_success'] = date
      }
    }

    // memory_formation: After ~25 experiences
    if (achievedMilestones.includes('memory_formation') && !achievements['memory_formation']) {
      if (i >= 24) {
        achievements['memory_formation'] = date
      }
    }

    // imitation_mastery: After ~40 experiences with good success rate
    if (achievedMilestones.includes('imitation_mastery') && !achievements['imitation_mastery']) {
      if (i >= 39 && successCount / (i + 1) >= 0.6) {
        achievements['imitation_mastery'] = date
      }
    }

    // diverse_experience: After experiencing 5+ different task types
    if (achievedMilestones.includes('diverse_experience') && !achievements['diverse_experience']) {
      if (taskTypes.size >= 5) {
        achievements['diverse_experience'] = date
      }
    }

    // self_reflection: After ~70 experiences
    if (achievedMilestones.includes('self_reflection') && !achievements['self_reflection']) {
      if (i >= 69) {
        achievements['self_reflection'] = date
      }
    }

    // task_mastery: After ~90 experiences with high success rate
    if (achievedMilestones.includes('task_mastery') && !achievements['task_mastery']) {
      if (i >= 89 && successCount / (i + 1) >= 0.65) {
        achievements['task_mastery'] = date
      }
    }
  }

  return achievements
}

// Categorize task for diversity tracking
function categorizeTask(task: string): string {
  const lower = task.toLowerCase()
  if (lower.includes('정렬') || lower.includes('sort')) return 'sorting'
  if (lower.includes('탐색') || lower.includes('search') || lower.includes('bfs') || lower.includes('dfs')) return 'search'
  if (lower.includes('클래스') || lower.includes('class') || lower.includes('패턴')) return 'oop'
  if (lower.includes('트리') || lower.includes('tree') || lower.includes('그래프') || lower.includes('graph')) return 'graph'
  if (lower.includes('문자열') || lower.includes('string')) return 'string'
  if (lower.includes('함수') || lower.includes('function')) return 'function'
  if (lower.includes('알고리즘') || lower.includes('algorithm')) return 'algorithm'
  if (lower.includes('dp') || lower.includes('동적')) return 'dp'
  return 'general'
}

// Get experience number at a given time
function getExperienceNumberAtTime(
  experiences: Array<{ created_at: string | null }>,
  time: Date
): number {
  const timeMs = time.getTime()
  for (let i = 0; i < experiences.length; i++) {
    const createdAt = experiences[i].created_at
    if (createdAt && new Date(createdAt).getTime() >= timeMs) {
      return i + 1
    }
  }
  return experiences.length
}
