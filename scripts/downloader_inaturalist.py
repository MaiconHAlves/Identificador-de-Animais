import os
import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import argparse

# Configurações de Espécies (Taxon IDs do iNaturalist)
SPECIES_MAP = {
    "capivara": 74442,
    "tatu": 47075, # Dasypus novemcinctus
    "anta": 43353,
    "lobo_guara": 42091,
    "gamba": 42658, # Didelphis albiventris
    "quati": 41670,
    "veado_catingueiro": 74552,
    "cutia": 43721,
    "tamandua_bandeira": 47107,
    "tamandua_mirim": 47104,
    "cachorro_do_mato": 42087,
    "jaguatirica": 41997,
    "mao_pelada": 41667,
    "serpente": 26036,
    "jacare": 41249,
    "seriema": 14
}

BASE_URL = "https://api.inaturalist.org/v1/observations"
PLACE_ID = 6878  # Brasil

class INaturalistDownloader:
    def __init__(self, output_dir, max_workers=5):
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.session = requests.Session()
        # User-Agent é obrigatório para evitar bloqueios
        self.session.headers.update({"User-Agent": "FaunaDetection-DatasetBuilder/1.0 (Python)"})

    def get_observation_images(self, species_name, taxon_id, limit=100):
        print(f"\n[*] Pesquisando {species_name} (Taxon ID: {taxon_id})...")
        params = {
            "taxon_id": taxon_id,
            "place_id": PLACE_ID,
            "verifiable": "true",
            "quality_grade": "research", # Apenas fotos confirmadas pela comunidade
            "per_page": min(limit, 200),
            "order_by": "votes", # Prioriza fotos "melhores"
            "license": "cc0,cc-by,cc-by-nc" # Licenças amigáveis
        }

        all_urls = []
        page = 1
        downloaded_count = 0

        while downloaded_count < limit:
            params["page"] = page
            try:
                response = self.session.get(BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                if not results:
                    break

                for obs in results:
                    for photo in obs.get("photos", []):
                        if downloaded_count >= limit:
                            break
                        # Troca 'square' ou 'small' por 'medium' ou 'large' para melhor qualidade
                        url = photo.get("url", "").replace("square", "large")
                        if url:
                            all_urls.append(url)
                            downloaded_count += 1
                
                if len(results) < params["per_page"]:
                    break
                
                page += 1
                time.sleep(1) # Respeita rate limit da API (100 req/min)
            except Exception as e:
                print(f"[!] Erro ao buscar página {page}: {e}")
                break

        return all_urls

    def download_image(self, url, species_dir, index):
        ext = url.split('.')[-1].split('?')[0]
        if ext.lower() not in ['jpg', 'jpeg', 'png']:
            ext = 'jpg'
        
        filename = f"imagem_{index:03d}.{ext}"
        filepath = os.path.join(species_dir, filename)

        if os.path.exists(filepath):
            return "skipped"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return "success"
        except Exception as e:
            return f"error: {e}"

    def run(self, species_list=None, limit_per_species=100):
        if not species_list:
            species_list = SPECIES_MAP.keys()

        for name in species_list:
            taxon_id = SPECIES_MAP.get(name)
            if not taxon_id:
                print(f"[!] Espécie {name} não encontrada no mapeamento.")
                continue

            urls = self.get_observation_images(name, taxon_id, limit=limit_per_species)
            if not urls:
                print(f"[!] Nenhuma imagem encontrada para {name}.")
                continue

            species_dir = os.path.join(self.output_dir, name)
            os.makedirs(species_dir, exist_ok=True)

            print(f"[*] Baixando {len(urls)} imagens para {name}...")
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self.download_image, url, species_dir, i+1): url for i, url in enumerate(urls)}
                
                for future in tqdm(as_completed(futures), total=len(urls), desc=name):
                    res = future.result()
                    # Log opcional aqui se necessário

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Downloader de imagens de fauna brasileira do iNaturalist")
    parser.add_argument("--species", type=str, help="Nome da espécie separada por vírgula (ou 'all')", default="all")
    parser.add_argument("--limit", type=int, help="Limite de imagens por espécie", default=50)
    parser.add_argument("--workers", type=int, help="Número de threads", default=5)
    args = parser.parse_args()

    output_base = "datasets/brasil_animais"
    
    if args.species == "all":
        target_species = list(SPECIES_MAP.keys())
    else:
        target_species = [s.strip() for s in args.species.split(",")]

    downloader = INaturalistDownloader(output_base, max_workers=args.workers)
    downloader.run(target_species, limit_per_species=args.limit)
    print("\n[V] Concluído! Imagens salvas em:", output_base)
