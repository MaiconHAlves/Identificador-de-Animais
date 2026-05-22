"""
gpu_test.py — Diagnostico rapido da RTX 3090 (e RTX 3080).

O que faz:
  1. Lista GPUs e estado idle (PCIe gen, clocks, temp, power).
  2. Roda stress test FP32 matmul 8192x8192 sustentado por ~15s na 3090.
  3. Amostra estado da GPU durante o stress (pra detectar throttling/ASPM).
  4. Mede TFLOPS reais e compara com o esperado (3090 saudavel: 30-35 TFLOPS).
  5. Repete o teste rapido na 3080 pra comparacao.

Uso: py -3.12 gpu_test.py
Saida: gpu_test_report.txt no mesmo diretorio.

Tempo total: ~30-40 segundos.
"""
import subprocess
import time
import sys
import threading
from datetime import datetime

OUTPUT = "gpu_test_report.txt"

# Limpa arquivo
open(OUTPUT, "w", encoding="utf-8").close()

def log(msg):
    with open(OUTPUT, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

def hr():
    log("-" * 70)

log(f"=== GPU stress test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
log("")

# === 1. Lista GPUs e capacidades ===
def query_smi(fields, device=None):
    cmd = ['nvidia-smi', '--query-gpu=' + fields, '--format=csv']
    if device is not None:
        cmd.extend(['-i', str(device)])
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except Exception as e:
        return f"[erro nvidia-smi: {e}]"

log("--- GPUs disponiveis (capacidades maximas) ---")
log(query_smi("index,name,memory.total,pcie.link.gen.max,pcie.link.width.max,driver_version"))

# === 2. Importar PyTorch ===
try:
    import torch
except ImportError:
    log("ERRO: PyTorch nao instalado. Rode: pip install torch")
    sys.exit(1)

if not torch.cuda.is_available():
    log("ERRO: CUDA nao disponivel.")
    sys.exit(1)

log(f"PyTorch: {torch.__version__}")
log(f"CUDA: {torch.version.cuda}")
log(f"GPUs detectadas: {torch.cuda.device_count()}")
for i in range(torch.cuda.device_count()):
    log(f"  [{i}] {torch.cuda.get_device_name(i)}")
log("")


# === 3. Funcao de stress test ===
FIELDS_DYN = ("pcie.link.gen.current,pcie.link.width.current,"
              "clocks.current.sm,clocks.current.memory,"
              "temperature.gpu,power.draw,utilization.gpu,memory.used")

def stress_test(device_idx, label, duration=15.0, size=8192):
    """Roda matmul sustentado e amostra estado da GPU."""
    hr()
    log(f"=== STRESS TEST: {label} (GPU {device_idx}) ===")
    hr()

    name = torch.cuda.get_device_name(device_idx)
    props = torch.cuda.get_device_properties(device_idx)
    vram_gb = props.total_memory / 1e9
    log(f"GPU: {name}")
    log(f"VRAM total: {vram_gb:.1f} GB")
    log(f"Compute capability: {props.major}.{props.minor}")
    log(f"Multi-processors: {props.multi_processor_count}")
    log("")

    log("--- Estado idle (pre-stress) ---")
    log(query_smi(FIELDS_DYN, device_idx))

    device = torch.device(f'cuda:{device_idx}')

    # Aloca tensores
    log(f"Alocando matrizes {size}x{size} FP32 ({4*size*size/1e6:.1f} MB cada)...")
    try:
        a = torch.randn(size, size, device=device, dtype=torch.float32)
        b = torch.randn(size, size, device=device, dtype=torch.float32)
    except Exception as e:
        log(f"ERRO alocando: {e}")
        return None

    # Aquece (CUBLAS init)
    for _ in range(3):
        c = torch.matmul(a, b)
    torch.cuda.synchronize(device)

    # Stress sustentado com sampling em background
    samples = []
    stop_event = threading.Event()

    def sampler():
        while not stop_event.wait(2.5):  # amostra a cada 2.5s
            samples.append(query_smi(FIELDS_DYN, device_idx))

    sampler_thread = threading.Thread(target=sampler, daemon=True)
    sampler_thread.start()

    flops_per_op = 2 * size**3
    log(f"Rodando matmul sustentado por ~{duration}s...")
    start = time.perf_counter()
    ops = 0
    while time.perf_counter() - start < duration:
        c = torch.matmul(a, b)
        torch.cuda.synchronize(device)
        ops += 1
    elapsed = time.perf_counter() - start

    stop_event.set()
    sampler_thread.join(timeout=3)

    tflops = (ops * flops_per_op) / elapsed / 1e12
    log(f"\nOperacoes: {ops}")
    log(f"Tempo:     {elapsed:.2f}s")
    log(f"Throughput: {tflops:.1f} TFLOPS FP32")
    log("")

    log("--- Amostras durante stress ---")
    for i, s in enumerate(samples):
        log(f"[t+{(i+1)*2.5:.1f}s]")
        log(s)

    # Limpa VRAM
    del a, b, c
    torch.cuda.empty_cache()

    return tflops


# === 4. Identifica a 3090 ===
gpu_3090_idx = None
gpu_3080_idx = None
for i in range(torch.cuda.device_count()):
    name = torch.cuda.get_device_name(i)
    if "3090" in name:
        gpu_3090_idx = i
    elif "3080" in name:
        gpu_3080_idx = i

if gpu_3090_idx is None:
    log("AVISO: RTX 3090 nao detectada. Pulando teste.")
else:
    tflops_3090 = stress_test(gpu_3090_idx, "RTX 3090 (principal)", duration=15.0)

if gpu_3080_idx is not None:
    log("")
    tflops_3080 = stress_test(gpu_3080_idx, "RTX 3080 (secundaria)", duration=8.0)

# === 5. Veredicto ===
hr()
log("=== VEREDICTO ===")
hr()

if gpu_3090_idx is not None and tflops_3090 is not None:
    log(f"\nRTX 3090: {tflops_3090:.1f} TFLOPS FP32")
    log("Esperado para RTX 3090 saudavel: 30-35 TFLOPS sustentado")
    if tflops_3090 < 22:
        log(">>> [PROBLEMA] Throughput muito abaixo do esperado.")
        log(">>> Possiveis causas:")
        log(">>>   - PCIe travado em Gen 1 sob carga (verificar amostras acima)")
        log(">>>   - Thermal throttling (verificar temperature.gpu nas amostras)")
        log(">>>   - Power limit baixo (verificar power.draw)")
        log(">>>   - Slot/riser PCIe degradado")
    elif tflops_3090 < 28:
        log(">>> [SUBOTIMO] Throughput no limite inferior, mas funcional.")
        log(">>> Verificar PCIe gen.current e temperature.gpu nas amostras.")
    else:
        log(">>> [OK] RTX 3090 saudavel. Manter. Nao trocar para 3080.")

if gpu_3080_idx is not None and 'tflops_3080' in dir():
    log(f"\nRTX 3080: {tflops_3080:.1f} TFLOPS FP32")
    log("Esperado para RTX 3080 saudavel: 25-30 TFLOPS sustentado")

log("\n=== Fim do teste ===")
log(f"Relatorio salvo em: {OUTPUT}")
