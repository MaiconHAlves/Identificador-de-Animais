from roboflow import Roboflow

api_key = "Lc4vZgIj0qrwK2lWdtWp"
rf = Roboflow(api_key=api_key)

ws_id = "maiconhalves"
try:
    print(f"Tentando workspace: {ws_id}")
    ws = rf.workspace(ws_id)
    projects = ws.projects()
    print(f"Sucesso! Projetos em {ws_id}:")
    for p in projects:
        print(f"- {p}")
except Exception as e:
    print(f"Falha: {e}")
