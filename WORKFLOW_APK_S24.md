# Workflow: APKs para Samsung S24

_Criado: 2026-05-06_

## Contexto

O app usa OpenCV DNN no Android (S24 e emulador). Descoberto que:
- YOLOv8s (44MB) → scores=0 no OpenCV 4.5.1 (bug silencioso da lib)
- YOLOv8n (12MB) → funciona corretamente no OpenCV 4.5.1
- S24 tem NPU Exynos 2400 mas não está sendo usado (OpenCV DNN só usa CPU)

---

## Opção A — Funcional Imediato (1 classe)

**Modelo:** `animal_wild_br_nodfl.onnx` (12MB, YOLOv8n, 1 classe: fauna BR)  
**Backend:** OpenCV DNN CPU  
**Status:** ✅ Testado e funcional no emulador (CAM:21 | IA:6 FPS | hits=4-10)

### Passos
1. `mobile/main.py` → modelo `animal_wild_br_nodfl.onnx` ✅ (já editado)
2. Rodar `build_local.sh` → `bin/animaldetector-*-arm64-v8a-debug.apk`
3. Instalar no S24 via ADB e testar

### Limitação
Detecta apenas `animal_wild` (fauna BR). Não detecta pessoas, carros, etc.

---

## Opção B — 95 Classes no Android (YOLOv8n fine-tune)

**Modelo:** `full_detection_v3_nano_nodfl.onnx` (YOLOv8n fine-tunado nas mesmas 95 classes)
**Backend:** OpenCV DNN CPU
**Status:** 🛠️ Script pronto, treino pendente
**Pré-requisito:** Opção A confirmada funcional no S24

### IMPORTANTE: não dá pra "re-exportar"
YOLOv8s e YOLOv8n são arquiteturas diferentes (canais distintos nas camadas C2f).
Não dá pra carregar pesos do `s` e exportar como `n`. **A solução é fine-tune do YOLOv8n
com o mesmo dataset que treinou o v2 (`datasets/full_detection.yaml`).**

### Passos

1. **Confirmar dataset disponível**
   - `D:/datasets/coco/train2017` (~118k imgs) e `val2017` (~5k imgs)
   - `datasets/br_detection/images/{train,val}` (15 espécies BR)
   - `datasets/full_detection.yaml` aponta corretamente

2. **(NOVO) Pré-passo crítico — corrigir labels BR antes de treinar:**

   Histórico:
   - 1ª tentativa (`auto_label_br.py` usando v2 como teacher): ❌ 4.5% de auto-labeled.
     Razão: o v2 foi treinado com bbox degenerada (imagem inteira), perdeu capacidade
     de localização. Ele classifica mas não gera bboxes plausíveis.
   - 2ª tentativa (`auto_label_br_v2.py` usando YOLOv8x COCO como teacher genérico):
     usa modelo COCO grande pra detectar QUALQUER objeto/animal genérico, depois
     re-rotula com a classe BR esperada (vinda do filename).

   ```bash
   py -3.12 scripts/auto_label_br_v2.py
   ```
   - Teacher: `yolov8x.pt` (download automático ~130MB) — não usa o v2
   - Conf threshold baixo (0.05) sem filtrar classe
   - 3 tiers de preferência: animais COCO > outras classes > pessoa (último recurso)
   - Filtros: área 1%-95% (descarta "imagem inteira" e ruído)
   - Output em `datasets/br_detection/labels_v3/`
   - Imagens problemáticas vão pra `_review_manual.txt`
   - Após review: `mv datasets/br_detection/labels datasets/br_detection/labels_old && mv datasets/br_detection/labels_v3 datasets/br_detection/labels`

3. **Rodar o treino do nano (script já criado, modo qualidade)**
   ```bash
   py -3.12 scripts/train_full_nano.py
   ```
   - Base: `yolov8n.pt` (download automático ~6MB)
   - Output: `D:/training/runs/full_detection_v3_nano/weights/best.pt`
   - **Tempo estimado RTX 3090: ~8-12h** (150 epochs, batch=128, sem freeze, augmentation forte)
   - VRAM: ~6GB (cabe folgado)
   - Resume automático se cair no meio (procura `last.pt` no path)
   - Filosofia: priorizar resultado sobre tempo de treino

