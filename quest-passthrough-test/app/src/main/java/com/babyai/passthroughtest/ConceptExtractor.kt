package com.babyai.passthroughtest

/**
 * Phase A4.2 — MVP 명사 추출기
 *
 * 단순 규칙 기반:
 *  - lowercase
 *  - 문장부호 → 공백
 *  - 길이 3+ 필터
 *  - stopword 제외
 *  - "a", "an", "the" 뒤 첫 명사 추출 경향 (단순화: 단어마다 개별 판정)
 *
 * 정교한 파싱은 A4.3에서 LLM 호출로 대체 예정.
 */
object ConceptExtractor {

    private val STOPWORDS = setOf(
        // 관사/대명사/지시
        "a", "an", "the", "this", "that", "these", "those",
        "it", "its", "they", "them", "their", "there", "here",
        "i", "you", "we", "he", "she", "his", "her", "our", "your",
        // be/have/do
        "is", "are", "was", "were", "be", "been", "being", "am",
        "have", "has", "had", "having",
        "do", "does", "did", "doing",
        // 전치사/접속사
        "in", "on", "at", "by", "for", "of", "with", "to", "from",
        "and", "or", "but", "not", "also", "as", "if", "so",
        "into", "onto", "upon", "about", "against", "between",
        "through", "across", "over", "under", "above", "below",
        "front", "back", "top", "bottom", "side",
        // 일반 서술어/서술자
        "see", "sees", "seen", "looks", "looking", "appears", "looks",
        "sits", "lies", "stands", "placed", "placed",
        "some", "any", "all", "many", "more", "most", "few", "several",
        "can", "could", "will", "would", "may", "might", "must",
        "shows", "showing", "shown", "displays", "displaying",
        "with", "without", "within", "which", "what", "who", "whom",
        // 일반적 서술 단어
        "image", "picture", "photo", "shot", "view", "scene",
        "object", "objects", "item", "items", "thing", "things",
        "lot", "kind", "type",
        // 숫자/수량
        "one", "two", "three", "four", "five", "six", "seven",
        "first", "second", "third",
    )

    private val PUNCT_REGEX = Regex("[\\p{Punct}\\d]")
    private val WHITESPACE_REGEX = Regex("\\s+")

    /**
     * 한 응답 텍스트에서 개별 후보 단어 집합 반환.
     * 중복 제거는 호출자가 담당.
     */
    fun extract(text: String): List<String> {
        val lowered = text.lowercase()
        val cleaned = lowered.replace(PUNCT_REGEX, " ")
        val tokens = cleaned.split(WHITESPACE_REGEX)
            .filter { it.length >= 3 }
            .filter { it !in STOPWORDS }
        return tokens
    }

    /**
     * 여러 응답에서 누적 집합 + 빈도 계산.
     */
    fun accumulate(
        responses: List<String>,
        existing: MutableMap<String, Int> = mutableMapOf()
    ): Map<String, Int> {
        for (r in responses) {
            for (tok in extract(r)) {
                existing[tok] = (existing[tok] ?: 0) + 1
            }
        }
        return existing
    }
}
