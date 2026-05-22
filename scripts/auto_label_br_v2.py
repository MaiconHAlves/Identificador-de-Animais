"""
Auto-label v2 — usando YOLOv8x COCO pré-treinado como teacher GENÉRICO.

Por que esse script existe:
O `full_detection_v2/best.pt` foi treinado com labels degeneradas (bbox = imagem
inteira), então perdeu a capacidade de gerar bboxes plausíveis para as classes
BR — só consegue classificar. Resultado: auto_label_br.py (que usava o v2 como
teacher) atingiu apenas 4.5% de auto-labeled.

Estratégia v2:
1. Usar YOLOv8x pré-treinado em COCO (não o v2!) — modelo grande, 130MB, sabe
   detectar bem QUALQUER objeto/animal genérico que aparece com clareza na cena.
2. NÃO filtrar por classe COCO detectada — fotos do iNaturalist têm 1 animal
   centralizado e dominante; YOLOv8x detecta isso como *algum* objeto (cat, dog,
   bird, bear, ou até como classe não-animal — não importa).
3. Pegar a bbox de maior score×área dentro do range plausível (1%-95% da imagem).
4. Re-rotular com a classe BR esperada (extraída do filename).
5. Imagens onde YOLOv8x não detecta NADA → review manual.

Limitações:
- Espécies sem proxy próximo no COCO (anta, capivara, jacaré, serpente, tatu)
  podem ainda ter taxa baixa. Pra essas, vai pra review.
- Se a foto tiver outros objetos COCO (ex: pessoa segurando o animal), pode
  pegar a pessoa em vez do animal. Vamos preferir bbox NÃO-pessoa quando possível.

Uso:
  py -3.12 scripts/auto_label_br_v2.py
  py -3.12 scripts/auto_label_br_v2.py --teacher yolov8x.pt --conf 0.05
"""
import argparse
import sys
import shutil
from pathlib import Path
from collections import defaultdict


SPECIES_TO_CLASS = {
    "anta":               80,
    "cachorro_do_mato":   81,
    "capivara":           82,
    "cutia":              83,
    "gamba":              84,
    "jacare":             85,
    "jaguatirica":        86,
    "lobo_guara":         87,
    "mao_pelada":         88,
    "quati":              89,
    "seriema":            90,
    "serpente":           91,
    "tamandua_bandeira":  92,
    "tamandua_mirim":     93,
    "tatu":               94,
}

# Classes COCO que são animais ou objetos plausíveis de "ser confundido com fauna"
# Usadas como hint pra preferir essas bboxes quando disponível
COCO_ANIMAL_CLASSES = {14, 15, 16, 17, 18, 19, 20, 21, 22, 23}  # bird..giraffe
COCO_PERSON_CLASS = 0
# Classes COCO claramente NÃO-animais que não queremos pegar
COCO_BLACKLIST = {
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,  # veículos, sinais, etc
    24, 25, 26, 27, 28,  # bagagem
    39, 40, 41, 42, 43, 44, 45,  # cozinha
    56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75,  # móveis/eletrônicos
    76, 78, 79,  # scissors, hair drier, toothbrush
}


