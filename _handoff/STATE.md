# STATE — 2026-05-13 (T015.b.ipc Sessão 3: FAIL — crash JNI DeleteRef novo; aguarda decisão Maicon)

## Última sincronização

- **T015 fase 2 (D10 / AAR pré-compilado) executada** entre 11/05 noite e 12/05 manhã pelo Claude Code:
  - Módulo `:detectionservice` criado em `_research/litert_poc/`, AAR `detection_service.aar` gerado.
  - APK `1.0.28-rc2` (universal arm64-v8a + x86_64, ~155 MB) builda e instala em AVD `google_apis` API 29 x86_64.
  - App Kivy/Python/SDL2 sobe, Service Kotlin carrega — **smoke qualitativo PASS** (PID 8612, 245 MB, 35+ min vivo).
- **Bloqueio quantitativo descoberto:** `test_ipc_roundtrip.py` via `adb shell` não funciona — Pyjnius precisa do JVM context do processo Android, não do shell separado. Resultado: `frames_success = 0`.
- **Decisão Maicon (12/05):** **não pular pro S24** — respeitar política rigorosa "emulador antes do S24". Criar **T015.b.ipc**.
- **TASK.md atual: T015.b.ipc** — auto-trigger via flag file `/sdcard/run_ipc_test` + thread interno em `main.py`. APK alvo `1.0.28-rc3`. Conteúdo completo em `_handoff/TASK.md`.
- Política emulador→S24 **mantida e endurecida** — virou regra explícita do projeto.
- T014 fase 1 + T014.b ✅ desde 11/05 (não regrediu).

## Estado atual do app

**APK em produção:** `bin/animaldetector-1.0.27-arm64-v8a-debug.apk` (94 MB) — permanece em campo até T016 entregar 1.0.28.
- Runtime: `cv2.dnn` 4.5.1 CPU ARM, ~9 fps real, COCO 80 + BR 15 via frame skip alternado.
- Rollback: APK 1.0.26 permanece em `bin/`.

**APKs de validação T015 (não substituem 1.0.27):**
- `1.0.28-rc1` (T015 fase 1) — bloqueado no build, Kotlin não suportado no template p4a.
- `1.0.28-rc2` (T015 fase 2 / D10) — smoke qualitativo PASS no emulador, gate quantitativo SKIP.
- `1.0.28-rc3` (T015.b.ipc, alvo) — adicionar auto-trigger pra destravar quantitativo.

## TASK ativa: T015.b.ipc Sessão 3 — FAIL / aguarda Maicon

**Resultado da Sessão 3 (13/05/2026):**
- APK `1.0.284` (equivalente rc4) buildado com GREEN LIGHT.
- Deploy + flag `ipc_bench.flag` + app start: OK.
- IPC trigger disparou, `onBind` OK, benchmark iniciou 100 frames.
- **Crash 1s depois:** `CheckJNI::DeleteRef` em `jnius.so` (thread benchmark, tid=10544). SIGABRT.
- Nota: `version = 1.0.28-rc4` rejeitado pelo p4a (ValueError); usando `1.0.284`.
- Detalhes completos + opções em `_handoff/RESULT.md` seção "Sessão 3".

**Decisão pendente:** Fix #4 (Opções A/B/C/D em RESULT.md). Recomendação: testar no S24 primeiro (CheckJNI inativo em release) antes de refatorar IPC.

## TASK histórica: T015.b.ipc — Auto-trigger IPC Benchmark no Emulador

Embutir bloco condicional em `mobile/main.py` que dispara `test_ipc_roundtrip.py` (100 frames) dentro do processo do app quando a flag `/sdcard/run_ipc_test` existir. Sem flag, app abre normal. Thread remove a flag ao terminar como sinal de conclusão.

Critério emulador (relaxado por virtualization overhead):
- `frames_success ≥ 95` de 100
- P95 < 30 ms (preferível < 20)
- P99 < 80 ms (preferível < 50)
- Zero `FATAL EXCEPTION` no logcat, zero ANR

