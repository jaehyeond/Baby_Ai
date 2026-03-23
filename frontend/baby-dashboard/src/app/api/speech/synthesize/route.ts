import { NextRequest, NextResponse } from 'next/server'

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { text, voice, speaking_rate, pitch } = body

    if (!text) {
      return NextResponse.json(
        { error: 'Text is required' },
        { status: 400 }
      )
    }

    const response = await fetch(`${FASTAPI_URL}/api/speech/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        voice: voice || 'Kore',
        speaking_rate: speaking_rate || 1.0,
        pitch: pitch || 0.0,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Speech API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to synthesize speech' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('[Speech API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
