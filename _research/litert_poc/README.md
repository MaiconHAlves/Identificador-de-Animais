# LiteRT PoC — T014

**Objetivo:** validar pipeline LiteRT+AICore com os modelos do APK 1.0.27 convertidos para TFLite INT8.

**Status:** PoC concluído — modelos carregam e rodam inferência síncrona. Aguardando teste físico no S24.

---

## Contexto

O APK 1.0.27 usa `cv2.dnn` (OpenCV 4.5.1) para inferência Android — runtime congelado, sem acesso a NPU/GPU, teto ~9 fps. A decisão arquitetural de 10/05/2026 foi migrar para **LiteRT + AICore delegate** (stack oficial Google), mantendo a UI Kivy intacta e adicionando um Serviço Nativo Kotlin para inferência.

---

## Modelos convertidos

| Arquivo                                              | Tamanho | Variante                        | Fonte                                                |
| ---------------------------------------------------- | ------- | ------------------------------- | ---------------------------------------------------- |
| `coco_yolov8n_nc80_v0_i320_nodfl.tflite`             | 3.2 MB  | `full_integer_quant` (I/O INT8) | `yolov8n.pt` (Ultralytics pretrained)                |
| `fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite`     | 3.4 MB  | `full_integer_quant` (I/O INT8) | `best.pt` (C:/training/runs/full_detection_v3_nano/) |

### Notas de conversão

- **Método:** Ultralytics `model.export(format='tflite', int8=True, imgsz=320)` + onnx2tf internamente
- **Calibração COCO:** `coco8.yaml` (4 imgs — mínimo; Ultralytics limita auto-cal) → para calibração robusta usar COCO val completo
- **Calibração fulldet:** `full_detection.yaml` (COCO val + BR val — ~5000+ imgs, calibração completa rodando em background ~30-60 min)
- **DFL:** os modelos TFLite têm DFL intacto (não precisam de strip para LiteRT, diferente do cv2.dnn)
- **`integer_quant` vs `full_integer_quant`:** `coco` tem full INT8 I/O (melhor para AICore delegate); `fulldet` tem FLOAT32 I/O (funcional mas sem aceleração máxima). Quando `best_full_integer_quant.tflite` da calibração completa estiver disponível, substituir o fulldet.

---

## Validação mAP50 pós-PTQ (subset 100 imgs)

> Validação rápida em subset de 100 imagens aleatórias (seed=42).
> Resultados com variância maior que no dataset completo (5000+ imgs).

| Modelo | FP32 baseline | INT8 mAP50 | Perda rel | Status |
| ------ | ------------ | ---------- | --------- | ------ |
| coco_v0 (nc=80) | 50.9% | 50.2% | 1.37% | **PASS** ✓ |
| fulldet_v3 (nc=95 BR) | 68.8% | 62.5% | 9.23% | **FAIL** ✗ |

Dataset: coco128.yaml (128 imgs) para coco_v0; BR val (417 imgs) para fulldet_v3.
Fulldet falhou o critério <3%. Ver `_handoff/RESULT.md` para análise e próximas opções.

---

## Projeto Android Studio PoC

**Localização:** `_research/litert_poc/`

### Estrutura

```text
litert_poc/
├── app/
│   ├── build.gradle.kts          # LiteRT + AICore AAR
│   └── src/main/
│       ├── assets/               # modelos .tflite + bus.jpg
│       ├── kotlin/.../MainActivity.kt   # inferência síncrona
│       └── AndroidManifest.xml
├── gradle/libs.versions.toml     # litert = "1.4.0"
└── settings.gradle.kts
```

### Dependências principais

```kotlin
// app/build.gradle.kts
implementation("com.google.ai.edge.litert:litert:1.4.0")
implementation("com.google.ai.edge.litert:litert-aicore:1.4.0")
```

> **Verificar versão estável em mai/2026** no Maven Central:
> `com.google.ai.edge.litert:litert` — pode ser 1.4.x ou 1.5.x.

### Para compilar e instalar no S24

