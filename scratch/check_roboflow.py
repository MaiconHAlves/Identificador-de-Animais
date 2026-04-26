from roboflow import Roboflow
import json

api_key = "Lc4vZgIj0qrwK2lWdtWp"
rf = Roboflow(api_key=api_key)

try:
    # Tenta listar os workspaces
    workspaces = rf.list_workspaces()
    print("Workspaces disponíveis:")
    for ws in workspaces:
        print(f"- {ws}")
except Exception as e:
    print(f"Erro ao listar: {e}")
