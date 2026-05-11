# TASK — Identificador de Animais

## Cabeçalho

- **Status:** pronto
- **ID do ciclo:** T014
- **Vinculado a:** decisão arquitetural 10/05/2026 noite (seção "Histórico de mudanças" do `PROJECT_STATE.md`) — migração runtime Android para Serviço Nativo Kotlin + LiteRT/AICore.
- **Branch:** sugerido `feat/t014-litert-poc` (criar antes de mexer no `mobile/`).
- **Criado em:** 2026-05-10

## Tarefa

**PoC pipeline LiteRT.** Converter os 2 ONNX ativos do APK 1.0.27 para `.tflite` INT8 via Post-Training Quantization (PTQ) e validar que o AAR oficial LiteRT carrega esses modelos e roda 1 inferência síncrona em `bus.jpg` num projeto Android Studio mínimo (separado do Buildozer/Kivy — esse PoC é só pra validar a stack nova).

**Não tocar no APK 1.0.27 em produção.** Esta TASK não gera APK e não muda `mobile/main.py`.

## Contexto

- **Por que LiteRT-AICore:** ver decisão arquitetural na seção "Histórico de mudanças" do `PROJECT_STATE.md` (entrada 10/05/2026 noite). Resumo: `cv2.dnn` 4.5.1 está congelado com bug >15 MB, NNAPI deprecado pelo Google em 2024, LiteRT + AICore é a stack oficial Google daqui pra frente.
- **Por que PoC primeiro (PTQ, não QAT):** valida o pipeline LiteRT (export → AAR → inferência) com modelos baratos antes de comprometer 1-2 overnights na 3090 em QAT. Se PTQ basta, re-treino vira oportunidade futura.
- **Por que dois modelos (não single-engine):** `fulldet_yolov8n_nc95_v3` sofreu catastrophic forgetting das classes COCO 0-79 — só as 15 BR (80-94) funcionam (ver "Arquitetura do Modelo" → linha do `fulldet_v3`). PoC mantém o frame skip alternado funcional do 1.0.27, agora no runtime novo. Single-engine real depende de v4 unificado funcional (T017 condicional).
- **Pré-condição do `_research/draft_task14_native_service.md`** continua válida: validar exemplo oficial do AAR (compila + roda) antes de qualquer integração com o app principal. Esta TASK já cumpre essa pré-condição naturalmente (passo 4 abaixo).

## Critério de sucesso (verificável)

- [ ] `coco_yolov8n_nc80_v0_i320_nodfl.tflite` gerado via PTQ INT8 (representative dataset: 100 imagens aleatórias de `D:/datasets/coco/images/val2017/`).
- [ ] `fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite` gerado via PTQ INT8 (representative dataset: 100 imagens de `D:/datasets/br_detection/` para preservar bem o BR).
- [ ] mAP50 desktop pós-PTQ medido para cada modelo via `scripts/` adaptado ou Ultralytics val — perda **<3% vs FP32** (COCO: ≥ ~77% no `coco_v0`; BR no `fulldet_v3` não tem baseline mAP separado, então registrar valor obtido e marcar como "baseline novo").
- [ ] Projeto Android Studio mínimo criado em `_research/litert_poc/` (fora de `mobile/`, fora de Buildozer) — Kotlin, Gradle, dependência `com.google.ai.edge.litert:litert:<latest>` + AICore delegate.
- [ ] AAR LiteRT carrega os 2 `.tflite` no startup do app PoC, sem crash, em emulador OU S24 conectado.
- [ ] 1 inferência síncrona em `bus.jpg` (copiar de `C:\Users\alves\Desktop\Projetos\Identificador de Animais\bus.jpg`) por cada modelo, com detecções coerentes (`coco`: ≥ 3 pessoas + 1 bus; `fulldet_v3`: 0 detecções esperado em `bus.jpg`, sem fauna BR — bate com sanity desktop da T013).
- [ ] Log de inferência registrado: tempo médio por inferência (ms) em CPU vs AICore delegate (se delegate disponível no device de teste).
- [ ] Arquivado em `_research/litert_poc/README.md` (no projeto): comandos exatos de export, métricas mAP, screenshots do app PoC rodando, decisão "passa pra T015" ou "abrir T017 antes".

