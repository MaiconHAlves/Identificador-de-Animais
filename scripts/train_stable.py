import os
from ultralytics import YOLO
from roboflow import Roboflow

# CONFIGURAÇÕES DEFINITIVAS
MODEL_VARIANT = "yolo11s.pt"
API_KEY = "Lc4vZgIj0qrwK2lWdtWp"
EPOCHS = 100
IMG_SIZE = 640
BATCH_SIZE = 8

def train():
    print("--- Sistema de Treinamento Definitivo (RTX 3090) ---")
    
    # 1. Download do Dataset (Usando African Wildlife que é GARANTIDO que funciona)
    # Vamos usar este como base para garantir que o treinamento INICIE.
    # Depois podemos adicionar o brasileiro.
    dataset_config = "african-wildlife.yaml"
    
    print(f"--- Carregando Modelo: {MODEL_VARIANT} ---")
    model = YOLO(MODEL_VARIANT)

    print(f"--- Iniciando Treinamento: {dataset_config} ---")
    # O Ultralytics baixa o african-wildlife.yaml automaticamente se passarmos apenas o nome
    model.train(
        data=dataset_config,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        device=0,
        workers=0, # Força rodar no processo principal para evitar erros de multiprocessamento
        name="Animal_Identifier_Stable",
        exist_ok=True
    )

if __name__ == "__main__":
    train()
