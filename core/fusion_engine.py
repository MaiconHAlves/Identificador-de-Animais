import cv2
import numpy as np

class FusionEngine:
    def __init__(self, max_jitter_ns=100_000_000): # 100ms em nanosegundos
        self.max_jitter_ns = max_jitter_ns

    def sync_frames(self, buffer_rgb, buffer_thermal):
        """
        Encontra o par de quadros com o menor delta temporal.
        buffer_rgb e buffer_thermal são listas de tuplas (timestamp_ns, frame)
        """
        if not buffer_rgb or not buffer_thermal:
            return None, None, 0

        best_rgb = None
        best_thermal = None
        min_delta = float('inf')

        # Busca exaustiva no buffer circular (O(N*M))
        # Como o buffer é pequeno (5-10 frames), o impacto é desprezível
        for ts_rgb, frame_rgb in buffer_rgb:
            for ts_thermal, frame_thermal in buffer_thermal:
                delta = abs(ts_rgb - ts_thermal)
                if delta < min_delta:
                    min_delta = delta
                    best_rgb = frame_rgb
                    best_thermal = frame_thermal

        return best_rgb, best_thermal, min_delta

    def apply_overlay(self, rgb_frame, thermal_frame, alpha=0.4):
        """
        Redimensiona o frame térmico, aplica mapa de cores e funde com o RGB.
        """
        if rgb_frame is None or thermal_frame is None:
            return rgb_frame

        h, w = rgb_frame.shape[:2]

        # 1. Redimensionar térmica para o tamanho da RGB
        thermal_resized = cv2.resize(thermal_frame, (w, h))

        # 2. Normalizar e aplicar mapa de cores se for 1 canal (Grayscale)
        if len(thermal_resized.shape) == 2:
            # Normalização para 8-bit (0-255)
            thermal_8bit = cv2.normalize(thermal_resized, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            # Aplicar mapa de calor (JET ou HOT)
            thermal_colored = cv2.applyColorMap(thermal_8bit, cv2.COLORMAP_JET)
        else:
            thermal_colored = thermal_resized

        # 3. Alpha Blending
        fused = cv2.addWeighted(rgb_frame, 1.0 - alpha, thermal_colored, alpha, 0)
        
        return fused

if __name__ == "__main__":
    print("Módulo de Fusão de Sensores pronto.")
