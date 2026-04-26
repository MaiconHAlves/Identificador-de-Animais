from roboflow import Roboflow
import sys

api_key = "Lc4vZgIj0qrwK2lWdtWp"
rf = Roboflow(api_key=api_key)

# Tenta adivinhar o workspace baseado no nome do usuário
possible_workspaces = ["adalt-alves", "alves", "identificador-de-animais"]

for ws_id in possible_workspaces:
    try:
        print(f"Tentando workspace: {ws_id}")
        ws = rf.workspace(ws_id)
        projects = ws.projects()
        print(f"Sucesso! Projetos em {ws_id}:")
        for p in projects:
            print(f"- {p}")
    except Exception as e:
        print(f"Falha: {e}")
