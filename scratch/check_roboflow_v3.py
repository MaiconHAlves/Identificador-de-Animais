import requests

api_key = "Lc4vZgIj0qrwK2lWdtWp"
url = f"https://api.roboflow.com/workspaces?api_key={api_key}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        print("Workspaces:")
        data = response.json()
        for ws in data.get('workspaces', []):
            ws_id = ws.get('id')
            print(f"\nWorkspace: {ws_id}")
            # Listar projetos deste workspace
            proj_url = f"https://api.roboflow.com/{ws_id}?api_key={api_key}"
            proj_resp = requests.get(proj_url)
            if proj_resp.status_code == 200:
                proj_data = proj_resp.json()
                for proj in proj_data.get('projects', []):
                    print(f"  - Projeto: {proj.get('id')} (Versões: {proj.get('versions')})")
    else:
        print(f"Erro: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Erro: {e}")
