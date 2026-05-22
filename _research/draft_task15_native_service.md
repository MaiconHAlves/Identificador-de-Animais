# Draft T015 — Skeleton Serviço Nativo Kotlin + IPC Python↔Kotlin

> ⚠️ **Status:** RASCUNHO pré-redigido pelo Cowork em 10/05/2026 noite. Será promovido a `_handoff/TASK.md` quando **T014 fechar com sucesso** (mAP loss <3% e AAR LiteRT carrega sem crash). Não executar agora — T014 ainda ativa.
>
> Vinculado a **D09** (`_agent/DECISION_LOG_ANDROID.md`) — migração runtime cv2.dnn → Serviço Nativo Kotlin + LiteRT/AICore.

---

## Cabeçalho previsto

- **Status:** rascunho (vira `pronto` após T014 ✅)
- **ID do ciclo:** T015
- **Vinculado a:** D09 (DECISION_LOG_ANDROID) + entrada "10/05/2026 (noite) — Decisão arquitetural" no PROJECT_STATE
- **Branch:** sugerido `feat/t015-native-service`
- **Dependência:** T014 concluída com PoC LiteRT funcional em `_research/litert_poc/`
- **Criado em:** _(preencher quando promover)_

## Tarefa

Criar o **Serviço Nativo Android (Kotlin)** que vai hospedar a inferência LiteRT no app principal. Esta TASK foca **apenas no esqueleto e na ponte de comunicação Python↔Kotlin** — a inferência real fica pra T016. Critério de sucesso é "Python envia frame, Kotlin recebe e responde com detecção mock, sem crash em 1000 frames seguidos".

## Contexto

- **T014 já validou:** AAR LiteRT carrega e roda inferência síncrona em projeto Android Studio isolado (`_research/litert_poc/`). Pipeline de export ONNX→TFLite INT8 está mapeado.
- **Esta TASK NÃO toca em LiteRT** — só prepara o canal de comunicação. Quando T016 entrar, basta substituir `mock_detect()` por chamada real ao Interpreter.
- **IPC escolhido:** **Messenger + Bound Service** (não AIDL). Razão: payload de frame é grande (≥ 300 KB pra NV21 320×320×1.5), AIDL Parcelable é otimizado pra payloads pequenos. Messenger via Handler+Message com `setData(Bundle)` carregando byte array é mais simples e tem latência comparável pra esse tamanho. Se T015 mostrar latência ruim, T016 pode pivotar pra Shared Memory (ASharedMemory / MemoryFile) — registrar como fallback.
- **Buildozer + p4a:** o serviço Kotlin precisa ser compilado e incluído no APK final via `android.gradle_dependencies` e/ou `android.add_src` no `buildozer.spec`. Investigar receita exata durante a TASK — `_research/draft_task14_native_service.md` (já re-anotado pós-D09) tem a referência inicial.

## Critério de sucesso (verificável)

- [ ] Módulo Gradle Kotlin criado em `mobile/service/` (ou estrutura equivalente que sobreviva ao build Buildozer).
- [ ] `DetectionService.kt` implementado: Bound Service com Messenger, recebe `MSG_INFER` carregando `Bundle{ "frame": ByteArray, "engine_idx": Int, "width": Int, "height": Int }`, responde com `MSG_RESULT` carregando `Bundle{ "detections": ParcelableArray<DetectionDTO> }` mock (3 detecções fixas).
- [ ] Wrapper Python em `mobile/service_bridge.py` usando **Pyjnius** ou **`android.activity`** pra conectar/bind ao serviço; método `send_frame(frame: np.ndarray, engine_idx: int) -> list[Detection]` que faz roundtrip síncrono ou async com callback.
- [ ] APK 1.0.28-rc1 builda (Buildozer aceita o módulo Kotlin) e instala no S24.
- [ ] Teste em runtime: 1000 frames sequenciais via `mobile/main.py` adaptado (rodando junto da pipeline cv2.dnn atual, lado a lado — mock retorna 3 detecções fixas que devem aparecer em paralelo).
- [ ] **Latência IPC medida e logada:** P50, P95, P99 da roundtrip Python→Kotlin→Python. Critério: P95 < 10 ms, P99 < 30 ms. Se P99 > 50 ms, registrar e considerar Shared Memory fallback antes de T016.
- [ ] Zero crash, zero ANR, zero ConnectionLost no Service.
- [ ] `RESULT.md` documenta: caminho do APK, comandos de build, screenshots, métricas IPC, e indica "passa pra T016" ou "pivotar pra Shared Memory".

