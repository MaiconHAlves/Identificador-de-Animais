import os
import sys
import subprocess

def install_requirements():
    print("--- [CLAUDE] INICIANDO SETUP DE ALTA PERFORMANCE ---")
    
    # Lista de dependências críticas
    requirements = [
        "kivy[base] @ https://github.com/kivy/kivy/archive/master.zip", # Versão estável mais recente
        "opencv-python",
        "onnxruntime-gpu", # Específico para RTX 3090
        "numpy<2.0.0",      # Garantir compatibilidade com ONNX
        "ultralytics",
        "pillow"
    ]
    
    for req in requirements:
        print(f"Instalando: {req}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", req])

def generate_model():
    print("\n--- [CLAUDE] VERIFICANDO MODELO YOLOv8 ---")
    if not os.path.exists("yolov8n.onnx"):
        print("Exportando modelo para formato ONNX otimizado...")
        from ultralytics import YOLO
        model = YOLO('yolov8n.pt')
        model.export(format='onnx', dynamic=True)
    else:
        print("Modelo yolov8n.onnx já presente.")

if __name__ == "__main__":
    try:
        install_requirements()
        generate_model()
        print("\n--- [CLAUDE] SETUP CONCLUÍDO COM SUCESSO ---")
        print("Para rodar: py -3.12 mobile/main.py")
    except Exception as e:
        print(f"\n[ERRO CRÍTICO] Falha no setup: {e}")