def species_from_filename(filename: str) -> int | None:
    name = Path(filename).stem.lower()
    for species in sorted(SPECIES_TO_CLASS.keys(), key=len, reverse=True):
        if name.startswith(species):
            return SPECIES_TO_CLASS[species]
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--teacher", type=str, default="yolov8x.pt",
                        help="Modelo teacher COCO. Default: yolov8x.pt (download automático ~130MB).")
    parser.add_argument("--conf", type=float, default=0.05,
                        help="Confiança mínima — bem baixa propositalmente. Default 0.05.")
    parser.add_argument("--imgsz", type=int, default=1280,
                        help="Tamanho de inferência. Default 1280.")
    parser.add_argument("--no_tta", action="store_true",
                        help="Desativa TTA. Default: TTA ativo.")
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--root", type=str, default="datasets/br_detection")
    parser.add_argument("--min_area_pct", type=float, default=0.01)
    parser.add_argument("--max_area_pct", type=float, default=0.95)
    parser.add_argument("--allow_blacklist", action="store_true",
                        help="Aceita bboxes de classes COCO blacklisted (móveis, veículos). Default: descarta.")
    parser.add_argument("--allow_person", action="store_true",
                        help="Aceita bbox de pessoa (classe 0). Default: só usa se for a única opção.")
    args = parser.parse_args()

    print(f"Teacher: {args.teacher} (COCO pré-treinado, modo proxy genérico)")
    print(f"Confiança mínima: {args.conf}")
    print(f"imgsz: {args.imgsz} | TTA: {not args.no_tta} | Device: {args.device}")
    print()

    from ultralytics import YOLO
    model = YOLO(args.teacher)

    root = Path(args.root)
    if not root.exists():
        print(f"[ERRO] Pasta de dataset não existe: {root}")
        sys.exit(1)

    labels_v3 = root / "labels_v3"
    review_log = root / "_review_manual.txt"
    if labels_v3.exists():
        print(f"[AVISO] {labels_v3} já existe. Apagando para regenerar...")
        shutil.rmtree(labels_v3)
    (labels_v3 / "train").mkdir(parents=True)
    (labels_v3 / "val").mkdir(parents=True)

    stats = {
        "total":                0,
        "auto_labeled":         0,
        "review_manual":        0,
        "no_species_in_name":   0,
        "by_species":           defaultdict(lambda: {
            "total": 0, "auto": 0, "review": 0,
            "via_coco_animal": 0, "via_other": 0, "via_person": 0,
        }),
    }
    review_lines = []

    for split in ("train", "val"):
        img_dir = root / "images" / split
        out_dir = labels_v3 / split
        if not img_dir.exists():
            print(f"[AVISO] Pasta não existe: {img_dir}")
            continue

        images = sorted(list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.jpeg")) + list(img_dir.glob("*.png")))
        print(f"\n=== Split: {split} ({len(images)} imagens) ===")

        for img_path in images:
            stats["total"] += 1
            expected_class = species_from_filename(img_path.name)

            if expected_class is None:
                stats["no_species_in_name"] += 1
                review_lines.append(f"{split}/{img_path.name}\tprefixo_desconhecido")
                continue

            species_name = next((k for k, v in SPECIES_TO_CLASS.items() if v == expected_class), "?")
            stats["by_species"][species_name]["total"] += 1

            results = model.predict(
                source=str(img_path),
                imgsz=args.imgsz,
                conf=args.conf,
                device=args.device,
                augment=(not args.no_tta),
                iou=0.5,
                verbose=False,
            )
            r = results[0]

            if r.boxes is None or len(r.boxes) == 0:
                stats["review_manual"] += 1
                stats["by_species"][species_name]["review"] += 1
                review_lines.append(f"{split}/{img_path.name}\tnada_detectado_conf>={args.conf}")
                continue

            cls_arr  = r.boxes.cls.cpu().numpy().astype(int)
            conf_arr = r.boxes.conf.cpu().numpy()
            xywhn    = r.boxes.xywhn.cpu().numpy()

            # Classifica candidatos por tier
            #   Tier 1: classe animal COCO (preferida)
            #   Tier 2: outras classes não-blacklist e não-pessoa
            #   Tier 3: pessoa (só se única opção)
            #   Filtro: área válida sempre
            tier1, tier2, tier3 = [], [], []
            for i in range(len(cls_arr)):
                cls_i = int(cls_arr[i])
                conf_i = float(conf_arr[i])
                x, y, w, h = xywhn[i]
                area = w * h
                if area < args.min_area_pct or area > args.max_area_pct:
                    continue
                if cls_i in COCO_BLACKLIST and not args.allow_blacklist:
                    continue
                # score combinado: prioriza confiança alta + área razoável
                score = conf_i * (area ** 0.3)  # raiz cubica suave do area
                cand = (score, conf_i, x, y, w, h, cls_i)
                if cls_i in COCO_ANIMAL_CLASSES:
                    tier1.append(cand)
                elif cls_i == COCO_PERSON_CLASS:
                    tier3.append(cand)
                else:
                    tier2.append(cand)

            chosen = None
            tier_used = None
            for tier_name, tier_list in [("via_coco_animal", tier1),
                                         ("via_other", tier2)]:
                if tier_list:
                    chosen = max(tier_list, key=lambda t: t[0])
                    tier_used = tier_name
                    break
            if chosen is None and (args.allow_person or True):
                # último recurso: pessoa
                if tier3:
                    chosen = max(tier3, key=lambda t: t[0])
                    tier_used = "via_person"

            if chosen is None:
                stats["review_manual"] += 1
                stats["by_species"][species_name]["review"] += 1
                detected_classes = sorted(set(cls_arr.tolist()))
                review_lines.append(
                    f"{split}/{img_path.name}\tsem_candidato_valido:{detected_classes}"
                )
                continue

            _score, _conf, x, y, w, h, _coco_cls = chosen
            label_path = out_dir / (img_path.stem + ".txt")
            with label_path.open("w") as f:
                # Re-rotula com a classe BR esperada (não a classe COCO detectada)
                f.write(f"{expected_class} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
            stats["auto_labeled"] += 1
            stats["by_species"][species_name]["auto"] += 1
            stats["by_species"][species_name][tier_used] += 1

            if stats["auto_labeled"] % 200 == 0:
                print(f"  [{stats['auto_labeled']}] {img_path.name} → {tier_used}")

    if review_lines:
        review_log.write_text("\n".join(review_lines), encoding="utf-8")

    print("\n" + "=" * 78)
    print("RELATÓRIO FINAL — AUTO-LABEL v2 (COCO-proxy)")
    print("=" * 78)
    print(f"Total de imagens:          {stats['total']}")
    print(f"Auto-labeled (com bbox):   {stats['auto_labeled']}  ({stats['auto_labeled']*100/max(stats['total'],1):.1f}%)")
    print(f"Para review manual:        {stats['review_manual']}")
    print()
    print(f"{'Espécie':<22} {'total':>6} {'auto':>6} {'animal':>7} {'outro':>6} {'pessoa':>7} {'%auto':>7}")
    print("-" * 78)
    for species in sorted(SPECIES_TO_CLASS.keys()):
        s = stats["by_species"][species]
        if s["total"] == 0:
            continue
        pct = (s["auto"] / s["total"] * 100) if s["total"] else 0
        print(f"{species:<22} {s['total']:>6} {s['auto']:>6} {s['via_coco_animal']:>7} {s['via_other']:>6} {s['via_person']:>7} {pct:>6.1f}%")

    print()
    print(f"Labels novas em: {labels_v3}")
    if review_lines:
        print(f"Review manual em: {review_log}")
    print()
    print("Quando satisfeito:")
    print(f"  mv {root}/labels {root}/labels_old")
    print(f"  mv {labels_v3} {root}/labels")
    print(f"  py -3.12 scripts/train_full_nano.py")


if __name__ == "__main__":
    main()
