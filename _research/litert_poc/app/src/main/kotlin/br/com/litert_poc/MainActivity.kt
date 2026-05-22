package br.com.litert_poc

import android.content.res.AssetManager
import android.graphics.BitmapFactory
import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import com.google.ai.edge.litert.InterpreterApi
import com.google.ai.edge.litert.InterpreterApi.Options.TfLiteRuntime
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel

private const val TAG = "LiteRTPoC"

// Modelos empacotados em assets/ (copiados pelo script copy_models_to_poc.py)
private val MODELS = listOf(
    ModelConfig("coco_yolov8n_nc80_v0_i320_nodfl.tflite",   nc = 80,  label = "coco_v0"),
    ModelConfig("fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite", nc = 95, label = "fulldet_v3"),
)

private const val TEST_IMAGE = "bus.jpg"
private const val IMG_SIZE   = 320

data class ModelConfig(val filename: String, val nc: Int, val label: String)

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        Log.i(TAG, "=== LiteRT PoC T014 iniciado ===")

        val bitmap = assets.open(TEST_IMAGE).use { BitmapFactory.decodeStream(it) }
        Log.i(TAG, "Imagem de teste: ${bitmap.width}x${bitmap.height} (${TEST_IMAGE})")

        for (model in MODELS) {
            Log.i(TAG, "\n--- ${model.label} (${model.filename}) ---")
            runPocForModel(model, bitmap)
        }

        Log.i(TAG, "=== PoC concluído — ver logcat tag LiteRTPoC ===")
    }

    private fun runPocForModel(cfg: ModelConfig, bitmap: android.graphics.Bitmap) {
        val modelBuf = try {
            loadModelFile(assets, cfg.filename)
        } catch (e: Exception) {
            Log.e(TAG, "[${cfg.label}] ERRO ao abrir modelo: $e")
            return
        }
        Log.i(TAG, "[${cfg.label}] modelo carregado (${modelBuf.capacity() / 1024} KB)")

        // ── Cria intérprete e inspeciona tensores ─────────────────────────────
        val opts = InterpreterApi.Options()
            .setRuntime(TfLiteRuntime.PREFER_SYSTEM_OVER_APPLICATION)
            .setNumThreads(4)
        val interp = try {
            InterpreterApi.create(modelBuf, opts)
        } catch (e: Exception) {
            Log.e(TAG, "[${cfg.label}] ERRO ao criar intérprete: $e")
            return
        }

        // Log tensor info
        val inTensor  = interp.getInputTensor(0)
        val outTensor = interp.getOutputTensor(0)
        Log.i(TAG, "[${cfg.label}] Input:  shape=${inTensor.shape().toList()}  dtype=${inTensor.dataType()}")
        Log.i(TAG, "[${cfg.label}] Output: shape=${outTensor.shape().toList()} dtype=${outTensor.dataType()}")

        val inShape  = inTensor.shape()   // e.g. [1, 320, 320, 3]
        val outShape = outTensor.shape()  // e.g. [1, 84, 2100] ou [1, 2100, 84]

        // Escala de dequantização do output (para full_integer_quant INT8)
        val outScale  = outTensor.quantizationParams().scale.takeIf { it != 0f } ?: 1f
        val outZero   = outTensor.quantizationParams().zeroPoint
        Log.i(TAG, "[${cfg.label}] Output quant: scale=$outScale zero=$outZero")

        // ── Pré-processa imagem ───────────────────────────────────────────────
        val inputBuf = preprocessBitmap(bitmap, inShape)
        inputBuf.rewind()

        // ── Aloca buffer de saída ─────────────────────────────────────────────
        val outSize = outShape.fold(1) { acc, d -> acc * d }
        val outputBuf = ByteBuffer.allocateDirect(outSize)  // INT8 = 1 byte/elem
        outputBuf.order(ByteOrder.nativeOrder())

        // ── Inferência ────────────────────────────────────────────────────────
        val t0 = System.currentTimeMillis()
        try {
            interp.run(inputBuf, outputBuf)
        } catch (e: Exception) {
            // Tenta com FloatBuffer se INT8 falhar (modelo pode ter FLOAT32 output)
            Log.w(TAG, "[${cfg.label}] INT8 output falhou, tentando FLOAT32: $e")
            val floatBuf = ByteBuffer.allocateDirect(outSize * 4)
            floatBuf.order(ByteOrder.nativeOrder())
            inputBuf.rewind()
            interp.run(inputBuf, floatBuf)
            val elapsed = System.currentTimeMillis() - t0
            floatBuf.rewind()
            analyzeFloatOutput(cfg.label, "CPU-FP32", floatBuf, outShape, cfg.nc, elapsed)
            interp.close()
            return
        }
        val elapsed = System.currentTimeMillis() - t0

        // ── Analisa output INT8 ───────────────────────────────────────────────
        outputBuf.rewind()
        analyzeInt8Output(cfg.label, "CPU", outputBuf, outShape, cfg.nc, outScale, outZero, elapsed)

        // ── Tenta AICore delegate (S24 Exynos NPU) ───────────────────────────
        tryAicore(modelBuf, bitmap, cfg, inShape, outShape)

        interp.close()
    }

    private fun analyzeInt8Output(
        label: String, backend: String, buf: ByteBuffer,
        shape: IntArray, nc: Int, scale: Float, zero: Int, elapsedMs: Long
    ) {
        // Detecta orientação: [1, channels, anchors] ou [1, anchors, channels]
        val (channels, anchors) = if (shape.size == 3) {
            if (shape[1] >= 4 + nc) Pair(shape[1], shape[2])  // [1, 4+nc, 2100]
            else Pair(shape[2], shape[1])                       // [1, 2100, 4+nc]
        } else Pair(4 + nc, 2100)

        var maxScore = Float.NEGATIVE_INFINITY
        var maxClass = -1
        var hits025  = 0

        buf.rewind()
        val rawBytes = ByteArray(buf.remaining())
        buf.get(rawBytes)

        // Assumindo layout [1, channels, anchors] → scores em [4..4+nc-1, :]
        for (b in 0 until anchors) {
            for (c in 4 until channels.coerceAtMost(4 + nc)) {
                val idx = c * anchors + b
                if (idx >= rawBytes.size) break
                val rawVal = rawBytes[idx].toInt()
                val score  = (rawVal - zero) * scale
                if (score > maxScore) { maxScore = score; maxClass = c - 4 }
                if (score > 0.25f) hits025++
            }
        }

        Log.i(TAG, "[$label][$backend] ${elapsedMs}ms | max_score=${"%.4f".format(maxScore)} class=$maxClass hits>0.25=$hits025")
    }

    private fun analyzeFloatOutput(
        label: String, backend: String, buf: ByteBuffer,
        shape: IntArray, nc: Int, elapsedMs: Long
    ) {
        val (channels, anchors) = if (shape.size == 3) {
            if (shape[1] >= 4 + nc) Pair(shape[1], shape[2]) else Pair(shape[2], shape[1])
        } else Pair(4 + nc, 2100)

        var maxScore = Float.NEGATIVE_INFINITY
        var maxClass = -1
        var hits025  = 0

        val floats = FloatArray(buf.remaining() / 4)
        buf.asFloatBuffer().get(floats)

        for (b in 0 until anchors) {
            for (c in 4 until channels.coerceAtMost(4 + nc)) {
                val idx = c * anchors + b
                if (idx >= floats.size) break
                val score = floats[idx]
                if (score > maxScore) { maxScore = score; maxClass = c - 4 }
                if (score > 0.25f) hits025++
            }
        }

        Log.i(TAG, "[$label][$backend] ${elapsedMs}ms | max_score=${"%.4f".format(maxScore)} class=$maxClass hits>0.25=$hits025")
    }

    private fun tryAicore(
        modelBuf: MappedByteBuffer, bitmap: android.graphics.Bitmap,
        cfg: ModelConfig, inShape: IntArray, outShape: IntArray
    ) {
        try {
            val opts = InterpreterApi.Options()
                .setRuntime(TfLiteRuntime.FROM_SYSTEM_ONLY)
            val interp = InterpreterApi.create(modelBuf, opts)
            val inputBuf = preprocessBitmap(bitmap, inShape)
            val outSize  = outShape.fold(1) { acc, d -> acc * d }
            val outputBuf = ByteBuffer.allocateDirect(outSize)
            outputBuf.order(ByteOrder.nativeOrder())

            val t0 = System.currentTimeMillis()
            interp.run(inputBuf, outputBuf)
            val elapsed = System.currentTimeMillis() - t0

            val outTensor = interp.getOutputTensor(0)
            val scale = outTensor.quantizationParams().scale.takeIf { it != 0f } ?: 1f
            val zero  = outTensor.quantizationParams().zeroPoint
            outputBuf.rewind()
            analyzeInt8Output(cfg.label, "AICore", outputBuf, outShape, cfg.nc, scale, zero, elapsed)
            interp.close()
        } catch (e: Exception) {
            Log.w(TAG, "[${cfg.label}] AICore não disponível: ${e.message}")
        }
    }

    private fun preprocessBitmap(bitmap: android.graphics.Bitmap, inShape: IntArray): ByteBuffer {
        val h = if (inShape.size >= 2) inShape[1] else IMG_SIZE
        val w = if (inShape.size >= 3) inShape[2] else IMG_SIZE
        val scaled = android.graphics.Bitmap.createScaledBitmap(bitmap, w, h, true)
        val buf = ByteBuffer.allocateDirect(1 * h * w * 3)
        buf.order(ByteOrder.nativeOrder())
        val pixels = IntArray(h * w)
        scaled.getPixels(pixels, 0, w, 0, 0, w, h)
        for (px in pixels) {
            buf.put(((px shr 16) and 0xFF).toByte())  // R
            buf.put(((px shr  8) and 0xFF).toByte())  // G
            buf.put(( px         and 0xFF).toByte())  // B
        }
        buf.rewind()
        return buf
    }

    private fun loadModelFile(assets: AssetManager, filename: String): MappedByteBuffer {
        val fd = assets.openFd(filename)
        return FileInputStream(fd.fileDescriptor).channel
            .map(FileChannel.MapMode.READ_ONLY, fd.startOffset, fd.declaredLength)
    }
}
