import { NextRequest, NextResponse } from 'next/server'

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const response = await fetch(`${FASTAPI_URL}/api/curiosity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Curiosity API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to process curiosity request', details: errorText },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('[Curiosity API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = searchParams.get('limit') || '20'
    const status = searchParams.get('status') || ''

    const url = new URL(`${FASTAPI_URL}/api/curiosity`)
    url.searchParams.set('limit', limit)
    if (status) url.searchParams.set('status', status)

    const response = await fetch(url.toString())

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Curiosity API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to get curiosity data' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('[Curiosity API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
