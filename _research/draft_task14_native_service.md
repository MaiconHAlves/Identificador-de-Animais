# DRAFT — TASK 14 (Serviço Nativo Kotlin + ORT + IPC)

⚠️ **Esboço, não publicado.** Só publica em `_handoff/TASK.md` se TASK 13 frustrar a meta de 5-10 fps. Veja `_research/2026-05-10_inference_runtimes_android.md` pra contexto da decisão.

---

## Quando ativar

Esta TASK só entra em jogo se o RESULT da TASK 13 vier com:
- FPS de IA percebido < 5 no S24, OU
- Cobertura COCO+BR quebrada por algum motivo, OU
- Falsos positivos pessoa→fauna BR insuportáveis em campo (cross-suppression entre frames falhou demais).

Se TASK 13 entregar 6-10 fps com cobertura intacta, **não ativa** — vai pro backlog Fase 2 pós-AM5.

---

## Objetivo

Migrar inferência YOLOv8 do cv2.dnn 4.5.1 CPU pra **ONNX Runtime Android oficial + NNAPI Execution Provider** rodando dentro de um **Foreground Service Kotlin**. App Python (Kivy) continua como UI; comunicação via **LocalSocket** (IPC).

Esperado: ~30+ fps de inferência usando NPU Exynos 2400.

---

## Pré-condições críticas (gate antes de comprometer 40-60h)

### Pré-condição 1 — Validar exemplo oficial Microsoft

```bash
git clone https://github.com/microsoft/onnxruntime-inference-examples.git
cd onnxruntime-inference-examples/mobile/examples/object_detection/android
```

- Repo vivo? Commits 2025+?
- Exemplo compila com NDK 26b + Android Studio?
- Smoke test no S24: rodar MobileNet ou YOLOv8 official → confirma FPS 30+ com NNAPI?

**Se falhar:** parar. Reportar erro. Não comprometer com refactor.

### Pré-condição 2 — Validar template p4a customization

```bash
# Conferir que o template aceita Java/Kotlin custom
ls .buildozer/android/platform/build-arm64-v8a/dists/animaldetector/src/main/java/
```

p4a suporta `android.add_src` no `buildozer.spec` pra incluir fontes Java/Kotlin customizados. Validar antes que essa pipeline funciona com um Service trivial (sem ORT).

### Pré-condição 3 — Confirmação Maicon

Apresentar plano completo + custo (40-60h) + ganho esperado (30+ fps) + impacto arquitetural (IA migra pra Kotlin). **Maicon precisa autorizar explicitamente** antes da TASK rodar — não é como TASKs anteriores onde a direção já estava acordada.

---

## Arquitetura proposta

```
┌─────────────────────────────────────────────────────┐
│  Kivy App (Python — UI, sensores, fluxo)            │
│  ┌──────────────────────────────────────────────┐   │
│  │ Câmera → frame YUV → BGR (existente)         │   │
│  │ frame → envia via LocalSocket pro Service    │   │
│  │ recebe JSON [bboxes, scores, classes]        │   │
│  │ desenha na tela (ui_tactical.py existente)   │   │
│  └──────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────┘
                 │ LocalSocket (named pipe ANR-safe)
                 ▼
┌─────────────────────────────────────────────────────┐
│  Foreground Service (Kotlin — IA)                   │
│  ┌──────────────────────────────────────────────┐   │
│  │ ORT Android (com.microsoft.onnxruntime)      │   │
│  │ SessionOptions com NNAPIExecutionProvider    │   │
│  │ Carrega coco_*.onnx + fulldet_*.onnx         │   │
│  │ Recebe frame BGR via socket                  │   │
│  │ Faz inferência → bbox + score + class        │   │
│  │ Encoda JSON → envia de volta                 │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Por que LocalSocket e não Binder/AIDL?**
- LocalSocket é IPC mais simples no Android (Unix domain socket).
- Pyjnius consegue criar/conectar facilmente.
- Latência baixa (~1-2 ms por mensagem), suficiente pra frame rate 30 fps.
- Não requer interface IDL gerada.

**Por que Foreground Service e não Activity ou Worker?**
- Service rodando em foreground não é morto pelo sistema mesmo se UI for pausada.
- Permite IA rodar continuamente enquanto câmera está ativa.
- WorkManager é pra tasks discretos, não streaming.

---

## Esboço de passos (sujeito a revisão na publicação real)

### Passo 1 — Validação dos pré-requisitos
Conforme seção "Pré-condições críticas" acima. Reportar resultado. Sem PoC validado, parar.

### Passo 2 — Esboçar `service/AnimalDetectorService.kt`
Skeleton de Foreground Service:
- `onStartCommand`: cria notification, inicia ORT session.
- Loop: aceita conexão LocalSocket, recebe frame bytes, processa, devolve JSON.
- `onDestroy`: libera ORT session.

### Passo 3 — Setup do ORT no Service
```kotlin
val sessionOptions = OrtSession.SessionOptions().apply {
    addNnapi()  // Habilita NNAPIExecutionProvider
    setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
}
val ortEnv = OrtEnvironment.getEnvironment()
val sessionCoco = ortEnv.createSession(modelPathCoco, sessionOptions)
val sessionBr   = ortEnv.createSession(modelPathBr, sessionOptions)
```

Confirmar via log: `NNAPIExecutionProvider` ativo. Se cair pra CPU, investigar particionamento de ops.

### Passo 4 — Protocolo LocalSocket
Formato proposto (binário simples pra evitar overhead JSON em frames grandes):

**Request (Python → Kotlin):**
```
[4 bytes width LE] [4 bytes height LE] [W*H*3 bytes BGR uint8]
```

**Response (Kotlin → Python):**
```
[4 bytes n_detections LE]
para cada detection:
    [4 bytes x_le] [4 bytes y_le] [4 bytes w_le] [4 bytes h_le]
    [4 bytes score_float_le] [4 bytes class_id_le]
