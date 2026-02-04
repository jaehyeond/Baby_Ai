import { NextRequest, NextResponse } from 'next/server'

// Supabase Edge Function URL
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://extbfhoktzozgqddjcps.supabase.co'
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

/**
 * World Model API - Imagination Engine
 *
 * POST actions:
 * - imagine: Start an imagination session on a topic
 * - predict: Generate a prediction for a scenario
 * - simulate: Run a goal-oriented simulation
 * - verify: Verify a past prediction with actual outcome
 * - stats: Get prediction accuracy statistics
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action } = body

    // Validate action
    const validActions = ['imagine', 'predict', 'simulate', 'verify', 'stats']
    if (!validActions.includes(action)) {
      return NextResponse.json(
        { error: 'Unknown action', details: `Action '${action}' is not supported. Valid actions: ${validActions.join(', ')}` },
        { status: 400 }
      )
    }

    // Call Supabase Edge Function
    const response = await fetch(`${SUPABASE_URL}/functions/v1/imagination-engine`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error(`[Imagination API] Edge Function error:`, errorText)
      return NextResponse.json(
        { error: 'Failed to process imagination request', details: errorText },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('[Imagination API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function GET() {
  try {
    // Get World Model stats
    const response = await fetch(`${SUPABASE_URL}/functions/v1/imagination-engine`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        action: 'stats',
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Imagination API] Edge Function error:', errorText)
      return NextResponse.json(
        { error: 'Failed to get imagination stats' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('[Imagination API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
