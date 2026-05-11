# Pesquisa: Inferência ML acelerada em Python-on-Android (2024-2026)

**Data:** 2026-05-10
**Contexto:** Após bloqueio das TASKs 10 (onnxruntime) e 12 (tflite-runtime), investigamos rotas viáveis pra atingir 5-10+ fps de inferência YOLOv8 mantendo Python-on-Android (Buildozer + Kivy + p4a).
**Alvo:** Samsung S24 Ultra (NPU Exynos 2400), YOLOv8n FP32 i320/i416.

Este arquivo consolida 2 rodadas de pesquisa profunda do Gemini CLI + análise crítica do Cowork. Referência cruzada permanente — quando o assunto voltar (provavelmente após Fase 2 pós-AM5), começar aqui.

---

## Resumo executivo

**Estado do ecossistema:** nenhum runtime ML mainstream (`onnxruntime`, `onnxruntime-mobile`, `tflite-runtime`, `ai-edge-litert`, `tflite-support`, MediaPipe) tem wheel Python `android_aarch64` no PyPI. Causa: Android usa bionic libc, wheels Linux usam glibc/musl. `tflite-runtime` foi **descontinuado pelo Google em 2024**.

**Caminhos viáveis pra NNAPI/GPU em Python-on-Android (validados):**

| Opção | Esforço real | FPS realista (S24 i320) | Risco | Mantém Python puro? |
|---|---|---|---|---|
| Pyjnius + AAR oficial ORT | 15-25h | **3-8 fps** | Baixo | ✅ | 
| ctypes + libonnxruntime.so | **40-60h** (R&D inédito) | 12-20 fps | Alto | ✅ |
| Serviço Nativo Kotlin + IPC | 40-60h | **30+ fps** | Médio | ⚠️ Só UI (IA em Java) |
| Compilar ORT do source NDK | 60h+ build only | 12-20 fps | Extremo (Bazel/CMake frágil) | ✅ |

**Recomendação Cowork:** se necessário (TASK 13 não bastar), partir pra **Serviço Nativo Kotlin**, não Pyjnius (JNI overhead enterra) nem ctypes (R&D inédito sem PoC público). Mesmo custo de horas (~40-60h), único caminho com 30+ fps comprovado e ORT é stack oficial Microsoft pra Android.

---

## Pesquisa Gemini #1 — recomendação Pyjnius+AAR (DESCARTADA)

### Output original

```
1. Wheels e Runtimes (Status 2024-2026): não existem wheels oficiais aarch64-linux-android
   para onnxruntime ou tflite-runtime no PyPI. Google substituiu TFLite por LiteRT, mas
   suporte Python continua focado em x86_64/arm64 Server/Desktop.

2. Receitas p4a: popcornell/onnxruntime-android-build é referência mas instável.
   Tendência: usar lib nativa, não compilar binding Python.

3. C-API + ctypes: extrair .so do AAR Maven oficial, ctypes em Python pra
   OrtCreateSession. 30+ FPS com NNAPI.

4. Pyjnius + AAR (Official Android Runtimes): android.gradle_dependencies =
   com.microsoft.onnxruntime:onnxruntime-android:latest.release. 25-45 fps com NNAPI.

5. Foreground Service Kotlin: 50+ fps. 60h+ esforço.

6. FPS S24 Ultra:
   - OpenCV DNN CPU: 2-3 fps
   - ORT AAR Pyjnius CPU: 8-12 fps
   - ORT AAR Pyjnius NNAPI: 25-45 fps  [SUPERESTIMADO]
   - MNN ctypes Vulkan: 40+ fps

Recomendação: Opção 2 (Pyjnius + AAR) é sweet spot. Esforço 20h.
```

### Crítica Cowork

- **Superestimou FPS Pyjnius**: 25-45 só com modelo INT8 muito bem calibrado + ops 100% mapeados pra NPU. Real: 10-18 FP32, 15-30 INT8 — e **isso sem contar overhead JNI**.
- **Subestimou esforço Pyjnius**: 20h ignora overhead JNI por chamada (50-200 µs × 5-10 chamadas/frame), conversão BGR→OnnxTensor zero-copy, refactor DetectionEngine. Real: 25-40h.
- **`popcornell/onnxruntime-android-build`**: repo não verificado. Risco de menção genérica do modelo.

