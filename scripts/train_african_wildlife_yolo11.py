import os
from ultralytics import YOLO

# CONFIGURAÇÕES TÁTICAS
MODEL_VARIANT = "yolo11s.pt"  # s = Small (Equilíbrio ideal entre velocidade e precisão para RTX 3090)
DATASET_CONFIG = "african-wildlife.yaml" # Dataset público oficial da Ultralytics
EPOCHS = 50 # Reduzi para 50 para um teste rápido, mas completo.
IMG_SIZE = 640
BATCH_SIZE = 32 # A 3090 aguenta um batch maior com o modelo Small

def train():
    print(f"--- Iniciando Sistema de Treinamento YOLO11 (GPU 0: RTX 3090) ---")
    
    # 1. Carregar Modelo Base
    # Se o yolo11s.pt não existir, ele será baixado automaticamente
    print(f"--- Carregando Modelo Base: {MODEL_VARIANT} ---")
    model = YOLO(MODEL_VARIANT)

    # 2. Treinamento
    # O dataset african-wildlife.yaml será baixado automaticamente pela Ultralytics
    print(f"--- Iniciando Treinamento: {DATASET_CONFIG} ---")
    results = model.train(
        data=DATASET_CONFIG,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        device=0,         # Força RTX 3090 (GPU 0)
        name="Animal_Identifier_African_Wildlife",
        patience=10,
        exist_ok=True,
        workers=8        # Otimiza o carregamento de dados
    )

    # 3. Exportação para Android (ONNX)
    print("--- Treinamento Concluído. Exportando para Mobile (ONNX)... ---")
    # Exportamos para ONNX que é o formato mais leve e compatível com nosso app Kivy
    path = model.export(format="onnx", imgsz=IMG_SIZE)
    print(f"\n[SUCESSO] Modelo exportado para: {path}")
    print("Este arquivo .onnx deve ser colocado na pasta 'models/' do seu projeto mobile.")

if __name__ == "__main__":
    train()
