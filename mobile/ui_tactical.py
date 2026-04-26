import cv2
import numpy as np

class TacticalOverlay:
    def __init__(self):
        self.color_neon_cyan = (255, 230, 0) # Ciano/Azul Neon (BGR)
        self.color_danger = (0, 0, 255)      # Vermelho
        self.color_safe = (0, 255, 65)       # Verde Tático
        self.thermal_mode = False
        self.scan_line_y = 0
        # Mapeamento de Classes (Baseado no Treinamento Híbrido)
        self.class_names = {
            0: "ANIMAL",
            1: "CACHORRO",
            2: "GATO",
            3: "VACA/BOI",
            4: "CAVALO",
            5: "CAPIVARA",
            6: "ONCA_PARDA",
            7: "LOBO_GUARA",
            8: "OUTRO_ANIMAL"
        }

    def apply_thermal_filter(self, frame):
        """Simulação de Visão Térmica Dinâmica (Overlay de 30%)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        thermal = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
        
        # 4. Ajuste de saturação para parecer menos 'desenho' e mais 'sensor'
        hsv = cv2.cvtColor(thermal, cv2.COLOR_BGR2HSV)
        hsv[:,:,1] = hsv[:,:,1] * 0.8 # Reduz saturação
        thermal = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        return thermal

    def draw_tactical_box(self, frame, x, y, w, h, color, label):
        """Bounding box 'Premium Target Lock' com linhas finas e cantos agressivos."""
        
        # Cor dinâmica para modo térmico
        base_color = (255, 255, 255) if self.thermal_mode else color
        
        t = 1 # Espessura ultra-fina para visual premium
        l = int(min(w, h) * 0.15) # Comprimento do canto (15%)
        gap = 2 # Pequeno espaço entre o objeto e a mira

        # Desenhar cantos com anti-aliasing manual (usando polylines)
        # Top-Left
        cv2.line(frame, (x-gap, y-gap), (x-gap+l, y-gap), base_color, t, cv2.LINE_AA)
        cv2.line(frame, (x-gap, y-gap), (x-gap, y-gap+l), base_color, t, cv2.LINE_AA)
        # Top-Right
        cv2.line(frame, (x+w+gap, y-gap), (x+w+gap-l, y-gap), base_color, t, cv2.LINE_AA)
        cv2.line(frame, (x+w+gap, y-gap), (x+w+gap, y-gap+l), base_color, t, cv2.LINE_AA)
        # Bottom-Left
        cv2.line(frame, (x-gap, y+h+gap), (x-gap+l, y+h+gap), base_color, t, cv2.LINE_AA)
        cv2.line(frame, (x-gap, y+h+gap), (x-gap, y+h+gap-l), base_color, t, cv2.LINE_AA)
        # Bottom-Right
        cv2.line(frame, (x+w+gap, y+h+gap), (x+w+gap-l, y+h+gap), base_color, t, cv2.LINE_AA)
        cv2.line(frame, (x+w+gap, y+h+gap), (x+w+gap, y+h+gap-l), base_color, t, cv2.LINE_AA)

        # Texto Tático
        font = cv2.FONT_HERSHEY_SIMPLEX
        fs = 0.35 # Font scale menor
        # Sombra/Outline preto para legibilidade
        cv2.putText(frame, label, (x, y - 8), font, fs, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, label, (x, y - 8), font, fs, base_color, 1, cv2.LINE_AA)

    def draw_hud_elements(self, frame):
        """Elementos de HUD minimalistas."""
        h, w = frame.shape[:2]
        color = (255, 255, 255) if self.thermal_mode else (65, 255, 0)
        
        # Center Crosshair sutil - Removido (Mantendo apenas a estrutura da função se necessário)
        pass

    def process_frame(self, frame, detections):
        # 1. Aplicar Filtro Térmico se ativo (Overlay Suave)
        if self.thermal_mode:
            frame = self.apply_thermal_filter(frame)

        # 2. Mapeamento de Classes (Híbrido)
        # IDs Globais COCO -> IDs Táticas HUD
        global_map = {
            16: 4, # Dog -> CACHORRO
            15: 5, # Cat -> GATO
            19: 6, # Cow -> BOI
            17: 7, # CAVALO
            0: 8   # Person/Vehicle (Simplificado)
        }

        # 3. Desenhar HUD e Bounding Boxes
        self.draw_hud_elements(frame)
        
        for det in detections:
            label_id = det["label_id"]
            
            # Se a fonte for o motor global, traduzir a ID
            if det.get("source") == "global":
                label_id = global_map.get(label_id, 8) # 8 como padrão (Outros)

            conf = det['confidence']
            x, y, w, h = det['box']
            
            # Busca o nome da classe ou usa um genérico
            class_name = self.class_names.get(label_id, "OBJECT")
            label = f"{class_name}: {conf:.1%}"
            
            color = self.color_danger if conf > 0.7 else self.color_safe
            self.draw_tactical_box(frame, x, y, w, h, color, label)
            
        return frame

if __name__ == "__main__":
    print("Módulo UI Tática Premium carregado.")
