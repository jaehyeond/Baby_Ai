package com.babyai.passthroughtest

import android.util.Log
import java.io.BufferedReader
import java.io.InputStreamReader

/**
 * Phase A3.1 — SELinux Kill-Switch
 * 앱 UID에서 외부 프로세스 실행이 가능한지 점진적으로 검증.
 *
 * 결과 4가지:
 *  OK         — 정상 실행, stdout 수신
 *  DENIED     — SELinux or permission denied
 *  NOT_FOUND  — 실행 파일 없음
 *  OTHER      — 기타 오류
 */
object ProcessTester {

    private const val TAG = "ProcessTester"

    data class Result(
        val status: String,
        val exitCode: Int,
        val stdout: String,
        val stderr: String,
        val elapsedMs: Long,
        val error: String? = null
    )

    fun runCommand(
        cmd: List<String>,
        timeoutMs: Long = 10_000,
        env: Map<String, String> = emptyMap()
    ): Result {
        val start = System.currentTimeMillis()
        return try {
            val pb = ProcessBuilder(cmd).redirectErrorStream(false)
            if (env.isNotEmpty()) {
                pb.environment().putAll(env)
            }
            val process = pb.start()

            val stdoutReader = BufferedReader(InputStreamReader(process.inputStream))
            val stderrReader = BufferedReader(InputStreamReader(process.errorStream))

            val finished = process.waitFor(timeoutMs, java.util.concurrent.TimeUnit.MILLISECONDS)
            if (!finished) {
                process.destroyForcibly()
                return Result(
                    status = "TIMEOUT",
                    exitCode = -1,
                    stdout = "",
                    stderr = "",
                    elapsedMs = System.currentTimeMillis() - start,
                    error = "timeout after ${timeoutMs}ms"
                )
            }

            val stdout = stdoutReader.readText()
            val stderr = stderrReader.readText()
            val exit = process.exitValue()
            val elapsed = System.currentTimeMillis() - start

            val status = when {
                exit == 0 -> "OK"
                stderr.contains("Permission denied", ignoreCase = true) -> "DENIED"
                stderr.contains("No such file", ignoreCase = true) -> "NOT_FOUND"
                stderr.contains("operation not permitted", ignoreCase = true) -> "DENIED"
                else -> "OTHER"
            }

            Result(status, exit, stdout, stderr, elapsed)
        } catch (e: Exception) {
            val elapsed = System.currentTimeMillis() - start
            Log.e(TAG, "runCommand failed", e)
            val status = when {
                e.message?.contains("Permission denied", ignoreCase = true) == true -> "DENIED"
                e.message?.contains("error=13", ignoreCase = true) == true -> "DENIED"
                e.message?.contains("No such file", ignoreCase = true) == true -> "NOT_FOUND"
                e.message?.contains("error=2", ignoreCase = true) == true -> "NOT_FOUND"
                else -> "OTHER"
            }
            Result(status, -1, "", "", elapsed, e.message)
        }
    }

    /**
     * SELinux + 실행 권한 3단계 스모크 테스트
     */
    fun smokeTest(): List<Pair<String, Result>> {
        val tests = listOf(
            "echo hello" to listOf("/system/bin/echo", "hello"),
            "ls system bin" to listOf("/system/bin/ls", "/system/bin/"),
            "ls /data/local/tmp (app UID 일반 차단)" to listOf("/system/bin/ls", "/data/local/tmp/"),
            "uname" to listOf("/system/bin/uname", "-a"),
            "id" to listOf("/system/bin/id")
        )
        return tests.map { (label, cmd) ->
            label to runCommand(cmd)
        }
    }
}
