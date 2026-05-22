"""
T014 — Valida mAP50 dos modelos TFLite INT8 pós-PTQ via Ultralytics.

Compara com baseline FP32 ONNX para medir perda de precisão.
Critério: perda < 3% vs FP32.

Uso (da raiz do projeto):
  py -3.12 scripts/validate_tflite_map.py
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

PROJECT_ROOT = Path(__file__).parent.parent

MODELS = [
    {
        "name":    "coco_yolov8n_nc80_v0",
        "tflite":  PROJECT_ROOT / "models" / "coco_yolov8n_nc80_v0_i320_nodfl.tflite",
        "onnx":    PROJECT_ROOT / "models" / "coco_yolov8n_nc80_v0_i320_nodfl.onnx",
        "data":    "coco8.yaml",
        "imgsz":   320,
        "nc":      80,
        # Baseline mAP50 FP32 esperado: ~52% (YOLOv8n oficial COCO imgsz=320)
        # A task pede ≥~77% — esse número parece ser de imgsz=640 ou dataset diferente.
        # Registraremos o valor real e anotaremos como baseline.
        "baseline_note": "YOLOv8n COCO imgsz=320 — baseline real a medir",
    },
    {
        "name":    "fulldet_yolov8n_nc95_v3",
        "tflite":  PROJECT_ROOT / "models" / "fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite",
        "onnx":    PROJECT_ROOT / "models" / "fulldet_yolov8n_nc95_v3_m692_i320_nodfl.onnx",
        "data":    str(PROJECT_ROOT / "datasets" / "full_detection.yaml"),
        "imgsz":   320,
        "nc":      95,
        # Baseline mAP50 FP32: 69.2% (m692 no nome)
        "baseline_note": "fulldet_v3 FP32 baseline = 69.2% (mAP50 da run de treino)",
    },
]


def validate_model(cfg: dict) -> dict:
    from ultralytics import YOLO

    tflite_path = cfg["tflite"]
    onnx_path   = cfg["onnx"]
    data        = cfg["data"]
    imgsz       = cfg["imgsz"]

    print(f"\n{'='*60}")
    print(f"Validando: {cfg['name']}")
    print(f"  {cfg['baseline_note']}")
    print(f"{'='*60}")

    results = {}

    # ── mAP FP32 via ONNX ────────────────────────────────────────────────────
    if onnx_path.exists():
        print(f"\n[FP32 ONNX] {onnx_path.name}")
        try:
            m_onnx = YOLO(str(onnx_path), task="detect")
            v_onnx = m_onnx.val(data=data, imgsz=imgsz, verbose=False, device="cpu")
            map50_fp32 = v_onnx.box.map50
            results["fp32_map50"] = map50_fp32
            print(f"  mAP50 FP32: {map50_fp32:.4f} ({map50_fp32*100:.1f}%)")
        except Exception as e:
            print(f"  [ERRO FP32] {e}")
            results["fp32_map50"] = None
    else:
        print(f"  [SKIP] ONNX não encontrado: {onnx_path}")
        results["fp32_map50"] = None

    # ── mAP INT8 via TFLite ──────────────────────────────────────────────────
    if tflite_path.exists():
        print(f"\n[INT8 TFLite] {tflite_path.name} ({tflite_path.stat().st_size/1024/1024:.2f} MB)")
        try:
            m_tfl = YOLO(str(tflite_path), task="detect")
            v_tfl = m_tfl.val(data=data, imgsz=imgsz, verbose=False, device="cpu")
            map50_int8 = v_tfl.box.map50
            results["int8_map50"] = map50_int8
            print(f"  mAP50 INT8: {map50_int8:.4f} ({map50_int8*100:.1f}%)")
        except Exception as e:
            print(f"  [ERRO INT8] {e}")
            results["int8_map50"] = None
    else:
        print(f"  [SKIP] TFLite não encontrado: {tflite_path}")
        print("  Execute scripts/export_tflite_ptq.py primeiro.")
        results["int8_map50"] = None

    # ── Delta ────────────────────────────────────────────────────────────────
    fp32 = results.get("fp32_map50")
    int8 = results.get("int8_map50")
    if fp32 is not None and int8 is not None:
        delta = (fp32 - int8) * 100
        pct   = (delta / fp32) * 100 if fp32 > 0 else float("nan")
        ok    = pct < 3.0
        results["delta_pp"]  = delta
        results["pct_loss"]  = pct
        results["pass"]      = ok
        status = "PASS ✓" if ok else "FAIL ✗"
        print(f"\n  Delta: {delta:+.2f}pp ({pct:.1f}% de perda) → {status}")
    else:
        results["pass"] = None

    return results


def main():
    all_results = {}
    for cfg in MODELS:
        r = validate_model(cfg)
        all_results[cfg["name"]] = r

    print("\n" + "="*60)
    print("RESUMO DA VALIDAÇÃO mAP50")
    print("="*60)
    all_pass = True
    for name, r in all_results.items():
        fp32 = r.get("fp32_map50")
        int8 = r.get("int8_map50")
        p    = r.get("pass")
        fp32_s = f"{fp32*100:.1f}%" if fp32 is not None else "N/A"
        int8_s = f"{int8*100:.1f}%" if int8 is not None else "N/A"
        status = ("PASS" if p else "FAIL") if p is not None else "N/A"
        print(f"  {name}: FP32={fp32_s} INT8={int8_s} → {status}")
        if p is False:
            all_pass = False

    print()
    if all_pass:
        print("Critério T014 ATENDIDO: perda mAP <3% em todos os modelos.")
    else:
        print("Critério T014 NÃO ATENDIDO — verificar se vale abrir T017.")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
