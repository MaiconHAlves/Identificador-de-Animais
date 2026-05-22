package com.maiconalves.animaldetector

import android.app.Service
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Message
import android.os.Messenger
import android.util.Log

class DetectionService : Service() {

    companion object {
        private const val TAG = "DetectionService"
        const val MSG_INFER  = 1
        const val MSG_RESULT = 2

        // T015 — mock fixo; substituir por LiteRT real na T016
        private val MOCK_DETECTIONS = arrayOf(
            DetectionDTO(classId =  0, label = "person", confidence = 0.91f, x1 = 0.10f, y1 = 0.10f, x2 = 0.40f, y2 = 0.90f),
            DetectionDTO(classId =  2, label = "car",    confidence = 0.85f, x1 = 0.50f, y1 = 0.30f, x2 = 0.90f, y2 = 0.70f),
            DetectionDTO(classId = 16, label = "dog",    confidence = 0.72f, x1 = 0.20f, y1 = 0.50f, x2 = 0.50f, y2 = 0.90f),
        )
    }

    private val incomingHandler = object : Handler(Looper.getMainLooper()) {
        override fun handleMessage(msg: Message) {
            when (msg.what) {
                MSG_INFER -> handleInfer(msg)
                else -> super.handleMessage(msg)
            }
        }
    }

    private val messenger = Messenger(incomingHandler)

    override fun onBind(intent: Intent): IBinder {
        Log.i(TAG, "onBind — DetectionService pronto (mock)")
        return messenger.binder
    }

    override fun onUnbind(intent: Intent): Boolean {
        Log.i(TAG, "onUnbind")
        return false
    }

    private fun handleInfer(msg: Message) {
        val replyTo = msg.replyTo ?: run {
            Log.w(TAG, "MSG_INFER sem replyTo — ignorado")
            return
        }

        val reply = Message.obtain(null, MSG_RESULT)
        val bundle = Bundle()
        bundle.putParcelableArray("detections", MOCK_DETECTIONS)
        reply.data = bundle

        try {
            replyTo.send(reply)
        } catch (e: Exception) {
            Log.e(TAG, "Falha ao enviar MSG_RESULT: $e")
        }
    }
}
