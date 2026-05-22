"""
pre_build_check.py — Protocolo pré-build+emulador
Verifica e ajusta o sistema antes de rodar build Android + teste no emulador.

Uso:
  py -3.12 pre_build_check.py              # verifica + corrige automaticamente
  py -3.12 pre_build_check.py --check-only # só relata, sem corrigir

Chamado automaticamente pelo supervisor_loop.py antes de cada iteração.
"""
import subprocess, sys, time, urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHECK_ONLY = "--check-only" in sys.argv

ADB      = r"C:\Users\alves\AppData\Local\Android\Sdk\platform-tools\adb.exe"
EMU_AVD  = "S24_Ultra_Android16"
EMU_SER  = "emulator-5554"
OLLAMA_MAIN = "http://localhost:11434"
OLLAMA_3080 = "http://localhost:11435"
DISK_MIN_GB = 4.0
VRAM_MIN_MB = 3000   # mínimo livre na 3090 para Qwen rodar
RAM_MIN_GB  = 8.0
GPU_MAX_C   = 80

issues  = []
fixes   = []
blocked = []  # problemas que impedem o build

def ok(msg):   print(f"  [OK] {msg}")
def warn(msg): print(f"  [!]  {msg}"); issues.append(msg)
def fix(msg):  print(f"  [FIX] {msg}"); fixes.append(msg)
def stop(msg): print(f"  [STOP] {msg}"); blocked.append(msg)
def run(cmd, **kw): return subprocess.run(cmd, capture_output=True, text=True, timeout=15, **kw)


# ── GPU ───────────────────────────────────────────────────────────────────────
def check_gpu():
    print("\n[GPU]")
    try:
        r = run(["nvidia-smi",
                 "--query-gpu=index,name,temperature.gpu,power.draw,utilization.gpu,memory.used,memory.free",
                 "--format=csv,noheader"])
        for line in r.stdout.strip().splitlines():
            idx, name, temp, power, util, used, free = [x.strip() for x in line.split(",")]
            temp_i = int(temp); free_mb = int(free.replace(" MiB",""))
            used_mb = int(used.replace(" MiB",""))
            print(f"  GPU{idx} {name}: {temp_i}°C  {power}  {util}util  {used_mb}MiB/{used_mb+free_mb}MiB")
            if temp_i >= GPU_MAX_C:
                stop(f"GPU{idx} temp {temp_i}°C >= {GPU_MAX_C}°C — aguardar resfriamento")
            if idx == "0" and free_mb < VRAM_MIN_MB:
                warn(f"GPU0 VRAM livre {free_mb}MB < {VRAM_MIN_MB}MB — Qwen pode ficar lento")
    except Exception as e:
        warn(f"nvidia-smi falhou: {e}")


# ── OLLAMA 3080 ───────────────────────────────────────────────────────────────
def check_ollama_3080():
    print("\n[OLLAMA 3080 — porta 11435]")
    try:
        urllib.request.urlopen(f"{OLLAMA_3080}/", timeout=3)
        # Está ativo — kill (RTX 3080 deve ficar livre durante build+emulador)
        warn("Ollama 3080 (porta 11435) ativo — não é necessário durante build")
        if not CHECK_ONLY:
            # Matar pela porta 11435 E pelo processo na GPU1 (runner pode sobreviver ao server)
            run(["powershell", "-Command",
                     # por porta
                     "netstat -ano | Select-String '11435' | "
                     "ForEach-Object { ($_ -split '\\s+')[-1] } | "
                     "Select-Object -Unique | "
                     "ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }; "
                     # por GPU1 compute — mata runners Ollama na 3080
                     "$pids = (nvidia-smi -i 1 --query-compute-apps=pid,name --format=csv,noheader "
                     "| Select-String 'ollama' | ForEach-Object { ($_ -split ',')[0].Trim() }); "
                     "$pids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
                     ])
            fix("Ollama 3080 encerrado (porta + runner GPU1) — VRAM 3080 livre")
    except Exception:
        ok("Ollama 3080 offline (correto para build+emulador)")