Recomendação dele foi rejeitada pelos critérios acima — Cowork sugeriu adiar decisão até TASK 13 fechar.

---

## Pesquisa Gemini #2 — recomendação ctypes (PARCIAL)

### Output original

```
1. Wheels Python Android: confirma que NÃO EXISTEM wheels android_aarch64 oficiais
   no PyPI para Python 3.12. Android usa bionic libc, PyPI usa glibc/musl.

2. Receitas p4a: comunidade Kivy mudou foco. Em vez de receitas para Python C-extensions,
   recomenda C-API via ctypes ou AARs via Pyjnius.

3. C-API + ctypes: estratégia mais robusta para Python puro.
   - Baixar AAR oficial onnxruntime-android do Maven Central
   - Extrair jni/arm64-v8a/libonnxruntime.so
   - android.add_libs_aarch64 = libonnxruntime.so no buildozer.spec
   - ctypes.CDLL('libonnxruntime.so') + mapear OrtCreateEnv, OrtRun, etc.
   - Esforço: 15-25h. FPS: 15-25.

4. Pyjnius + AAR: alta viabilidade, mas com desvantagens críticas de performance.
   Para inferência de imagens (320x320x3 = 307.200 floats), camada JNI iterando sobre
   conversões pode adicionar centenas de ms por frame, anulando ganho NPU.
   PoC: aicelen/Onnx-Kivy-Android (serve para dados pequenos, não vídeo real-time).
   FPS: 3-5. Esforço: 5-10h.

5. Foreground Service Nativo: 30+ fps. 40h+. Mantém Python só para UI.

6. FPS S24 Ultra (Exynos 2400 + NNAPI):
   - OpenCV cv2.dnn CPU: 1.5-2 fps
   - Pyjnius + ONNX AAR: 3-5 fps
   - Python ctypes + ONNX .so: 15-25+ fps  [otimista]
   - Serviço Android Nativo: 30+ fps

Recomendação: Opção 1 (C-API + ctypes). Único caminho viável pra Python-on-Android
puro saltar de 1.67 para 5-10+ fps. Extrair libonnxruntime.so do AAR, empacotar via
android.add_libs_aarch64, escrever wrapper Python ctypes com NNAPI EP.
```

### Crítica Cowork

**Pontos onde a #2 acertou:**
- Enterrou Pyjnius com base no JNI overhead (correto — 307k floats por frame mata o speedup).
- `aicelen/Onnx-Kivy-Android` é POC de classificação, não vídeo real-time (correto).
- Sem wheel Python Android e provavelmente não haverá.
- Foreground Service entrega 30+ fps de verdade.

**Pontos onde a #2 escorregou:**

- **Esforço ctypes 15-25h é otimista demais**. Inclui só extrair .so + buildozer + chamadas básicas. Não inclui:
  - Mapear C-API ORT manualmente (~20-30 funções essenciais com structs aninhados, ponteiros-pra-ponteiros, callbacks). **+15-25h.**
  - Gerenciar lifetime de buffers numpy vs ORT (garantir que GC não recolha array enquanto ORT usa). **+5-10h.**
  - Configurar NNAPI Execution Provider via `OrtSessionOptions` (API menos documentada que core). **+3-6h.**
  - Debugar segfaults sem stack trace utilizável. **+5-15h.**
  - Refactor DetectionEngine + fallbacks. **+4-6h.**
  - **Total realista: 40-60h.**

- **Nenhum PoC público com ctypes + libonnxruntime.so + NNAPI funcionando em Python-on-Android foi citado.** O Gemini não conseguiu provar que alguém fez isso funcionar. Maicon seria pioneiro — isso multiplica risco/esforço.

- **FPS 15-25 ctypes**: topo otimista. YOLOv8 com particionamento NNAPI raramente bate 25. Realista 12-20.

---

## Matriz de decisão final (Cowork)

Substituindo as tabelas anteriores (que tinham premissas erradas das pesquisas):

