"""
Curadoria do dataset COCO para o modelo unificado de 4 classes.

Classes mapeadas:
  animal_wild (0)    <- bear(21), elephant(20), zebra(22), giraffe(23),
                        bird(14), horse(17) em contexto selvagem
  animal_domestic (1) <- dog(16), cat(15), cow(19), sheep(18), horse(17)
  human (2)          <- person(0)
  vehicle (3)        <- bicycle(1), car(2), motorcycle(3), bus(5), truck(7)

Uso:
  py -3.12 scripts/prepare_dataset.py --coco_dir E:/datasets/coco
  (baixa automaticamente se --coco_dir não existir)
"""
import os
import json
import shutil
import argparse
from pathlib import Path
from collections import defaultdict

# COCO class id -> nossa classe (id, nome)
COCO_MAP = {
    0:  (2, "human"),
    1:  (3, "vehicle"),   # bicycle
    2:  (3, "vehicle"),   # car
    3:  (3, "vehicle"),   # motorcycle
    5:  (3, "vehicle"),   # bus
    7:  (3, "vehicle"),   # truck
    14: (0, "animal_wild"),    # bird (grandes — pato, galinha filtrados por area)
    15: (1, "animal_domestic"), # cat
    16: (1, "animal_domestic"), # dog
    17: (1, "animal_domestic"), # horse
    18: (1, "animal_domestic"), # sheep
    19: (1, "animal_domestic"), # cow
    20: (0, "animal_wild"),    # elephant
    21: (0, "animal_wild"),    # bear
    22: (0, "animal_wild"),    # zebra
    23: (0, "animal_wild"),    # giraffe
}

MIN_AREA = 1000   # ignora anotações minúsculas (pássaros pequenos, etc.)


def download_coco(dest: Path):
    import urllib.request, zipfile
    dest.mkdir(parents=True, exist_ok=True)
    urls = {
        "train2017.zip":          "http://images.cocodataset.org/zips/train2017.zip",
        "val2017.zip":            "http://images.cocodataset.org/zips/val2017.zip",
        "annotations_trainval2017.zip": "http://images.cocodataset.org/annotations/annotations_trainval2017.zip",
    }
    for fname, url in urls.items():
        out = dest / fname
        if not out.exists():
            print(f"Baixando {fname} ...")
            urllib.request.urlretrieve(url, out)
        print(f"Extraindo {fname} ...")
        with zipfile.ZipFile(out, "r") as z:
            z.extractall(dest)
    print("Download COCO concluído.")


def coco_bbox_to_yolo(bbox, img_w, img_h):
    """[x, y, w, h] absoluto -> [cx, cy, w, h] normalizado."""
    x, y, w, h = bbox
    cx = (x + w / 2) / img_w
    cy = (y + h / 2) / img_h
    return cx, cy, w / img_w, h / img_h


def process_split(split, coco_dir: Path, out_dir: Path):
    ann_file = coco_dir / "annotations" / f"instances_{split}2017.json"
    img_src  = coco_dir / f"{split}2017"
    img_dst  = out_dir / "images" / split
    lbl_dst  = out_dir / "labels" / split
    img_dst.mkdir(parents=True, exist_ok=True)
    lbl_dst.mkdir(parents=True, exist_ok=True)

    print(f"\nCarregando {ann_file} ...")
    with open(ann_file) as f:
        coco = json.load(f)

    # image_id -> {width, height, file_name}
    images = {img["id"]: img for img in coco["images"]}

    # image_id -> lista de anotações mapeadas
    mapped = defaultdict(list)
    for ann in coco["annotations"]:
        cid = ann["category_id"] - 1   # COCO usa 1-indexed
        if cid not in COCO_MAP:
            continue
        if ann.get("area", 0) < MIN_AREA:
            continue
        mapped[ann["image_id"]].append((COCO_MAP[cid][0], ann["bbox"]))

    copied = 0
    for img_id, anns in mapped.items():
        img_info = images[img_id]
        src_path = img_src / img_info["file_name"]
        if not src_path.exists():
            continue
        dst_path = img_dst / img_info["file_name"]
        shutil.copy2(src_path, dst_path)

        lbl_path = lbl_dst / (Path(img_info["file_name"]).stem + ".txt")
        with open(lbl_path, "w") as f:
            for cls_id, bbox in anns:
                cx, cy, w, h = coco_bbox_to_yolo(bbox, img_info["width"], img_info["height"])
                f.write(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")
        copied += 1

    print(f"  {split}: {copied} imagens com anotações relevantes copiadas.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--coco_dir", default="E:/datasets/coco",
                        help="Diretório com COCO (baixa se não existir)")
    parser.add_argument("--out_dir", default="data/unified_dataset")
    args = parser.parse_args()

    coco_dir = Path(args.coco_dir)
    out_dir  = Path(args.out_dir)

    if not (coco_dir / "annotations").exists():
        print(f"COCO não encontrado em {coco_dir}. Iniciando download (~20GB)...")
        download_coco(coco_dir)

    process_split("train", coco_dir, out_dir)
    process_split("val",   coco_dir, out_dir)
    print(f"\nDataset pronto em: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
