import { NextRequest, NextResponse } from 'next/server'

// Supabase Edge Function URL
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://extbfhoktzozgqddjcps.supabase.co'
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { image, mime_type, enable_world_understanding = true } = body

    if (!image) {
      return NextResponse.json(
        { error: 'Image data is required' },
        { status: 400 }
      )
    }

    // Call Supabase Edge Function directly
    const response = await fetch(`${SUPABASE_URL}/functions/v1/vision-process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        image_data: image,
        mime_type: mime_type || 'image/jpeg',
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[Vision API] Edge Function error:', errorText)
      return NextResponse.json(
        { error: 'Failed to process image' },
        { status: response.status }
      )
    }

    const data = await response.json()

    // Phase 4.4: Call world-understanding for physical world analysis
    if (enable_world_understanding && data.visual_experience) {
      try {
        const worldResponse = await fetch(`${SUPABASE_URL}/functions/v1/world-understanding`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
          },
          body: JSON.stringify({
            image_data: image,
            mime_type: mime_type || 'image/jpeg',
            visual_experience_id: data.visual_experience.id,
            objects_detected: data.visual_experience.objects_detected || [],
            development_stage: data.visual_experience.development_stage || 0,
            action: 'analyze',
          }),
        })

        if (worldResponse.ok) {
          const worldData = await worldResponse.json()
          // Merge world understanding data into response
          data.world_understanding = {
            physical_objects: worldData.physical_objects,
            spatial_relations: worldData.spatial_relations,
            tracking_events: worldData.tracking_events,
            physics_insights: worldData.physics_insights,
            emotional_response: worldData.emotional_response,
          }
          console.log('[Vision API] World understanding processed:', {
            objects: worldData.physical_objects?.length || 0,
            relations: worldData.spatial_relations?.length || 0,
          })
        } else {
          console.warn('[Vision API] World understanding failed, continuing without it')
        }
      } catch (worldError) {
        console.warn('[Vision API] World understanding error:', worldError)
        // Continue without world understanding data
      }
    }

    return NextResponse.json(data)

  } catch (error) {
    console.error('[Vision API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
