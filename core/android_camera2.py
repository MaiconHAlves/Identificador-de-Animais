"""
Camera2 via CameraHelper.java + pyjnius.

CameraDevice.StateCallback e CameraCaptureSession.StateCallback são classes ABSTRATAS —
pyjnius só implementa interfaces Java. CameraHelper.java encapsula as abstratas e expõe
FrameCallback (interface), que Python implementa normalmente via PythonJavaClass.
"""
import threading
import numpy as np

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False


def _safe_extract(buf, expected_size: int, label: str = "") -> "np.ndarray":
    """
    Converte buffer (jnius ByteArray) em np.uint8 array de EXATAMENTE expected_size bytes.
    - Pad com zeros se buffer veio curto (off-by-one no Camera2 do Samsung S24).
    - Trunca se veio longo.
    Loga 1x por label pra rastreabilidade. Sem o pad, reshape lança exception
    silenciosa em pyjnius callback → tela branca.
    """
    raw = np.frombuffer(bytes(buf), dtype=np.uint8)
    actual = len(raw)
    if actual == expected_size:
        return raw
    if not hasattr(_safe_extract, "_warned"):
        _safe_extract._warned = set()
    key = f"{label}:{actual}->{expected_size}"
    if key not in _safe_extract._warned:
        delta = expected_size - actual
        sign = "+" if delta > 0 else ""
        print(f"[CV-PAD] Buffer {label}: {actual} bytes recebido, {expected_size} esperado (delta={sign}{delta})")
        _safe_extract._warned.add(key)
    if actual < expected_size:
        out = np.zeros(expected_size, dtype=np.uint8)
        out[:actual] = raw
        return out
    return raw[:expected_size]


