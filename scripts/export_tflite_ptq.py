"""
T014 — Exporta modelos para TFLite INT8 via PTQ usando Ultralytics.

Fontes:
  - coco_yolov8n_nc80_v0: yolov8n.pt (Ultralytics pretrained)
  - fulldet_yolov8n_nc95_v3: E:/training/runs/full_detection_v3_nano/weights/best.pt

Saídas em models/:
  - coco_yolov8n_nc80_v0_i320_nodfl.tflite  (INT8 PTQ, calibrado em COCO val)
  - fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite  (INT8 PTQ, calibrado em full_detection val)

Uso (da raiz do projeto):
  py -3.12 scripts/export_tflite_ptq.py
  py -3.12 scripts/export_tflite_ptq.py --only fulldet
  py -3.12 scripts/export_tflite_ptq.py --only fulldet --calibration /tmp/cal_br.yaml
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

FULLDET_PT   = Path("E:/training/runs/full_detection_v3_nano/weights/best.pt")
FULLDET_DATA = str(PROJECT_ROOT / "datasets" / "full_detection.yaml")

# Suprimir avisos verbosos do TF antes de importar ultralytics
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")


def find_tflite(export_result) -> Path | None:
    """Localiza o arquivo full_integer_quant.tflite gerado pelo Ultralytics.
    full_integer_quant é obrigatório para hardware delegates (AICore/NPU).
    """
    if export_result is None:
        return None
    candidate = Path(str(export_result))
    if candidate.suffix == ".tflite":
        return candidate if candidate.exists() else None
    # Procura no diretório _saved_model/ gerado pelo Ultralytics
    saved_dir = candidate if candidate.is_dir() else candidate.parent
    # Ordem de preferência: full_integer_quant > int8 > qualquer .tflite
    priority_names = ["full_integer_quant", "int8"]
    all_tflite = list(saved_dir.glob("*.tflite"))  # não rglob — evita pegar models/
    for prio in priority_names:
        for m in all_tflite:
            if prio in m.name:
                return m
    return all_tflite[0] if all_tflite else None


def export_model(weights: str | Path, data: str, imgsz: int,
                 out_name: str, label: str) -> Path | None:
    from ultralytics import YOLO

    print(f"\n{'='*60}")
    print(f"Exportando: {label}")
    print(f"  weights: {weights}")
    print(f"  data:    {data}")
    print(f"  imgsz:   {imgsz} | int8: True")
    print(f"{'='*60}")

    model = YOLO(str(weights))
    result = model.export(
        format="tflite",
        imgsz=imgsz,
        int8=True,
        data=data,
    )

    tflite_src = find_tflite(result)
    if tflite_src is None or not tflite_src.exists():
        print(f"[ERRO] TFLite não encontrado após export. result={result}")
        return None

    out_path = MODELS_DIR / out_name
    shutil.copy2(tflite_src, out_path)
    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"\n[OK] {out_name} ({size_mb:.2f} MB) → {out_path}")
    return out_path


def parse_args():
    p = argparse.ArgumentParser(description="Exporta modelos YOLOv8 → TFLite INT8 PTQ")
    p.add_argument(
        "--only",
        choices=["coco", "fulldet"],
        default=None,
        help="Exportar só um modelo (coco | fulldet). Padrão: ambos.",
    )
    p.add_argument(
        "--calibration",
        default=None,
        metavar="YAML",
        help="YAML de calibração alternativo para fulldet (ex: /tmp/cal_br.yaml). "
             "Padrão: datasets/full_detection.yaml",
    )
    return p.parse_args()


def main():
    args = parse_args()
    only = args.only
    fulldet_data = args.calibration or FULLDET_DATA

    results = {}

    # ── 1. COCO model ────────────────────────────────────────────────────────
    if only in (None, "coco"):
        out_coco = export_model(
            weights="yolov8n.pt",
            data="coco8.yaml",           # Ultralytics mini-COCO (auto-baixa se necessário)
            imgsz=320,
            out_name="coco_yolov8n_nc80_v0_i320_nodfl.tflite",
            label="COCO yolov8n nc=80 i320 INT8",
        )
        results["coco"] = out_coco
    else:
        print("[SKIP] coco_v0 — --only fulldet especificado")

    # ── 2. Fulldet model ─────────────────────────────────────────────────────
    if only in (None, "fulldet"):
        if not FULLDET_PT.exists():
            print(f"[ERRO] best.pt não encontrado: {FULLDET_PT}")
            results["fulldet"] = None
        else:
            out_fulldet = export_model(
                weights=FULLDET_PT,
                data=fulldet_data,
                imgsz=320,
                out_name="fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite",
                label="Fulldet yolov8n nc=95 i320 INT8",
            )
            results["fulldet"] = out_fulldet
    else:
        print("[SKIP] fulldet_v3 — --only coco especificado")

    # ── Resumo ────────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("RESUMO DO EXPORT")
    print("="*60)
    for key, path in results.items():
        if path and path.exists():
            size_mb = path.stat().st_size / 1024 / 1024
            print(f"  ✓ {key}: {path.name} ({size_mb:.2f} MB)")
        else:
            print(f"  ✗ {key}: FALHOU")

    ok = all(p and p.exists() for p in results.values())
    print("\nPróximo passo: py -3.12 scripts/validate_tflite_quick.py")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