4. **Exportar para ONNX nodfl**
   ```bash
   py -3.12 scripts/export_unified.py \
     --weights D:/training/runs/full_detection_v3_nano/weights/best.pt \
     --out models/full_detection_v3_nano_nodfl.onnx
   ```
   Tamanho esperado do ONNX final: ~12-15 MB (compatível com OpenCV DNN).

5. **Atualizar `mobile/main.py` linha 51**
   ```python
   self.detector = DetectionEngine(model_paths=[
       "models/full_detection_v3_nano_nodfl.onnx",
   ], conf_threshold=0.25)
   ```

6. **Adicionar ao `source.exclude_patterns` do buildozer.spec o modelo antigo** (se ainda estiver lá)
   - Já tem: `models/full_detection_v2_nodfl.onnx` etc.
   - Garantir que `full_detection_v3_nano_nodfl.onnx` NÃO está no exclude

7. **Rebuild APK + testar no S24**
   ```bash
   sudo bash build_local.sh
   ```

### Por que YOLOv8n funciona e YOLOv8s não no Android
OpenCV 4.5.1 (usado pelo `cv2.dnn` no Android) tem bug com modelos > ~15-40 MB:
retorna zeros na head de scores. YOLOv8n (~12MB) usa menos canais nas camadas C2f
e fica abaixo do limite. Foi confirmado experimentalmente: `yolov8n_nodfl.onnx` (12MB,
80 classes) funciona; `full_detection_v2_nodfl_cv451_noattn.onnx` (43MB, 95 classes,
arquitetura `s`) carrega mas retorna `max_score=0.000` em todos os frames.

ONNX Runtime no Android está bloqueado por outro motivo (`libdl.so.2 not found` em
Android 16) — ver Opção C.

---

## Opção C — GPU/NPU via onnxruntime-android

**Modelo:** `full_detection_v2_nodfl.onnx` (95 classes, YOLOv8s)  
**Backend:** onnxruntime com NNAPI Execution Provider  
**Pré-requisito:** Opção B funcionando no S24

### Passos
1. Mudar `detection_engine.py`:
   ```python
   # Remover: if self._android: _load_opencv
   # Sempre tentar onnxruntime primeiro:
   self._load_ort(model_paths)  # já tem fallback para opencv
   ```
2. Criar recipe p4a para onnxruntime-android:
   - Verificar `p4a-recipes/` — adicionar recipe onnxruntime
   - onnxruntime tem builds pré-compilados para arm64: `onnxruntime-android`
   - Alternativa: usar `onnxruntime` wheel para Android via pip
3. Adicionar ao `buildozer.spec`:
   ```
   requirements = python3, kivy, opencv, numpy, pillow, onnxruntime
   ```
4. Para NNAPI (NPU do S24):
   ```python
   providers = ['NNAPIExecutionProvider', 'CPUExecutionProvider']
   ```
5. Build APK + testar no S24

### Benefício
- Usa NPU Exynos 2400 do S24
- 95 classes (COCO + fauna BR)
- Velocidade esperada: >15 FPS IA

---

## Estado Atual

| APK | Modelo | Classes | Android Backend | Status |
|-----|--------|---------|-----------------|--------|
| emulador-x86_64 | animal_wild_br_nodfl.onnx | 1 | OpenCV DNN | ✅ Funcional |
| **arm64-A** (a buildar) | animal_wild_br_nodfl.onnx | 1 | OpenCV DNN | 🔨 Em build |
| arm64-B | full_detection_v2 re-export nano | 95 | OpenCV DNN | ⏳ Aguardando A |
| arm64-C | full_detection_v2 original | 95 | onnxruntime NNAPI | ⏳ Aguardando B |

---

## Arquivos-chave

| Arquivo | Papel |
|---------|-------|
| `mobile/main.py` | Seleciona modelo (linha ~52) |
| `buildozer.spec` | Requirements e archs |
| `build_local.sh` | Build arm64 para S24 |
| `build_emulator.sh` | Build x86_64 para emulador |
| `scripts/strip_dfl_head.py` | Strip DFL do ONNX exportado |
| `scripts/export_unified.py` | Export .pt → ONNX nodfl |
| `core/detection_engine.py` | Engine de inferência (OpenCV/ORT) |
