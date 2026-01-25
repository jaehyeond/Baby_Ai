# Phase 4.5: Tool Use & Agency

**Version**: 1.2
**Created**: 2025-01-21
**Updated**: 2026-01-25
**Status**: ✅ Completed
**Edge Function Version**: v14

---

## Overview

Baby AI가 외부 도구를 사용하여 정보를 검색하고 작업을 수행할 수 있는 능력을 부여합니다.

### 현재 문제

```
사용자: "경험이라는 단어의 사전적 정의를 찾아봐"
Baby AI: "검색이 뭐야? 인터넷이 뭐야? 어떻게 하는데? 경험이 뭐야?"
```

Baby AI는 질문만 반복하고 직접 정보를 찾지 못합니다.

### 목표

```
사용자: "경험이라는 단어의 사전적 정의를 찾아봐"
Baby AI: [사전 API 호출] "경험이란 '자신이 실제로 해 보거나 겪어 봄. 또는 거기서 얻은 지식이나 기능'이래! 신기하다!"
```

---

## Step-by-Step Implementation

### Step 1: 감정 감쇠(Decay) 로직 추가 ✅

**목표**: 감정이 100%로 수렴하는 문제 해결

**파일**: `supabase/functions/conversation-process/index.ts`

**변경 사항**:
```typescript
// 추가할 함수
function applyEmotionDecay(
  babyState: BabyState,
  lastUpdatedAt: string
): Partial<BabyState> {
  const emotions = ['joy', 'curiosity', 'fear', 'surprise', 'frustration', 'boredom'];
  const neutralValue = 0.5;
  const decayRatePerHour = 0.05; // 시간당 5% 감쇠

  const lastUpdate = new Date(lastUpdatedAt);
  const hoursSinceUpdate = (Date.now() - lastUpdate.getTime()) / (1000 * 60 * 60);
  const decayFactor = Math.min(decayRatePerHour * hoursSinceUpdate, 0.5); // 최대 50%까지만 감쇠

  const updates: Partial<BabyState> = {};

  for (const emotion of emotions) {
    const currentValue = babyState[emotion] ?? 0.5;
    // 중립값(0.5)을 향해 감쇠
    updates[emotion] = currentValue + (neutralValue - currentValue) * decayFactor;
  }

  return updates;
}
```

**updateBabyState 함수 수정**:
```typescript
async function updateBabyState(/* ... */) {
  // 기존 상태 조회
  const { data: currentState } = await supabase
    .from('baby_state')
    .select('*')
    .single();

  // 1. 먼저 decay 적용
  const decayedEmotions = applyEmotionDecay(currentState, currentState.updated_at);

  // 2. 그 다음 대화에 따른 감정 변화 적용
  const emotionChanges = getEmotionChanges(dominantEmotion);

  // 3. 최종 감정 계산 (decay + 변화)
  const finalEmotions = mergeEmotions(decayedEmotions, emotionChanges);

  // 4. DB 업데이트
  await supabase.from('baby_state').update(finalEmotions);
}
```

### Step 2: 대화 컨텍스트 로드 기능 ✅

**목표**: 이전 대화를 기억하고 연속적인 대화 가능

**파일**: `supabase/functions/conversation-process/index.ts`

**변경 사항**:
```typescript
// 추가할 함수
async function loadConversationContext(
  supabase: SupabaseClient,
  conversationId: string | null,
  limit: number = 5
): Promise<ConversationMessage[]> {
  if (!conversationId) {
    // 새 대화 - 가장 최근 대화 세션의 마지막 몇 개 메시지 로드
    const { data } = await supabase
      .from('audio_conversations')
      .select('user_input, ai_response, created_at')
      .order('created_at', { ascending: false })
      .limit(limit);

    return (data ?? []).reverse();
  }

  // 기존 대화 - 해당 대화의 메시지 로드
  const { data } = await supabase
    .from('audio_conversations')
    .select('user_input, ai_response, created_at')
    .eq('conversation_id', conversationId)
    .order('created_at', { ascending: true })
    .limit(limit);

  return data ?? [];
}
```

**generateResponse 함수 수정**:
```typescript
async function generateResponse(/* ... */) {
  // 대화 컨텍스트 로드
  const conversationHistory = await loadConversationContext(supabase, conversationId);

  // 프롬프트에 대화 히스토리 포함
  const historyText = conversationHistory
    .map(msg => `사용자: ${msg.user_input}\nBaby: ${msg.ai_response}`)
    .join('\n\n');

  const prompt = `${systemPrompt}

## 이전 대화 (참고용)
${historyText}

## 현재 대화
사용자: "${userMessage}"

응답:`;

  // Gemini 호출
  const result = await model.generateContent(prompt);
}
```

### Step 3: Gemini Function Calling 통합 ✅

**목표**: Baby AI가 외부 도구를 사용할 수 있게 함

**파일**: `supabase/functions/conversation-process/index.ts`

