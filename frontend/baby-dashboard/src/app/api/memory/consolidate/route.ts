import { NextRequest, NextResponse } from 'next/server'

// Supabase Edge Function URL
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://extbfhoktzozgqddjcps.supabase.co'
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const {
      action = 'consolidate',
      trigger_type = 'manual',
      hours_window = 24,
      decay_threshold_days = 30,
      limit = 10
    } = body

    // Call Supabase Edge Function
    const response = await fetch(`${SUPABASE_URL}/functions/v1/memory-consolidation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        action,
        trigger_type,
        hours_window,
        decay_threshold_days,
        limit,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Memory API] Edge Function error:', errorText)
      return NextResponse.json(
        { error: 'Failed to process memory consolidation request', details: errorText },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

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
    // Get consolidation stats
    const response = await fetch(`${SUPABASE_URL}/functions/v1/memory-consolidation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        action: 'get_stats',
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Memory API] Edge Function error:', errorText)
      return NextResponse.json(
        { error: 'Failed to get consolidation stats' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('[Memory API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
