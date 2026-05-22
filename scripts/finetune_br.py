"""
Fine-tune do modelo unificado com fauna brasileira.
Parte do best.pt já treinado no COCO (~2-3h na RTX 3090).

Uso:
  py -3.12 scripts/finetune_br.py
"""
from ultralytics import YOLO
from pathlib import Path
import torch

BASE_WEIGHTS = Path("runs/detect/training/runs/unified_v1-6/weights/best.pt")
DATA_YAML    = Path("datasets/finetune_br/data.yaml").resolve()
EPOCHS       = 50
IMG_SIZE     = 640
BATCH        = 64   # 3090 24GB suporta facilmente
WORKERS      = 8
PROJECT      = "training/runs"
NAME         = "finetune_br_v2"


def main():
    if not BASE_WEIGHTS.exists():
        print(f"[ERRO] Pesos base não encontrados: {BASE_WEIGHTS}")
        return
    if not DATA_YAML.exists():
        print(f"[ERRO] data.yaml não encontrado: {DATA_YAML}")
        print("       Execute primeiro: py -3.12 scripts/download_roboflow_br.py --api_key SUA_CHAVE")
        return

    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Base: {BASE_WEIGHTS}")
    print(f"Dataset: {DATA_YAML}")

    model = YOLO(str(BASE_WEIGHTS))
    model.train(
        data=str(DATA_YAML),
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH,
        workers=WORKERS,
        device=0,
        project=PROJECT,
        name=NAME,
        # Fine-tune: lr menor, freeze backbone
        lr0=0.001, lrf=0.01,
        freeze=10,          # congela as 10 primeiras camadas (backbone)
        hsv_h=0.015, hsv_s=0.5, hsv_v=0.3,
        degrees=5.0, translate=0.1, scale=0.3,
        fliplr=0.5, mosaic=0.8, mixup=0.05,
        patience=15, save=True, save_period=5,
        verbose=True, plots=True,
    )

    best = Path(PROJECT) / NAME / "weights" / "best.pt"
    print(f"\nFine-tune concluído. Melhor modelo: {best}")
    print("Próximo passo: py -3.12 scripts/export_unified.py --weights", best)


if __name__ == "__main__":
    main()
