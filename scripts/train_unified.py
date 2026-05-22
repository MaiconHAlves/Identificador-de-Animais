"""
Treino do modelo unificado de 4 classes para detecção em estrada/área aberta.

Uso:
  py -3.12 scripts/train_unified.py

Pré-requisito:
  py -3.12 scripts/prepare_dataset.py --coco_dir E:/datasets/coco
"""
from ultralytics import YOLO
from pathlib import Path
import torch

DATA_YAML  = Path("data/unified.yaml").resolve()
EPOCHS     = 100
IMG_SIZE   = 640
BATCH      = 64    # RTX 3090 24GB — yolov8n usa ~8GB com batch=64
WORKERS    = 8
MODEL_BASE = "yolov8n.pt"   # nano: rápido no Android; troque por yolov8s.pt p/ mais precisão
PROJECT    = "training/runs"
NAME       = "unified_v1"


LAST_PT = Path("runs/detect/training/runs/unified_v1-6/weights/last.pt")


def main():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # Resume from checkpoint if available, else start fresh
    if LAST_PT.exists():
        print(f"Retomando de: {LAST_PT}")
        model = YOLO(str(LAST_PT))
        model.train(resume=True)
    else:
        print(f"Dataset: {DATA_YAML}")
        model = YOLO(MODEL_BASE)
        model.train(
            data=str(DATA_YAML),
            epochs=EPOCHS,
            imgsz=IMG_SIZE,
            batch=BATCH,
            workers=WORKERS,
            device=0,
            project=PROJECT,
            name=NAME,
            hsv_h=0.015, hsv_s=0.7, hsv_v=0.4,
            degrees=10.0, translate=0.1, scale=0.5,
            flipud=0.0, fliplr=0.5, mosaic=1.0, mixup=0.1,
            patience=20, save=True, save_period=10,
            verbose=True, plots=True,
        )

    best = LAST_PT.parent / "best.pt" if LAST_PT.exists() else Path(PROJECT) / NAME / "weights" / "best.pt"
    print(f"\nTreino concluído. Melhor modelo: {best}")
    return best


if __name__ == "__main__":
    best_pt = main()
