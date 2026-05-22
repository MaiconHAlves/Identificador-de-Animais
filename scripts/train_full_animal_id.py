import os
from ultralytics import YOLO

# CONFIGURAÇÕES TÁTICAS - ROAD SENTINEL 1.0 (OFFLINE STABLE)
MODEL_VARIANT = "yolo11s.pt"
EPOCHS = 50 
IMG_SIZE = 640
DATA_PATH = "E:/Projetos/Identificador de Animais/fauna_br/data.yaml"

def train():
    print(f"\n--- INICIANDO TREINAMENTO OFFLINE: ROAD SENTINEL (GPU: RTX 3090) ---")
    
    # Carregar modelo que já conhece Cães/Gatos/Bois/Cavalos
    model = YOLO(MODEL_VARIANT)
    
    print(f"--- Iniciando Fine-Tuning: Preservando Domésticos + Aprendendo Fauna BR ---")
    results = model.train(
        data=DATA_PATH,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=8,
        device=0,
        name="Road_Sentinel_Offline",
        exist_ok=True,
        freeze=10 # Mantém o conhecimento de cães/bois intacto
    )
    
    # Exportação Final
    print("--- Exportando 'Cérebro' Multiespécies para Mobile ---")
    onnx_path = model.export(format="onnx", imgsz=IMG_SIZE)
    
    if not os.path.exists("models"): os.makedirs("models")
    final_path = os.path.join("models", "road_sentinel_detector.onnx")
    import shutil
    shutil.copy(onnx_path, final_path)
    
    print(f"\n[SUCESSO] Treinamento concluído: {final_path}")

if __name__ == "__main__":
    train()