| Opção | Esforço real | FPS realista | Risco | Recomendação |
|---|---|---|---|---|
| Pyjnius + AAR | 15-25h | 3-8 fps | Baixo | **DESCARTADO** — JNI overhead não atende meta |
| ctypes + libonnxruntime.so | **40-60h** | 12-20 fps | Alto (R&D inédito sem PoC público) | Médio — ROI ruim dado o risco |
| **Serviço Nativo Kotlin + IPC** | 40-60h | **30+ fps** | Médio (template p4a) | **Único caminho comprovado** se TASK 13 frustar |
| Compilar ORT source NDK | 60h+ build | 12-20 fps | Extremo | Descartado |

### Por que Serviço Nativo > ctypes

Mesmo custo de horas, mas:

- **ctypes** é território R&D. Nenhum PoC público. Maicon vira beta tester sozinho. Segfaults sem stack trace. ORT C-API tem 100+ funções a mapear, lifetime de buffers tricky.
- **Serviço Nativo Kotlin** usa ORT Android (stack oficial Microsoft, milhares de apps em produção). Refactor cirúrgico no template p4a. IPC via LocalSocket bem documentado. Dobra de FPS vs ctypes (30+ vs 12-20).
- **Trade-off do Serviço Nativo** ("perde Python puro") é menor do que parece: Kivy permanece pra UI, sensores, fluxo, persistência. Só a inferência migra pra Java/Kotlin, isolada em módulo. App continua "majoritariamente Python".

### Pré-condição obrigatória da TASK 14 (Serviço Nativo)

Antes de comprometer 40-60h:

1. Claude Code abre `microsoft/onnxruntime-inference-examples/android` e valida:
   - Repo vivo, commits recentes (2025+).
   - Exemplo Kotlin **compila** com NDK atual.
   - Exemplo **roda** no S24 (smoke test num modelo MobileNet ou YOLOv8 oficial).
2. Só após PoC validado, partir pro refactor real.

Sem isso, risco de gastar 20h e descobrir que a stack do exemplo está quebrada.

---

## Caminho condicional acordado com Maicon

```
TASK 13 (cv2.dnn + skip alternado + i320) → resultado:

├─ Se ~6-10 fps percebido com COCO+BR mantidos:
│   └─ Encerra fase de aceleração. App entra em produção pra uso de campo.
│       TASK 14 vira backlog "Fase 2 pós-AM5".
│
└─ Se < 5 fps ou cobertura quebrada:
    └─ TASK 14 = Serviço Nativo Kotlin + IPC.
        (NÃO Pyjnius nem ctypes — pesquisa enterrou.)
```

---

## Referências verificáveis (priorizar)

- `microsoft/onnxruntime-inference-examples/android` — stack oficial Microsoft, ponto de partida confirmado pra Serviço Nativo.
- Documentação NNAPI Execution Provider: https://onnxruntime.ai/docs/execution-providers/NNAPI-ExecutionProvider.html
- python-for-android template: https://github.com/kivy/python-for-android/tree/develop/pythonforandroid/bootstraps/sdl2/build/templates

## Referências citadas mas NÃO verificadas (sob suspeita)

- `popcornell/onnxruntime-android-build` (Gemini #1) — não confirmado vivo.
- `aicelen/Onnx-Kivy-Android` (Gemini #2) — provavelmente POC de classificação, não validado pra vídeo.
- "Tutorial de conceito ONNX C-API" (Gemini #2) — link genérico, sem URL específica.

Quando virar TASK 14, Claude Code valida esses repos antes de qualquer comprometimento.

---

## Lição arquitetural pro projeto

Python-on-Android com Buildozer/Kivy é stack viável **enquanto a IA cabe em cv2.dnn CPU**. Quando o gargalo for NNAPI/GPU/NPU, a fronteira do ecossistema é cruzada: ou aceitar particionar (UI Python + IA Java via Serviço Nativo), ou virar R&D pessoal (ctypes + libs nativas). Tentar manter Python puro 100% nesse cenário custa mais horas que o ganho final justifica.

Esta lição entra em peso na decisão da Fase 2 (re-treino unificado pós-AM5 fim 2026): se o app precisar evoluir pra 30+ fps de IA em produção, **provavelmente** o Serviço Nativo Kotlin será inevitável. Vale planejar a arquitetura desde já assumindo essa migração futura como cenário plausível.
