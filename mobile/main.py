import threading
import numpy as np
import os
import sys

# Configurações de estabilidade para Samsung S24 / Android 14+
# Desativa multisampling que causa SIGABRT na HWUI da Samsung
os.environ['KIVY_GRAPHICS'] = 'gles'
os.environ['KIVY_GL_BACKEND'] = 'sdl2'

from kivy.config import Config
Config.set('graphics', 'multisamples', '0')
Config.set('kivy', 'exit_on_escape', '0')

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ListProperty

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
    conf_threshold = NumericProperty(0.25)
    active_camera_id = NumericProperty(0)
    menu_active = BooleanProperty(False)
    available_cameras = ListProperty([])

    def on_conf_threshold(self, instance, value):
        """Atualiza a sensibilidade do motor de detecção em tempo real."""
        if hasattr(self, 'detector'):
            self.detector.conf_threshold = value

    def build(self):
        # Carregar o Design Tático
        self.root = Builder.load_file('mobile/style.kv')

        # Emulador/debug: modelo BR 12MB para FPS > 7 e diagnóstico de scores=0
        # Produção S24: trocar para full_detection_v2_nodfl.onnx (95 classes)
        self.detector = DetectionEngine(model_paths=[
            "models/animal_wild_br_nodfl.onnx",
        ], conf_threshold=0.25)
        self.fusion = FusionEngine()
        self.audio = AudioManager()
        self.ui_tactical = TacticalOverlay()

        self.is_thermal_active = False
        self.is_recording = False
        self.running = True
        self._is_paused = False
        self.active_camera_id = 0
        self.last_detections = []
        self.current_risk = 0.0
        self._texture = None
        self._model_fps = 0.0
        self._model_frame_times = []

        # Gerenciamento de Sensores (Câmera será iniciada apenas via callback de permissão)
        self.rgb_manager = SensorManager(sensor_id=0, width=1280, height=720)
        self.thermal_manager = SensorManager(sensor_id=1, width=1280, height=720)

        # Thread de IA com controle de pausa (aguarda frame válido)
        self.ia_thread = threading.Thread(target=self.ia_processing_loop, daemon=True)
        self.ia_thread.start()

        # Iniciar Update da UI a 30 FPS (Fix Erro Térmico S24)
        Clock.schedule_interval(self.update_ui, 1.0 / 30.0)

        return self.root

    def on_start(self):
        from kivy.utils import platform
        if platform == 'android':
            from android.permissions import request_permissions, check_permission, Permission
            perms = [Permission.CAMERA, Permission.RECORD_AUDIO]
            if all(check_permission(p) for p in perms):
                # Permissões já concedidas — inicia câmera diretamente sem onPause
                Clock.schedule_once(lambda dt: self._start_camera(), 0.5)
            else:
                request_permissions(perms, self._on_permissions_result)
        else:
            self._start_camera()

    def _on_permissions_result(self, permissions, results):
        if results and all(results):
            # Usar Clock para agendar o início e dar fôlego ao sistema
            Clock.schedule_once(lambda dt: self._start_camera(), 0.5)
        else:
            print("Permissões negadas — câmera não iniciada")

    def _start_camera(self, cam_id=None):
        print(f"[IA-DEBUG] Iniciando _start_camera(id={cam_id})")
        ids = SensorManager.list_cameras()
        print(f"[DEBUG] IDs detectados: {ids}")
        self.available_cameras = [str(i) for i in ids] if ids else ["0"]
        
        target_id = cam_id if cam_id is not None else (ids[0] if ids else 0)
        
        self.rgb_manager.stop()
        self.rgb_manager = SensorManager(sensor_id=target_id)
        if self.rgb_manager.start():
            self.active_camera_id = target_id
            print(f"[OK] Câmera {target_id} ativa.")
        
    def set_camera(self, camera_id: int):
        if camera_id == self.active_camera_id:
            return
        self.rgb_manager.stop()
        self.rgb_manager = SensorManager(sensor_id=camera_id)
        self.active_camera_id = camera_id
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

    def on_pause(self):
        """Liberar recursos ao minimizar o app."""
        self._is_paused = True
        if hasattr(self, 'rgb_manager'):
            self.rgb_manager.stop()
        return True # Permite que o Android pause o app

    def on_resume(self):
        """Reiniciar recursos ao voltar ao app."""
        if self._is_paused:
            self._is_paused = False
            # Pequeno delay para garantir que a superfície da câmera esteja pronta
            Clock.schedule_once(lambda dt: self._start_camera(self.active_camera_id), 0.5)

    def ia_processing_loop(self, *args):
        """Loop de processamento pesado (IA + Cálculo de Risco)"""
        import time
        consecutive_errors = 0
        self._ia_thread_running = True
        while self._ia_thread_running:
            if self._is_paused:
                time.sleep(0.5)
                continue
                
            try:
                _, frame = self.rgb_manager.get_latest_frame()
                if frame is None:
                    time.sleep(0.033)
                    continue
                detections = self.detector.detect(frame)
                consecutive_errors = 0
                if detections is not None:
                    self.last_detections = detections
                    _now = time.time()
                    self._model_frame_times.append(_now)
                    self._model_frame_times = [t for t in self._model_frame_times if _now - t < 2.0]
                    self._model_fps = len(self._model_frame_times) / 2.0
                    if self.last_detections:
                        max_conf = max(d['confidence'] for d in self.last_detections)
                        self.current_risk = max_conf
                        self.target_count = len(self.last_detections)
                    else:
                        self.current_risk = 0.0
                        self.target_count = 0
                    self.audio.set_risk_level(self.current_risk)
            except Exception as e:
                consecutive_errors += 1
                print(f"ia_processing_loop erro ({consecutive_errors}): {e}")
                if consecutive_errors >= 10:
                    break
                time.sleep(0.1)

    def update_ui(self, dt):
        if self._is_paused:
            return
            
        # Corrigido: get_latest_frame retorna (timestamp, frame)
        _, frame_rgb = self.rgb_manager.get_latest_frame()
        _, frame_thermal = (None, None)
        if self.is_thermal_active:
            _, frame_thermal = self.thermal_manager.get_latest_frame()
        
        if frame_rgb is not None:
            # 1. Aplicar Fusão se houver sinal térmico
            if self.is_thermal_active and frame_thermal is not None:
                display_frame = self.fusion.apply_overlay(frame_rgb, frame_thermal)
            
            # 2. Aplicar OTIMIZAÇÃO: Evitar cópia desnecessária se não houver detecções ou filtros
            if not self.last_detections and not self.ui_tactical.thermal_mode:
                display_frame = frame_rgb
            else:
                # Só copia se precisar desenhar (preserva o original para a thread de IA)
                display_frame = self.ui_tactical.process_frame(frame_rgb.copy(), self.last_detections)
            
            # 3. Atualizar Widget do Kivy
            # Inversão vertical e BGR->RGB via slicing numpy
            buf = display_frame[::-1, :, ::-1].tobytes()
            h_f, w_f = display_frame.shape[:2]
            
            if self._texture is None or self._texture.width != w_f or self._texture.height != h_f:
                self._texture = Texture.create(size=(w_f, h_f), colorfmt='rgb')
            
            self._texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
            self.root.ids.main_feed.texture = self._texture
            
            # 4. Atualizar Labels dinâmicos
            self.root.ids.status_footer.text = f"SCANNING REGION: ALPHA-01 | TARGETS: {self.target_count}"
            cam_fps = int(getattr(self.rgb_manager, 'cam_fps', 0))
            mdl_fps = int(getattr(self, '_model_fps', 0))
            self.root.ids.fps_label.text = f"CAM: {cam_fps} | IA: {mdl_fps} FPS"

    def on_stop(self):
        """Finalização Segura"""
        self.running = False
        self._ia_thread_running = False
        self._is_paused = True
        self.rgb_manager.stop()
        self.thermal_manager.stop()
        self.audio.stop()
        print("Sistema encerrado com segurança.")

if __name__ == "__main__":
    AnimalDetectorApp().run()
