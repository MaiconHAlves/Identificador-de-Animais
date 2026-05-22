"""
Agente Qwen local via Ollama REST API (sem open-interpreter).
RTX 3090 (heavy): qwen3-coder:heavy @ localhost:11435  ← default
RTX 3080 (light): qwen3-coder:light @ localhost:11434  ← flag --light

Uso:
  py -3.12 qwen.py "faça X"               # tarefa direta (RTX 3090 heavy)
  py -3.12 qwen.py --task TASK.md         # tarefa de arquivo
  py -3.12 qwen.py --supervisor "prompt"  # modo supervisor (JSON output)
  py -3.12 qwen.py --light "analise X"    # usa RTX 3080 porta 11434
  py -3.12 qwen.py --light --task TASK.md
"""
import sys
import argparse
import subprocess
import re
from pathlib import Path

import requests

OLLAMA_MAIN  = "http://localhost:11435"
OLLAMA_LIGHT = "http://localhost:11434"
MODEL_MAIN   = "qwen3-coder:heavy"
MODEL_LIGHT  = "qwen3-coder:light"
MODEL_SUP    = "qwen3-coder:heavy"
PROJECT_DIR  = Path.cwd()

SYSTEM_PROMPT = f"""Você é o Agente Qwen executando tarefas de build Android no Windows.
Diretório do projeto: {PROJECT_DIR}

PROTOCOLO:
1. Leia a tarefa antes de agir
2. Execute comandos em blocos de código (```powershell ou ```wsl)
3. Analise resultados e continue até concluir
4. Ao concluir com sucesso: escreva SUCCESS.md usando um bloco powershell
5. Se falhar 3x no mesmo erro: escreva ESCALATE.md com o erro exato e o que foi tentado

FORMATOS DE COMANDOS ACEITOS:
```powershell
Get-Content "arquivo.log" -Tail 20
```

```wsl
ls /root/build-animais/bin/*.apk 2>/dev/null && echo APK_READY || echo no_apk
```

Para escrever arquivo:
```powershell
Set-Content "SUCCESS.md" -Value "APK instalado com sucesso" -Encoding UTF8
```
"""

# ── Execução de comandos ───────────────────────────────────────────────────────

def _run_proc(args_list, timeout=120):
    try:
        r = subprocess.run(
            args_list, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace"
        )
        out = r.stdout.strip()
        err = r.stderr.strip()
        combined = out + ("\nSTDERR: " + err if err else "")
        return combined.strip() or "(sem output)"
    except subprocess.TimeoutExpired:
        return f"TIMEOUT: comando demorou mais de {timeout}s"
    except Exception as e:
        return f"ERRO ao executar: {e}"


def run_powershell(cmd, timeout=120):
    return _run_proc(["powershell", "-NonInteractive", "-Command", cmd], timeout)


def run_wsl(cmd, timeout=120):
    return _run_proc(["wsl", "-d", "Ubuntu-24.04", "-e", "bash", "-c", cmd], timeout)


# ── Parsing de blocos de código ───────────────────────────────────────────────

def extract_blocks(text):
    """Extrai blocos ```lang\ncode``` do texto do modelo."""
    # Remove raciocínio interno (<think>...</think>) do Qwen3
    clean = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    blocks = re.findall(r"```([\w]*)\n(.*?)```", clean, re.DOTALL)
    return [(lang.lower(), code.strip()) for lang, code in blocks if code.strip()], clean


def execute_blocks(blocks):
    """Executa blocos e retorna lista de resultados."""
    results = []
    for lang, code in blocks:
        if lang in ("powershell", "ps", "ps1", "cmd", "batch"):
            print(f"  [PS] {code[:100]}")
            out = run_powershell(code)
        elif lang in ("wsl", "bash", "sh"):
            print(f"  [WSL] {code[:100]}")
            out = run_wsl(code)
        else:
            continue  # python, json, etc — não executar
        # Trunca para preservar contexto (8K)
        out_trunc = out[:800] + ("...[truncado]" if len(out) > 800 else "")
        results.append(f"```{lang}\n{code[:120]}...\n```\nResultado:\n{out_trunc}")
    return results


