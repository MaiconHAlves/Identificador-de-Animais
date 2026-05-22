import os
import json
import time
import argparse
import requests
import numpy as np
from PIL import Image
from pathlib import Path

try:
    import onnxruntime as ort
except ImportError:
    ort = None

# Configurações de Classes e iNaturalist
CLASSES_BR = {
    "80": {"name": "anta", "sci": ["Tapirus terrestris"], "target": 150},
    "81": {"name": "cachorro_do_mato", "sci": ["Cerdocyon thous"], "target": 150},
    "82": {"name": "capivara", "sci": ["Hydrochoerus hydrochaeris"], "target": 300},
    "83": {"name": "cutia", "sci": ["Dasyprocta aguti"], "target": 150},
    "84": {"name": "gamba", "sci": ["Didelphis marsupialis"], "target": 150},
    "85": {"name": "jacare", "sci": ["Caiman latirostris"], "target": 300},
    "86": {"name": "jaguatirica", "sci": ["Leopardus pardalis"], "target": 150},
    "87": {"name": "lobo_guara", "sci": ["Chrysocyon brachyurus"], "target": 150},
    "88": {"name": "mao_pelada", "sci": ["Procyon cancrivorus"], "target": 150},
    "89": {"name": "quati", "sci": ["Nasua nasua"], "target": 150},
    "90": {"name": "seriema", "sci": ["Cariama cristata"], "target": 300},
    "91": {"name": "serpente", "sci": ["Bothrops jararaca", "Crotalus durissus"], "target": 300},
    "92": {"name": "tamandua_bandeira", "sci": ["Myrmecophaga tridactyla"], "target": 150},
    "93": {"name": "tamandua_mirim", "sci": ["Tamandua tetradactyla"], "target": 150},
    "94": {"name": "tatu", "sci": ["Dasypus novemcinctus"], "target": 300}
}

