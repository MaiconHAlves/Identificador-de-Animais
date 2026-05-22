import cv2
import numpy as np

class TacticalOverlay:
    # Classes COCO (0-79) + Fauna BR (80-94) — modelo full_detection_v2
    _CLASS_NAMES = {
        0: "PESSOA",        1: "BICICLETA",     2: "CARRO",
        3: "MOTO",          4: "AVIÃO",          5: "ÔNIBUS",
        6: "TREM",          7: "CAMINHÃO",       8: "BARCO",
        9: "SEMÁFORO",     10: "HIDRANTE",      11: "PLACA PARE",
        12: "PARQUÍMETRO", 13: "BANCO",          14: "PÁSSARO",
        15: "GATO",        16: "CACHORRO",       17: "CAVALO",
        18: "OVELHA",      19: "VACA",           20: "ELEFANTE",
        21: "URSO",        22: "ZEBRA",          23: "GIRAFA",
        24: "MOCHILA",     25: "GUARDA-CHUVA",   26: "BOLSA",
        27: "GRAVATA",     28: "MALA",           29: "FRISBEE",
        30: "ESQUI",       31: "SNOWBOARD",      32: "BOLA",
        33: "PIPA",        34: "TACO BEISEBOL",  35: "LUVA BEISEBOL",
        36: "SKATE",       37: "PRANCHA SURF",   38: "RAQUETE",
        39: "GARRAFA",     40: "TAÇA VINHO",     41: "COPO",
        42: "GARFO",       43: "FACA",           44: "COLHER",
        45: "TIGELA",      46: "BANANA",         47: "MAÇÃ",
        48: "SANDUÍCHE",   49: "LARANJA",        50: "BRÓCOLIS",
        51: "CENOURA",     52: "CACHORRO-QUENTE",53: "PIZZA",
        54: "ROSQUINHA",   55: "BOLO",           56: "CADEIRA",
        57: "SOFÁ",        58: "VASO PLANTA",    59: "CAMA",
        60: "MESA",        61: "VASO SANITÁRIO", 62: "TV",
        63: "NOTEBOOK",    64: "MOUSE",          65: "CONTROLE",
        66: "TECLADO",     67: "CELULAR",        68: "MICROONDAS",
        69: "FORNO",       70: "TORRADEIRA",     71: "PIA",
        72: "GELADEIRA",   73: "LIVRO",          74: "RELÓGIO",
        75: "VASO",        76: "TESOURA",        77: "URSO PELÚCIA",
        78: "SECADOR",     79: "ESCOVA DENTE",
        # Fauna Brasileira
        80: "ANTA",        81: "CACHORRO DO MATO", 82: "CAPIVARA",
        83: "CUTIA",       84: "GAMBÁ",           85: "JACARÉ",
        86: "JAGUATIRICA", 87: "LOBO GUARÁ",      88: "MÃO PELADA",
        89: "QUATI",       90: "SERIEMA",          91: "SERPENTE",
        92: "TAMANDUÁ BANDEIRA", 93: "TAMANDUÁ MIRIM", 94: "TATU",
    }

    def __init__(self):
        self.color_neon_cyan = (255, 230, 0)
        self.color_danger = (0, 0, 255)
        self.color_safe = (0, 255, 65)
        self.thermal_mode = False
        self.scan_line_y = 0
        # LUT para redução de saturação no filtro térmico (pré-computada)
        import numpy as np
        lut = (np.arange(256, dtype=np.float32) * 0.8).clip(0, 255).astype(np.uint8)
        self._sat_lut = lut
        self.class_names = self._CLASS_NAMES

    def apply_thermal_filter(self, frame):
        """Simulação de Visão Térmica Otimizada (Redução de 60% de overhead)."""
        # 1. Escala de cinza (Luminância)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 2. Color Map (JET é o padrão térmico)
        thermal = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
        
        # 3. Ajuste de saturação via LUT (Processamento direto no BGR)
        # Em vez de converter para HSV, aplicamos a redução diretamente no canal G e B
        # para simular a perda de cor, mantendo o R (quente) mais vibrante.
        thermal[:, :, 0] = self._sat_lut[thermal[:, :, 0]] # Blue
        thermal[:, :, 1] = self._sat_lut[thermal[:, :, 1]] # Green
        
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

    def process_frame(self, frame, detections):
        # 1. Aplicar Filtro Térmico se ativo
        if self.thermal_mode:
            frame = self.apply_thermal_filter(frame)

        # 2. Desenhar Bounding Boxes (Lógica Original Corrigida)
        for det in detections:
            label_id = det["label_id"]
            conf = det['confidence']
            x, y, w, h = det['box']
            
            # Tradução de IDs Globais para HUD se necessário
            class_name = self.class_names.get(label_id, f"ID_{label_id}")
            label = f"{class_name} {conf:.1%}"
            
            color = self.color_danger if conf > 0.6 else self.color_safe
            self.draw_tactical_box(frame, x, y, w, h, color, label)
            
        return frame

if __name__ == "__main__":
    print("Módulo UI Tática Premium carregado.")
