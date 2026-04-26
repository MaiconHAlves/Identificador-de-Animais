import requests
import json

api_key = "Lc4vZgIj0qrwK2lWdtWp"

def search_roboflow(query):
    # Endpoint de busca do Roboflow Universe via API
    url = f"https://api.roboflow.com/universe/search?q={query}&api_key={api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.status_code, "text": response.text}
    except Exception as e:
        return {"error": str(e)}

queries = ["brazilian wildlife", "thermal animal detection", "infrared wildlife"]

for q in queries:
    print(f"\n--- Buscando por: {q} ---")
    result = search_roboflow(q)
    if "error" in result:
        print(f"Erro: {result['error']} - {result.get('text', '')}")
    else:
        # Listar os top 3 projetos encontrados
        projects = result.get('projects', [])
        for p in projects[:3]:
            print(f"Projeto: {p.get('name')}")
            print(f"ID: {p.get('id')}")
            print(f"Workspace: {p.get('workspace')}")
            print(f"Versões: {p.get('versions')}")
            print("-" * 20)