def _yuv_to_bgr(y_buf, u_buf, v_buf, w: int, h: int, 
                y_ps: int, y_rs: int, u_ps: int, u_rs: int, v_ps: int, v_rs: int) -> np.ndarray | None:
    """
    Converte YUV_420_888 para BGR usando strides reais para evitar corrupção de imagem.
    """
    if not _HAS_CV2:
        return None
    import time
    if not hasattr(_yuv_to_bgr, "_frame_count"):
        _yuv_to_bgr._frame_count = 0
        _yuv_to_bgr._last_log = time.perf_counter()

    _yuv_to_bgr._frame_count += 1
    if _yuv_to_bgr._frame_count == 1:
        print(f"[DEBUG] _yuv_to_bgr: Primeiro frame recebido! y={len(y_buf)} u={len(u_buf)} v={len(v_buf)}")
    start_t = time.perf_counter()
    
    try:
        # 1. Calcular tamanhos esperados ANTES de converter
        y_size_needed  = h * y_rs
        uv_size_needed = (h // 2) * v_rs   # válido p/ NV21 (intercalado) e I420

        # 2. Converter ByteArray do jnius com pad/trunc seguro.
        # Samsung S24 tem off-by-one no buffer Y do Camera2 (153599 vs 153600 esperado).
        # Sem pad, np.reshape lança exception silenciosa em callback pyjnius → tela branca.
        y_raw = _safe_extract(y_buf, y_size_needed,  "Y")
        u_raw = _safe_extract(u_buf, uv_size_needed, "U")
        v_raw = _safe_extract(v_buf, uv_size_needed, "V")

        # 3. Extração segura do Plano Y (Luminância)
        y_plane = y_raw[:y_size_needed].reshape(h, y_rs)[:, :w]

        # 4. Reconstrução Cromática
        if u_ps == 2:
            # NV21/NV12 (Intercalado)
            yuv_full = np.empty((h + h // 2, w), dtype=np.uint8)
            yuv_full[:h, :] = y_plane

            # UV plane: h//2 linhas, cada uma com v_rs bytes
            uv_size_needed = (h // 2) * v_rs
            uv_data = v_raw[:uv_size_needed].reshape(h // 2, v_rs)[:, :w]
            yuv_full[h:, :] = uv_data

            res = cv2.cvtColor(yuv_full, cv2.COLOR_YUV2BGR_NV21)
        else:
            # I420 (Plana)
            u_plane = u_raw[:(h//2)*u_rs].reshape(h//2, u_rs)[:, :w//2]
            v_plane = v_raw[:(h//2)*v_rs].reshape(h//2, v_rs)[:, :w//2]

            y_flat = y_plane.flatten()
            u_flat = u_plane.flatten()
            v_flat = v_plane.flatten()
            yuv_flat = np.concatenate([y_flat, u_flat, v_flat])
            yuv_img = yuv_flat.reshape((h + h // 2, w))

            res = cv2.cvtColor(yuv_img, cv2.COLOR_YUV2BGR_I420)

        # Heartbeat log a cada 30 frames
        if _yuv_to_bgr._frame_count % 30 == 0:
            now = time.perf_counter()
            dt = now - _yuv_to_bgr._last_log
            fps = 30 / dt if dt > 0 else 0
            print(f"[CV-PULSE] FPS: {fps:.1f} | Conv: {(now-start_t)*1000:.1f}ms")
            _yuv_to_bgr._last_log = now

        return res
            
    except Exception as e:
        if _yuv_to_bgr._frame_count % 30 == 0:
            print(f"[CV-ERROR] Falha na conversão: {e}")
        return None


class Camera2Capture:
    """
    Captura de câmera para Android 14+ usando CameraHelper.java via pyjnius.
    """

    def __init__(self, camera_id: int = 0, width: int = 640, height: int = 480):
        self._id     = str(camera_id)
        self._width  = width
        self._height = height
        self._frame  = None
        self._lock   = threading.Lock()
        self._running = False
        self._helper  = None
        self._cb      = None
        self._error   = None   # mensagem de erro se start() falhar

    def start(self) -> bool:
        try:
            from jnius import autoclass, PythonJavaClass, java_method
        except ImportError:
            return False

        try:
            CameraHelper   = autoclass('org.kivy.android.CameraHelper')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            ContextClass   = autoclass('android.content.Context')
        except Exception:
            return False

        # Tentar ID 0 primeiro se for emulador
        try:
            activity = PythonActivity.mActivity
            ctx_enum = activity.getApplicationContext()
            cam_mgr  = ctx_enum.getSystemService(ContextClass.CAMERA_SERVICE)
            java_ids = cam_mgr.getCameraIdList()
            id_list  = [str(java_ids[i]) for i in range(len(java_ids))]
            print(f"android_camera2: cameras detectadas: {id_list}")
            
            # Prioridade: se ID 0 existe, usamos ele para webcam física
            if "0" in id_list:
                cam2_id = "0"
            else:
                cam2_id = id_list[0] if id_list else "0"
        except Exception:
            cam2_id = self._id

        error_msg = [None]
        opened_event = threading.Event()
        self_ref = self 

        class FrameCB(PythonJavaClass):
            __javainterfaces__ = ['org/kivy/android/CameraHelper$FrameCallback']
            __javacontext__    = 'app'

            @java_method('([B[B[BIIIIIIII)V')
            def onFrame(self, y, u, v, w, h, y_ps, y_rs, u_ps, u_rs, v_ps, v_rs):
                if not hasattr(self, "_frames"): self._frames = 0
                self._frames += 1
                if self._frames % 30 == 0:
                    print(f"[DEBUG] android_camera2: onFrame hit count={self._frames}")
                frame = _yuv_to_bgr(y, u, v, w, h, y_ps, y_rs, u_ps, u_rs, v_ps, v_rs)
                if frame is not None:
                    with self_ref._lock:
                        self_ref._frame = frame

            @java_method('(Ljava/lang/String;)V')
            def onError(self, msg):
                print(f"android_camera2: erro recebido do Java: {msg}")
                error_msg[0] = msg
                opened_event.set()

            @java_method('()V')
            def onOpened(self):
                opened_event.set()

        try:
            activity = PythonActivity.mActivity
            ctx = activity.getApplicationContext()
            helper = CameraHelper()
            cb = FrameCB()
            helper.open(ctx, cam2_id, self._width, self._height, cb)

            if not opened_event.wait(timeout=4.0):
                self._error = f"timeout ao abrir câmera {cam2_id}"
                print(f"android_camera2: {self._error}")
                return False

            if error_msg[0]:
                self._error = error_msg[0]
                print(f"android_camera2: falha na inicialização: {self._error}")
                return False

            self._helper  = helper
            self._running = True
            self._cb = cb
            return True

        except Exception as e:
            self._error = str(e)
            print(f"android_camera2: exceção ao abrir câmera: {e}")
            return False

    def get_frame(self) -> np.ndarray | None:
        with self._lock:
            return self._frame

    def has_error(self) -> bool:
        return self._error is not None

    def is_opened(self) -> bool:
        return self._running and self._helper is not None

    def stop(self):
        self._running = False
        if self._helper:
            try:
                self._helper.close()
            except Exception as e:
                print(f"android_camera2: erro ao fechar câmera: {e}")
            self._helper = None
