import cv2
import threading
import time
from collections import deque


def _tick_fps(buf: deque, now: float, window: float = 2.0) -> float:
    """Adiciona timestamp e retorna FPS médio na janela dada."""
    buf.append(now)
    while buf and now - buf[0] > window:
        buf.popleft()
    return len(buf) / window


def _is_android() -> bool:
    try:
        from kivy.utils import platform
        return platform == 'android'
    except Exception:
        return False


class SensorManager:
    """
    Gerencia captura assíncrona de câmera.
    Android 14+: usa Camera2 API via pyjnius (OpenCV VideoCapture falha no thread SDL).
    Desktop: usa OpenCV VideoCapture diretamente.
    """
    def __init__(self, sensor_id=0, buffer_size=5, width=640, height=480):
        self.sensor_id = sensor_id
        self.buffer_size = buffer_size
        self.width = width
        self.height = height
        self.buffer = deque(maxlen=buffer_size)
        self.running = False
        self.lock = threading.Lock()
        self._cam2 = None   # Camera2Capture (Android)
        self.cap   = None   # cv2.VideoCapture (desktop)
        self.cam_fps = 0.0

    def start(self) -> bool:
        if _is_android():
            return self._start_android()
        return self._start_desktop()

    def _start_android(self) -> bool:
        from core.android_camera2 import Camera2Capture
        time.sleep(1.5)  # aguarda Camera HAL estabilizar após permission grant
        self._cam2 = Camera2Capture(self.sensor_id, width=self.width, height=self.height)
        if self._cam2.start():
            self.running = True
            self.thread = threading.Thread(target=self._update_android, daemon=True)
            self.thread.start()
            return True
        # Fallback: emulador ou dispositivo sem CameraHelper — tenta OpenCV
        print(f"Camera2 falhou no sensor {self.sensor_id} — tentando OpenCV VideoCapture")
        return self._start_desktop()

    def _start_desktop(self) -> bool:
        self.cap = cv2.VideoCapture(self.sensor_id)
        if not self.cap.isOpened():
            print(f"Erro: Não foi possível abrir o sensor {self.sensor_id}")
            return False
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.running = True
        self.thread = threading.Thread(target=self._update_desktop, daemon=True)
        self.thread.start()
        return True

    def _update_android(self):
        fps_buf = deque()
        last_frame = None
        while self.running:
            frame = self._cam2.get_frame()
            if frame is not None and frame is not last_frame:
                last_frame = frame
                ts = time.monotonic_ns()
                with self.lock:
                    self.buffer.append((ts, frame))
                self.cam_fps = _tick_fps(fps_buf, time.monotonic())
            time.sleep(0.033)

    def _update_desktop(self):
        fps_buf = deque()
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                ts = time.monotonic_ns()
                with self.lock:
                    self.buffer.append((ts, frame))
                self.cam_fps = _tick_fps(fps_buf, time.monotonic())
            else:
                time.sleep(0.01)

    def get_latest_frame(self):
        with self.lock:
            if self.buffer:
                return self.buffer[-1]
            return None, None

    def stop(self):
        self.running = False
        if self._cam2:
            self._cam2.stop()
        if self.cap:
            self.cap.release()
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2)

    @staticmethod
    def list_cameras(max_index: int = 5) -> list[int]:
        if _is_android():
            # Samsung S24: 0=traseira principal, 1=frontal
            return [0, 1]
        valid = []
        for idx in range(max_index):
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                valid.append(idx)
            cap.release()
        return valid

if __name__ == "__main__":
    # Teste simples do manager
    manager = SensorManager(0)
    if manager.start():
        time.sleep(2)
        ts, frame = manager.get_latest_frame()
        print(f"Frame capturado em {ts} com formato {frame.shape if frame is not None else 'None'}")
        manager.stop()
