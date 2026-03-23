import { NextRequest, NextResponse } from 'next/server'

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

// Phase 4d: world-understanding FastAPI 이식 예정
// 현재 sense/page.tsx는 /api/vision/process를 직접 사용하므로 이 route는 미호출
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const response = await fetch(`${FASTAPI_URL}/api/vision/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_data: body.image_data || '',
        mime_type: body.mime_type || 'image/jpeg',
        prompt: `세계 이해 분석: ${body.action || 'analyze'}`,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[World Understanding API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to process world understanding', details: errorText },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('[World Understanding API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
