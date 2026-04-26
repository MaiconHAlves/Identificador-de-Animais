import cv2
import numpy as np
import random
import time
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture

# Importações dos módulos core
from mobile.audio_manager import AudioManager
from mobile.ui_tactical import TacticalOverlay

class AdvancedMockDetector:
    def __init__(self):
        self.target_pos = None 
        self.timer = 0
        self.target_class = "ANIMAL"

    def detect(self, frame_w, frame_h):
        if self.target_pos is None and random.random() > 0.98:
            self.target_pos = [frame_w - 100, frame_h // 2 + 80, 20, 20]
            self.timer = 100 

        if self.target_pos:
            x, y, w, h = self.target_pos
            x -= 6
            y += 3
            w += 2
            h += 2
            self.target_pos = [x, y, w, h]
            self.timer -= 1
            
            if self.timer <= 0 or x < 0:
                self.target_pos = None
                return []
            
            risk = 0.98 if x < 400 else 0.70
            return [{"label_id": self.target_class, "confidence": risk, "box": self.target_pos}]
        return []

class RealisticApp(App):
    def build(self):
        self.layout = BoxLayout()
        self.img_display = Image()
        self.layout.add_widget(self.img_display)
        
        self.detector = AdvancedMockDetector()
        self.ui_tactical = TacticalOverlay()
        self.audio = AudioManager()
        
        self.cap = cv2.VideoCapture("scripts/isolated_road.mp4")
        self.last_detections = []
        
        Clock.schedule_interval(self.update_frame, 1.0/30.0)
        return self.layout

    def update_frame(self, dt):
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return

        frame = cv2.resize(frame, (640, 480))
        h, w = frame.shape[:2]
        
        # IA Simulada
        self.last_detections = self.detector.detect(w, h)
        risk = self.last_detections[0]['confidence'] if self.last_detections else 0.0
        self.audio.set_risk_level(risk)

        # 1. Visual Térmico PIP
        thermal_roi = cv2.applyColorMap(frame, cv2.COLORMAP_JET)
        for det in self.last_detections:
            x, y, bw, bh = [int(v) for v in det['box']]
            cv2.rectangle(thermal_roi, (x, y), (x+bw, y+bh), (255, 255, 255), -1)
        thermal_pip = cv2.resize(thermal_roi, (160, 120))

        # 2. HUD Tático
        display_frame = self.ui_tactical.process_frame(frame.copy(), self.last_detections)
        
        # 3. PIP e Status
        display_frame[20:140, 460:620] = thermal_pip
        cv2.rectangle(display_frame, (460, 20), (620, 140), (0, 255, 0), 1)
        
        status_color = (0, 0, 255) if risk > 0.8 else (0, 255, 0)
        status_text = "ALERTA: ANIMAL NA PISTA!" if risk > 0.8 else "SISTEMA ATIVO: ESCANEANDO"
        cv2.putText(display_frame, status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        # Atualizar Kivy
        buf = cv2.flip(display_frame, 0).tobytes()
        texture = Texture.create(size=(w, h), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.img_display.texture = texture

    def on_stop(self):
        self.cap.release()
        self.audio.stop()

if __name__ == "__main__":
    print("--- INICIANDO SIMULACAO REALISTA (RODOVIA ISOLADA) ---")
    RealisticApp().run()
