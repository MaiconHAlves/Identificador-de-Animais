# Identificador de Animais

App Android (Kivy + Buildozer) que detecta animais, humanos e veículos em tempo real via câmera, usando YOLOv8 → ONNX → OpenCV DNN no Android e ONNX Runtime no Desktop.

## Onde olhar primeiro

| Arquivo | Pra quê |
|---------|---------|
| `PROJECT_STATE.md` | **Estado completo do projeto** — modelos ativos, datasets, scripts, problemas resolvidos, histórico de mudanças. Ler primeiro. |
| `WORKFLOW_APK_S24.md` | **Fonte da verdade do plano de execução** — Opções A/B/C, comandos, tabela de status dos APKs. |
| `SUCCESS.md` | Marcos atingidos. |
| `RESOURCES.md` | Links e materiais externos. |
| `_handoff/` | Canal Cowork ↔ Claude Code (Antigravity). `STATE.md` resume o handoff atual; `TASK.md` é o pedido pra quem está no terminal. |

## Estado em 1 frase (08/05/2026)

Treino do **`full_detection_v3_nano`** (YOLOv8n, 95 classes — 80 COCO + 15 espécies BR) rodando overnight em RTX 3090 (~8-12h, 150 epochs). Próxima ação humana: amanhã.

## Stack rápida

- **Linguagem/runtime:** Python 3.12, Kivy, Buildozer, OpenCV 4.13 (desktop) / OpenCV 4.5.1 (Android via cv2.dnn).
- **Treino:** PyTorch + Ultralytics YOLOv8 em RTX 3090 (24 GB VRAM).
- **Inferência:**
  - Android: OpenCV DNN CPU (modelos `nodfl`, < ~15 MB por causa do bug do OpenCV 4.5.1 com modelos maiores).
  - Desktop: ONNX Runtime DirectML/CUDA (com DFL nativo).
- **Build:** WSL → `build_local.sh` → APK arm64-v8a.
- **Dispositivo-alvo:** Samsung S24 Ultra (NPU Exynos 2400 ainda inativa — chega na Opção C).

## Datasets

- `D:/datasets/coco/` — COCO 2017 (80 classes, 118k+5k imgs)
- `D:/datasets/br_detection/` — 15 espécies BR (1.008 imgs, labels v3 via auto-label)
- `D:/datasets/african-wildlife/` — auxiliar
- `datasets/full_detection.yaml` — combina COCO + BR, nc=95

## Convenções deste projeto

- **Decisões importantes** vão pra seção "Histórico de mudanças" do `PROJECT_STATE.md`, com data.
- **Nomes de modelos (padrão a partir de 10/05/2026):** `<escopo>_<arch>_nc<NN>_v<N>_m<MMM>_<flags>.onnx`
  - `escopo` = domínio (`fulldet` = COCO+BR, `wildbr` = só fauna BR, `coco` = só COCO).
  - `arch` = `yolov8n`/`yolov8s`/`yolov8m`.
  - `nc<NN>` = nº de classes (ex: `nc95`).
  - `v<N>` = versão da run.
  - `m<MMM>` = mAP50 × 1000 (ex: `m692` = 69.2%). Omitir em modelos legados sem métrica registrada.
  - `flags` (alfabéticas, no fim): `nodfl` (DFL stripped — obrigatório pro OpenCV DNN Android), `cv451` (compat OpenCV 4.5.1), `fp16`, `int8`, `noattn`, `i320`/`i1280` (imgsz não-default).
  - Exemplo: `fulldet_yolov8n_nc95_v3_m692_nodfl.onnx`.
  - Modelos antigos não serão renomeados (rastreabilidade do que já rodou).
- **Treinos longos** vão pra `D:/training/runs/<run-name>/`; pesos em `weights/best.pt` e `last.pt` (resume automático).
- **Mobile (Kivy):** modelo é selecionado em `mobile/main.py` (linha ~52). HUD em `mobile/style.kv` linha 84 já não tem mais valores hardcoded.

## Stack de IAs do Maicon (referência)

- **Claude Code** — codificação principal.
- **Qwen3 Coder local** (`qwen3-coder:8k`) na RTX 3090 via Ollama — `qwen.py` invoca via Open Interpreter.
- **Gemini CLI** — pesquisa e brainstorming.

## Idioma

Sempre responder em **português (pt-BR)**.
