import cv2
import threading
import numpy as np
import os
import sys
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty, BooleanProperty

# Garantir que a raiz do projeto esteja no path para as importações do core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importações do Core e Mobile
from core.sensor_manager import SensorManager
from core.detection_engine import DetectionEngine
from core.fusion_engine import FusionEngine
from mobile.audio_manager import AudioManager
from mobile.ui_tactical import TacticalOverlay


class AnimalDetectorApp(App):
    current_risk = NumericProperty(0.0)
    target_count = NumericProperty(0)
    menu_active = BooleanProperty(False)
    conf_threshold = NumericProperty(0.85)

    def on_conf_threshold(self, instance, value):
        """Atualiza a sensibilidade do motor de detecção em tempo real."""
        if hasattr(self, 'engine'):
            self.engine.threshold = value

    def build(self):
        # Carregar o Design Tático
        self.root = Builder.load_file('mobile/style.kv')

        # Inicialização dos Motores
        self.detector = DetectionEngine(model_paths=[
            "models/global_animal_detector.onnx",
            "models/hybrid_animal_detector.onnx"
        ])
        self.fusion = FusionEngine()
        self.audio = AudioManager()
        self.ui_tactical = TacticalOverlay()

        self.is_thermal_active = False
        self.is_recording = False
        self.running = True
        self.last_detections = []
        self.current_risk = 0.0

        # Gerenciamento de Sensores (Câmera será iniciada apenas via callback de permissão)
        self.rgb_manager = SensorManager(sensor_id=0)
        self.thermal_manager = SensorManager(sensor_id=1)

        # Thread de IA com controle de pausa (aguarda frame válido)
        self.ia_thread = threading.Thread(target=self.ia_processing_loop, daemon=True)
        self.ia_thread.start()

        # Iniciar Update da UI a 30 FPS (Fix Erro Térmico S24)
        Clock.schedule_interval(self.update_ui, 1.0 / 30.0)

        return self.root

    def on_start(self):
        from kivy.utils import platform
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            # Android 14+ exige permissões específicas para mídia
            permissions = [Permission.CAMERA, Permission.RECORD_AUDIO]
            request_permissions(permissions, self._on_permissions_result)
        else:
            self._start_camera()

    def _on_permissions_result(self, permissions, results):
        if results and all(results):
            # Usar Clock para agendar o início e dar fôlego ao sistema
            Clock.schedule_once(lambda dt: self._start_camera(), 0.5)
        else:
            print("Permissões negadas — câmera não iniciada")

    def _start_camera(self):
        self.rgb_manager.start()

    def toggle_thermal(self):
        self.is_thermal_active = not self.is_thermal_active
        self.ui_tactical.thermal_mode = self.is_thermal_active
        print(f"Modo Térmico: {self.is_thermal_active}")

    def capture_photo(self):
        print("CAPTURANDO FOTO...")
        # Lógica de salvar frame será implementada
    
    def toggle_recording(self):
        self.is_recording = not self.is_recording
        self.root.ids.rec_btn.text = "STOP" if self.is_recording else "REC"
        print(f"Gravação: {self.is_recording}")

    def ia_processing_loop(self):
        """Loop de processamento pesado (IA + Cálculo de Risco)"""
        while self.running:
            _, frame = self.rgb_manager.get_latest_frame()
            if frame is not None:
                # Detecção
                self.last_detections = self.detector.detect(frame)
                
                # Cálculo de Risco Progressivo
                if self.last_detections:
                    max_conf = max([d['confidence'] for d in self.last_detections])
                    self.current_risk = max_conf
                    self.target_count = len(self.last_detections)
                else:
                    self.current_risk = 0.0
                    self.target_count = 0
                
                # Atualizar Áudio
                self.audio.set_risk_level(self.current_risk)
                
            threading.Event().wait(0.01) # Sleep leve de 10ms

    def update_ui(self, dt):
        """Thread da UI: Renderização e Fusão"""
        _, frame_rgb = self.rgb_manager.get_latest_frame()
        _, frame_thermal = self.thermal_manager.get_latest_frame()
        
        if frame_rgb is not None:
            display_frame = frame_rgb.copy()
            
            # 1. Aplicar Fusão se houver sinal térmico
            if self.is_thermal_active and frame_thermal is not None:
                display_frame = self.fusion.apply_overlay(display_frame, frame_thermal)
            
            # 2. Aplicar HUD e Bounding Boxes Táticas
            display_frame = self.ui_tactical.process_frame(display_frame, self.last_detections)
            
            # 3. Atualizar Widget do Kivy
            buf = cv2.flip(display_frame, 0).tobytes()
            texture = Texture.create(size=(display_frame.shape[1], display_frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.root.ids.main_feed.texture = texture
            
            # 4. Atualizar Labels dinâmicos
            self.root.ids.status_footer.text = f"SCANNING REGION: ALPHA-01 | TARGETS: {self.target_count}"

    def on_stop(self):
        """Finalização Segura"""
        self.running = False
        self.rgb_manager.stop()
        self.thermal_manager.stop()
        self.audio.stop()
        print("Sistema encerrado com segurança.")

if __name__ == "__main__":
    AnimalDetectorApp().run()
