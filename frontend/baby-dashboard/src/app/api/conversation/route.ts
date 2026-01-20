import { NextRequest, NextResponse } from 'next/server'

// Supabase Edge Function URL
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://extbfhoktzozgqddjcps.supabase.co'
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { message, audio_data, mime_type, duration_ms, conversation_id } = body

    if (!message && !audio_data) {
      return NextResponse.json(
        { error: 'Message or audio data is required' },
        { status: 400 }
      )
    }

    // Call Supabase Edge Function for conversation processing
    const response = await fetch(`${SUPABASE_URL}/functions/v1/conversation-process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        message,
        audio_data,
        mime_type,
        duration_ms,
        conversation_id,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Conversation API] Edge Function error:', errorText)
      return NextResponse.json(
        { error: 'Failed to process conversation' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('[Conversation API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// Get conversation history
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const conversationId = searchParams.get('conversation_id')
    const limit = searchParams.get('limit') || '20'

    const url = new URL(`${SUPABASE_URL}/functions/v1/conversation-history`)
    if (conversationId) {
      url.searchParams.set('conversation_id', conversationId)
    }
    url.searchParams.set('limit', limit)

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Conversation API] Edge Function error:', errorText)
      return NextResponse.json(
        { error: 'Failed to get conversation history' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('[Conversation API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
