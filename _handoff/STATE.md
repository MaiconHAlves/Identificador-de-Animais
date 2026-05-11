# STATE — 2026-05-10 (noite — T014 ATIVA: migração pra LiteRT/AICore)

## Última sincronização
- Cowork ↔ Claude Code: **T014 (PoC LiteRT + AICore) escrita e marcada `Status: pronto`** após decisão arquitetural 10/05/2026 noite (modo automático). Detalhes em `_handoff/TASK.md`. Backlog T014→T017 sequenciado no `PROJECT_STATE.md` (histórico).
- Ciclo anterior T013 concluído ✅ e arquivado em `_handoff/historico/T013_2026-05-10_frame-skip-i320-apk-1.0.27.md`.

## Estado atual do app

**APK em produção:** `bin/animaldetector-1.0.27-arm64-v8a-debug.apk` (94 MB) — permanece em campo até T016 entregar 1.0.28.
- IA: ~9 fps real, COCO 80 classes + fauna BR 15 classes ativas via frame skip alternado.
- Cada modelo atualiza a ~4.5 Hz (frame par → COCO, ímpar → BR, união como `last_detections`).
- Câmera: ~28-30 fps mantido.
- Runtime atual: `cv2.dnn` 4.5.1 CPU ARM — **em vias de ser substituído por LiteRT + AICore** (decisão 10/05 noite).
- Rollback: APK 1.0.26 permanece em `bin/`.

## TASK ativa: T014 — PoC LiteRT + AICore

Converter os 2 ONNX ativos (`coco_v0_i320` + `fulldet_v3_i320`) → `.tflite` INT8 (PTQ) e validar AAR LiteRT mínimo em projeto Android Studio (isolado de `mobile/`). **Não toca no APK 1.0.27.** Critério: mAP loss <3% e AAR carrega+roda sem crash em `bus.jpg`. Custo estimado ~6-10h. Conteúdo completo em `_handoff/TASK.md`.

## TASK 13 — concluída ✅ (10/05/2026)

| Item | Resultado |
|------|-----------|
| Re-export i320 nodfl (COCO + BR) | ✅ 2 modelos, ~12-13 MB cada |
| Bug DFL_PREFIXES no export_unified.py | ✅ Corrigido — ampliado 19→24 nós |
| Refactor `core/detection_engine.py` (`detect_one` + extraído `_process_single_engine`) | ✅ Paridade desktop OK |
| Refactor `mobile/main.py` `ia_processing_loop` com cache + alternância | ✅ |
| APK 1.0.27 build (26 min, primeira build com numpy do zero) | ✅ 94 MB |
| Validação S24 (logcat: 2 engines, alternância detectada, 9 fps medidos) | ✅ |
| Validação visual em campo Maicon (animais + pessoas) | ✅ |

## Backlog sequenciado (após T014)

| Item | Trigger | Custo |
|------|---------|-------|
| **T015 — Skeleton Serviço Nativo Kotlin + IPC** | T014 ✅ (mAP loss <3% e AAR roda) | ~15-25h |
| **T016 — Pipeline completo + APK 1.0.28** | T015 ✅ | ~10-20h |
| **T017 — Re-treino v4 + QAT INT8** *(condicional)* | T016 mostrar cobertura insuficiente OU 30+ fps abrir espaço pra yolov8s | 1-2 overnights 3090 |
| Calibração de `conf_threshold` | Maicon perceber falsos positivos/negativos no 1.0.27 enquanto T014→T016 não entregam | 15-30 min |
| Migração `C:\datasets` + `C:\training` → `E:\` | NVMe Samsung 970 Pro chega 18/05 | 30-60 min + SMART check |

## Histórico recente

- TASK 13 (frame skip alternado + i320 → APK 1.0.27): **concluída ✅** — 9 fps reais, app em produção.
- TASK 12 (TFLite+NNAPI): bloqueada — `tflite-runtime` descontinuado pelo Google em 2024.
- TASK 10 (onnxruntime+NNAPI): bloqueada — sem wheel Android no PyPI.
- TASK 9 (aceleração via imgsz 416): parcial — APK 1.0.26 estável a ~1.67 fps.
- TASK 8 (reorg filesystem + fix YUV + APK 1.0.24): concluída ✅.
- TASK 7B (diagnóstico tela branca): concluída ✅.
- TASK 6 (APK 1.0.23 dual model): concluída ✅.

## Documentos de referência

- `PROJECT_STATE.md` — estado completo + histórico consolidado das decisões.
- `_research/2026-05-10_inference_runtimes_android.md` — pesquisa profunda do ecossistema Python-on-Android pra ML (2 rodadas Gemini + análise crítica Cowork). Consultar antes de qualquer movimento futuro envolvendo NNAPI/GPU.
- `_research/draft_task14_native_service.md` — TASK 14 pré-escrita (Foreground Service Kotlin + ORT NNAPI), arquivada como backlog Fase 2.


## Delta desde último update

- T013 arquivado em `historico/T013_2026-05-10_frame-skip-i320-apk-1.0.27.md`.
