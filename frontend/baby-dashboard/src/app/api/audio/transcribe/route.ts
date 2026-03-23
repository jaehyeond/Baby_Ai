import { NextRequest, NextResponse } from 'next/server'

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const audioFile = formData.get('audio') as File | null
    const durationStr = formData.get('duration') as string | null

    if (!audioFile) {
      return NextResponse.json(
        { error: 'Audio file is required' },
        { status: 400 }
      )
    }

    // Convert File to base64
    const arrayBuffer = await audioFile.arrayBuffer()
    const base64Audio = Buffer.from(arrayBuffer).toString('base64')
    const duration = durationStr ? parseFloat(durationStr) : 0

    const response = await fetch(`${FASTAPI_URL}/api/audio/transcribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        audio_data: base64Audio,
        mime_type: audioFile.type || 'audio/webm',
        duration_ms: Math.round(duration * 1000),
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Audio API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to transcribe audio' },
        { status: response.status }
      )
    }

    const data = await response.json()
    // FastAPI returns { text, confidence, language, duration_ms }
    // Map to { transcript } for backwards compatibility with sense/page.tsx
    return NextResponse.json({
      transcript: data.text || '',
      text: data.text || '',
      confidence: data.confidence ?? 0.9,
      language: data.language || 'ko-KR',
    })

  } catch (error) {
    console.error('[Audio API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
