import { NextRequest, NextResponse } from 'next/server'

// Phase 4b: Supabase Edge Function → FastAPI
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const response = await fetch(`${FASTAPI_URL}/api/metacognition`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Metacognition API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to process metacognition request', details: errorText },
        { status: response.status }
      )
    }

    return NextResponse.json(await response.json())

  } catch (error) {
    console.error('[Metacognition API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function GET() {
  try {
    const response = await fetch(`${FASTAPI_URL}/api/metacognition`)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Metacognition API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to get metacognition stats' },
        { status: response.status }
      )
    }

    return NextResponse.json(await response.json())

  } catch (error) {
    console.error('[Metacognition API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