class BRDatasetDownloader:
    def __init__(self, base_dir, model_path=None):
        self.base_dir = Path(base_dir)
        self.img_dir = self.base_dir / "datasets" / "br_detection" / "images" / "train"
        self.lbl_dir = self.base_dir / "datasets" / "br_detection" / "labels" / "train"
        self.progress_file = self.base_dir / "download_progress.json"
        self.model_path = model_path
        self.session = None
        self.stats = {c["name"]: {"downloaded": 0, "detected": 0, "fallback": 0, "failed": 0} for c in CLASSES_BR.values()}

        self.img_dir.mkdir(parents=True, exist_ok=True)
        self.lbl_dir.mkdir(parents=True, exist_ok=True)

        if ort and model_path and os.path.exists(model_path):
            try:
                self.session = ort.InferenceSession(model_path)
                print(f"[INFO] Modelo ONNX carregado: {model_path}")
                self.anchors, self.strides = self._make_anchors()
            except Exception as e:
                print(f"[WARN] Erro ao carregar modelo: {e}")
        else:
            print("[INFO] Usando apenas fallback para labels (modelo não disponível)")

    def _make_anchors(self, img_size=640):
        anchor_points, stride_tensor = [], []
        for s in [8, 16, 32]:
            h = img_size // s
            w = img_size // s
            sx = np.arange(w) + 0.5
            sy = np.arange(h) + 0.5
            sx, sy = np.meshgrid(sx, sy)
            anchor_points.append(np.stack((sx, sy), -1).reshape(-1, 2))
            stride_tensor.append(np.full((h * w, 1), s))
        return np.concatenate(anchor_points), np.concatenate(stride_tensor)

    def _softmax(self, x, axis=-1):
        e_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return e_x / e_x.sum(axis=axis, keepdims=True)

    def _dfl_decode(self, raw_boxes):
        b, c, a = raw_boxes.shape
        reg_max = 16
        x = raw_boxes.reshape(b, 4, reg_max, a)
        x = self._softmax(x, axis=2)
        weight = np.arange(reg_max).reshape(1, 1, reg_max, 1)
        x = np.sum(x * weight, axis=2)  # [1, 4, 8400] ltrb distances
        return x

    def predict_yolo(self, img_path, target_id):
        if not self.session:
            return None
        try:
            img = Image.open(img_path).convert('RGB')
            img_resized = img.resize((640, 640))
            input_data = np.array(img_resized).astype(np.float32) / 255.0
            input_data = input_data.transpose(2, 0, 1)[np.newaxis, ...]

            outputs = self.session.run(None, {self.session.get_inputs()[0].name: input_data})
            raw_boxes = outputs[0]   # [1, 64, 8400]
            scores = outputs[1][0]   # [95, 8400]

            dist = self._dfl_decode(raw_boxes)[0]  # [4, 8400]
            lt = self.anchors.T - dist[:2]
            rb = self.anchors.T + dist[2:]
            x1y1 = lt * self.strides.T
            x2y2 = rb * self.strides.T

            class_scores = scores[int(target_id), :]
            best_idx = np.argmax(class_scores)

            if class_scores[best_idx] > 0.25:
                box = np.array([x1y1[0, best_idx], x1y1[1, best_idx],
                                x2y2[0, best_idx], x2y2[1, best_idx]])
                cx = ((box[0] + box[2]) / 2) / 640
                cy = ((box[1] + box[3]) / 2) / 640
                w  = (box[2] - box[0]) / 640
                h  = (box[3] - box[1]) / 640
                # Clamp to [0,1]
                cx, cy = max(0.0, min(1.0, cx)), max(0.0, min(1.0, cy))
                w,  h  = max(0.01, min(1.0, w)),  max(0.01, min(1.0, h))
                return f"{target_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"
        except Exception as e:
            print(f"  [WARN] Detecção falhou para {img_path}: {e}")
        return None

    def load_progress(self):
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {}

    def save_progress(self, progress):
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=4)

    def count_existing(self, class_name):
        return len(list(self.img_dir.glob(f"{class_name}_inat_*.jpg")))

    def download_class(self, class_id, class_info, dry_run=False):
        progress = self.load_progress()
        class_name = class_info["name"]
        sci_names  = class_info["sci"]
        target_count = class_info["target"]

        # Contar arquivos já existentes para não re-baixar
        current_count = self.count_existing(class_name)
        progress[class_id] = current_count

        if current_count >= target_count:
            print(f"[SKIP] {class_name}: {current_count}/{target_count} já existem")
            return

        print(f"\n[{class_name}] {current_count}/{target_count} — baixando {target_count - current_count} novas")

        for sci in sci_names:
            if current_count >= target_count:
                break
            page = 1
            while current_count < target_count:
                url = "https://api.inaturalist.org/v1/observations"
                params = {
                    "taxon_name": sci,
                    "quality_grade": "research",
                    "photos": "true",
                    "place_id": 6878,
                    "per_page": 50,
                    "page": page,
                }
                try:
                    time.sleep(1.1)
                    response = requests.get(url, params=params, timeout=15)
                    data = response.json()
                    results = data.get("results", [])
                    if not results:
                        print(f"  Sem mais resultados para {sci} (página {page})")
                        break

                    for obs in results:
                        if current_count >= target_count:
                            break
                        obs_id = obs["id"]
                        photos = obs.get("photos", [])
                        if not photos:
                            continue

                        photo_url = photos[0]["url"].replace("square", "large")
                        filename  = f"{class_name}_inat_{obs_id}"
                        img_path  = self.img_dir / f"{filename}.jpg"
                        lbl_path  = self.lbl_dir / f"{filename}.txt"

                        if img_path.exists():
                            continue

                        if dry_run:
                            print(f"  [DRY] {filename}.jpg ← {photo_url[:60]}...")
                            current_count += 1
                            continue

                        # Download com retry
                        img_bytes = None
                        for attempt in range(2):
                            try:
                                r = requests.get(photo_url, timeout=15)
                                if r.status_code == 200:
                                    img_bytes = r.content
                                    break
                            except Exception:
                                time.sleep(2)

                        if not img_bytes:
                            self.stats[class_name]["failed"] += 1
                            continue

                        # Salvar e validar dimensões
                        img_path.write_bytes(img_bytes)
                        try:
                            with Image.open(img_path) as chk:
                                if chk.width < 224 or chk.height < 224:
                                    img_path.unlink()
                                    continue
                        except Exception:
                            img_path.unlink()
                            self.stats[class_name]["failed"] += 1
                            continue

                        # Gerar label
                        label = self.predict_yolo(img_path, class_id)
                        if label:
                            self.stats[class_name]["detected"] += 1
                        else:
                            label = f"{class_id} 0.500000 0.550000 0.750000 0.800000"
                            self.stats[class_name]["fallback"] += 1

                        lbl_path.write_text(label)
                        current_count += 1
                        self.stats[class_name]["downloaded"] += 1
                        progress[class_id] = current_count

                        if current_count % 10 == 0:
                            self.save_progress(progress)
                            print(f"  {class_name}: {current_count}/{target_count}")

                    page += 1
                    if page > 20:
                        break

                except Exception as e:
                    print(f"  [ERR] API falhou (página {page}): {e}")
                    break

        self.save_progress(progress)
        print(f"  {class_name}: concluído com {current_count} imagens")

    def print_report(self):
        print("\n" + "=" * 60)
        print("RELATÓRIO FINAL")
        print(f"{'Classe':<22} | {'Baixadas':>8} | {'Modelo':>6} | {'Fallback':>8} | {'Erros':>5}")
        print("-" * 60)
        total = {"downloaded": 0, "detected": 0, "fallback": 0, "failed": 0}
        for name, s in self.stats.items():
            if any(s.values()):
                print(f"{name:<22} | {s['downloaded']:>8} | {s['detected']:>6} | {s['fallback']:>8} | {s['failed']:>5}")
                for k in total:
                    total[k] += s[k]
        print("-" * 60)
        print(f"{'TOTAL':<22} | {total['downloaded']:>8} | {total['detected']:>6} | {total['fallback']:>8} | {total['failed']:>5}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Download fauna BR via iNaturalist + labels YOLO automáticas")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem baixar")
    parser.add_argument("--class", dest="class_name", type=str, help="Focar em uma classe (ex: capivara)")
    parser.add_argument("--reset", action="store_true", help="Reseta progresso salvo")
    args = parser.parse_args()

    base_path  = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_path, "models", "full_detection_v2_nodfl.onnx")

    downloader = BRDatasetDownloader(base_path, model_path)

    if args.reset and downloader.progress_file.exists():
        downloader.progress_file.unlink()
        print("[INFO] Progresso resetado.")

    # Priorizar classes com 0% detecção
    priority = {"capivara", "jacare", "seriema", "serpente", "tatu"}
    ordered = sorted(CLASSES_BR.items(),
                     key=lambda x: (0 if x[1]["name"] in priority else 1, x[0]))

    for cid, cinfo in ordered:
        if args.class_name and args.class_name.lower() != cinfo["name"].lower():
            continue
        downloader.download_class(cid, cinfo, dry_run=args.dry_run)

    downloader.print_report()


if __name__ == "__main__":
    main()
