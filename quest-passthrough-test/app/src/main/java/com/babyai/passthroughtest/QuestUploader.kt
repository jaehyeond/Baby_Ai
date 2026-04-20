package com.babyai.passthroughtest

import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * Phase A4.3 — Quest → PC FastAPI Concept uploader
 *
 * 경량 HTTP 클라이언트. OkHttp 의존성 없이 표준 HttpURLConnection 사용.
 * 호출자는 background thread에서 호출해야 함 (network on main thread 금지).
 *
 * 실패 시 로컬 파일 저장은 MainActivity가 이미 수행 중 (saveConceptFile/saveSummaryFile).
 * 따라서 여기서는 단순 fire-and-log: 실패해도 전체 파이프라인 중단 안 됨.
 */
object QuestUploader {

    private const val TAG = "QuestUploader"
    private const val PATH = "/api/vision/quest-concepts"
    private const val CONNECT_TIMEOUT_MS = 5000
    private const val READ_TIMEOUT_MS = 10000

    private val ISO_FMT = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    data class UploadResult(
        val success: Boolean,
        val httpStatus: Int,
        val responseBody: String,
        val errorMessage: String?
    )

    fun isoTimestamp(epochMs: Long = System.currentTimeMillis()): String =
        ISO_FMT.format(Date(epochMs))

    /**
     * Quest passthrough 관측을 PC로 전송.
     *
     * @param baseUrl  e.g. "http://192.168.0.10:8000"  (trailing slash 없음)
     * @param vlmResponse  llama.cpp stdout
     * @param conceptsRaw  ConceptExtractor.extract() 결과
     * @param inferenceMs  추론 elapsed
     * @param imageWidth/Height  JPEG 해상도
     * @param camera  Camera2 ID (e.g. "50")
     * @param jpegPath  로컬 경로 (참조용 — 업로드 안 함)
     */
    fun upload(
        baseUrl: String,
        vlmResponse: String,
        conceptsRaw: List<String>,
        inferenceMs: Long,
        imageWidth: Int,
        imageHeight: Int,
        camera: String?,
        jpegPath: String?,
        modelName: String = "SmolVLM-500M-Q8"
    ): UploadResult {
        if (baseUrl.isBlank()) {
            return UploadResult(false, 0, "", "baseUrl empty (POST disabled)")
        }
        val url = URL("$baseUrl$PATH")
        val payload = JSONObject().apply {
            put("timestamp", isoTimestamp())
            put("source", "quest_passthrough")
            put("model", modelName)
            put("image_meta", JSONObject().apply {
                put("width", imageWidth)
                put("height", imageHeight)
                if (camera != null) put("camera", camera)
            })
            put("vlm_response", vlmResponse)
            put("concepts_raw", JSONArray(conceptsRaw))
            put("inference_ms", inferenceMs)
            if (jpegPath != null) put("jpeg_path", jpegPath)
        }.toString()

        var conn: HttpURLConnection? = null
        return try {
            conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = READ_TIMEOUT_MS
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                setRequestProperty("Accept", "application/json")
            }
            conn.outputStream.use { it.write(payload.toByteArray(Charsets.UTF_8)) }
            val status = conn.responseCode
            val body = (if (status in 200..299) conn.inputStream else conn.errorStream)
                ?.bufferedReader()?.use { it.readText() } ?: ""
            Log.i(TAG, "POST $url → $status (${body.take(200)})")
            UploadResult(status in 200..299, status, body, null)
        } catch (e: Exception) {
            Log.w(TAG, "upload failed: ${e.javaClass.simpleName}: ${e.message}")
            UploadResult(false, 0, "", e.message ?: e.javaClass.simpleName)
        } finally {
            conn?.disconnect()
        }
    }
}
