"""
Auto-label das imagens da fauna brasileira usando o modelo full_detection_v2 (YOLOv8s, 95 classes).

Substitui as labels degeneradas atuais (bbox = imagem inteira, "0.5 0.5 1.0 1.0")
por bboxes verdadeiras geradas pela inferência do v2 no desktop com ORT/CUDA
(sem o bug do OpenCV DNN).

Lógica:
1. Para cada imagem em datasets/br_detection/images/{train,val}/, extrai a classe
   esperada do nome do arquivo (ex: capivara_imagem_NNN.jpg → classe 82).
2. Roda inferência com o modelo v2.
3. Mantém apenas bboxes da classe esperada com conf >= --conf (default 0.4).
4. Se houver pelo menos 1 bbox válida → escreve label em datasets/br_detection/labels_v3/{train,val}/.
5. Se não houver → registra em _review_manual.txt para revisão humana.

Saída: datasets/br_detection/labels_v3/ (não sobrescreve as labels antigas em labels/).
Quando o resultado estiver bom, copiar manualmente labels_v3/ → labels/.

Uso:
  py -3.12 scripts/auto_label_br.py
  py -3.12 scripts/auto_label_br.py --conf 0.5 --weights E:/training/runs/full_detection_v2/weights/best.pt
"""
import argparse
import sys
import shutil
from pathlib import Path
from collections import defaultdict


# Mapeamento espécie → class_id (espelha o full_detection.yaml, classes 80-94)
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


def species_from_filename(filename: str) -> int | None:
    """Extrai class_id da fauna BR a partir do prefixo do filename.

    Ex: 'capivara_imagem_001.jpg' → 82
        'tamandua_bandeira_imagem_001.jpg' → 92
        'tamandua_mirim_imagem_001.jpg' → 93
    Retorna None se o prefixo não bater com nenhuma espécie.
    """
    name = Path(filename).stem.lower()
    # Tenta casar com prefixos compostos primeiro (tamandua_bandeira antes de tamandua_*)
    for species in sorted(SPECIES_TO_CLASS.keys(), key=len, reverse=True):
        if name.startswith(species):
            return SPECIES_TO_CLASS[species]
    return None


