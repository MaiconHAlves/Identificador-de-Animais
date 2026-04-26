import os
from ultralytics import YOLO
from roboflow import Roboflow

# CONFIGURAÇÕES TÁTICAS (Brasil Edition - Time NEXO Engine)
MODEL_VARIANT = "yolo11s.pt"
DATASET_NAME = "brazilian-wildlife-animals-detection"
EPOCHS = 100
IMG_SIZE = 640
BATCH_SIZE = 8 

def download_dataset(api_key):
    """
    Faz o download do dataset especializado da Fauna Brasileira via Roboflow.
    """
    rf = Roboflow(api_key=api_key)
    # Dataset de Fauna do Interior de São Paulo (Altamente relevante)
    project = rf.workspace("brazilian-wildlife-trail-cams").project("fauna-do-interior-de-sao-paulo")
    dataset = project.version(1).download("yolov8") 
    return dataset.location

def train():
    api_key = "Lc4vZgIj0qrwK2lWdtWp"
    
    print(f"--- Iniciando Sistema de Treinamento YOLO11 (GPU 0: RTX 3090) ---")
    print(f"--- Foco: Fauna Brasileira (Capivara, Onça, etc.) ---")
    
    # 1. Download do Dataset Brasileiro
    print(f"--- Baixando Dataset: {DATASET_NAME} ---")
    try:
        dataset_path = download_dataset(api_key)
        yaml_path = os.path.join(dataset_path, "data.yaml")
    except Exception as e:
        print(f"[ERRO] Falha ao baixar dataset: {e}")
        return

    # 2. Carregar Modelo Base
    model = YOLO(MODEL_VARIANT)

    # 3. Treinamento Otimizado
    print(f"--- Iniciando Treinamento Especializado Brasil ---")
    results = model.train(
        data=yaml_path,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        device=0,         # RTX 3090
        workers=2,
        name="Animal_Identifier_Brazil_V1",
        exist_ok=True
    )

    # 4. Exportação para Mobile
    print("--- Treinamento Concluído. Exportando para Mobile (ONNX)... ---")
    path = model.export(format="onnx", imgsz=IMG_SIZE)
    print(f"\n[SUCESSO] Modelo BRASIL pronto e exportado para: {path}")

if __name__ == "__main__":
    train()
