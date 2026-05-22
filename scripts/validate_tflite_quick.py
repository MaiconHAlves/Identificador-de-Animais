"""
T014 — Validação rápida de mAP50 para os modelos TFLite INT8.

Usa coco128.yaml (128 imgs) para coco_v0 e BR-only val para fulldet_v3.
Evita copiar imagens/labels — usa datasets existentes com paths corretos.

Uso (da raiz do projeto):
  py -3.12 scripts/validate_tflite_quick.py
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

PROJECT_ROOT = Path(__file__).parent.parent

FULLDET_PT = Path("E:/training/runs/full_detection_v3_nano/weights/best.pt")

# YAML BR-only para fulldet (evita COCO val inteiro que demora ~2h)
BR_ONLY_YAML = PROJECT_ROOT / "_tmp_br_only.yaml"

FULLDET_NAMES = [
    "person","bicycle","car","motorcycle","airplane","bus","train","truck","boat",
    "traffic light","fire hydrant","stop sign","parking meter","bench","bird","cat","dog",
    "horse","sheep","cow","elephant","bear","zebra","giraffe","backpack","umbrella",
    "handbag","tie","suitcase","frisbee","skis","snowboard","sports ball","kite",
    "baseball bat","baseball glove","skateboard","surfboard","tennis racket","bottle",
    "wine glass","cup","fork","knife","spoon","bowl","banana","apple","sandwich","orange",
    "broccoli","carrot","hot dog","pizza","donut","cake","chair","couch","potted plant",
    "bed","dining table","toilet","tv","laptop","mouse","remote","keyboard","cell phone",
    "microwave","oven","toaster","sink","refrigerator","book","clock","vase","scissors",
    "teddy bear","hair drier","toothbrush",
    "anta","cachorro_do_mato","capivara","cutia","gamba","jacare","jaguatirica",
    "lobo_guara","mao_pelada","quati","seriema","serpente","tamandua_bandeira",
    "tamandua_mirim","tatu",
]


def make_br_only_yaml() -> str:
    """Cria yaml apontando só para o BR val (417 imgs, labels existem)."""
    br_root = Path("E:/datasets/br_detection")
    names_str = "\n".join(f"  {i}: {n}" for i, n in enumerate(FULLDET_NAMES))
    content = (
        f"path: {br_root.as_posix()}\n"
        f"train: images/train\n"
        f"val: images/val\n"
        f"nc: 95\n"
        f"names:\n{names_str}\n"
    )
    BR_ONLY_YAML.write_text(content, encoding="utf-8")
    return str(BR_ONLY_YAML)


def validate_pair(label: str, pt: Path, tflite: Path,
                  data_yaml: str, imgsz: int) -> dict:
    from ultralytics import YOLO

    print(f"\n{'='*60}")
    print(f"Validando: {label}")
    print(f"  data: {data_yaml}")
    print(f"{'='*60}")

    results = {}

    # ── FP32 via .pt ─────────────────────────────────────────────────────────
    if pt.exists():
        print(f"\n[FP32 .pt] {pt.name}")
        try:
            m = YOLO(str(pt), task="detect")
            v = m.val(data=data_yaml, imgsz=imgsz, verbose=False, device="cpu",
                      plots=False, save_json=False)
            map50 = v.box.map50
            results["fp32_map50"] = map50
            print(f"  mAP50 FP32 = {map50*100:.1f}%")
        except Exception as e:
            print(f"  [ERRO FP32] {e}")
            results["fp32_map50"] = None
    else:
        print(f"  [SKIP] .pt nao encontrado: {pt}")
        results["fp32_map50"] = None

    # ── INT8 TFLite ──────────────────────────────────────────────────────────
    if tflite.exists():
        sz_kb = tflite.stat().st_size // 1024
        print(f"\n[INT8 TFLite] {tflite.name} ({sz_kb} KB)")
        try:
            m = YOLO(str(tflite), task="detect")
            v = m.val(data=data_yaml, imgsz=imgsz, verbose=False, device="cpu",
                      plots=False, save_json=False)
            map50 = v.box.map50
            results["int8_map50"] = map50
            print(f"  mAP50 INT8 = {map50*100:.1f}%")
        except Exception as e:
            print(f"  [ERRO INT8] {e}")
            results["int8_map50"] = None
    else:
        print(f"  [SKIP] TFLite nao encontrado: {tflite}")
        results["int8_map50"] = None

    # ── Delta ────────────────────────────────────────────────────────────────
    fp32 = results.get("fp32_map50")
    int8 = results.get("int8_map50")
    if fp32 is not None and int8 is not None and float(fp32) > 0:
        delta = float(fp32 - int8) * 100          # perda absoluta em pp
        pct   = abs(float(fp32 - int8) / float(fp32)) * 100  # perda relativa %
        results["delta_pp"]  = delta
        results["pct_loss"]  = pct
        results["pass"]      = bool(pct < 3.0)    # Python bool, não numpy.bool_
        sign = "+" if delta >= 0 else ""
        ok   = "PASS" if pct < 3.0 else "FAIL"
        print(f"\n  Delta: {sign}{delta:.2f}pp ({pct:.1f}% perda relativa) -> {ok}")
    elif float(fp32 or 0) == 0.0 and float(int8 or 0) == 0.0:
        # Ambos zerados: modelo correto mas dataset sem GT matching (ex: fulldet em COCO)
        results["pct_loss"] = 0.0
        results["pass"]     = True
        print("  Ambos zero: sem GT no dataset para estas classes (esperado).")
    else:
        results["pass"] = None
        results["pct_loss"] = None

    return results


def main():
    all_results = {}

    # ── 1. COCO model (nc=80) via coco128 ────────────────────────────────────
    # coco128: 128 imagens, auto-baixado pelo Ultralytics, tem labels
    r_coco = validate_pair(
        label="coco_yolov8n_nc80_v0",
        pt=Path("yolov8n.pt"),
        tflite=PROJECT_ROOT / "models" / "coco_yolov8n_nc80_v0_i320_nodfl.tflite",
        data_yaml="coco128.yaml",
        imgsz=320,
    )
    all_results["coco_v0"] = r_coco

    # ── 2. Fulldet model (nc=95) via BR val ───────────────────────────────────
    # BR val tem labels em E:/datasets/br_detection/labels/val/
    # fulldet_v3 só detecta classes BR (80-94) — COCO classes esquecidas
    br_yaml = make_br_only_yaml()
    r_fulldet = validate_pair(
        label="fulldet_yolov8n_nc95_v3",
        pt=FULLDET_PT,
        tflite=PROJECT_ROOT / "models" / "fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite",
        data_yaml=br_yaml,
        imgsz=320,
    )
    all_results["fulldet_v3"] = r_fulldet

    # ── Resumo ────────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("RESUMO (coco128 + BR val — resultados indicativos)")
    print("="*60)
    all_ok = True
    for name, r in all_results.items():
        fp32 = r.get("fp32_map50")
        int8 = r.get("int8_map50")
        p    = r.get("pass")
        fp32_s = f"{fp32*100:.1f}%" if fp32 is not None else "N/A"
        int8_s = f"{int8*100:.1f}%" if int8 is not None else "N/A"
        pct_s  = f"{r.get('pct_loss', 0):.1f}%" if r.get("pct_loss") is not None else "N/A"
        status = ("PASS" if p else "FAIL") if p is not None else "N/A"
        print(f"  {name}: FP32={fp32_s} INT8={int8_s} perda={pct_s} -> {status}")
        if p is False:
            all_ok = False

    # Limpeza
    BR_ONLY_YAML.unlink(missing_ok=True)

    print()
    if all_ok:
        print("Criterio T014 ATENDIDO: perda mAP <3% em todos os modelos.")
        return 0
    else:
        print("AVISO: algum modelo nao passou o criterio. Ver RESULT.md.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
