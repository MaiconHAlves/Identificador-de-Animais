import cv2
import numpy as np

class TacticalOverlay:
    def __init__(self):
        self.color_danger = (0, 0, 255)    # Vermelho
        self.color_warning = (0, 255, 255) # Amarelo
        self.color_safe = (0, 255, 0)      # Verde
        self.scan_line_y = 0

    def draw_tactical_box(self, frame, x, y, w, h, color, label):
        """Desenha uma bounding box estilizada com cantos reforçados e label com fundo."""
        thickness = 2
        corner_len = min(w, h) // 4
        
        # 1. Cantos Reforçados (Glow Effect Simulado com Linha Dupla)
        # Top-Left
        cv2.line(frame, (x, y), (x + corner_len, y), color, thickness + 1)
        cv2.line(frame, (x, y), (x, y + corner_len), color, thickness + 1)
        
        # Top-Right
        cv2.line(frame, (x + w, y), (x + w - corner_len, y), color, thickness + 1)
        cv2.line(frame, (x + w, y), (x + w, y + corner_len), color, thickness + 1)
        
        # Bottom-Left
        cv2.line(frame, (x, y + h), (x + corner_len, y + h), color, thickness + 1)
        cv2.line(frame, (x, y + h), (x, y + h - corner_len), color, thickness + 1)
        
        # Bottom-Right
        cv2.line(frame, (x + w, y + h), (x + w - corner_len, y + h), color, thickness + 1)
        cv2.line(frame, (x + w, y + h), (x + w, y + h - corner_len), color, thickness + 1)

        # 2. Label com Fundo Semi-transparente
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = 0.5
        (text_w, text_h), _ = cv2.getTextSize(label, font, font_scale, 1)
        
        cv2.rectangle(frame, (x, y - text_h - 10), (x + text_w + 10, y), color, -1)
        cv2.putText(frame, label, (x + 5, y - 5), font, font_scale, (255, 255, 255), 1)

    def draw_hud_elements(self, frame):
        """Adiciona elementos de scanner e moldura tática."""
        h, w = frame.shape[:2]
        color = (0, 255, 0) # HUD Verde
        
        # Moldura nos cantos da tela
        m = 40 # margem
        l = 60 # comprimento da linha
        
        # Top-Left
        cv2.line(frame, (m, m), (m + l, m), color, 1)
        cv2.line(frame, (m, m), (m, m + l), color, 1)
        
        # Bottom-Right
        cv2.line(frame, (w - m, h - m), (w - m - l, h - m), color, 1)
        cv2.line(frame, (w - m, h - m), (w - m, h - m - l), color, 1)

        # Scanning Line (Efeito visual)
        self.scan_line_y = (self.scan_line_y + 10) % h
        cv2.line(frame, (0, self.scan_line_y), (w, self.scan_line_y), color, 1)
        
        # Texto de Status
        cv2.putText(frame, "AI SYSTEM: ACTIVE", (w - 180, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
        cv2.putText(frame, "FUSION MODE: THERMAL+RGB", (w - 240, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    def process_frame(self, frame, detections):
        """Pipeline principal de desenho"""
        self.draw_hud_elements(frame)
        
        for det in detections:
            x, y, w, h = det['box']
            conf = det['confidence']
            label = f"ANIMAL {conf:.0%}"
            
            # Escolha de cor por risco
            color = self.color_danger if conf > 0.7 else self.color_warning
            
            self.draw_tactical_box(frame, x, y, w, h, color, label)
            
        return frame

if __name__ == "__main__":
    print("Módulo UI Tática carregado.")
