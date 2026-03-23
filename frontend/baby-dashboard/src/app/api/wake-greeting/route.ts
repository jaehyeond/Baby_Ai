import { NextResponse } from 'next/server'

// Phase 4b: Supabase → FastAPI
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

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
    // 1. Get current baby state from FastAPI
    let stage = 2
    let emotion = 'joy'
    try {
      const stateRes = await fetch(`${FASTAPI_URL}/api/state`)
      if (stateRes.ok) {
        const stateData = await stateRes.json() as {
          development_stage: number
          emotional_state: Record<string, number>
        }
        stage = stateData.development_stage ?? 2
        // Determine dominant emotion from emotional_state map
        const emotionState = stateData.emotional_state || {}
        const dominant = Object.entries(emotionState).reduce(
          (max, [key, val]) => val > max[1] ? [key, val] : max,
          ['joy', 0] as [string, number]
        )
        emotion = dominant[0]
      }
    } catch (stateErr) {
      console.error('[WakeGreeting] Failed to get state:', stateErr)
    }

    // 2. Generate greeting text (logic stays in Route, no TTS until Phase 4d)
    const greetingText = generateGreeting(stage, emotion)

    return NextResponse.json({
      greeting_text: greetingText,
      audio_url: null,  // TTS: Phase 4d
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
