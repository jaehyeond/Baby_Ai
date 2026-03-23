---
name: conversation-pipeline
description: This skill should be used when modifying conversation processing, memory recall, Gemini prompt construction, or the message pipeline in the Baby AI project. Covers the v30 conversation-process architecture including extractKeywords, loadRelevantConcepts, loadRelevantExperiences, and formatMemoryContext flow. Also applies when working with emotional modulation (LC-NE Adaptive Gain) or the "모르겠어요" prohibition rule.
version: 1.0.0
---

# Conversation Pipeline Architecture (v30)

The conversation-process Edge Function is the most critical and frequently modified component. Understand this architecture before making changes.

## Pipeline Flow

```
User message
  → extractKeywords(message)
  → loadRelevantConcepts(keywords, limit=10)
  → loadRelevantExperiences(keywords, limit=5)
  → formatMemoryContext(concepts, experiences)
  → Inject into Gemini prompt as memory context
  → Gemini generates response
  → Store experience + update emotional state
  → Return response with extras (recall stats)
```

### Key Functions

| Function | Input | Output | Notes |
|----------|-------|--------|-------|
| `extractKeywords()` | User message text | Array of keyword strings | Extracts meaningful terms |
| `loadRelevantConcepts()` | Keywords, limit=10 | Concept objects with descriptions | Queries Neo4j |
| `loadRelevantExperiences()` | Keywords, limit=5 | Experience objects with context | Queries Neo4j |
| `formatMemoryContext()` | Concepts + Experiences | Formatted string for prompt | Structures recall data |

## Gemini Prompt Rules

### Mandatory [필수 규칙] Section

The prompt includes a `[필수 규칙]` section that enforces:

1. **"모르겠어요" 금지** — Baby must never say "I don't know" or equivalent. Always attempt an answer based on available knowledge.
2. **Response length** — Currently constrained to "1-3 sentences" (this contributes to shallow recall usage).
3. **Memory integration** — Response must reference recalled concepts/experiences when relevant.

### Current Limitations (v30)

| Problem | Cause | Impact |
|---------|-------|--------|
| Gemini uses only 2-3 of 10 recalled concepts | Descriptions too brief (1 line each) | Shallow knowledge integration |
| Responses feel generic despite rich recall | "1-3문장" constraint too restrictive | Prevents detailed memory usage |
| No temporal awareness | Current date not injected into prompt | Cannot reference "yesterday" or time-relative concepts |

**When modifying the pipeline**: Do not make these limitations worse. Improvements should expand memory utilization, not further constrain it.

## Emotional Modulation: LC-NE Adaptive Gain (v28)

Based on Aston-Jones & Cohen (2005) locus coeruleus-norepinephrine model.

The emotional modulator adjusts response characteristics based on Baby's current emotional state:

- **High arousal** (curiosity, excitement) → More exploratory, varied responses
- **Low arousal** (boredom, calm) → More focused, routine responses
- **Negative valence** (fear, frustration) → Cautious, seeking comfort
- **Positive valence** (joy, interest) → Open, engaging responses

Modulation happens AFTER memory recall but BEFORE Gemini prompt construction. The emotional state influences which recalled memories are prioritized and how the prompt frames the interaction.

## Version History (Recent)

| Version | Change | Date |
|---------|--------|------|
| v30 | Memory Recall Pipeline + prompt enhancement | 2026-02-23 |
| v28 | LC-NE Adaptive Gain emotional modulator | earlier |
| v27 | Concept isolation bug fix (multi-tenant scoping) | earlier |
| v24 | F4 emotion downstream implementation | earlier |

## Modification Checklist

Before modifying conversation-process:

1. **Check current version** — Read CHANGELOG.md for latest version number
2. **Understand the full chain** — Trace from user input to Gemini response
3. **Preserve recall pipeline** — extractKeywords → load → format → inject
4. **Maintain [필수 규칙]** — Do not remove or weaken mandatory rules
5. **Test with real conversation** — Verify Baby responds coherently after changes
6. **Update extras** — Ensure recall statistics are saved in response extras
7. **Bump version number** — Increment in both code and CHANGELOG