# ── OLLAMA PRINCIPAL ──────────────────────────────────────────────────────────
def check_ollama_main():
    print("\n[OLLAMA PRINCIPAL — porta 11434]")
    try:
        urllib.request.urlopen(f"{OLLAMA_MAIN}/", timeout=3)
        ok("Ollama principal ativo")
    except Exception:
        warn("Ollama principal offline — Qwen não conseguirá analisar erros")
        if not CHECK_ONLY:
            subprocess.Popen(["C:\\Users\\alves\\start_qwen.bat"],
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
            fix("start_qwen.bat iniciado — aguardando Ollama subir...")
            time.sleep(12)


# ── RAM ───────────────────────────────────────────────────────────────────────
def check_ram():
    print("\n[RAM]")
    import psutil
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    free_gb = vm.available / 1024**3
    swap_gb = sw.used / 1024**3
    print(f"  RAM: {vm.used/1024**3:.1f}/{vm.total/1024**3:.0f}GB  livre={free_gb:.1f}GB  swap={swap_gb:.1f}GB")

    if free_gb < RAM_MIN_GB:
        warn(f"RAM livre {free_gb:.1f}GB < {RAM_MIN_GB}GB")
        if not CHECK_ONLY:
            # Liberar cache do Windows
            run(["powershell", "-Command",
                 "[System.GC]::Collect(); "
                 "[System.Runtime.GCSettings]::LargeObjectHeapCompactionMode = "
                 "[System.Runtime.GCLargeObjectHeapCompactionMode]::CompactOnce; "
                 "[System.GC]::Collect()"])
            fix("GC forçado no .NET runtime para liberar RAM")
    else:
        ok(f"RAM OK — {free_gb:.1f}GB livre")


# ── DISCO ─────────────────────────────────────────────────────────────────────
def check_disk():
    print("\n[DISCO C:]")
    import shutil
    free_gb = shutil.disk_usage("C:\\").free / 1e9
    print(f"  C: livre: {free_gb:.1f}GB")
    if free_gb < DISK_MIN_GB:
        stop(f"Disco C: apenas {free_gb:.1f}GB livre — mínimo {DISK_MIN_GB}GB")
        if not CHECK_ONLY:
            # Limpar APKs antigos (manter só os 2 mais recentes de cada arch)
            bin_dir = Path(r"c:\Users\alves\Desktop\Projetos\Identificador de Animais\bin")
            if bin_dir.exists():
                apks = sorted(bin_dir.glob("*.apk"), key=lambda p: p.stat().st_mtime)
                to_del = apks[:-2]  # manter os 2 mais novos
                freed = 0
                for apk in to_del:
                    freed += apk.stat().st_size
                    apk.unlink()
                fix(f"Apagados {len(to_del)} APKs antigos — +{freed/1024**2:.0f}MB")
    elif free_gb < 6.0:
        warn(f"Disco C: apertado ({free_gb:.1f}GB) — monitorar durante build")
    else:
        ok(f"Disco OK — {free_gb:.1f}GB livre")


# ── EMULADOR ──────────────────────────────────────────────────────────────────
def check_emulator():
    print("\n[EMULADOR]")
    try:
        r = run([ADB, "devices"])
        if EMU_SER in r.stdout:
            # Checar boot
            rb = run([ADB, "-s", EMU_SER, "shell", "getprop", "sys.boot_completed"])
            if rb.stdout.strip() == "1":
                ok(f"Emulador {EMU_SER} ativo e bootado")
            else:
                warn(f"Emulador presente mas ainda bootando")
        else:
            warn("Emulador não detectado")
            if not CHECK_ONLY:
                _start_emulator()
    except Exception as e:
        warn(f"ADB falhou: {e}")

def _start_emulator():
    print(f"  Iniciando {EMU_AVD}...")
    emu_path = r"C:\Users\alves\AppData\Local\Android\Sdk\emulator\emulator.exe"
    subprocess.Popen([emu_path, "-avd", EMU_AVD, "-no-snapshot-save", "-gpu", "swiftshader_indirect",
                      "-camera-back", "webcam0"],
                     creationflags=subprocess.DETACHED_PROCESS)
    fix(f"Emulador {EMU_AVD} iniciado")
    print("  Aguardando boot (máx 120s)...")
    for i in range(24):
        time.sleep(5)
        r = run([ADB, "-s", EMU_SER, "shell", "getprop", "sys.boot_completed"])
        if r.stdout.strip() == "1":
            fix(f"Emulador bootado em {(i+1)*5}s")
            return
    warn("Emulador demorou mais de 120s para bootar")


# ── PROCESSOS CONFLITANTES ────────────────────────────────────────────────────
def check_conflicts():
    print("\n[PROCESSOS CONFLITANTES]")
    import psutil
    heavy = []
    for p in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            name = p.info["name"].lower()
            mem_gb = p.info["memory_info"].rss / 1024**3
            # Processos pesados que não são parte do workflow
            if any(k in name for k in ["bitcoin", "chrome", "firefox", "steam"]) and mem_gb > 0.2:
                heavy.append((p.info["pid"], p.info["name"], mem_gb))
        except Exception:
            pass
    if heavy:
        for pid, name, mem in heavy:
            warn(f"Processo pesado: {name} (PID {pid}) usando {mem:.1f}GB RAM")
    else:
        ok("Sem processos conflitantes")


# ── RELATÓRIO FINAL ───────────────────────────────────────────────────────────
def report():
    print("\n" + "="*60)
    print("RESULTADO PRÉ-BUILD")
    print("="*60)
    if fixes:
        print(f"  Correções aplicadas ({len(fixes)}):")
        for f in fixes: print(f"    • {f}")
    if issues and not blocked:
        print(f"  Avisos ({len(issues)}):")
        for i in issues: print(f"    ⚠ {i}")
    if blocked:
        print(f"  BLOQUEADORES ({len(blocked)}) — NÃO iniciar build:")
        for b in blocked: print(f"    ✗ {b}")
        return False
    print(f"  {'BUILD LIBERADA' if not issues else 'BUILD LIBERADA COM AVISOS'} ✓")
    return True


def main():
    print("="*60)
    print("PRÉ-BUILD CHECK — Identificador de Animais")
    print(f"Modo: {'SOMENTE VERIFICAÇÃO' if CHECK_ONLY else 'VERIFICAR + CORRIGIR'}")
    print("="*60)

    check_gpu()
    check_ollama_3080()
    check_ollama_main()
    check_ram()
    check_disk()
    check_emulator()
    check_conflicts()

    ok = report()
    # Saída com código de retorno: 0=OK, 1=bloqueado
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
