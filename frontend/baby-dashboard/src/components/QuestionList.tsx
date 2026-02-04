'use client'

import { useState } from 'react'
import type { PendingQuestion } from '@/lib/database.types'

interface QuestionListProps {
  /** List of pending questions */
  questions: PendingQuestion[]
  /** Whether questions are loading */
  isLoading: boolean
  /** Callback when a question is selected to answer */
  onSelectQuestion: (question: PendingQuestion) => void
  /** Callback when a question is skipped */
  onSkipQuestion: (questionId: string) => void
}

// Question type display configuration
const QUESTION_TYPE_CONFIG: Record<string, { label: string; emoji: string; color: string; textColor: string }> = {
  personal: {
    label: '개인',
    emoji: '👤',
    color: 'bg-blue-500/20',
    textColor: 'text-blue-400',
  },
  preference: {
    label: '취향',
    emoji: '💜',
    color: 'bg-purple-500/20',
    textColor: 'text-purple-400',
  },
  experience: {
    label: '경험',
    emoji: '📚',
    color: 'bg-amber-500/20',
    textColor: 'text-amber-400',
  },
  relationship: {
    label: '관계',
    emoji: '💕',
    color: 'bg-pink-500/20',
    textColor: 'text-pink-400',
  },
}

/**
 * QuestionList - Display list of pending questions
 *
 * Features:
 * - Shows all pending questions sorted by priority
 * - Expandable/collapsible card style
 * - Quick answer or skip actions
 * - Type-specific styling
 */
export function QuestionList({
  questions,
  isLoading,
  onSelectQuestion,
  onSkipQuestion,
}: QuestionListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  if (isLoading) {
    return (
      <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-slate-700 animate-pulse" />
          <div className="flex-1">
            <div className="h-4 bg-slate-700 rounded animate-pulse w-1/3 mb-2" />
            <div className="h-3 bg-slate-700/50 rounded animate-pulse w-2/3" />
          </div>
        </div>
      </div>
    )
  }

  if (questions.length === 0) {
    return (
      <div className="bg-slate-900/50 rounded-xl p-6 border border-slate-700/50 text-center">
        <div className="w-16 h-16 mx-auto mb-3 rounded-full bg-gradient-to-br from-pink-400/20 to-purple-500/20 flex items-center justify-center">
          <span className="text-3xl">🐣</span>
        </div>
        <p className="text-slate-400 text-sm">
          지금은 궁금한 게 없어요
        </p>
        <p className="text-slate-500 text-xs mt-1">
          비비가 새로운 호기심이 생기면 알려드릴게요
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <span className="text-lg">🐣</span>
          <span className="text-sm font-medium text-slate-300">
            비비의 궁금증
          </span>
          <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded-full">
            {questions.length}개
          </span>
        </div>
      </div>

      {/* Question Cards */}
      <div className="space-y-2">
        {questions.map((question, index) => {
          const config = QUESTION_TYPE_CONFIG[question.question_type] || {
            label: question.question_type,
            emoji: '❓',
            color: 'bg-gray-500/20',
            textColor: 'text-gray-400',
          }
          const isExpanded = expandedId === question.id
          const isFirst = index === 0

          return (
            <div
              key={question.id}
              className={`bg-slate-900/50 rounded-xl border transition-all duration-200 ${
                isFirst
                  ? 'border-purple-500/50 shadow-lg shadow-purple-500/10'
                  : 'border-slate-700/50'
              }`}
            >
              {/* Card Header */}
              <button
                onClick={() => setExpandedId(isExpanded ? null : question.id)}
                className="w-full p-4 flex items-start gap-3 text-left"
              >
                {/* Priority Indicator */}
                <div className={`flex-shrink-0 w-8 h-8 rounded-full ${config.color} flex items-center justify-center`}>
                  <span className="text-base">{config.emoji}</span>
                </div>

                {/* Question Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs font-medium ${config.textColor}`}>
                      {config.label}
                    </span>
                    {isFirst && (
                      <span className="text-xs bg-gradient-to-r from-pink-500 to-purple-500 text-white px-2 py-0.5 rounded-full">
                        우선
                      </span>
                    )}
                    {question.priority && question.priority > 0.7 && (
                      <span className="text-xs text-amber-400">
                        ⭐
                      </span>
                    )}
                  </div>
                  <p className={`text-sm text-white ${isExpanded ? '' : 'line-clamp-2'}`}>
                    {question.question}
                  </p>
                  {question.context && isExpanded && (
                    <p className="text-xs text-slate-500 mt-2 italic border-l-2 border-slate-600 pl-2">
                      &quot;{question.context}&quot;
                    </p>
                  )}
                </div>

                {/* Expand Icon */}
                <div className="flex-shrink-0">
                  <svg
                    className={`w-5 h-5 text-slate-500 transition-transform duration-200 ${
                      isExpanded ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>

              {/* Expanded Actions */}
              {isExpanded && (
                <div className="px-4 pb-4 flex gap-2">
                  <button
                    onClick={() => onSkipQuestion(question.id)}
                    className="flex-1 py-2 px-3 text-sm text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-colors"
                  >
                    나중에
                  </button>
                  <button
                    onClick={() => onSelectQuestion(question)}
                    className="flex-1 py-2 px-3 text-sm text-white bg-gradient-to-r from-pink-500 to-purple-500 hover:opacity-90 rounded-lg transition-opacity font-medium"
                  >
                    답변하기
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