**Step 3.1: 도구 정의**
```typescript
const tools = [
  {
    name: "search_dictionary",
    description: "한국어 단어의 사전적 정의를 검색합니다",
    parameters: {
      type: "object",
      properties: {
        word: {
          type: "string",
          description: "검색할 단어"
        }
      },
      required: ["word"]
    }
  },
  {
    name: "search_wikipedia",
    description: "Wikipedia에서 정보를 검색합니다",
    parameters: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "검색어"
        }
      },
      required: ["query"]
    }
  },
  {
    name: "calculate",
    description: "간단한 수학 계산을 수행합니다",
    parameters: {
      type: "object",
      properties: {
        expression: {
          type: "string",
          description: "계산할 수식 (예: 2+2, 10*5)"
        }
      },
      required: ["expression"]
    }
  }
];
```

**Step 3.2: 발달 단계별 도구 제한**

> ⚠️ **v14 변경**: 원래 `web_search`는 TEEN(stage 4)에서 해금 예정이었으나,
> 사용자 요청에 따라 **CHILD(stage 3)부터 해금**으로 앞당겨짐.

```typescript
function getAvailableTools(developmentStage: number): Tool[] {
  const toolsByStage: Record<number, string[]> = {
    0: [], // NEWBORN - 도구 없음
    1: [], // INFANT - 도구 없음
    2: ["search_dictionary"], // TODDLER - 사전만
    3: ["search_dictionary", "search_wikipedia", "calculate", "web_search"], // CHILD (v14: web_search 추가)
    // 4+ (TEEN): 모든 도구 + 향후 복잡한 도구 체인
  };

  const availableToolNames = toolsByStage[developmentStage] ?? [];
  return tools.filter(tool => availableToolNames.includes(tool.name));
}
```

**Step 3.3: 도구 실행 핸들러**
```typescript
async function executeTool(toolName: string, args: Record<string, any>): Promise<string> {
  switch (toolName) {
    case "search_dictionary":
      return await searchDictionary(args.word);
    case "search_wikipedia":
      return await searchWikipedia(args.query);
    case "calculate":
      return calculate(args.expression);
    case "web_search":  // v14 추가
      return await webSearch(args.query);
    default:
      return "알 수 없는 도구입니다";
  }
}

async function searchDictionary(word: string): Promise<string> {
  // 네이버 국어사전 API 또는 국립국어원 API 사용
  const response = await fetch(
    `https://opendict.korean.go.kr/api/search?key=${KOREAN_DICT_API_KEY}&q=${encodeURIComponent(word)}&req_type=json`
  );
  const data = await response.json();

  if (data.channel?.item?.[0]?.sense?.[0]?.definition) {
    return data.channel.item[0].sense[0].definition;
  }
  return `"${word}"의 정의를 찾을 수 없습니다`;
}

async function searchWikipedia(query: string): Promise<string> {
  const response = await fetch(
    `https://ko.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(query)}`
  );
  const data = await response.json();

  if (data.extract) {
    return data.extract.substring(0, 500); // 처음 500자만
  }
  return `"${query}"에 대한 정보를 찾을 수 없습니다`;
}

