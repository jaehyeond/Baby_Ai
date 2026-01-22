import { NextRequest, NextResponse } from 'next/server'

// Supabase Edge Function URL
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://extbfhoktzozgqddjcps.supabase.co'
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action } = body

    // Route to appropriate Edge Function
    let functionName: string
    if (action === 'generate' || action === 'get_queue' || action === 'get_stats') {
      functionName = 'generate-curiosity'
    } else if (action === 'explore' || action === 'explore_batch' || action === 'get_status') {
      functionName = 'autonomous-exploration'
    } else {
      return NextResponse.json(
        { error: 'Unknown action', details: `Action '${action}' is not supported` },
        { status: 400 }
      )
    }

    // Call Supabase Edge Function
    const response = await fetch(`${SUPABASE_URL}/functions/v1/${functionName}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error(`[Curiosity API] Edge Function error (${functionName}):`, errorText)
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

export async function GET() {
  try {
    // Get curiosity queue stats
    const response = await fetch(`${SUPABASE_URL}/functions/v1/generate-curiosity`, {
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
      console.error('[Curiosity API] Edge Function error:', errorText)
      return NextResponse.json(
        { error: 'Failed to get curiosity stats' },
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
