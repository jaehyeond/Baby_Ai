import { NextRequest, NextResponse } from 'next/server'

// Phase 4b: Supabase → FastAPI
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

async function getBabyState(): Promise<{ development_stage: number; emotional_state: Record<string, number> }> {
  try {
    const res = await fetch(`${FASTAPI_URL}/api/state`)
    if (!res.ok) return { development_stage: 0, emotional_state: {} }
    return await res.json()
  } catch {
    return { development_stage: 0, emotional_state: {} }
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action = 'generate', goal_id, outcome, insight, experience_id } = body

    // Get current baby state from FastAPI instead of Supabase
    const stateData = await getBabyState()
    const emotionState = stateData.emotional_state || {}

    const currentEmotions = {
      curiosity: emotionState.curiosity ?? 0.5,
      joy: emotionState.joy ?? 0.5,
      fear: emotionState.fear ?? 0.1,
      frustration: emotionState.frustration ?? 0.1,
      boredom: emotionState.boredom ?? 0.3,
      surprise: emotionState.surprise ?? 0.2,
    }

    const response = await fetch(`${FASTAPI_URL}/api/goals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action,
        development_stage: stateData.development_stage,
        current_emotions: currentEmotions,
        goal_id,
        outcome,
        insight,
        experience_id,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Goals API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to process goals request', details: errorText },
        { status: response.status }
      )
    }

    return NextResponse.json(await response.json())

  } catch (error) {
    console.error('[Goals API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function GET() {
  try {
    const response = await fetch(`${FASTAPI_URL}/api/goals`)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Goals API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to get goals' },
        { status: response.status }
      )
    }

    return NextResponse.json(await response.json())

  } catch (error) {
    console.error('[Goals API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
