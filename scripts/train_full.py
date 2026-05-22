"""
Treina YOLOv8s com COCO (80 classes) + fauna brasileira (15 classes) = 95 classes.
Baixa COCO automaticamente (~20GB) na primeira execução.

Uso:
  py -3.12 scripts/train_full.py
"""
from ultralytics import YOLO
from pathlib import Path
import torch

torch.backends.cudnn.benchmark = True  # speedup ~10% para input fixo 640x640

BASE_MODEL = "yolov8s.pt"       # pretrained COCO — baixado automaticamente
DATA_YAML  = Path("datasets/full_detection.yaml").resolve()
EPOCHS     = 50                  # v2: labels COCO corretos, cabeça de 95 classes do zero
BATCH      = 64                  # RTX 3090 24GB — batch=64 usa ~12GB VRAM
WORKERS    = 4                   # i7-9700F 8 cores, 18GB RAM livre
PROJECT    = "E:/training/runs"
NAME       = "full_detection_v2"
LAST_PT    = Path("E:/training/runs/full_detection_v2/weights/last.pt")


def main():
    if not DATA_YAML.exists():
        print(f"[ERRO] {DATA_YAML} não encontrado.")
        print("       Execute primeiro: py -3.12 scripts/prepare_full_dataset.py")
        return

    print(f"GPU: {torch.cuda.get_device_name(0)}")

    if LAST_PT.exists():
        print(f"[RESUMINDO] Checkpoint encontrado: {LAST_PT}")
        model = YOLO(str(LAST_PT))
        model.train(resume=True)
        best = LAST_PT.parent / "best.pt"
        print(f"\nTreino concluído. Melhor modelo: {best}")
        print(f"Próximo passo: py -3.12 scripts/export_unified.py --weights {best}")
        return

    print(f"Base: {BASE_MODEL} (COCO pretrained)")
    print(f"Dataset: {DATA_YAML}")

    model = YOLO(BASE_MODEL)
    model.train(
        data=str(DATA_YAML),
        epochs=EPOCHS,
        imgsz=640,
        batch=BATCH,
        workers=WORKERS,
        device=0,
        project=PROJECT,
        name=NAME,
        # v2: freeze=5 (descongela mais backbone), labels COCO corretos
        lr0=0.01, lrf=0.01,
        freeze=5,
        hsv_h=0.015, hsv_s=0.7, hsv_v=0.4,
        degrees=10.0, translate=0.1, scale=0.5,
        fliplr=0.5, mosaic=1.0, mixup=0.1,
        patience=20, save=True, save_period=5,
        amp=True,    # fp16 — reduz VRAM ~40% e acelera ~20% na RTX 3090
        cache=False, # desativa cache de imagens (118k imgs = ~140GB, nao cabe em RAM)
        verbose=True, plots=True,
        exist_ok=True,
    )

    best = Path(PROJECT) / NAME / "weights" / "best.pt"
    print(f"\nTreino concluído. Melhor modelo: {best}")
    print(f"Próximo passo: py -3.12 scripts/export_unified.py --weights {best}")


if __name__ == "__main__":
    main()
