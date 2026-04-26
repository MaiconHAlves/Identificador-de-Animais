import requests
import re

api_key = "Lc4vZgIj0qrwK2lWdtWp"

def get_project_details(workspace, project):
    url = f"https://api.roboflow.com/{workspace}/{project}?api_key={api_key}"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    return None

# Lista de projetos promissores que encontramos no log de busca anterior
promising_projects = [
    ("brazilian-wildlife-trail-cams", "fauna-do-interior-de-sao-paulo"),
    ("thermal-wildlife", "thermal-wildlife-detection"),
    ("infrared-wildlife", "infrared-animals"),
    ("capstone-project-vxwzt", "thermal-animal-detection"),
    ("wildlife-vsqzi", "wildlife-animal-detection-y0l6v")
]

print("--- Validando Projetos via API ---")
for ws, proj in promising_projects:
    print(f"Verificando {ws}/{proj}...")
    details = get_project_details(ws, proj)
    if details:
        print(f"  [SUCESSO] Nome: {details.get('project', {}).get('name')}")
        print(f"  Versões: {details.get('project', {}).get('versions')}")
    else:
        print(f"  [FALHA] Sem acesso ou projeto não existe.")
