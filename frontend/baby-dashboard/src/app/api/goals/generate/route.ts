import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

// Supabase Edge Function URL
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://extbfhoktzozgqddjcps.supabase.co'
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action = 'generate', goal_id, outcome, insight, experience_id } = body

    // Get current baby state for emotions and stage
    const { data: babyState } = await supabase
      .from('baby_state')
      .select('*')
      .order('updated_at', { ascending: false })
      .limit(1)
      .single()

    const currentEmotions = babyState ? {
      curiosity: babyState.curiosity || 0.5,
      joy: babyState.joy || 0.5,
      fear: babyState.fear || 0.1,
      frustration: babyState.frustration || 0.1,
      boredom: babyState.boredom || 0.3,
      surprise: babyState.surprise || 0.2,
    } : undefined

    // Call Supabase Edge Function
    const response = await fetch(`${SUPABASE_URL}/functions/v1/autonomous-goals`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        action,
        development_stage: babyState?.development_stage || 0,
        current_emotions: currentEmotions,
        goal_id,
        outcome,
        insight,
        experience_id,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Goals API] Edge Function error:', errorText)
      return NextResponse.json(
        { error: 'Failed to process goals request', details: errorText },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('[Goals API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function GET() {
  try {
    // Get active goals
    const response = await fetch(`${SUPABASE_URL}/functions/v1/autonomous-goals`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        action: 'get_goals',
        limit: 10,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Goals API] Edge Function error:', errorText)
      return NextResponse.json(
        { error: 'Failed to get goals' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('[Goals API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
