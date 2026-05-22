import threading
import time
from kivy.core.audio import SoundLoader

class AudioManager:
    def __init__(self, sound_path="assets/beep.wav"):
        self.sound_low = SoundLoader.load(sound_path)
        if self.sound_low is None:
            print(f"AudioManager: arquivo de som não encontrado: {sound_path}")
        self.risk_level = 0.0
        self.running = True
        self.lock = threading.Lock()
        self._playing = False

        self.base_interval = 1.2
        self.min_interval = 0.08

        self.audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self.audio_thread.start()

    def set_risk_level(self, level):
        with self.lock:
            self.risk_level = max(0.0, min(1.0, level))

    def _audio_loop(self):
        while self.running:
            with self.lock:
                risk = self.risk_level

            if risk > 0.3 and self.sound_low:
                # Guard: não enfileira novo play se o anterior ainda toca
                if not self._playing or self.sound_low.state != 'play':
                    self._playing = True
                    self.sound_low.volume = 0.3 + (risk * 0.7)
                    self.sound_low.play()

                interval = self.base_interval * (1.0 - risk) ** 2
                time.sleep(max(self.min_interval, interval))
            else:
                self._playing = False
                time.sleep(1.0)

    def trigger_alert(self, alert_type="detected"):
        pass

    def stop(self):
        self.running = False
        if self.audio_thread.is_alive():
            self.audio_thread.join()
        print("AudioManager: Sistema de áudio desativado.")

if __name__ == "__main__":
    print("Módulo de Áudio iniciado. Aguardando níveis de risco...")