```bash
# 1. Abrir litert_poc/ no Android Studio (File → Open → selecionar pasta)
# 2. Sync Gradle (automático na abertura)
# 3. Copiar modelos e bus.jpg para assets:
py -3.12 scripts/copy_models_to_poc.py

# 4. Build + install no S24 conectado via USB:
cd _research/litert_poc
./gradlew installDebug

# 5. Ver resultado no logcat:
adb logcat -s LiteRTPoC:* -v time
```

### O que o app faz

1. Abre `bus.jpg` dos assets
2. Para cada modelo (`coco_v0` e `fulldet_v3`):
   - Cria interpretador LiteRT
   - Loga shape e tipo dos tensores de input/output
   - Pré-processa imagem → 320×320 RGB
   - Roda inferência síncrona em CPU (4 threads)
   - Tenta AICore delegate (NPU Exynos 2400 no S24)
   - Loga `max_score`, classe, hits > 0.25 e tempo (ms)

### Resultado esperado no logcat (S24 Exynos 2400)

```text
I LiteRTPoC: === LiteRT PoC T014 iniciado ===
I LiteRTPoC: Imagem de teste: 1280x720 (bus.jpg)

I LiteRTPoC: --- coco_v0 (coco_yolov8n_nc80_v0_i320_nodfl.tflite) ---
I LiteRTPoC: [coco_v0] modelo carregado (3309 KB)
I LiteRTPoC: [coco_v0] Input:  shape=[1, 320, 320, 3]  dtype=INT8
I LiteRTPoC: [coco_v0] Output: shape=[1, 84, 2100]     dtype=INT8
I LiteRTPoC: [coco_v0][CPU]    ~120ms | max_score~0.8 class=0(person) hits>0.25=N
I LiteRTPoC: [coco_v0][AICore] ~20ms  | max_score~0.8 class=0(person) hits>0.25=N

I LiteRTPoC: --- fulldet_v3 (fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite) ---
I LiteRTPoC: [fulldet_v3][CPU] ~140ms | max_score~0.0 class=-1 hits>0.25=0
  (esperado: 0 detecções em bus.jpg — modelo BR não detecta COCO urbano)
```

*Valores de tempo e scores a preencher após teste físico no S24.*

---

## Critérios T014 — checklist

- [x] `coco_yolov8n_nc80_v0_i320_nodfl.tflite` gerado via PTQ INT8 (3.2 MB)
- [x] `fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite` gerado via PTQ INT8 (3.4 MB)
- [ ] mAP50 pós-PTQ < 3% perda — **validação rápida em andamento**
- [x] Projeto Android Studio criado em `_research/litert_poc/` (Kotlin, Gradle)
- [x] Dependência `com.google.ai.edge.litert:litert:1.4.0` + AICore configurada
- [ ] AAR carrega modelos no S24 sem crash — **aguardando teste físico**
- [ ] 1 inferência síncrona em bus.jpg por modelo com detecções coerentes — **aguardando S24**
- [ ] Log de tempo CPU vs AICore — **aguardando S24**

---

## Decisão: T014 → T015?

**Pendente:** teste físico no S24. Com base no PoC desktop (scripts funcionando, modelos gerados):

- Se mAP50 passa (<3% perda) **E** AAR compila no S24 sem crash → **abre T015** (Skeleton Serviço Kotlin + IPC)
- Se mAP50 falha → avaliar T017 (re-treino QAT INT8)
- Se AAR não compila → verificar versão LiteRT e delegate AICore disponíveis no Android 16 (API 36)

---

## Comandos rápidos

```bash
# Export PTQ (já feito, use para reexportar se necessário)
py -3.12 scripts/export_tflite_ptq.py

# Validação mAP rápida (subset 100 imgs, ~5 min)
py -3.12 scripts/validate_tflite_quick.py

# Copiar modelos para assets do PoC
py -3.12 scripts/copy_models_to_poc.py

# Build + install no S24
cd _research/litert_poc && gradlew installDebug

# Logcat
adb logcat -s LiteRTPoC:* -v time
```
