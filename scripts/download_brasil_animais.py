"""
Download de imagens de animais silvestres brasileiros via iNaturalist API.
Fonte: https://api.inaturalist.org — gratuita, sem autenticação, licença CC.

Uso:
  py -3.12 scripts/download_brasil_animais.py
  py -3.12 scripts/download_brasil_animais.py --max_per_species 300
"""
import time
import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Brazil place_id no iNaturalist
BRAZIL_PLACE_ID = 6744

# Espécies alvo: taxon_id iNaturalist -> nome pasta
# IDs confirmados pelo Gemini (maio 2026) — mais confiáveis que taxon_name
SPECIES = {
    74442: "capivara",          # ~18.400 imagens BR
    85553: "cobra",             # ~18.500 imagens BR (Serpentes)
    42658: "gamba",             # ~6.500 imagens BR
    41670: "quati",             # ~3.200 imagens BR
    43721: "cutia",             # ~2.400 imagens BR
    47070: "tatu",              # ~2.800 imagens BR
    43353: "anta",              # ~2.200 imagens BR
    47103: "tamandua_bandeira", # ~1.900 imagens BR
    42091: "lobo_guara",        # ~1.500 imagens BR
    42176: "veado_catingueiro", # ~1.100 imagens BR
    # Adicionais
    43415: "cachorro_do_mato",
    41922: "jaguatirica",
    41669: "mao_pelada",
}

# Datasets já anotados (YOLO format) disponíveis no Roboflow Universe:
# - Fauna do interior de SP (Lobo-guará, Cutia, Tatu, Gambá, Capivara):
#   https://universe.roboflow.com/brazilian-wildlife-trail-cams/fauna-do-interior-de-sao-paulo
# - Identification Model UFPA (Anta, Tamanduá, Quati, Veado, Capivara):
#   https://universe.roboflow.com/universidade-federal-do-par-dkvkc/identification-model
# - Snakes (cobras brasileiras):
#   https://universe.roboflow.com/snakes-v2/snakes
# Baixe esses primeiro — já vêm com bounding boxes prontas!

API_BASE   = "https://api.inaturalist.org/v1"
PAGE_SIZE  = 200


def fetch_observations(taxon_name: str, max_results: int) -> list[dict]:
    """Busca observações com foto e qualidade research-grade no Brasil."""
    observations = []
    page = 1
    while len(observations) < max_results:
        params = {
            "taxon_name":    taxon_name,
            "place_id":      BRAZIL_PLACE_ID,
            "quality_grade": "research",
            "photos":        "true",
            "per_page":      PAGE_SIZE,
            "page":          page,
            "order":         "desc",
            "order_by":      "created_at",
        }
        try:
            r = requests.get(f"{API_BASE}/observations", params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
            if not results:
                break
            observations.extend(results)
            total = data.get("total_results", 0)
            print(f"  [{taxon_name}] página {page}: {len(observations)}/{min(max_results, total)} observações")
            if len(observations) >= total or len(observations) >= max_results:
                break
            page += 1
            time.sleep(0.5)  # respeita rate limit iNaturalist
        except Exception as e:
            print(f"  Erro na página {page}: {e}")
            break
    return observations[:max_results]


def extract_photo_urls(observations: list[dict]) -> list[str]:
    """Extrai URLs de fotos em resolução média (medium ~500px)."""
    urls = []
    for obs in observations:
        for photo in obs.get("photos", []):
            url = photo.get("url", "")
            # iNaturalist: substitui 'square' (75px) por 'medium' (500px)
            url = url.replace("/square.", "/medium.")
            if url:
                urls.append(url)
    return urls


def download_image(url: str, dest: Path) -> bool:
    if dest.exists():
        return True
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            dest.write_bytes(r.content)
            return True
    except Exception:
        pass
    return False


def download_species(taxon_name: str, folder_name: str, out_dir: Path,
                     max_per_species: int, workers: int):
    species_dir = out_dir / folder_name
    species_dir.mkdir(parents=True, exist_ok=True)

    # Pula se já tem imagens suficientes
    existing = list(species_dir.glob("*.jpg"))
    if len(existing) >= max_per_species:
        print(f"[SKIP] {folder_name}: {len(existing)} imagens já existem")
        return

    print(f"\n[{folder_name}] Buscando observações de '{taxon_name}'...")
    obs = fetch_observations(taxon_name, max_per_species * 2)  # pede 2x para ter margem
    urls = extract_photo_urls(obs)
    urls = urls[:max_per_species]
    print(f"  {len(urls)} fotos encontradas. Baixando...")

    ok = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {
            ex.submit(download_image, url, species_dir / f"{folder_name}_{i:04d}.jpg"): i
            for i, url in enumerate(urls)
        }
        for f in as_completed(futures):
            if f.result():
                ok += 1

    print(f"  [{folder_name}] {ok}/{len(urls)} imagens salvas em {species_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_dir",          default="datasets/brasil_animais")
    parser.add_argument("--max_per_species",  type=int, default=200)
    parser.add_argument("--workers",          type=int, default=8)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Destino: {out_dir.resolve()}")
    print(f"Máximo por espécie: {args.max_per_species}")
    print(f"Espécies: {len(SPECIES)}\n")

    for taxon, folder in SPECIES.items():
        download_species(taxon, folder, out_dir, args.max_per_species, args.workers)

    total = sum(len(list((out_dir / f).glob("*.jpg"))) for f in SPECIES.values())
    print(f"\nConcluído! Total de imagens: {total}")
    print(f"Próximo passo: anotar com Roboflow ou usar auto-labeler (SAM2)")


if __name__ == "__main__":
    main()
