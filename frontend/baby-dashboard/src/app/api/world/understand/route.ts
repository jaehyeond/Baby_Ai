import { NextRequest, NextResponse } from 'next/server'

// Supabase Edge Function URL
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://extbfhoktzozgqddjcps.supabase.co'
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const {
      image_data,
      mime_type = 'image/jpeg',
      visual_experience_id,
      objects_detected,
      previous_objects,
      development_stage = 0,
      action = 'analyze',
    } = body

    // Call Supabase Edge Function
    const response = await fetch(`${SUPABASE_URL}/functions/v1/world-understanding`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        image_data,
        mime_type,
        visual_experience_id,
        objects_detected,
        previous_objects,
        development_stage,
        action,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[World Understanding API] Edge Function error:', errorText)
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
