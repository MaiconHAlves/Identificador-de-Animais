import cv2
import threading
import numpy as np
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture

# Importações do Core e Mobile
from core.sensor_manager import SensorManager
from core.detection_engine import DetectionEngine
from core.fusion_engine import FusionEngine
from mobile.audio_manager import AudioManager
from mobile.ui_tactical import TacticalOverlay

class AnimalDetectorApp(App):
    def build(self):
        # 1. Configuração da UI
        self.layout = BoxLayout(orientation='vertical')
        self.img_display = Image()
        self.layout.add_widget(self.img_display)
        
        # 2. Inicialização dos Motores
        self.detector = DetectionEngine(model_path="yolov8n.onnx")
        self.fusion = FusionEngine()
        self.audio = AudioManager()
        self.ui_tactical = TacticalOverlay()
        
        # 3. Gerenciamento de Sensores
        self.rgb_manager = SensorManager(sensor_id=0) # Câmera Principal
        self.thermal_manager = SensorManager(sensor_id=1) # Câmera Secundária / Térmica
        
        self.rgb_manager.start()
        # self.thermal_manager.start() # Ativar quando o hardware estiver presente
        
        # 4. Estado do Sistema
        self.running = True
        self.last_detections = []
        self.current_risk = 0.0
        
        # 5. Agendamento da UI (30 FPS)
        Clock.schedule_interval(self.update_ui, 1.0 / 30.0)
        
        # 6. Iniciar Thread de Inteligência (IA e Áudio)
        self.ia_thread = threading.Thread(target=self.ia_processing_loop, daemon=True)
        self.ia_thread.start()
        
        return self.layout

    def ia_processing_loop(self):
        """Loop de processamento pesado (IA + Cálculo de Risco)"""
        while self.running:
            _, frame = self.rgb_manager.get_latest_frame()
            if frame is not None:
                # Detecção
                self.last_detections = self.detector.detect(frame)
                
                # Cálculo de Risco Progressivo
                if self.last_detections:
                    # Risco baseado na confiança e tamanho da box (proximidade simulada)
                    max_conf = max([d['confidence'] for d in self.last_detections])
                    self.current_risk = max_conf
                else:
                    self.current_risk = 0.0
                
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
            if frame_thermal is not None:
                display_frame = self.fusion.apply_overlay(display_frame, frame_thermal)
            
            # 2. Aplicar HUD e Bounding Boxes Táticas
            display_frame = self.ui_tactical.process_frame(display_frame, self.last_detections)
            
            # 3. Atualizar Widget do Kivy
            buf = cv2.flip(display_frame, 0).tobytes()
            texture = Texture.create(size=(display_frame.shape[1], display_frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.img_display.texture = texture

    def on_stop(self):
        """Finalização Segura"""
        self.running = False
        self.rgb_manager.stop()
        self.thermal_manager.stop()
        self.audio.stop()
        print("Sistema encerrado com segurança.")

if __name__ == "__main__":
    AnimalDetectorApp().run()
