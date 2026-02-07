import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://extbfhoktzozgqddjcps.supabase.co'
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// Development stage names
const STAGE_NAMES: Record<number, string> = {
  0: 'NEWBORN',
  1: 'INFANT',
  2: 'BABY',
  3: 'TODDLER',
  4: 'CHILD',
}

// Greeting templates based on development stage and emotion
function generateGreeting(stage: number, emotion: string): string {
  const stageName = STAGE_NAMES[stage] || 'BABY'

  // Stage-appropriate greetings
  const greetings: Record<string, string[]> = {
    NEWBORN: ['응...?', '아...'],
    INFANT: ['응!', '아, 형아!'],
    BABY: ['네, 형아!', '형아! 안녕!', '응, 형아!'],
    TODDLER: ['네, 형아! 뭐해?', '형아! 나 여기 있어!', '안녕, 형아! 오늘 뭐 할 거야?'],
    CHILD: ['안녕, 형아! 뭐 해?', '형아! 나한테 볼일 있어?', '네, 형아! 오늘 기분이 좋아!'],
  }

  // Emotion-influenced variations
  if (emotion === 'joy' && stage >= 2) {
    return ['형아! 헤헤, 안녕!', '형아! 나 오늘 기분 좋아!', '안녕 형아! 놀자!'][Math.floor(Math.random() * 3)]
  }
  if (emotion === 'curiosity' && stage >= 3) {
    return ['형아! 궁금한 거 있어!', '형아! 나 뭔가 알고 싶어!'][Math.floor(Math.random() * 2)]
  }
  if (emotion === 'fear' && stage >= 1) {
    return ['형아...?', '형아, 나 좀 무서워...'][Math.floor(Math.random() * 2)]
  }

  const stageGreetings = greetings[stageName] || greetings.BABY
  return stageGreetings[Math.floor(Math.random() * stageGreetings.length)]
}

export async function POST() {
  try {
    // 1. Get current baby state
    const { data: babyState, error: stateError } = await supabase
      .from('baby_state')
      .select('development_stage, dominant_emotion, joy, curiosity, fear')
      .single()

    if (stateError) {
      console.error('[WakeGreeting] Failed to get baby state:', stateError)
    }

    const stage = babyState?.development_stage ?? 2
    const emotion = babyState?.dominant_emotion ?? 'joy'

    // 2. Generate greeting text
    const greetingText = generateGreeting(stage, emotion)

    // 3. Generate TTS audio via speech-synthesize Edge Function
    let audioUrl: string | undefined
    try {
      const ttsResponse = await fetch(`${SUPABASE_URL}/functions/v1/speech-synthesize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        },
        body: JSON.stringify({
          text: greetingText,
          voice: 'ko-KR-Neural2-A',
          speaking_rate: 1.1,
          pitch: 2.0,
        }),
      })

      if (ttsResponse.ok) {
        const ttsData = await ttsResponse.json()
        audioUrl = ttsData.audio_url
      } else {
        console.error('[WakeGreeting] TTS failed:', await ttsResponse.text())
      }
    } catch (ttsErr) {
      console.error('[WakeGreeting] TTS error:', ttsErr)
    }

    return NextResponse.json({
      greeting_text: greetingText,
      audio_url: audioUrl,
      emotion,
      development_stage: stage,
    })

  } catch (error) {
    console.error('[WakeGreeting] Error:', error)
    return NextResponse.json(
      { error: 'Failed to generate greeting', greeting_text: '네, 형아!' },
      { status: 500 }
    )
  }
}