Critério S24 (a aplicar após gate emulador fechar):
- P95 < 10 ms, P99 < 30 ms, 1000 frames

Tech debt rastreável: comentário no bloco de `main.py` "T015.b.ipc — REMOVER em produção final", vira cleanup item pra T016.

## Backlog sequenciado (após T015.b.ipc)

| Item | Trigger | Custo |
|------|---------|-------|
| **S24 benchmark (T015 fase 3)** | T015.b.ipc PASS emulador | 1-2h (instalar + medir) |
| **T016 — Pipeline completo + APK 1.0.28** (substitui mock por LiteRT real + integra na câmera + remove tech debt do auto-trigger) | T015 fase 3 ✅ no S24 | ~10-20h |
| **D11 — pivot Shared Memory IPC** *(condicional)* | T015 S24 P99 > 50 ms | decisão arquitetural |
| **T017 — Re-treino v4 + QAT INT8** *(condicional)* | T016 mostrar cobertura insuficiente OU 30+ fps abrir espaço pra yolov8s | 1-2 overnights 3090 |
| Calibração de `conf_threshold` | Maicon perceber falsos positivos/negativos no 1.0.27 enquanto T015→T016 não entregam | 15-30 min |
| Migração `C:\datasets` + `C:\training` → `E:\` | NVMe Samsung 970 Pro chega 18/05 | 30-60 min + SMART check |

## Histórico recente

- **TASK 14 (PoC LiteRT + AICore, fase 1 + T014.b): concluída ✅** — 11/05/2026.
- **TASK 15 fase 1 (try direto Kotlin via add_src):** bloqueada — p4a/SDL2 não tem Kotlin plugin no template. Resolveu virando D10 (AAR).
- **TASK 15 fase 2 (D10/AAR):** smoke qualitativo PASS no emulador, gate quantitativo SKIP por Pyjnius/JVM context. Resolveu virando T015.b.ipc.
- **TASK 13 (frame skip i320 → APK 1.0.27):** concluída ✅, app em produção.

## Documentos de referência

- `PROJECT_STATE.md` — histórico completo. Última entrada: 12/05/2026 (T015.b smoke + T015.b.ipc).
- `_research/2026-05-10_inference_runtimes_android.md` — pesquisa do ecossistema Python-on-Android.
- `_research/litert_poc/` — projeto Android Studio Kotlin com módulos `:app` (PoC LiteRT da T014) e `:detectionservice` (Service da T015 fase 2). **Não tocar no `:app`** durante T015.b.ipc.
- `_handoff/RESULT.md` — contém T014 (fase 1 + T014.b), T015 fase 1 (bloqueio), e T015.b (smoke + SKIP quantitativo). T015.b.ipc adicionará nova seção.

## Lições registradas

- **PTQ INT8 precisa de ≥300 imgs representativas na calibração** (T014).
- **fulldet_v3 só detecta classes BR 80-94** (catastrophic forgetting), validação mAP só sobre o subset BR.
- **Kotlin não compila direto no p4a/SDL2 template** — sempre via AAR pré-compilado (D10).
- **Pyjnius (testes Android) precisa de JVM context do processo do app** — não roda via `adb shell` separado. Padrão de solução: flag file em `/sdcard/` + thread interno disparado pelo `main.py`. Detalhes na entrada 12/05/2026 do PROJECT_STATE.

## Delta desde último update

- T015 fase 2 (D10) executada e validada parcialmente: smoke qualitativo PASS, quantitativo SKIP.
- Bloqueio Pyjnius/JVM context identificado e diagnosticado.
- T015.b.ipc desenhada e promovida pra `_handoff/TASK.md` (auto-trigger via flag file).
- APKs intermediários `1.0.28-rc1` (falha build) e `1.0.28-rc2` (smoke PASS) registrados como histórico.
- D10 (AAR pré-compilado) consolidado como decisão arquitetural definitiva da T015.
- Política emulador→S24 reafirmada: Maicon escolheu T015.b.ipc em vez de pular pro S24.
