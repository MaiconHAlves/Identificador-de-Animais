import threading
import time
from kivy.core.audio import SoundLoader

import threading
import time
import numpy as np
from kivy.core.audio import SoundLoader

class AudioManager:
    def __init__(self, sound_path="assets/beep.wav"):
        # Sons pré-carregados para diferentes níveis (se existirem)
        self.sound_low = SoundLoader.load(sound_path)
        self.risk_level = 0.0 
        self.running = True
        self.lock = threading.Lock()
        
        # Parâmetros de Áudio Tático
        self.base_interval = 1.2 # Segundos (Risco Zero)
        self.min_interval = 0.08  # Segundos (Risco Máximo - "Beep Contínuo")
        
        # Thread dedicada para o Sonar
        self.audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self.audio_thread.start()

    def set_risk_level(self, level):
        """Ajusta o nível de risco (0.0 a 1.0)"""
        with self.lock:
            self.risk_level = max(0.0, min(1.0, level))

    def _audio_loop(self):
        """Gerencia a cadência do sonar baseada no nível de perigo"""
        while self.running:
            with self.lock:
                risk = self.risk_level
            
            if risk > 0.1:
                # Toca o bip
                if self.sound_low:
                    # Ajusta o volume proporcionalmente ao risco (mais alto se mais perto)
                    self.sound_low.volume = 0.3 + (risk * 0.7)
                    self.sound_low.play()
                
                # Cálculo de Cadência Exponencial (estilo sensor de ré/sonar)
                # O intervalo diminui drasticamente conforme o risco aumenta
                interval = self.base_interval * (1.0 - risk)**2
                interval = max(self.min_interval, interval)
                
                time.sleep(interval)
            else:
                # Standby: Pulso lento de 'Sistema Operacional'
                time.sleep(1.0)

    def trigger_alert(self, alert_type="detected"):
        """Gatilho para alertas verbais ou sons específicos"""
        # Futura expansão: "ONÇA DETECTADA" (TTS)
        pass

    def stop(self):
        self.running = False
        print("AudioManager: Sistema de áudio desativado.")

    def stop(self):
        self.running = False
        if self.audio_thread.is_alive():
            self.audio_thread.join()

if __name__ == "__main__":
    print("Módulo de Áudio iniciado. Aguardando níveis de risco...")
