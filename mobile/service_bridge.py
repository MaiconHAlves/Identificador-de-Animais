"""
T015 — Bridge Python → DetectionService Kotlin (Bound Service via Messenger/Pyjnius).

Roda apenas em contexto Android (Kivy/p4a). No desktop, importar levanta ImportError
de jnius — tratar no caller com try/except.

Uso típico:
    bridge = ServiceBridge()
    bridge.bind_service()                       # main thread: registra ServiceConnection
    # ... no thread que vai chamar send_frame():
    bridge.setup_reply_in_current_thread()      # cria Handler/Messenger nesta thread
    detections = bridge.send_frame(frame_bytes, engine_idx=0)
    # ao final da thread:
    from jnius import detach; detach()
    bridge.unbind()

DetectionDTO fields (vindos do Kotlin):
    classId: int, label: str, confidence: float,
    x1, y1, x2, y2: float  (normalizados 0..1)
"""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass
class Detection:
    class_id: int
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float


class ServiceBridge:
    """Wrapper para Bound Service DetectionService via Messenger (IPC).

    T015.b.ipc Fix #4 — REMOVER em produção final:
    Todos os objetos Pyjnius (autoclass instances, PythonJavaClass) são criados e
    destruídos na mesma thread Python. Cross-thread sharing é proibido. Refs vivem
    em threading.local() — não como atributos do bridge.
    """

    MSG_INFER  = 1
    MSG_RESULT = 2
    SERVICE_CLASS = "com.maiconalves.animaldetector.DetectionService"

    def __init__(self) -> None:
        self._messenger = None  # populated via ServiceConnection.onServiceConnected (main thread)
        self._connection = None
        self._last_detections: list[Detection] = []
        # T015.b.ipc Fix #4 — REMOVER em produção final
        # storage por-thread pra Handler/Messenger/ResultHandler/Event
        self._tls = threading.local()

    # ── bind_service (main thread) ───────────────────────────────────────────

    def bind_service(self) -> None:
        """Registra ServiceConnection e chama bindService(). Roda na main thread.

        NÃO cria _reply_messenger aqui — isso é responsabilidade de
        setup_reply_in_current_thread(), que deve ser chamado na thread
        que vai usar send_frame().
        """
        from jnius import autoclass, PythonJavaClass, java_method  # type: ignore[import]

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent         = autoclass("android.content.Intent")
        Messenger      = autoclass("android.os.Messenger")

        bridge = self

        class _ServiceConn(PythonJavaClass):
            __javainterfaces__ = ["android/content/ServiceConnection"]

            @java_method("(Landroid/content/ComponentName;Landroid/os/IBinder;)V")
            def onServiceConnected(self, name, binder):
                bridge._messenger = Messenger(binder)

            @java_method("(Landroid/content/ComponentName;)V")
            def onServiceDisconnected(self, name):
                bridge._messenger = None

        # ServiceConnection é registrado na main thread, callbacks rodam na main thread
        # → criação e uso na mesma thread (regra Opção A)
        self._connection = _ServiceConn()
        ctx = PythonActivity.mActivity
        intent = Intent()
        intent.setClassName(ctx.getPackageName(), self.SERVICE_CLASS)
        ctx.bindService(intent, self._connection, 1)  # BIND_AUTO_CREATE = 1

    # ── setup_reply_in_current_thread (thread do caller) ─────────────────────

    def setup_reply_in_current_thread(self) -> None:
        """Cria Handler/Messenger de resposta NA THREAD CHAMADORA.

        T015.b.ipc Fix #4 — REMOVER em produção final:
        Todo o staff Pyjnius vive em threading.local(), garantindo que o
        DeleteLocalRef do __dealloc__ aconteça no mesmo JNIEnv onde o objeto
        foi criado.
        """
        from jnius import autoclass, PythonJavaClass, java_method  # type: ignore[import]

        Messenger = autoclass("android.os.Messenger")
        Handler   = autoclass("android.os.Handler")
        Looper    = autoclass("android.os.Looper")

        bridge = self

        class _ResultHandler(PythonJavaClass):
            __javainterfaces__ = ["android/os/Handler$Callback"]

            @java_method("(Landroid/os/Message;)Z")
            def handleMessage(self, msg):
                if msg.what == ServiceBridge.MSG_RESULT:
                    raw = msg.getData().getParcelableArray("detections")
                    bridge._last_detections = [
                        Detection(
                            class_id=d.classId, label=d.label,
                            confidence=d.confidence,
                            x1=d.x1, y1=d.y1, x2=d.x2, y2=d.y2,
                        )
                        for d in (raw or [])
                    ]
                bridge._tls.result_event.set()
                return True

        # Refs fortes em threading.local() pra impedir GC cross-thread
        self._tls.result_event = threading.Event()
        self._tls.result_handler = _ResultHandler()
        self._tls.handler = Handler(Looper.getMainLooper(), self._tls.result_handler)
        self._tls.reply_messenger = Messenger(self._tls.handler)

    # ── unbind ────────────────────────────────────────────────────────────────

    def unbind(self) -> None:
        """Desbinda do service e libera recursos."""
        if self._connection is None:
            return
        from jnius import autoclass  # type: ignore[import]
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        try:
            PythonActivity.mActivity.unbindService(self._connection)
        except Exception:
            pass
        self._messenger = None
        self._connection = None

    # ── send_frame ────────────────────────────────────────────────────────────

    def send_frame(
        self,
        frame_bytes: bytes,
        engine_idx: int = 0,
        width: int = 320,
        height: int = 320,
        timeout: float = 0.1,
    ) -> list[Detection]:
        """Envia frame ao service e aguarda resposta (síncrono, com timeout).

        Retorna lista de Detection. Retorna [] se service não está bound ou timeout.
        T015.b.ipc Fix #4 — REMOVER em produção final:
        Requer setup_reply_in_current_thread() chamado nesta thread antes.
        """
        if self._messenger is None:
            return []

        reply_messenger = getattr(self._tls, "reply_messenger", None)
        result_event = getattr(self._tls, "result_event", None)
        if reply_messenger is None or result_event is None:
            raise RuntimeError(
                "setup_reply_in_current_thread() não foi chamado nesta thread"
            )

        from jnius import autoclass  # type: ignore[import]
        Message = autoclass("android.os.Message")
        Bundle  = autoclass("android.os.Bundle")

        msg = Message.obtain(None, self.MSG_INFER)
        bundle = Bundle()
        bundle.putByteArray("frame", frame_bytes)
        bundle.putInt("engine_idx", engine_idx)
        bundle.putInt("width", width)
        bundle.putInt("height", height)
        msg.setData(bundle)
        msg.replyTo = reply_messenger

        result_event.clear()
        try:
            self._messenger.send(msg)
        except Exception:
            return []

        result_event.wait(timeout)
        return list(self._last_detections)