## Arquivos esperados (a criar)

- `mobile/service/build.gradle.kts` — módulo Kotlin novo
- `mobile/service/src/main/AndroidManifest.xml` — declarar Service exportado `false`
- `mobile/service/src/main/kotlin/com/maicon/animaldetector/DetectionService.kt` — Bound Service principal
- `mobile/service/src/main/kotlin/com/maicon/animaldetector/DetectionDTO.kt` — Parcelable do resultado
- `mobile/service_bridge.py` — wrapper Python (Pyjnius)
- `buildozer.spec` (modificado) — `android.gradle_dependencies` + `android.add_src` apontando pro módulo

## Arquivos a NÃO tocar

- `core/detection_engine.py` — integração real com cv2.dnn fica até T016
- `mobile/main.py` (mudanças mínimas — só pra teste 1000 frames; integração completa no T016)
- `models/*.onnx` — runtime antigo permanece em paralelo até T016 trocar
- Tudo de `_research/litert_poc/` da T014 — referência apenas

## Comandos típicos

```bash
# Verificar receita p4a pra módulo Kotlin extra
cd p4a-recipes && grep -r "gradle_dependencies\|add_src" .

# Build APK 1.0.28-rc1
buildozer android debug 2>&1 | tee build_t015.log

# Teste IPC isolado (antes de buildar APK)
# desenvolver app Android Studio mínimo carregando o módulo service/ e exercitar via instrumented test

# Logcat filtrado
adb logcat -s DetectionService:* PythonBridge:*

# Smoke test 1000 frames
python mobile/test_ipc_roundtrip.py --frames 1000 --report /tmp/ipc_metrics.json
```

## Restrições

- **NÃO mudar runtime de inferência ainda.** cv2.dnn continua sendo o motor real do APK 1.0.28-rc1. O Service apenas existe e responde mock.
- **NÃO publicar como APK estável.** 1.0.28-rc1 é build de validação interna. APK estável vira 1.0.28 no fim da T016.
- **NÃO tocar `_research/litert_poc/`** — preservar PoC isolado.
- **Atenção ao tamanho do payload IPC:** se Messenger Bundle estourar 1 MB (limite do Binder), reduzir resolução do frame antes de enviar (NV21 320×320 cabe folgado em ~150 KB).
- **Lifecycle:** Service não pode segurar wakelock indefinido. Usar Bound (não Started) — quando Activity desbindar, Service termina. Documentar isso no RESULT pra T016 alinhar.

## Próxima ação após T015

Se ✅ (latência IPC dentro do critério): Cowork escreve T016 — substitui mock_detect() por LiteRT + AICore real, integra com pipeline da câmera (substituindo cv2.dnn no caminho de inferência), entrega APK 1.0.28 final.

Se ❌ por latência IPC alta: Cowork avalia pivotar pra **ASharedMemory** (zero-copy via memfd) ou **ContentProvider** com pipe. Registrar trade-off no DECISION_LOG_ANDROID (D10).

Se ❌ por build Buildozer (módulo Kotlin não aceito): pode precisar empacotar o Service como AAR pré-buildado e importar via `android.add_aars`. Custo adicional ~5-10h.

---

## Pesquisa pendente antes de promover esta TASK pra `pronto`

1. **Confirmar versão estável do AAR LiteRT em mai/2026** — `com.google.ai.edge.litert:litert:?` (verificar Maven Central).
2. **Suporte AICore delegate no Exynos 2400 do S24** — Pixel-first; Samsung pode ter limitações. Pesquisa Gemini sugerida.
3. **Receita p4a para módulo Kotlin no Buildozer** — testar em sandbox isolado antes de comprometer com a TASK real.

(Itens 1 e 2 também são objeções pendentes do D09 — resolvidos durante T014. Item 3 é específico de T015.)
