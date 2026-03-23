import { NextRequest, NextResponse } from 'next/server'

// Phase 4a: Supabase Edge Function → FastAPI
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { message } = body

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      )
    }

    const response = await fetch(`${FASTAPI_URL}/api/conversation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Conversation API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to process conversation' },
        { status: response.status }
      )
    }

    // FastAPI 응답: { output, success, emotional_state, development_stage, experience_id }
    // 클라이언트(sense/page.tsx)가 기대하는 필드: response, emotion, is_question, audio_url
    const data = await response.json() as {
      output: string
      success: boolean
      emotional_state: Record<string, number | string>
      development_stage: number
      experience_id: string | null
    }

    return NextResponse.json({
      response: data.output,
      emotion: data.emotional_state?.dominant_emotion ?? 'neutral',
      is_question: data.output?.includes('?') ?? false,
      audio_url: null,  // TTS는 Phase 4d에서 speech/synthesize 이식 후 추가
      success: data.success,
      development_stage: data.development_stage,
      experience_id: data.experience_id,
      emotional_state: data.emotional_state,
    })

  } catch (error) {
    console.error('[Conversation API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// GET: conversation history — FastAPI 미구현, 빈 배열 반환 (Phase 4c에서 추가)
export async function GET() {
  return NextResponse.json({ history: [] })
}