function calculate(expression: string): string {
  // 안전한 수식 계산 (eval 대신)
  try {
    const sanitized = expression.replace(/[^0-9+\-*/().]/g, '');
    const result = Function(`"use strict"; return (${sanitized})`)();
    return String(result);
  } catch {
    return "계산할 수 없는 수식입니다";
  }
}
```

**Step 3.4: 응답 생성 흐름 수정**
```typescript
async function generateResponse(
  model: GenerativeModel,
  supabase: SupabaseClient,
  userMessage: string,
  babyState: BabyState,
  conversationId: string | null
): Promise<{ response: string; toolUsed?: string }> {
  const availableTools = getAvailableTools(babyState.development_stage);

  // 대화 컨텍스트 로드
  const history = await loadConversationContext(supabase, conversationId);

  // 시스템 프롬프트 생성
  const systemPrompt = buildSystemPrompt(babyState, availableTools);

  // Gemini 호출 (Function Calling 포함)
  const result = await model.generateContent({
    contents: [{ role: "user", parts: [{ text: userMessage }] }],
    systemInstruction: systemPrompt,
    tools: availableTools.length > 0 ? [{ functionDeclarations: availableTools }] : undefined,
  });

  const response = result.response;

  // Function Call이 있는지 확인
  const functionCall = response.candidates?.[0]?.content?.parts?.find(
    part => part.functionCall
  )?.functionCall;

  if (functionCall) {
    // 도구 실행
    const toolResult = await executeTool(functionCall.name, functionCall.args);

    // 도구 결과를 포함하여 최종 응답 생성
    const finalResult = await model.generateContent({
      contents: [
        { role: "user", parts: [{ text: userMessage }] },
        { role: "model", parts: [{ functionCall }] },
        { role: "function", parts: [{ functionResponse: { name: functionCall.name, response: { result: toolResult } } }] }
      ],
      systemInstruction: systemPrompt,
    });

    return {
      response: finalResult.response.text() ?? "응답을 생성할 수 없습니다",
      toolUsed: functionCall.name,
    };
  }

  return { response: response.text() ?? "응답을 생성할 수 없습니다" };
}
```

---

## Implementation Order

| 순서 | 작업 | 복잡도 | 예상 영향 |
|------|------|--------|-----------|
| 1 | 감정 감쇠 로직 | 낮음 | 감정 100% 수렴 해결 |
| 2 | 대화 컨텍스트 로드 | 중간 | 대화 연속성 확보 |
| 3 | Function Calling 통합 | 높음 | 도구 사용 능력 부여 |

---

## Testing Plan

### 1. 감정 감쇠 테스트
```
1. 여러 번 대화하여 감정을 높임
2. 1시간 후 감정 값 확인
3. 0.5(중립)을 향해 감쇠되었는지 확인
```

### 2. 대화 컨텍스트 테스트
```
1. "내 이름은 철수야"라고 말함
2. 페이지 새로고침
3. "내 이름이 뭐야?"라고 물음
4. "철수"라고 답하는지 확인
```

### 3. 도구 사용 테스트
```
1. Baby를 TODDLER 단계로 발달시킴
2. "경험이라는 단어의 뜻을 찾아봐"라고 요청
3. 사전 검색 결과가 응답에 포함되는지 확인
```

---

## API Keys Required

| 서비스 | 환경변수 | 용도 |
|--------|----------|------|
| 국립국어원 API | `KOREAN_DICT_API_KEY` | 사전 검색 |
| (선택) Google CSE | `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_ID` | 웹 검색 |

---

## Success Criteria

- [x] 감정이 더 이상 100%로 수렴하지 않음
- [x] 새로고침 후에도 이전 대화 맥락 유지
- [x] TODDLER 단계에서 사전 검색 가능
- [x] CHILD 단계에서 Wikipedia 검색 가능
- [x] 발달 단계에 따라 사용 가능한 도구가 제한됨

## Deployment Notes

**Edge Function Version**: v14 (deployed 2026-01-25)

### 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v9 | 2025-01-21 | 초기 배포 - 감정 감쇠, 대화 컨텍스트, Function Calling |
| v13 | 2026-01-25 | 🐛 버그 수정: experience_concepts 연결 누락 |
| v14 | 2026-01-25 | ✨ 신규: `web_search` 도구 추가 (CHILD 단계부터) |

### v13 버그 수정 (2026-01-25)

**문제**: `extractAndSaveConcepts()` 함수가 `experience_concepts` 테이블에 INSERT를 하지 않음

**증상**:
- 최근 경험들의 `concept_count`가 모두 0
- 수면 통합(memory consolidation)이 뉴런에 영향 X (Hebb's Law 적용 불가)

**원인**:
```typescript
// v12 이전: idMap에 conceptId 저장만 하고 experience_concepts INSERT 누락
for (const c of concepts) {
  idMap.set(c.name, conceptId);
  // ❌ experience_concepts INSERT 없음!
}
```

**수정**:
```typescript
// v13: 개념 추출 후 experience_concepts에 연결
if (expId && conceptId) {
  await supabase.from('experience_concepts').insert({
    experience_id: expId,
    concept_id: conceptId,
    relevance: 0.7,
    co_activation_count: 1,
    created_at: new Date().toISOString()  // ✅ 올바른 컬럼명
  });
}
```

**검증**:
- 테스트: "컴퓨터가 뭐야?"
- 결과: `concepts_linked: 4`
- DB 확인: 4개 개념 연결됨 (모르는 말, 질문, 비비, 알려주세요)

### v14 신규 기능: web_search (2026-01-25)

**배경**:
- 사용자가 "인터넷에서 찾아봐"라고 요청
- 비비(CHILD 단계)가 "인터넷이 뭐야?"라고 응답
- 범용 웹 검색 도구가 없었음

**추가된 도구**:
```typescript
{
  name: "web_search",
  description: "인터넷에서 최신 정보를 검색합니다",
  parameters: {
    type: "object",
    properties: {
      query: { type: "string", description: "검색어" }
    },
    required: ["query"]
  }
}
```

**발달 단계별 도구 (업데이트됨)**:
| 단계 | 해금 도구 |
|------|-----------|
| 0 (NEWBORN) | 없음 |
| 1 (INFANT) | 없음 |
| 2 (TODDLER) | search_dictionary |
| 3 (CHILD) | search_dictionary, search_wikipedia, calculate, **web_search** |
| 4+ (TEEN) | 모든 도구 |

**구현**: DuckDuckGo Instant Answer API (무료, API 키 불필요)

---

구현된 기능:
1. `applyEmotionDecay()` - 시간당 5% 중립값(0.5) 방향 감쇠
2. `loadConversationContext()` - 최근 5개 대화 로드
3. `getAvailableTools()` - 발달 단계별 도구 해금
4. `executeTool()` - Wikipedia/사전 검색, 계산, **웹 검색** 실행
5. Gemini Function Calling 통합
6. `extractAndSaveConcepts()` - 개념 추출 및 **experience_concepts 연결** (v13 수정)
