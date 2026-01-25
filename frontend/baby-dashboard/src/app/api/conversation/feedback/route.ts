import { NextRequest, NextResponse } from 'next/server'

// Supabase Edge Function URL
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://extbfhoktzozgqddjcps.supabase.co'
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

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

    // Call textual-backpropagation Edge Function
    const response = await fetch(`${SUPABASE_URL}/functions/v1/textual-backpropagation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        action: 'submit_feedback',
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
      console.error('[Feedback API] Edge Function error:', errorText)
      return NextResponse.json(
        { error: 'Failed to submit feedback' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

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

    let edgeFunctionAction: string
    const requestBody: Record<string, unknown> = {}

    switch (action) {
      case 'history':
        edgeFunctionAction = 'get_feedback_history'
        requestBody.limit = parseInt(limit)
        break
      case 'impact':
        if (!feedbackId) {
          return NextResponse.json(
            { error: 'feedback_id is required for impact action' },
            { status: 400 }
          )
        }
        edgeFunctionAction = 'get_impact_report'
        requestBody.feedback_id = feedbackId
        break
      case 'stats':
      default:
        edgeFunctionAction = 'get_propagation_stats'
        break
    }

    const response = await fetch(`${SUPABASE_URL}/functions/v1/textual-backpropagation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        action: edgeFunctionAction,
        ...requestBody,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Feedback API] Edge Function error:', errorText)
      return NextResponse.json(
        { error: 'Failed to get feedback data' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('[Feedback API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
