"""
Treina YOLOv8n (nano) com COCO (80 classes) + fauna brasileira (15 classes) = 95 classes.

Versão NANO criada para resolver o bug do OpenCV DNN com modelos YOLOv8s grandes (>40MB)
no Android, que retornam scores=0 em todos os frames. Yolov8n compila para ~12MB e
funciona corretamente com OpenCV DNN no Android (Samsung S24 inclusive).

Uso:
  py -3.12 scripts/train_full_nano.py
"""
from ultralytics import YOLO
from pathlib import Path
import torch

torch.backends.cudnn.benchmark = True  # speedup ~10% para input fixo 640x640

BASE_MODEL = "yolov8n.pt"        # NANO (era yolov8s.pt no v2 — gerou modelo 43MB que quebra OpenCV DNN)
DATA_YAML  = Path("datasets/full_detection.yaml").resolve()
# Modo qualidade — prioriza resultado sobre tempo de treino
EPOCHS     = 150                 # +90 vs v2 (era 50): nano precisa muito mais epochs pra rivalizar com s
BATCH      = 128                 # nano usa ~6GB VRAM com batch=128 — folga na 3090
WORKERS    = 4                   # i7-9700F 8 cores — workers=6 estoura RAM com cache='disk'+mixup
PROJECT    = "E:/training/runs"
NAME       = "full_detection_v3_nano"
LAST_PT    = Path(f"E:/training/runs/{NAME}/weights/last.pt")


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
        print(f"Próximo passo: py -3.12 scripts/export_unified.py --weights {best} --out models/full_detection_v3_nano_nodfl.onnx")
        return

    print(f"Base: {BASE_MODEL} (YOLOv8n nano — pretrained COCO)")
    print(f"Dataset: {DATA_YAML}")
    print(f"Output: E:/training/runs/{NAME}/weights/best.pt")

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
        # Modo qualidade — hiperparâmetros mais conservadores e augmentation mais forte:
        lr0=0.01, lrf=0.0001,         # decai mais agressivo no fim (era 0.01) → fine-tune mais fino
        warmup_epochs=5.0,            # warmup um pouco maior pra estabilizar nano
        freeze=0,                     # sem freeze — descongela tudo. Nano tem pouca capacidade, precisa otimizar TUDO
        # Augmentation mais agressivo para nano compensar capacidade menor
        hsv_h=0.02, hsv_s=0.8, hsv_v=0.5,
        degrees=15.0, translate=0.15, scale=0.6,
        fliplr=0.5, flipud=0.0,
        mosaic=1.0, mixup=0.2,        # +0.1 vs v2 — mais regularização
        copy_paste=0.1,               # nova augmentation (Ultralytics 8.x)
        close_mosaic=15,              # desliga mosaic nos últimos 15 epochs (estabiliza convergência)
        # Otimização e early stop generosos
        patience=50,                  # +25 vs v2 — não queremos parar cedo
        optimizer="auto",             # SGD por padrão, AdamW se Ultralytics decidir
        save=True, save_period=10,
        amp=True,                     # fp16 — reduz VRAM e acelera ~20% na RTX 3090
        cache='disk',                 # cache em .npy no C: (32GB RAM apertada pra cache=True)
        verbose=True, plots=True,
        exist_ok=True,
        # Validação completa todo epoch (qualidade > velocidade)
        val=True,
        rect=False,                   # sem rect (mantém augmentation aleatório)
    )

    best = Path(PROJECT) / NAME / "weights" / "best.pt"
    print(f"\nTreino concluído. Melhor modelo: {best}")
    print(f"\nPróximos passos:")
    print(f"  1. py -3.12 scripts/export_unified.py --weights {best} --out models/full_detection_v3_nano_nodfl.onnx")
    print(f"  2. Atualizar mobile/main.py linha 51 para apontar para 'models/full_detection_v3_nano_nodfl.onnx'")
    print(f"  3. Rebuild do APK e teste no S24")


if __name__ == "__main__":
    main()
