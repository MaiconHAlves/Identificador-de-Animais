"""
Prepara dataset completo: COCO (80 classes) + espécies brasileiras (15 classes).
Gera datasets/full_detection/data.yaml apontando para ambos.

Uso:
  py -3.12 scripts/prepare_full_dataset.py
"""
import shutil
import yaml
from pathlib import Path
from PIL import Image

BR_SPECIES_DIR = Path("datasets/brasil_animais")
OUT_DIR        = Path("datasets/br_detection")

# 15 espécies brasileiras mapeadas para class IDs 80-94
BR_CLASSES = [
    "anta", "cachorro_do_mato", "capivara", "cutia", "gamba",
    "jacare", "jaguatirica", "lobo_guara", "mao_pelada", "quati",
    "seriema", "serpente", "tamandua_bandeira", "tamandua_mirim", "tatu",
]
BR_CLASS_ID = {name: 80 + i for i, name in enumerate(BR_CLASSES)}

# Nomes COCO originais (80 classes, IDs 0-79)
COCO_NAMES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
    5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
    10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
    14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow",
    20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe", 24: "backpack",
    25: "umbrella", 26: "handbag", 27: "tie", 28: "suitcase", 29: "frisbee",
    30: "skis", 31: "snowboard", 32: "sports ball", 33: "kite",
    34: "baseball bat", 35: "baseball glove", 36: "skateboard",
    37: "surfboard", 38: "tennis racket", 39: "bottle", 40: "wine glass",
    41: "cup", 42: "fork", 43: "knife", 44: "spoon", 45: "bowl",
    46: "banana", 47: "apple", 48: "sandwich", 49: "orange",
    50: "broccoli", 51: "carrot", 52: "hot dog", 53: "pizza",
    54: "donut", 55: "cake", 56: "chair", 57: "couch",
    58: "potted plant", 59: "bed", 60: "dining table", 61: "toilet",
    62: "tv", 63: "laptop", 64: "mouse", 65: "remote", 66: "keyboard",
    67: "cell phone", 68: "microwave", 69: "oven", 70: "toaster",
    71: "sink", 72: "refrigerator", 73: "book", 74: "clock",
    75: "vase", 76: "scissors", 77: "teddy bear", 78: "hair drier",
    79: "toothbrush",
}


def convert_br_species():
    """Converte imagens BR para formato YOLO (bbox = imagem inteira)."""
    for split in ("train", "val"):
        (OUT_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    total = 0
    for species in BR_CLASSES:
        src_dir = BR_SPECIES_DIR / species
        if not src_dir.exists():
            print(f"[SKIP] {species} não encontrado em {src_dir}")
            continue

        images = sorted(src_dir.glob("*.jpg")) + sorted(src_dir.glob("*.png"))
        class_id = BR_CLASS_ID[species]

        # 80% treino, 20% validação
        split_idx = int(len(images) * 0.8)
        splits = [("train", images[:split_idx]), ("val", images[split_idx:])]

        for split_name, imgs in splits:
            for img_path in imgs:
                dst_img = OUT_DIR / "images" / split_name / f"{species}_{img_path.name}"
                dst_lbl = OUT_DIR / "labels" / split_name / f"{species}_{img_path.stem}.txt"

                shutil.copy2(img_path, dst_img)
                # Bbox imagem inteira: cx=0.5, cy=0.5, w=1.0, h=1.0
                dst_lbl.write_text(f"{class_id} 0.5 0.5 1.0 1.0\n")
                total += 1

    print(f"[OK] {total} imagens BR convertidas em {OUT_DIR}")
    return total


def create_yaml():
    """Gera data.yaml combinando COCO + espécies brasileiras."""
    all_names = dict(COCO_NAMES)
    for species in BR_CLASSES:
        all_names[BR_CLASS_ID[species]] = species

    # COCO será baixado automaticamente pelo ultralytics em datasets/coco/
    # BR fica em datasets/br_detection/
    yaml_data = {
        "path": ".",
        "train": [
            "datasets/coco/images/train2017",
            str((OUT_DIR / "images" / "train").resolve()),
        ],
        "val": [
            "datasets/coco/images/val2017",
            str((OUT_DIR / "images" / "val").resolve()),
        ],
        "nc": 95,
        "names": all_names,
    }

    yaml_path = Path("datasets/full_detection.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False)
    print(f"[OK] YAML gerado: {yaml_path}")
    return yaml_path


def main():
    print("=== Preparando dataset completo (COCO + fauna BR) ===")
    total = convert_br_species()
    if total == 0:
        print("[ERRO] Nenhuma imagem BR encontrada.")
        return
    yaml_path = create_yaml()
    print(f"\nPróximo passo:")
    print(f"  py -3.12 scripts/train_full.py")


if __name__ == "__main__":
    main()
