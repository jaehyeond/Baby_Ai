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

    // TTS: 대화 응답 텍스트를 음성으로 변환
    let audioUrl: string | null = null
    if (data.output) {
      try {
        const ttsController = new AbortController()
        const ttsTimeout = setTimeout(() => ttsController.abort(), 5000)
        const ttsRes = await fetch(`${FASTAPI_URL}/api/speech/synthesize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: data.output, voice: 'Kore' }),
          signal: ttsController.signal,
        })
        clearTimeout(ttsTimeout)
        if (ttsRes.ok) {
          const ttsData = await ttsRes.json()
          if (ttsData.audio_content) {
            audioUrl = `data:audio/wav;base64,${ttsData.audio_content}`
          }
        }
      } catch {
        // TTS 실패 시 텍스트 응답은 정상 반환
      }
    }

    return NextResponse.json({
      response: data.output,
      emotion: data.emotional_state?.dominant_emotion ?? 'neutral',
      is_question: data.output?.includes('?') ?? false,
      audio_url: audioUrl,
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
