package com.babyai.passthroughtest

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.ImageFormat
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.TotalCaptureResult
import android.media.ImageReader
import android.os.Bundle
import android.os.Handler
import android.os.HandlerThread
import android.util.Log
import android.app.Activity
import android.util.Size
import android.view.ViewGroup
import android.widget.ScrollView
import android.widget.TextView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : Activity() {

    companion object {
        private const val TAG = "PassthroughTest"
        private const val REQ_PERMISSIONS = 1001
        private const val HEADSET_CAMERA = "horizonos.permission.HEADSET_CAMERA"

        // intent extras
        private const val EXTRA_ROUNDS = "rounds"
        private const val EXTRA_PROMPT = "prompt"
        private const val EXTRA_RUN_DIAG = "run_diag"  // smoke + binary test
        private const val EXTRA_N_TOKENS = "n_tokens"
    }

    private lateinit var logView: TextView
    private lateinit var cameraManager: CameraManager
    private var cameraDevice: CameraDevice? = null
    private var captureSession: CameraCaptureSession? = null
    private var imageReader: ImageReader? = null
    private var backgroundThread: HandlerThread? = null
    private var backgroundHandler: Handler? = null

    // Run config
    private var targetRounds: Int = 1
    private var runDiag: Boolean = true
    private var prompt: String = "Describe what you see briefly."
    private var nTokens: Int = 64
    private var roundIdx: Int = 0
    private val roundStats = mutableListOf<RoundStat>()

    // Pre-resolved paths (set once)
    private var selectedCamera: String? = null
    private var exePath: String = ""
    private var nativeDir: String = ""

    @Volatile private var lastJpegPath: String? = null

    data class RoundStat(
        val round: Int,
        val captureMs: Long,
        val inferenceMs: Long,
        val cpuTotalMs: Long,   // llama.cpp total time (from stderr)
        val clipMs: Long,       // image slice encoded
        val tokensGenerated: Int,
        val tps: Double,
        val batteryStart: Int,
        val batteryEnd: Int,
        val tempStart: Int,     // 10분의 1 단위
        val tempEnd: Int,
        val output: String
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        targetRounds = intent.getIntExtra(EXTRA_ROUNDS, 1).coerceAtLeast(1)
        runDiag = intent.getBooleanExtra(EXTRA_RUN_DIAG, false)
        prompt = intent.getStringExtra(EXTRA_PROMPT) ?: "Describe what you see briefly."
        nTokens = intent.getIntExtra(EXTRA_N_TOKENS, 64)

        logView = TextView(this).apply {
            textSize = 14f
            setPadding(24, 24, 24, 24)
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        }
        val scrollView = ScrollView(this).apply { addView(logView) }
        setContentView(scrollView)

        log("=== Passthrough Test Phase A3.5 ===")
        log("Build: ${android.os.Build.MODEL} / ${android.os.Build.VERSION.RELEASE}")
        log("Config: rounds=$targetRounds, n=$nTokens, diag=$runDiag")
        log("Prompt: \"$prompt\"")

        cameraManager = getSystemService(Context.CAMERA_SERVICE) as CameraManager
        nativeDir = applicationInfo.nativeLibraryDir
        exePath = "$nativeDir/libllama-mtmd-cli-exe.so"

        startBackgroundThread()
        checkAndRequestPermissions()
    }

    override fun onDestroy() {
        super.onDestroy()
        closeCamera()
        stopBackgroundThread()
    }

    private fun startBackgroundThread() {
        backgroundThread = HandlerThread("CameraBackground").also { it.start() }
        backgroundHandler = Handler(backgroundThread!!.looper)
    }

    private fun stopBackgroundThread() {
        backgroundThread?.quitSafely()
        try { backgroundThread?.join() } catch (e: InterruptedException) { }
    }

    private fun checkAndRequestPermissions() {
        val need = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            != PackageManager.PERMISSION_GRANTED) need.add(Manifest.permission.CAMERA)
        if (ContextCompat.checkSelfPermission(this, HEADSET_CAMERA)
            != PackageManager.PERMISSION_GRANTED) need.add(HEADSET_CAMERA)

        if (need.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, need.toTypedArray(), REQ_PERMISSIONS)
        } else {
            onPermissionsReady()
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQ_PERMISSIONS) {
            val allGranted = grantResults.all { it == PackageManager.PERMISSION_GRANTED }
            if (allGranted) onPermissionsReady() else log("ERROR: permissions denied")
        }
    }

    private fun onPermissionsReady() {
        log("Permissions OK")
        val backCamera = pickBackCamera()
        if (backCamera == null) {
            log("ERROR: no back camera")
            return
        }
        selectedCamera = backCamera
        log("Selected camera: $backCamera")

        if (runDiag) {
            backgroundHandler?.post {
                runSmokeTest()
                runBinaryHelpTest()
                startRound(1)
            }
        } else {
            startRound(1)
        }
    }

    private fun pickBackCamera(): String? {
        return try {
            cameraManager.cameraIdList.firstOrNull { id ->
                val chars = cameraManager.getCameraCharacteristics(id)
                chars.get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_BACK
            }
        } catch (e: Exception) {
            log("pickBackCamera error: ${e.message}")
            null
        }
    }

    private fun startRound(round: Int) {
        roundIdx = round
        log("")
        log("================================")
        log("  Round $round / $targetRounds")
        log("================================")
        val cam = selectedCamera ?: return
        currentRoundCaptureStart = System.currentTimeMillis()
        currentRoundBattery = readBatteryPercent()
        currentRoundTemp = readBatteryTemp()
        openAndCapture(cam)
    }

    private var currentRoundCaptureStart: Long = 0
    private var currentRoundBattery: Int = -1
    private var currentRoundTemp: Int = -1

    private fun openAndCapture(cameraId: String) {
        try {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED) {
                log("CAMERA permission missing")
                return
            }

            val chars = cameraManager.getCameraCharacteristics(cameraId)
            val configMap = chars.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP) ?: return
            val jpegSizes = configMap.getOutputSizes(ImageFormat.JPEG) ?: return
            val pickedSize = jpegSizes
                .filter { it.width <= 1280 && it.height <= 960 }
                .maxByOrNull { it.width.toLong() * it.height.toLong() }
                ?: jpegSizes.first()

            imageReader = ImageReader.newInstance(
                pickedSize.width, pickedSize.height, ImageFormat.JPEG, 1
            ).apply {
                setOnImageAvailableListener({ reader ->
                    val image = reader.acquireLatestImage()
                    if (image != null) {
                        val buffer: ByteBuffer = image.planes[0].buffer
                        val bytes = ByteArray(buffer.remaining())
                        buffer.get(bytes)
                        saveJpegAndContinue(cameraId, bytes)
                        image.close()
                    }
                }, backgroundHandler)
            }

            cameraManager.openCamera(cameraId, object : CameraDevice.StateCallback() {
                override fun onOpened(device: CameraDevice) {
                    cameraDevice = device
                    createSession(device)
                }
                override fun onDisconnected(device: CameraDevice) {
                    device.close(); cameraDevice = null
                }
                override fun onError(device: CameraDevice, error: Int) {
                    log("Camera error code $error")
                    device.close(); cameraDevice = null
                }
            }, backgroundHandler)

        } catch (e: SecurityException) {
            log("SecurityException: ${e.message}")
        } catch (e: Exception) {
            log("open exception: ${e.message}")
        }
    }

    private fun createSession(device: CameraDevice) {
        try {
            val surface = imageReader!!.surface
            val builder = device.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE)
            builder.addTarget(surface)

            device.createCaptureSession(
                listOf(surface),
                object : CameraCaptureSession.StateCallback() {
                    override fun onConfigured(session: CameraCaptureSession) {
                        captureSession = session
                        session.capture(builder.build(), null, backgroundHandler)
                    }
                    override fun onConfigureFailed(session: CameraCaptureSession) {
                        log("Session configure FAILED")
                    }
                },
                backgroundHandler
            )
        } catch (e: Exception) {
            log("createSession exception: ${e.message}")
        }
    }

    private fun saveJpegAndContinue(cameraId: String, bytes: ByteArray) {
        try {
            val dir = File(getExternalFilesDir(null), "passthrough_captures")
            if (!dir.exists()) dir.mkdirs()
            val ts = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
            val file = File(dir, "r${roundIdx}_cam${cameraId}_${ts}.jpg")
            FileOutputStream(file).use { it.write(bytes) }
            lastJpegPath = file.absolutePath
            val captureMs = System.currentTimeMillis() - currentRoundCaptureStart
            log("Captured (round=$roundIdx): ${file.name} ${bytes.size}B in ${captureMs}ms")

            // 카메라는 즉시 닫아서 다음 라운드에 새로 열기 (단일 스냅샷)
            closeCamera()

            backgroundHandler?.post { runInference(captureMs) }
        } catch (e: Exception) {
            log("Save error: ${e.message}")
        }
    }

    private fun runInference(captureMs: Long) {
        val jpegPath = lastJpegPath ?: run {
            log("ERROR: no jpeg")
            return
        }

        val modelsDir = File(getExternalFilesDir(null), "models")
        val model = File(modelsDir, "SmolVLM-256M-Instruct-Q8_0.gguf")
        val mmproj = File(modelsDir, "mmproj-SmolVLM-256M-Instruct-Q8_0.gguf")
        if (!model.exists() || !mmproj.exists()) {
            log("ERROR: model missing")
            return
        }

        val cmd = listOf(
            exePath,
            "-m", model.absolutePath,
            "--mmproj", mmproj.absolutePath,
            "-c", "1024",
            "-t", "4",
            "-tb", "4",
            "--image", jpegPath,
            "-p", prompt,
            "-n", nTokens.toString(),
            "--temp", "0.1"
        )
        val env = mapOf("LD_LIBRARY_PATH" to nativeDir)
        val t0 = System.currentTimeMillis()
        val r = ProcessTester.runCommand(cmd, timeoutMs = 120_000, env = env)
        val elapsed = System.currentTimeMillis() - t0

        // 메트릭 파싱
        val stderr = r.stderr
        val totalMs = parseMsFromLine(stderr, "total time =")
        val clipMs = parseClipMs(stderr)
        val (evalRuns, evalTPS) = parseEvalStats(stderr)

        val batteryEnd = readBatteryPercent()
        val tempEnd = readBatteryTemp()

        val stat = RoundStat(
            round = roundIdx,
            captureMs = captureMs,
            inferenceMs = elapsed,
            cpuTotalMs = totalMs,
            clipMs = clipMs,
            tokensGenerated = evalRuns,
            tps = evalTPS,
            batteryStart = currentRoundBattery,
            batteryEnd = batteryEnd,
            tempStart = currentRoundTemp,
            tempEnd = tempEnd,
            output = r.stdout.trim().take(500)
        )
        roundStats.add(stat)

        log("R${roundIdx}: status=${r.status} elapsed=${elapsed}ms cpu=${totalMs}ms clip=${clipMs}ms tokens=${evalRuns} tps=${"%.1f".format(evalTPS)}")
        log("   batt=${currentRoundBattery}→${batteryEnd}% temp=${currentRoundTemp/10.0}→${tempEnd/10.0}°C")
        log("   out: ${stat.output.take(200)}")

        // 다음 라운드
        if (roundIdx < targetRounds) {
            backgroundHandler?.postDelayed({ startRound(roundIdx + 1) }, 500)
        } else {
            printSummary()
        }
    }

    private fun printSummary() {
        log("")
        log("=======================================")
        log("  SUMMARY: ${roundStats.size} rounds")
        log("=======================================")
        if (roundStats.isEmpty()) return

        val elapseds = roundStats.map { it.inferenceMs }
        val clips = roundStats.map { it.clipMs }.filter { it > 0 }
        val tpses = roundStats.map { it.tps }.filter { it > 0 }
        val tokens = roundStats.map { it.tokensGenerated }

        fun summarize(name: String, values: List<Long>) {
            if (values.isEmpty()) return
            val avg = values.average()
            val min = values.min()
            val max = values.max()
            val std = kotlin.math.sqrt(values.map { (it - avg) * (it - avg) }.average())
            log("$name: avg=${avg.toLong()}ms min=${min}ms max=${max}ms std=${std.toLong()}ms (n=${values.size})")
        }
        fun summarizeD(name: String, values: List<Double>) {
            if (values.isEmpty()) return
            val avg = values.average()
            val min = values.min()
            val max = values.max()
            log("$name: avg=${"%.1f".format(avg)} min=${"%.1f".format(min)} max=${"%.1f".format(max)} (n=${values.size})")
        }

        summarize("inference elapsed", elapseds)
        summarize("CLIP encode   ", clips)
        summarizeD("Gen TPS       ", tpses)

        log("")
        log("Battery: ${roundStats.first().batteryStart}% → ${roundStats.last().batteryEnd}% (drop ${roundStats.first().batteryStart - roundStats.last().batteryEnd}%)")
        log("Temp   : ${roundStats.first().tempStart/10.0}°C → ${roundStats.last().tempEnd/10.0}°C")

        log("")
        log("Per-round:")
        roundStats.forEach {
            log("  R${it.round}: ${it.inferenceMs}ms cpu=${it.cpuTotalMs}ms clip=${it.clipMs}ms tokens=${it.tokensGenerated} tps=${"%.1f".format(it.tps)} batt=${it.batteryEnd}% temp=${it.tempEnd/10.0}°C")
        }

        // 결과를 파일로 저장 (ADB pull용)
        saveSummaryFile()
    }

    private fun saveSummaryFile() {
        try {
            val dir = File(getExternalFilesDir(null), "results")
            if (!dir.exists()) dir.mkdirs()
            val ts = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
            val file = File(dir, "summary_${ts}.txt")
            file.writeText(buildString {
                appendLine("rounds=${targetRounds}, prompt=\"$prompt\", n=$nTokens")
                appendLine("round\telapsed\tcpu\tclip\ttokens\ttps\tbatt_start\tbatt_end\ttemp_start\ttemp_end\toutput")
                roundStats.forEach {
                    appendLine("${it.round}\t${it.inferenceMs}\t${it.cpuTotalMs}\t${it.clipMs}\t${it.tokensGenerated}\t${"%.1f".format(it.tps)}\t${it.batteryStart}\t${it.batteryEnd}\t${it.tempStart}\t${it.tempEnd}\t${it.output.replace("\n", " ").take(200)}")
                }
            })
            log("")
            log("Summary saved: ${file.absolutePath}")
        } catch (e: Exception) {
            log("saveSummaryFile error: ${e.message}")
        }
    }

    // --- diagnostics (runDiag=true일 때만) ---

    private fun runSmokeTest() {
        log("")
        log("=== SELinux smoke test ===")
        val results = ProcessTester.smokeTest()
        results.forEach { (label, r) ->
            log("[$label] status=${r.status} exit=${r.exitCode} ms=${r.elapsedMs}")
            if (r.stdout.isNotBlank()) log("  > ${r.stdout.trim().take(100)}")
            if (r.stderr.isNotBlank()) log("  ! ${r.stderr.trim().take(100)}")
        }
    }

    private fun runBinaryHelpTest() {
        log("")
        log("=== native binary exec test ===")
        val env = mapOf("LD_LIBRARY_PATH" to nativeDir)
        val r = ProcessTester.runCommand(listOf(exePath, "--version"), timeoutMs = 3_000, env = env)
        log("--version: status=${r.status} exit=${r.exitCode} ms=${r.elapsedMs}")
        if (r.stdout.isNotBlank()) log("  > ${r.stdout.trim().take(200)}")
        if (r.stderr.isNotBlank()) log("  ! ${r.stderr.trim().take(200)}")
    }

    // --- utilities ---

    private fun parseMsFromLine(text: String, marker: String): Long {
        // e.g. "total time =    5453.11 ms / 137 tokens"
        return try {
            val line = text.lines().firstOrNull { it.contains(marker) } ?: return -1
            val after = line.substringAfter(marker).trim()
            val numStr = after.substringBefore(" ").substringBefore("ms").trim()
            numStr.toDouble().toLong()
        } catch (e: Exception) { -1 }
    }

    private fun parseClipMs(text: String): Long {
        return try {
            val line = text.lines().firstOrNull { it.contains("image slice encoded") } ?: return -1
            // "image slice encoded in 4988 ms"
            val after = line.substringAfter("encoded in ").trim()
            after.substringBefore(" ").toLong()
        } catch (e: Exception) { -1 }
    }

    private fun parseEvalStats(text: String): Pair<Int, Double> {
        // "eval time = 1379.45 ms / 18 runs (76.64 ms per token, 13.05 tokens per second)"
        return try {
            val line = text.lines().firstOrNull {
                it.contains("eval time") && it.contains("per token") && !it.contains("prompt eval")
            } ?: return 0 to 0.0
            val runsStr = line.substringAfter("ms / ").substringBefore(" runs").trim()
            val tpsStr = line.substringAfter("per token,").substringBefore("tokens per second").trim()
            runsStr.toInt() to tpsStr.toDouble()
        } catch (e: Exception) { 0 to 0.0 }
    }

    private fun readBatteryPercent(): Int {
        val bm = getSystemService(Context.BATTERY_SERVICE) as android.os.BatteryManager
        return bm.getIntProperty(android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY)
    }
    private fun readBatteryTemp(): Int {
        // dumpsys 없이 BatteryManager로는 온도 직접 못 얻음. BroadcastReceiver로만.
        // 여기서는 /sys 접근 실패하므로 -1 반환
        return try {
            val intent = registerReceiver(null, android.content.IntentFilter(android.content.Intent.ACTION_BATTERY_CHANGED))
            intent?.getIntExtra(android.os.BatteryManager.EXTRA_TEMPERATURE, -1) ?: -1
        } catch (e: Exception) { -1 }
    }

    private fun closeCamera() {
        captureSession?.close(); captureSession = null
        cameraDevice?.close(); cameraDevice = null
        imageReader?.close(); imageReader = null
    }

    private fun log(msg: String) {
        Log.i(TAG, msg)
        runOnUiThread { logView.append("$msg\n") }
    }
}
