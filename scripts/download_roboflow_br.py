"""
Baixa 3 datasets de fauna brasileira do Roboflow Universe e mescla em
datasets/finetune_br/ com classes remapeadas para animal_wild (class 0).

Pré-requisito:
  py -3.12 -m pip install roboflow
  Conta gratuita em https://roboflow.com → copie sua API key em
  https://app.roboflow.com/settings/api

Uso:
  py -3.12 scripts/download_roboflow_br.py --api_key SUA_CHAVE_AQUI
"""
import argparse
import shutil
import yaml
from pathlib import Path


DATASETS = [
    # (workspace, project, version) — versões confirmadas via API
    ("brazilian-wildlife-trail-cams",      "fauna-do-interior-de-sao-paulo", 9),
    ("universidade-federal-do-par-dkvkc",  "identification-model",           11),
]

OUT_RAW    = Path("datasets/roboflow_br")
OUT_MERGED = Path("datasets/finetune_br")


def download_all(api_key: str):
    from roboflow import Roboflow
    rf = Roboflow(api_key=api_key)

    downloaded = []
    for ws, proj, ver in DATASETS:
        dest = OUT_RAW / proj
        if dest.exists() and any(dest.rglob("*.jpg")):
            print(f"[SKIP] {proj} já existe em {dest}")
            downloaded.append(dest)
            continue
        print(f"\n[DOWN] {ws}/{proj} v{ver} ...")
        try:
            project = rf.workspace(ws).project(proj)
            # tenta a versão pedida, cai para a mais recente se falhar
            try:
                project.version(ver).download("yolov8", location=str(dest))
            except Exception:
                latest = len(project.versions())
                print(f"  v{ver} não encontrada, tentando v{latest}...")
                project.version(latest).download("yolov8", location=str(dest))
            print(f"  Salvo em: {dest}")
            downloaded.append(dest)
        except Exception as e:
            print(f"  [ERRO] {proj}: {e}")

    return downloaded


def remap_labels(label_dir: Path):
    """Substitui o class_id de todos os labels por 0 (animal_wild)."""
    for lbl in label_dir.rglob("*.txt"):
        lines = lbl.read_text().splitlines()
        new_lines = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                parts[0] = "0"
                new_lines.append(" ".join(parts))
        lbl.write_text("\n".join(new_lines))


def merge(downloaded: list[Path]):
    for split in ("train", "val"):
        (OUT_MERGED / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUT_MERGED / "labels"  / split).mkdir(parents=True, exist_ok=True)

    total_imgs = 0
    for src_root in downloaded:
        for split in ("train", "valid", "val"):
            img_dir = src_root / split / "images"
            lbl_dir = src_root / split / "labels"
            if not img_dir.exists():
                # alguns datasets usam estrutura flat
                img_dir = src_root / split
                lbl_dir = src_root / split

            out_split = "val" if split in ("valid", "val") else "train"

            for img in img_dir.glob("*.jpg"):
                lbl = lbl_dir / img.with_suffix(".txt").name
                dst_img = OUT_MERGED / "images" / out_split / f"{src_root.name}_{img.name}"
                dst_lbl = OUT_MERGED / "labels"  / out_split / f"{src_root.name}_{lbl.stem}.txt"
                shutil.copy2(img, dst_img)
                if lbl.exists():
                    shutil.copy2(lbl, dst_lbl)
                    total_imgs += 1

    # Remap todas as classes para 0 (animal_wild)
    remap_labels(OUT_MERGED / "labels")

    # Gera data.yaml
    yaml_data = {
        "path": str(OUT_MERGED.resolve()),
        "train": "images/train",
        "val":   "images/val",
        "nc":    1,
        "names": {0: "animal_wild"},
    }
    yaml_path = OUT_MERGED / "data.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True)

    print(f"\n[OK] {total_imgs} imagens mescladas em {OUT_MERGED}")
    print(f"[OK] data.yaml gerado: {yaml_path}")
    return yaml_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api_key", required=True, help="Roboflow API key")
    args = parser.parse_args()

    OUT_RAW.mkdir(parents=True, exist_ok=True)
    downloaded = download_all(args.api_key)

    if downloaded:
        merge(downloaded)
        print("\nPróximo passo:")
        print("  py -3.12 scripts/finetune_br.py")
    else:
        print("\n[AVISO] Nenhum dataset baixado.")


if __name__ == "__main__":
    main()
