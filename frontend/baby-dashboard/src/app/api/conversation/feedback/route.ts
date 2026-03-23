import { NextRequest, NextResponse } from 'next/server'

// Phase 4c: Supabase Edge Function → FastAPI
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

/**
 * POST /api/conversation/feedback
 * Submit feedback on a Baby AI response
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { experience_id, rating, feedback_text, is_helpful, is_accurate, is_appropriate } = body

    if (!experience_id || !rating) {
      return NextResponse.json(
        { error: 'experience_id and rating are required' },
        { status: 400 }
      )
    }

    if (rating < 1 || rating > 5) {
      return NextResponse.json(
        { error: 'rating must be between 1 and 5' },
        { status: 400 }
      )
    }

    const response = await fetch(`${FASTAPI_URL}/api/conversation/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        experience_id,
        rating,
        feedback_text,
        is_helpful,
        is_accurate,
        is_appropriate,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Feedback API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to submit feedback' },
        { status: response.status }
      )
    }

    return NextResponse.json(await response.json())

  } catch (error) {
    console.error('[Feedback API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * GET /api/conversation/feedback
 * Get feedback history or stats
 * Query params:
 *   - action: 'history' | 'stats' | 'impact'
 *   - limit: number (for history)
 *   - feedback_id: string (for impact)
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const action = searchParams.get('action') || 'stats'
    const limit = searchParams.get('limit') || '20'
    const feedbackId = searchParams.get('feedback_id')

    if (action === 'impact' && !feedbackId) {
      return NextResponse.json(
        { error: 'feedback_id is required for impact action' },
        { status: 400 }
      )
    }

    const params = new URLSearchParams({ action, limit })
    if (feedbackId) params.set('feedback_id', feedbackId)

    const response = await fetch(`${FASTAPI_URL}/api/conversation/feedback?${params}`)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Feedback API] FastAPI error:', errorText)
      return NextResponse.json(
        { error: 'Failed to get feedback data' },
        { status: response.status }
      )
    }

    return NextResponse.json(await response.json())

  } catch (error) {
    console.error('[Feedback API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