```

Ou JSON simples se overhead aceitável (~5 ms parse vs ~0.1 ms binário).

### Passo 5 — Cliente Python no `core/detection_engine.py`
Adicionar novo backend `_load_native_service()` que:
- Inicia o Service via `Intent` + pyjnius.
- Conecta no LocalSocket.
- `_forward_native(frame)`: serializa frame, envia, recebe bboxes, retorna no formato do `detect()`.

Manter cv2.dnn como fallback se Service não responder em 100 ms (timeout).

### Passo 6 — Buildozer.spec
- `android.add_src = src/main/java` — incluir Kotlin sources.
- `android.gradle_dependencies = com.microsoft.onnxruntime:onnxruntime-android:1.17.1`
- Adicionar permission `FOREGROUND_SERVICE` no manifest.
- Bump versão pra 1.0.28 (ou seguinte ao que TASK 13 entregar).

### Passo 7 — Build + smoke test no S24
- APK compila com novas dependencies Gradle?
- Service inicia sem crash?
- Logcat mostra `NNAPIExecutionProvider` ativo?
- IPC LocalSocket conecta?

### Passo 8 — Refactor mobile/main.py
- Substituir `detector.detect_one(frame, idx)` por chamada via Service.
- Manter cache + ia_processing_loop existentes — só muda a fonte de detecções.

### Passo 9 — Validar no S24 + medir FPS

---

## Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| ORT NNAPI particiona ops e cai pra CPU | Média | Alto (perde speedup) | Modelo nodfl + ops conservadores. Aceitar 10-15 fps em vez de 30+. |
| LocalSocket overhead acima do esperado | Baixa | Médio | Protocolo binário direto, não JSON. |
| AAR ORT adiciona 30-50 MB ao APK | Alta | Médio | Aceitar — feature crítica. APK passa de ~90 → ~130 MB. |
| Service não inicia em background no Android 14+ | Média | Alto | Foreground Service correto + notification persistente. Requer `FOREGROUND_SERVICE_CAMERA` no Android 14+. |
| p4a template muda no future e quebra `android.add_src` | Baixa | Alto | Snapshot do `.aab`/`.apk` funcional como rollback. Pinning do p4a branch. |
| Refactor leva mais que 40-60h | Média | Médio | Time-box em 60h. Se não bater meta, voltar pra TASK 13 e re-avaliar. |

---

## O que NÃO fazer na TASK 14

- ❌ NÃO tentar Pyjnius + AAR direto (pesquisa enterrou — JNI overhead).
- ❌ NÃO tentar ctypes + libonnxruntime.so (R&D inédito, sem PoC público).
- ❌ NÃO migrar 100% pra Kotlin (perde Kivy UI que está estável).
- ❌ NÃO compilar ORT do source (Bazel cross-compile NDK = inferno).
- ❌ NÃO mexer no fix YUV de `core/android_camera2.py` (estável desde 1.0.24).

---

## Custo total esperado

- Pré-condição 1 (validar exemplo oficial): 2-4h.
- Pré-condição 2 (template p4a): 1-2h.
- Refactor completo (Passos 2-9): 35-50h.
- Buffer de imprevistos: 5-10h.
- **Total: 40-65h.**

Se Pré-condição 1 falhar (exemplo Microsoft quebrado), a TASK morre e voltamos pra avaliação de ctypes ou aceitar TASK 13 mesmo se < 5 fps.

---

## Vínculo com Fase 2 (re-treino unificado pós-AM5)

Mesmo que TASK 14 não rode agora, a arquitetura proposta deve **guiar o planejamento da Fase 2**. Se o app evoluir pra produção real (não só uso pessoal de Maicon), o Serviço Nativo é praticamente inevitável — toda app Android de visão computacional em escala faz IA fora do Python.

Pre-trabalho útil pra Fase 2 que aproveita esse draft:
- Quando re-exportar modelo v4 unificado, exportar diretamente já em FP16 (NNAPI gosta) + INT8 calibrado.
- Validar que ops do modelo v4 são todos mapeáveis pro NNAPI (sem custom layers).
- Considerar trocar Kivy UI por Compose se Service Nativo entrar em produção (Python só pra script/lógica auxiliar).

Decisão arquitetural fica pendente do resultado de uso real do app pós-Fase 2.
