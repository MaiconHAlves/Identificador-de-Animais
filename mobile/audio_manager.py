import threading
import time
from kivy.core.audio import SoundLoader

class AudioManager:
    def __init__(self, sound_path="assets/beep.wav"):
        self.sound = SoundLoader.load(sound_path)
        self.risk_level = 0.0 # 0.0 (sem risco) a 1.0 (colisão iminente)
        self.running = True
        self.lock = threading.Lock()
        
        # Thread dedicada para o "pulso" do bip
        self.audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self.audio_thread.start()

    def set_risk_level(self, level):
        """Define o nível de risco e ajusta a cadência automaticamente"""
        with self.lock:
            self.risk_level = max(0.0, min(1.0, level))

    def _audio_loop(self):
        """Loop que controla o intervalo entre os bips baseado no risco"""
        while self.running:
            with self.lock:
                current_risk = self.risk_level
            
            if current_risk > 0.1: # Limiar para começar a apitar
                # Tocar som
                if self.sound:
                    self.sound.play()
                
                # Calcular intervalo: 
                # Risco 0.1 -> 1.0 segundo de intervalo
                # Risco 1.0 -> 0.1 segundo de intervalo (metralhadora)
                interval = max(0.1, 1.0 - current_risk)
                time.sleep(interval)
            else:
                # Sem risco: dorme um pouco para economizar CPU
                time.sleep(0.5)

    def stop(self):
        self.running = False
        if self.audio_thread.is_alive():
            self.audio_thread.join()

if __name__ == "__main__":
    print("Módulo de Áudio iniciado. Aguardando níveis de risco...")
