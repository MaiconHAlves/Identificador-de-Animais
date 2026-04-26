import cv2
import threading
import time
from collections import deque

class SensorManager:
    """
    Gerencia a captura assíncrona de frames de múltiplos sensores (RGB e Térmico).
    Utiliza Ring Buffers para garantir que a IA sempre processe os quadros mais recentes.
    """
    def __init__(self, sensor_id=0, buffer_size=5):
        self.sensor_id = sensor_id
        self.buffer_size = buffer_size
        self.buffer = deque(maxlen=buffer_size)
        self.running = False
        self.cap = None
        self.lock = threading.Lock()

    def start(self):
        self.cap = cv2.VideoCapture(self.sensor_id)
        if not self.cap.isOpened():
            print(f"Erro: Não foi possível abrir o sensor {self.sensor_id}")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()
        return True

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                timestamp = time.monotonic_ns()
                with self.lock:
                    self.buffer.append((timestamp, frame))
            else:
                time.sleep(0.01)

    def get_latest_frame(self):
        with self.lock:
            if self.buffer:
                return self.buffer[-1]
            return None, None

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        if self.thread:
            self.thread.join()

if __name__ == "__main__":
    # Teste simples do manager
    manager = SensorManager(0)
    if manager.start():
        time.sleep(2)
        ts, frame = manager.get_latest_frame()
        print(f"Frame capturado em {ts} com formato {frame.shape if frame is not None else 'None'}")
        manager.stop()
