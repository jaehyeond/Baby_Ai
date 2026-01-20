import { NextRequest, NextResponse } from 'next/server'

// Supabase Edge Function URL
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://extbfhoktzozgqddjcps.supabase.co'
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

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

    // Call Supabase Edge Function for TTS
    const response = await fetch(`${SUPABASE_URL}/functions/v1/speech-synthesize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        text,
        voice: voice || 'ko-KR-Neural2-A', // Default Korean child voice
        speaking_rate: speaking_rate || 1.0,
        pitch: pitch || 0.0,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Speech API] Edge Function error:', errorText)
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
