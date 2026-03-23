import { NextRequest, NextResponse } from 'next/server'

// Phase 4a: Supabase Edge Function → FastAPI
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    // EF 파라미터: { action, trigger_type, hours_window, decay_threshold_days, limit }
    // FastAPI 파라미터: { mode: 'full'|'reinforce_only'|'decay_only', decay_rate }
    const { action = 'consolidate', decay_threshold_days } = body

    // action → mode 매핑
    let mode: 'full' | 'reinforce_only' | 'decay_only' = 'full'
    if (action === 'reinforce') mode = 'reinforce_only'
    else if (action === 'decay') mode = 'decay_only'
    // action === 'consolidate' | 기타 → 'full'

    if (action === 'get_stats') {
      // 통계 조회는 GET으로 위임
      const res = await fetch(`${FASTAPI_URL}/api/memory/consolidate`)
      if (!res.ok) {
        return NextResponse.json({ error: 'Failed to get stats' }, { status: res.status })
      }
      return NextResponse.json(await res.json())
    }

    // decay_threshold_days → decay_rate 근사 변환 (30일 기준 0.01/일)
    const decay_rate = decay_threshold_days
      ? Math.min(0.1, 1 / Number(decay_threshold_days))
      : 0.01

    const response = await fetch(`${FASTAPI_URL}/api/memory/consolidate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, decay_rate }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Memory API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to process memory consolidation request', details: errorText },
        { status: response.status }
      )
    }

    const data = await response.json() as {
      status: string
      mode: string
      reinforced?: number
      decayed?: boolean
    }

    return NextResponse.json({
      success: data.status === 'ok',
      stats: {
        reinforced: data.reinforced ?? 0,
        decayed: data.decayed ?? false,
        mode: data.mode,
      },
    })

  } catch (error) {
    console.error('[Memory API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function GET() {
  try {
    const response = await fetch(`${FASTAPI_URL}/api/memory/consolidate`)
    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to get consolidation stats' }, { status: response.status })
    }
    return NextResponse.json(await response.json())
  } catch (error) {
    console.error('[Memory API] Error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
