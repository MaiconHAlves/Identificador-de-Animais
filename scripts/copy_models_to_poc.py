"""
T014 — Copia modelos TFLite e bus.jpg para assets do projeto Android Studio PoC.

Uso (da raiz do projeto):
  py -3.12 scripts/copy_models_to_poc.py
"""

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_DIR = PROJECT_ROOT / "_research" / "litert_poc" / "app" / "src" / "main" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "models/coco_yolov8n_nc80_v0_i320_nodfl.tflite": "coco_yolov8n_nc80_v0_i320_nodfl.tflite",
    "models/fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite": "fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite",
    "bus.jpg": "bus.jpg",
}

ok = True
for src_rel, dst_name in FILES.items():
    src = PROJECT_ROOT / src_rel
    dst = ASSETS_DIR / dst_name
    if not src.exists():
        print(f"[SKIP] {src_rel} — não encontrado")
        ok = False
        continue
    shutil.copy2(src, dst)
    size_kb = dst.stat().st_size / 1024
    print(f"[OK] {dst_name} ({size_kb:.0f} KB)")

print(f"\nAssets em: {ASSETS_DIR}")
sys.exit(0 if ok else 1)
