"""
T015 — Benchmark de latência IPC Python→Kotlin→Python.

Mede P50/P95/P99 do roundtrip com DetectionService (mock T015).
Roda no dispositivo/emulador via adb shell ou integrado ao main.py.

Uso:
  # Gate emulador (100 frames):
  python mobile/test_ipc_roundtrip.py --frames 100 --target emulator --report /tmp/ipc_emu.json

  # Benchmark final S24 (1000 frames):
  python mobile/test_ipc_roundtrip.py --frames 1000 --target s24 --report /tmp/ipc_s24.json

Critério T015:
  P95 < 10 ms  ✓
  P99 < 30 ms  ✓
  Se P99 > 50 ms → registrar e considerar ASharedMemory fallback antes de T016.
"""

from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np


def run_benchmark(frames: int, report_path: str | None, target: str) -> dict | None:
    from mobile.service_bridge import ServiceBridge

    bridge = ServiceBridge()
    bridge.bind()
    time.sleep(0.5)  # aguarda bind completar

    dummy = np.zeros((320, 320, 3), dtype=np.uint8).tobytes()

    latencies_ms: list[float] = []
    crashes = 0

    print(f"[IPC benchmark] {frames} frames → {target}")
    for i in range(frames):
        t0 = time.perf_counter()
        try:
            bridge.send_frame(dummy, engine_idx=0, width=320, height=320)
        except Exception as exc:
            crashes += 1
            print(f"  [CRASH] frame {i}: {exc}")
            continue
        latencies_ms.append((time.perf_counter() - t0) * 1000)

        if (i + 1) % 100 == 0:
            recent = latencies_ms[-100:]
            print(f"  frame {i+1}/{frames} — P50={np.percentile(recent, 50):.1f}ms P95={np.percentile(recent, 95):.1f}ms")

    bridge.unbind()

    if not latencies_ms:
        print("ERRO: zero frames completados.")
        return None

    arr = np.array(latencies_ms)
    p50, p95, p99 = float(np.percentile(arr, 50)), float(np.percentile(arr, 95)), float(np.percentile(arr, 99))

    ok_p95 = p95 < 10.0
    ok_p99 = p99 < 30.0
    warn_p99 = p99 > 50.0

    print(f"\n{'='*52}")
    print(f"RESULTADO IPC — {target} ({len(latencies_ms)} frames, {crashes} crashes)")
    print(f"  P50 = {p50:.2f} ms")
    print(f"  P95 = {p95:.2f} ms  {'✓' if ok_p95 else '✗ (critério <10ms)'}")
    print(f"  P99 = {p99:.2f} ms  {'✓' if ok_p99 else '✗ (critério <30ms)'}{' ← CONSIDERAR SharedMemory' if warn_p99 else ''}")
    print(f"{'='*52}")

    result = {
        "target": target,
        "frames_ok": len(latencies_ms),
        "crashes": crashes,
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "pass_p95": ok_p95,
        "pass_p99": ok_p99,
        "warn_shared_memory": warn_p99,
    }

    if report_path:
        os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"  Relatório salvo: {report_path}")

    return result


def main() -> None:
    p = argparse.ArgumentParser(description="Benchmark IPC DetectionService")
    p.add_argument("--frames", type=int, default=100)
    p.add_argument("--target", default="emulator", choices=["emulator", "s24", "device"])
    p.add_argument("--report", default=None, metavar="PATH.json")
    args = p.parse_args()
    run_benchmark(args.frames, args.report, args.target)


if __name__ == "__main__":
    main()