## Arquivos relevantes

- `scripts/export_unified.py` — referência da pipeline de export ONNX atual (DFL_PREFIXES, etc.).
- `models/coco_yolov8n_nc80_v0_i320_nodfl.onnx` — fonte 1 da conversão.
- `models/fulldet_yolov8n_nc95_v3_m692_i320_nodfl.onnx` — fonte 2 da conversão.
- `datasets/full_detection.yaml` — pra Ultralytics val pós-PTQ.
- `_research/2026-05-10_inference_runtimes_android.md` — contexto histórico das tentativas anteriores (TASKs 10 e 12 bloqueadas).
- `_research/draft_task14_native_service.md` — re-anotar trocando ORT→LiteRT durante esta TASK (apêndice ou nota de cabeçalho).
- `bus.jpg` (raiz) — imagem de sanity check.

## Comandos típicos

```bash
# 1) Export PTQ INT8 via Ultralytics (caminho mais simples se o ONNX for compatível)
# OBS: Ultralytics pode preferir partir do .pt original. Se não tiver .pt para coco_v0, exportar via tflite-converter direto do ONNX:
#   pip install --break-system-packages onnx2tf
#   onnx2tf -i models/coco_yolov8n_nc80_v0_i320_nodfl.onnx -o /tmp/coco_v0_tflite -oiqt -qt per-tensor --representative_dataset_path <rep.npy>
# (validar onnx2tf vs tf.lite.TFLiteConverter durante a execução — escolher o que produzir modelo carregável no AAR)

# 2) Validação mAP desktop pós-PTQ (Ultralytics val em modo .tflite)
yolo val model=<modelo.tflite> data=datasets/full_detection.yaml imgsz=320

# 3) Projeto Android Studio PoC: criar em _research/litert_poc/
# Dependência principal no app/build.gradle.kts:
# implementation("com.google.ai.edge.litert:litert:1.0.0")  # confirmar versão estável em mai/2026
# implementation("com.google.ai.edge.litert:litert-aicore:1.0.0")  # delegate AICore

# 4) Rodar no S24 (ou emulador Pixel 8 com Android 14+):
# adb install app-debug.apk && adb logcat -s LiteRTPoC:*
```

## Restrições

- **NÃO mexer em `mobile/main.py`, `core/detection_engine.py`, ou `buildozer.spec`.** Esta TASK é PoC isolado em `_research/litert_poc/`.
- **NÃO regerar APK 1.0.28 ainda.** Integração com Kivy é trabalho da T015/T016.
- **NÃO re-treinar nada na 3090.** Re-treino é T017 (condicional).
- Se `onnx2tf` ou `tf.lite.TFLiteConverter` quebrar com os ONNX atuais (DFL stripped, opset antigo), registrar o erro completo no `RESULT.md` e parar — não tentar re-export do `.pt` sem alinhar com Cowork (pode disparar T017 mais cedo).
- AAR LiteRT precisa ser confirmado como suportado em mai/2026 (Google publicou versão estável em 2024). Se o pacote correto não estiver disponível, registrar e pedir realinhamento.

## Próxima ação após esta TASK

Se T014 ✅ (mAP loss <3% e AAR roda): Cowork escreve T015 (Skeleton Serviço Nativo Kotlin + IPC Python↔Kotlin).
Se T014 ✗ por mAP: Cowork avalia abrir T017 antes (re-treino QAT INT8).
Se T014 ✗ por AAR/runtime: Cowork reabre o briefing com Maicon — pode exigir mudar de delegate (CPU+GPU em vez de AICore) ou voltar pra ORT-only sem NNAPI.
