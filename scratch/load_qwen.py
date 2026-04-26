import requests
import json

url = "http://127.0.0.1:11434/api/generate"
payload = {
    "model": "qwen2.5-coder:14b-ctx4k",
    "prompt": "Status check for RTX 3090: Qwen 14B ctx4k reporting for duty.",
    "stream": False
}

try:
    print(f"Enviando requisição para carregar {payload['model']}...")
    response = requests.post(url, json=payload, timeout=60)
    print("Resposta recebida:")
    print(response.json().get('response', 'Sem resposta'))
except Exception as e:
    print(f"Erro ao carregar modelo: {e}")
