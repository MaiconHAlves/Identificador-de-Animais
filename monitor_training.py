import re, time, os, sys, subprocess, psutil
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

LOG          = r'E:\Projetos\Identificador de Animais\training_full.log'
PROJECT      = r'E:\Projetos\Identificador de Animais'
SCRIPT       = r'E:\Projetos\Identificador de Animais\scripts\train_full.py'
SPEC_FILE    = r'E:\Projetos\Identificador de Animais\scripts\train_full.py'
MAX_RESTARTS = 5
CHECK_INTERVAL = 120   # segundos entre checks

# Parâmetros ajustáveis em caso de crash
_batch   = 64
_workers = 4

train_proc = None   # processo de treino ativo

# ── Erros e suas correções ─────────────────────────────────────────────────
ERRORS_OOM      = ['CUDA out of memory', 'Insufficient memory', 'Failed to allocate',
                   'out of memory', 'torch.OutOfMemoryError']
ERRORS_WORKERS  = ['OSError: [WinError 1455]', 'ERROR_COMMITMENT_LIMIT',
                   'cv2.error', 'WinError 1455']
ERRORS_GENERIC  = ['RuntimeError', 'Killed', 'Segmentation fault',
                   'OSError: [WinError', 'AssertionError', 'Exception']


def log(msg):
    safe = msg.encode('ascii', errors='replace').decode('ascii')
    print(f"[{time.strftime('%H:%M:%S')}] {safe}", flush=True)


def read_log_tail(n=6000):
    if not os.path.exists(LOG):
        return []
    with open(LOG, 'rb') as f:
        f.seek(0, 2); size = f.tell()
        f.seek(max(0, size - n))
        content = f.read().decode('ascii', errors='replace')
    clean = re.sub(r'\x1b\[[0-9;]*[mKABCDHJfsu]', '', content)
    clean = re.sub(r'[^\x20-\x7E\n\r\t]', '?', clean)
    return [l for l in re.sub(r'\r', '\n', clean).split('\n') if l.strip()]


def write_file(name, content):
    with open(os.path.join(PROJECT, name), 'w', encoding='utf-8') as f:
        f.write(content)


def proc_alive(proc):
    if proc is None:
        return False
    try:
        return proc.poll() is None
    except Exception:
        return False


def kill_proc(proc):
    if proc is None:
        return
    try:
        parent = psutil.Process(proc.pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except Exception:
        pass


def patch_train_script(new_batch, new_workers):
    """Edita train_full.py em disco para refletir batch/workers reduzidos."""
    with open(SPEC_FILE, 'r', encoding='utf-8') as f:
        src = f.read()
    src = re.sub(r'(?m)^BATCH\s*=\s*\d+', f'BATCH   = {new_batch}', src)
    src = re.sub(r'(?m)^WORKERS\s*=\s*\d+', f'WORKERS = {new_workers}', src)
    with open(SPEC_FILE, 'w', encoding='utf-8') as f:
        f.write(src)
    log(f"train_full.py atualizado: BATCH={new_batch} WORKERS={new_workers}")


def start_training():
    global train_proc
    log("Iniciando processo de treino...")
    # Abre log em modo append para preservar histórico
    logfile = open(LOG, 'a')
    train_proc = subprocess.Popen(
        [sys.executable, SCRIPT],
        cwd=PROJECT,
        stdout=logfile,
        stderr=subprocess.STDOUT,
    )
    log(f"Treino iniciado (PID {train_proc.pid})")
    log("Aguardando 90s para estabilizar...")
    time.sleep(90)


def handle_crash(error_line):
    global _batch, _workers

    if any(e in error_line for e in ERRORS_OOM):
        _batch = max(8, _batch // 2)
        log(f"OOM detectado — reduzindo batch para {_batch}")
        patch_train_script(_batch, _workers)

    elif any(e in error_line for e in ERRORS_WORKERS):
        _workers = max(0, _workers - 1)
        log(f"Erro de workers/memoria — reduzindo workers para {_workers}")
        patch_train_script(_batch, _workers)

    else:
        log("Erro generico — reiniciando sem alterar parametros")

    kill_proc(train_proc)
    time.sleep(5)
    start_training()


# ── Loop principal ─────────────────────────────────────────────────────────
restarts = 0
log(f"Monitor v2 iniciado. Check a cada {CHECK_INTERVAL}s. Max restarts: {MAX_RESTARTS}")
start_training()

while True:
    try:
        lines = read_log_tail()

        # Status de epoch
        epoch_lines = [l for l in lines if re.search(r'^\s+\d+/50\s', l)]
        current = epoch_lines[-1].strip() if epoch_lines else 'aguardando primeiro epoch...'
        log(f"Epoch: {current}")

        # Processo morreu sem erro detectado no log?
        if not proc_alive(train_proc):
            log("AVISO: processo de treino nao esta ativo!")
            # Verifica se foi conclusao normal
            if any('50/50' in l for l in lines[-60:]) and any('Results saved' in l for l in lines[-30:]):
                log("Conclusao detectada no log — OK")
            elif restarts < MAX_RESTARTS:
                restarts += 1
                log(f"Processo morto sem conclusao. Restart {restarts}/{MAX_RESTARTS}...")
                start_training()
            else:
                write_file('ESCALATE.md',
                    f"# ESCALATE — processo morreu {restarts}x sem conclusao\n\n"
                    f"Ultimo epoch: {current}\n")
                log("ESCALATE.md escrito.")
                break

        # Conclusao normal
        if any('50/50' in l for l in lines[-60:]) and any('Results saved' in l for l in lines[-30:]):
            map_lines = [l for l in lines if re.search(r'^\s+all\s+\d+', l)]
            maps = [float(re.findall(r'(\d+\.\d+)', l)[2]) for l in map_lines
                    if len(re.findall(r'(\d+\.\d+)', l)) >= 3]
            best_map = max(maps) if maps else 0
            write_file('SUCCESS.md',
                f"# SUCCESS — Treinamento Concluido\n\n"
                f"Epoch: 50/50\n"
                f"Melhor mAP50: {best_map:.3f}\n"
                f"best.pt: E:/training/runs/full_detection_v2/weights/best.pt\n")
            log("SUCCESS.md escrito! Treino concluido.")
            break

        # Erro no log
        found_errors = []
        for l in lines[-50:]:
            if any(e in l for e in ERRORS_OOM + ERRORS_WORKERS + ERRORS_GENERIC):
                found_errors.append(l)

        if found_errors:
            err = found_errors[-1]
            log(f"ERRO: {err[:120]}")
            if restarts < MAX_RESTARTS:
                restarts += 1
                log(f"Aplicando correcao e reiniciando ({restarts}/{MAX_RESTARTS})...")
                handle_crash(err)
            else:
                write_file('ESCALATE.md',
                    f"# ESCALATE — {restarts} restarts falharam\n\n"
                    f"Ultimo epoch: {current}\n\n"
                    f"Ultimo erro:\n" + '\n'.join(found_errors[-5:]))
                log("ESCALATE.md escrito. Intervencao necessaria.")
                break

    except Exception as e:
        log(f"Erro no monitor: {e}")

    time.sleep(CHECK_INTERVAL)
