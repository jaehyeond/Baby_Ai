import { NextRequest, NextResponse } from 'next/server'

// Phase 4a: Supabase Edge Function → FastAPI
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

// Get current development stage from FastAPI (Supabase 직접 쿼리 제거)
async function getDevelopmentStage(): Promise<number> {
  try {
    const res = await fetch(`${FASTAPI_URL}/api/state`)
    if (!res.ok) return 0
    const data = await res.json() as { development_stage?: number }
    return data.development_stage ?? 0
  } catch {
    return 0
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { image, mime_type } = body

    if (!image) {
      return NextResponse.json(
        { error: 'Image data is required' },
        { status: 400 }
      )
    }

    const developmentStage = await getDevelopmentStage()

    const response = await fetch(`${FASTAPI_URL}/api/vision/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_data: image,
        mime_type: mime_type || 'image/jpeg',
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Vision API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to process image' },
        { status: response.status }
      )
    }

    const data = await response.json() as {
      visual_experience: Record<string, unknown>
      emotional_changes: Record<string, unknown>
      success: boolean
      message?: string
    }

    // world-understanding은 Phase 4d에서 FastAPI 이식 후 추가
    // development_stage는 클라이언트 참고용으로 포함
    return NextResponse.json({
      ...data,
      development_stage: developmentStage,
    })

  } catch (error) {
    console.error('[Vision API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