# ── Ollama API ────────────────────────────────────────────────────────────────

def ollama_chat(base_url, model, messages):
    resp = requests.post(
        f"{base_url}/api/chat",
        json={"model": model, "messages": messages, "stream": False},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


# ── Loop agente ───────────────────────────────────────────────────────────────

def run_agent(base_url, model, task, max_iter=12):
    # Registra arquivos de sinalização que já existem antes de começar
    # para não confundir com arquivos criados por sessões anteriores
    pre_existing = {f for f in ["SUCCESS.md", "ESCALATE.md"] if (PROJECT_DIR / f).exists()}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": task},
    ]

    for i in range(max_iter):
        print(f"\n[Qwen iter {i+1}/{max_iter}] Consultando {model}...")
        try:
            reply = ollama_chat(base_url, model, messages)
        except requests.exceptions.ConnectionError:
            print(f"[ERRO] Ollama não responde em {base_url}. Verifique se está rodando.")
            sys.exit(1)
        except Exception as e:
            print(f"[ERRO] API Ollama: {e}")
            sys.exit(1)

        blocks, clean = extract_blocks(reply)

        # Exibe resposta (sem <think>)
        preview = clean[:600] + ("..." if len(clean) > 600 else "")
        print(f"[Qwen] {preview}")

        messages.append({"role": "assistant", "content": reply})

        if not blocks:
            print("[Qwen] Sem blocos executáveis — encerrando.")
            break

        results = execute_blocks(blocks)
        if not results:
            print("[Qwen] Apenas blocos não executáveis (python/json) — encerrando.")
            break

        feedback = "Resultados da execução:\n\n" + "\n\n---\n\n".join(results)
        print(f"[Feedback] {feedback[:300]}...")
        messages.append({"role": "user", "content": feedback})

        # Encerra apenas se arquivo foi CRIADO NESTA SESSÃO (não pre-existente)
        for sig in ["SUCCESS.md", "ESCALATE.md"]:
            if (PROJECT_DIR / sig).exists() and sig not in pre_existing:
                print(f"[Qwen] {sig} criado nesta sessão — tarefa concluída.")
                break
        else:
            continue
        break

    print("\n[Qwen] Loop encerrado.")


def run_supervisor(base_url, model, prompt):
    messages = [
        {"role": "system", "content": "Responda apenas em JSON válido. Sem markdown, sem explicações."},
        {"role": "user",   "content": prompt},
    ]
    try:
        reply = ollama_chat(base_url, model, messages)
    except Exception as e:
        print(f"[ERRO] {e}")
        sys.exit(1)
    # Strip <think> antes de printar JSON
    clean = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
    print(clean)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Agente Qwen local via Ollama")
    parser.add_argument("prompt", nargs="*", help="Prompt direto")
    parser.add_argument("--task",       help="Arquivo .md com a tarefa")
    parser.add_argument("--supervisor", help="Modo supervisor (retorna JSON)")
    parser.add_argument("--light",      action="store_true",
                        help="Usa RTX 3080 porta 11435 (qwen2.5-coder:7b)")
    args = parser.parse_args()

    base_url = OLLAMA_LIGHT if args.light else OLLAMA_MAIN
    model    = MODEL_LIGHT  if args.light else MODEL_MAIN

    if args.supervisor:
        run_supervisor(base_url, MODEL_SUP, args.supervisor)

    elif args.task:
        task_file = Path(args.task)
        if not task_file.exists():
            print(f"[ERRO] Arquivo não encontrado: {task_file}")
            sys.exit(1)
        print(f"[Qwen] Executando tarefa: {task_file}")
        run_agent(base_url, model, task_file.read_text(encoding="utf-8"))

    elif args.prompt:
        run_agent(base_url, model, " ".join(args.prompt))

    else:
        print("[Qwen] Use: py -3.12 qwen.py --task TASK.md  ou  py -3.12 qwen.py 'tarefa'")
        sys.exit(1)


if __name__ == "__main__":
    main()