def find_default_weights() -> Path | None:
    """Procura .pt do v2 nos paths conhecidos. Retorna None se não achar."""
    candidates = [
        Path("E:/training/runs/full_detection_v2/weights/best.pt"),
        Path("E:/training/runs/full_detection_v2/weights/last.pt"),
        Path("runs/detect/training/runs/full_detection_v1/weights/best.pt"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=str, default=None,
                        help="Caminho do .pt do modelo v2. Se omitido, busca em paths conhecidos.")
    parser.add_argument("--conf", type=float, default=0.25,
                        help="Confiança mínima para aceitar uma bbox. Default 0.25 (modo qualidade).")
    parser.add_argument("--imgsz", type=int, default=1280,
                        help="Tamanho de inferência. Default 1280 (modo qualidade — detecta pequenos animais).")
    parser.add_argument("--no_tta", action="store_true",
                        help="Desativa TTA (Test-Time Augmentation). Default: TTA ativo (mais lento, mais preciso).")
    parser.add_argument("--device", type=str, default="0",
                        help="Device CUDA (default 0). Use 'cpu' se não tiver GPU.")
    parser.add_argument("--root", type=str, default="datasets/br_detection",
                        help="Raiz do dataset BR. Default datasets/br_detection.")
    parser.add_argument("--keep_other_classes", action="store_true",
                        help="Mantém bboxes de outras classes (default: filtra só a esperada).")
    parser.add_argument("--min_area_pct", type=float, default=0.01,
                        help="Área mínima da bbox como fração da imagem. Default 0.01 (1%%).")
    parser.add_argument("--max_area_pct", type=float, default=0.95,
                        help="Área máxima da bbox como fração da imagem. Default 0.95 (descarta 'imagem inteira').")
    args = parser.parse_args()

    # Resolve weights
    if args.weights:
        weights = Path(args.weights)
    else:
        weights = find_default_weights()
    if weights is None or not weights.exists():
        print(f"[ERRO] Não achei o .pt do v2. Tentei:")
        for p in [
            "E:/training/runs/full_detection_v2/weights/best.pt",
            "E:/training/runs/full_detection_v2/weights/last.pt",
            "runs/detect/training/runs/full_detection_v1/weights/best.pt",
        ]:
            print(f"  - {p}")
        print("Use --weights <path> para apontar manualmente.")
        sys.exit(1)
    print(f"Modelo: {weights}")
    print(f"Confiança mínima: {args.conf}")
    print(f"Device: {args.device}")
    print()

    # Carrega Ultralytics YOLO (faz NMS e decode automático)
    from ultralytics import YOLO
    model = YOLO(str(weights))

    root = Path(args.root)
    if not root.exists():
        print(f"[ERRO] Pasta de dataset não existe: {root}")
        sys.exit(1)

    # Cria estrutura de saída (não toca labels/ original)
    labels_v3 = root / "labels_v3"
    review_log = root / "_review_manual.txt"
    if labels_v3.exists():
        print(f"[AVISO] {labels_v3} já existe. Apagando para regenerar...")
        shutil.rmtree(labels_v3)
    (labels_v3 / "train").mkdir(parents=True)
    (labels_v3 / "val").mkdir(parents=True)

    # Estatísticas
    stats = {
        "total":               0,
        "auto_labeled":        0,
        "review_manual":       0,
        "no_species_in_name":  0,
        "by_species":          defaultdict(lambda: {"total": 0, "auto": 0, "review": 0}),
    }
    review_lines = []

    # Itera sobre train e val
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

            # Identifica nome legível da espécie
            species_name = next((k for k, v in SPECIES_TO_CLASS.items() if v == expected_class), "?")
            stats["by_species"][species_name]["total"] += 1

            # Infere — modo qualidade: TTA ativo + imgsz alto + threshold baixo
            results = model.predict(
                source=str(img_path),
                imgsz=args.imgsz,
                conf=args.conf,
                device=args.device,
                augment=(not args.no_tta),  # TTA: horizontal flip + multi-scale
                iou=0.5,                    # NMS um pouco mais permissivo
                verbose=False,
            )
            r = results[0]

            if r.boxes is None or len(r.boxes) == 0:
                stats["review_manual"] += 1
                stats["by_species"][species_name]["review"] += 1
                review_lines.append(f"{split}/{img_path.name}\tnada_detectado_conf>={args.conf}")
                continue

            # Filtra bboxes: classe esperada + área plausível (descarta "imagem inteira" e ruído)
            cls_arr  = r.boxes.cls.cpu().numpy().astype(int)
            conf_arr = r.boxes.conf.cpu().numpy()
            xywhn    = r.boxes.xywhn.cpu().numpy()  # [n, 4] x_center, y_center, w, h normalizado

            kept = []
            rejected_area = []
            for i in range(len(cls_arr)):
                cls_i = int(cls_arr[i])
                if not (args.keep_other_classes or cls_i == expected_class):
                    continue
                x, y, w, h = xywhn[i]
                area = w * h
                if area < args.min_area_pct or area > args.max_area_pct:
                    rejected_area.append((cls_i, float(conf_arr[i]), float(area)))
                    continue
                kept.append((cls_i, float(conf_arr[i]), x, y, w, h))

            # Se sobrou múltiplas bboxes da mesma classe, manter só a de maior confiança
            # (espécies BR raramente aparecem múltiplas vezes na mesma imagem do iNaturalist)
            if not args.keep_other_classes and len(kept) > 1:
                kept = [max(kept, key=lambda t: t[1])]

            if not kept:
                detected_classes = sorted(set(cls_arr.tolist()))
                stats["review_manual"] += 1
                stats["by_species"][species_name]["review"] += 1
                if rejected_area:
                    review_lines.append(
                        f"{split}/{img_path.name}\tarea_fora_de_range:{rejected_area}"
                    )
                else:
                    review_lines.append(
                        f"{split}/{img_path.name}\tdetectou_outras_classes:{detected_classes}"
                    )
                continue

            # Escreve label (ignora conf, mantém apenas formato YOLO)
            label_path = out_dir / (img_path.stem + ".txt")
            with label_path.open("w") as f:
                for cls_i, _conf, x, y, w, h in kept:
                    f.write(f"{cls_i} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
            stats["auto_labeled"] += 1
            stats["by_species"][species_name]["auto"] += 1

            if stats["auto_labeled"] % 100 == 0:
                print(f"  [{stats['auto_labeled']}] {img_path.name} → {len(kept)} bbox(es)")

    # Salva log de review manual
    if review_lines:
        review_log.write_text("\n".join(review_lines), encoding="utf-8")

    # Imprime relatório
    print("\n" + "=" * 60)
    print("RELATÓRIO FINAL")
    print("=" * 60)
    print(f"Total de imagens:          {stats['total']}")
    print(f"Auto-labeled (com bbox):   {stats['auto_labeled']}")
    print(f"Para review manual:        {stats['review_manual']}")
    print(f"Sem espécie no nome:       {stats['no_species_in_name']}")
    print()
    print(f"{'Espécie':<22} {'total':>8} {'auto':>8} {'review':>8} {'%auto':>8}")
    print("-" * 60)
    for species in sorted(SPECIES_TO_CLASS.keys()):
        s = stats["by_species"][species]
        if s["total"] == 0:
            continue
        pct = (s["auto"] / s["total"] * 100) if s["total"] else 0
        print(f"{species:<22} {s['total']:>8} {s['auto']:>8} {s['review']:>8} {pct:>7.1f}%")

    print()
    print(f"Labels novas em: {labels_v3}")
    if review_lines:
        print(f"Imagens para review manual: {review_log}")
        print(f"  → revisar visualmente as imagens listadas, decidir se descarta ou corrige a mão")
    print()
    print("Quando estiver satisfeito com o resultado:")
    print(f"  1. Backup das labels antigas: mv {root}/labels {root}/labels_old")
    print(f"  2. Aplicar as novas:           mv {labels_v3} {root}/labels")
    print(f"  3. Treinar nano:               py -3.12 scripts/train_full_nano.py")


if __name__ == "__main__":
    main()
