# Estado do Projeto — Identificador de Animais
_Atualizado: 2026-05-10_

---

## Objetivo
App Android que detecta e identifica animais, humanos e veículos em tempo real via câmera.
- Pipeline: câmera → YOLO (detecção) → label na tela
- Plataformas: Android (OpenCV cv2.dnn) + Desktop (ONNX Runtime DirectML/CUDA)

---

## Arquitetura do Modelo

### Atual (em uso) — pós-APK 1.0.27 em 10/05/2026
| Arquivo | Localização | Descrição |
|---------|-------------|-----------|
| `coco_yolov8n_nc80_v0_i320_nodfl.onnx` | `models/` | YOLOv8n, **80 classes COCO** (Ultralytics pré-treinado), **input 320×320 FP32** (~12 MB). **Ativo no APK 1.0.27** — cobre humanos, veículos, objetos urbanos. Roda em frames pares via `detect_one(idx=0)`. |
| `fulldet_yolov8n_nc95_v3_m692_i320_nodfl.onnx` | `models/` | YOLOv8n nominalmente 95 classes, **mas só as 15 fauna BR (80-94) são funcionais** — COCO 0-79 esquecidas (catastrophic forgetting, ver histórico 10/05). **input 320×320 FP32** (~13 MB). **Ativo no APK 1.0.27** — fauna BR sólida (jaguatirica 94%, lobo_guara 94.5%, anta 91% por classe). Roda em frames ímpares via `detect_one(idx=1)`. Será substituído pelo v4 unificado na Fase 2 (pós-AM5). |
| `coco_yolov8n_nc80_v0_i416_nodfl.onnx` | `models/` | YOLOv8n nc=80 i416 FP32 (~12 MB). Versão da TASK 9 (APK 1.0.26). Mantida como rollback. |
| `fulldet_yolov8n_nc95_v3_m692_i416_nodfl.onnx` | `models/` | YOLOv8n nc=95 i416 FP32 (~12 MB). Versão da TASK 9 (APK 1.0.26). Mantida como rollback. |
| `yolov8n_nodfl.onnx` | `models/` | YOLOv8n nc=80 i640 FP32. Baseline original (APK 1.0.24). Mantido como rollback histórico. |
| `fulldet_yolov8n_nc95_v3_m692_nodfl.onnx` | `models/` | YOLOv8n nc=95 i640 FP32 (12.79 MB). Versão original do v3. Mantido como rollback histórico. |
| `*_i416_fp16_nodfl.onnx` / `*_i416_int8_nodfl.onnx` | `models/` | Variantes FP16/INT8 i416 — **bloqueadas por incompatibilidade do cv2.dnn 4.5.1 Android** (ver "Problemas Conhecidos"). Não empacotadas no APK. Referência pra eventual TASK 14 (Serviço Nativo Kotlin + ORT NNAPI). |
| `animal_wild_br_nodfl.onnx` | `models/` | YOLOv8n, 1 classe (fauna BR genérica). Legado da Opção A original. |
| `full_detection_v2_nodfl_cv451_noattn.onnx` | `models/` | YOLOv8s, 95 classes. Bug do OpenCV 4.5.1 com modelos > 15 MB. Referência. |

**APK ativo:** `bin/animaldetector-1.0.27-arm64-v8a-debug.apk` (94 MB) — modelo dual i320 FP32 com **frame skip alternado** (frame par → COCO, ímpar → BR). Validado funcional no S24 em campo (10/05/2026 — animais e pessoas reconhecidos). **IA ~9 fps real** (vs 1.67 do 1.0.26, speedup 5.4×). Câmera ~28-30 fps. Cobertura COCO + BR mantida, cada modelo atualiza a ~4.5 Hz. **Meta de 5-7 fps atingida com folga.** Fase de aceleração fechada. Rollback: APK 1.0.26 permanece em `bin/`.

### Treino concluído — 10/05/2026 (com crash no epoch 136, pesos íntegros)
| Run | Localização | Descrição |
|-----|-------------|-----------|
| `full_detection_v3_nano` | `D:/training/runs/full_detection_v3_nano/` | YOLOv8n, 95 classes (80 COCO + 15 BR). 135/150 epochs concluídos (crash CUDA OOM no epoch 136 por close_mosaic + batch=128). **`best.pt` epoch 128: mAP50 = 69.5%, mAP50-95 = 50.9%.** Plateau desde epoch 127. Cowork escolheu **Opção A** (aceitar best.pt e exportar). TASK 4 ativa pro Claude Code: export ONNX nodfl + atualizar mobile + rebuild APK + limpeza D:. |

### Modelos treinados (histórico)
| Run | Localização | Descrição |
|-----|-------------|-----------|
| `unified_v1-6` | `runs/detect/training/runs/unified_v1-6/weights/best.pt` | 4 classes base. mAP50 ~0.91. **Base para fine-tunes.** |
| `finetune_br_v1` | `runs/detect/training/runs/finetune_br_v1-7/weights/best.pt` | nc=1 (animal_wild only). Descartado — esqueceu outras classes. |
| `finetune_br_v2` | `runs/detect/training/runs/finetune_br_v2/weights/best.pt` | nc=4 + fauna BR. mAP50=0.914. Problema: reconhecia humanos como animal_wild. |

### Modelos ONNX exportados
| Arquivo | Localização | Descrição |
|---------|-------------|-----------|
| `fulldet_yolov8n_nc95_v3_m692_nodfl.onnx` | `models/` | **Ativo (Opção B) — APK 1.0.22.** YOLOv8n nc=95, **12.79 MB**, opset 12, 16 nós DFL removidos. SHA256 `1C2A4595…078974`. |
| `animal_wild_br_nodfl.onnx` | `models/` | YOLOv8n nc=1, ~12 MB. Opção A (legado). |
| `full_detection_v2_nodfl_cv451_noattn.onnx` | `models/` | YOLOv8s nc=95, ~43 MB. Opção C (referência). |
| `yolov8n_nodfl.onnx` | `models/` | YOLOv8n nc=80 (COCO). Baseline. |

**Removidos em 08/05/2026** (limpeza pós-crash, 4 modelos antigos ~140 MB): `unified_animal_detector_*.onnx`, `hybrid_animal_detector_*.onnx`, `global_animal_detector_*.onnx`.

---

## Datasets

### Datasets ativos (pós-limpeza 08/05/2026)
| Dataset | Localização | Conteúdo |
|---------|-------------|---------|
| COCO 2017 | `C:/datasets/coco/` | 118.287 train + 5.000 val. 80 classes. **Migrado pra C: em 08/05; cópia HDD em D: removida em 10/05.** |
| BR Detection | `D:/datasets/br_detection/` | 1.008 imgs BR (15 espécies). Labels v3 sendo gerados via `auto_label_br_v2.py` (teacher: yolov8x.pt). |
| African Wildlife | `D:/datasets/african-wildlife/` | Auxiliar. Movido para `D:` em 08/05. |
| Full Detection YAML | `datasets/full_detection.yaml` | COCO + BR. nc=95. **Atualizado: aponta para `D:/datasets/br_detection/`.** |

### Datasets removidos em 08/05/2026 (limpeza pós-crash, +3.2 GB)
- `datasets/finetune_br/` — substituído pelo pipeline auto-label v2.
- `datasets/brasil_animais/` (iNaturalist) — redundante com br_detection.
- `datasets/roboflow_br/` — redundante.

### 15 Espécies Brasileiras (classes 80-94)
anta, cachorro_do_mato, capivara, cutia, gamba, jacare, jaguatirica, lobo_guara, mao_pelada, quati, seriema, serpente, tamandua_bandeira, tamandua_mirim, tatu

---

## Scripts

| Script | Localização | Uso |
|--------|-------------|-----|
| `prepare_full_dataset.py` | `scripts/` | Converte imgs BR para YOLO + gera full_detection.yaml |
| `train_full.py` | `scripts/` | Treina YOLOv8s com 95 classes (COCO + BR) |
| `finetune_br.py` | `scripts/` | Fine-tune com fauna BR. Atualmente v2, nc=4. |
| `export_unified.py` | `scripts/` | Exporta .pt → ONNX + strip DFL para Android |
| `download_roboflow_br.py` | `scripts/` | Baixa datasets Roboflow BR |
| `test_webcam.py` | raiz | Teste webcam desktop com DetectionEngine |
| `qwen.py` | raiz | Invoca Qwen3-coder local via Open Interpreter |

---

## Core

| Arquivo | Localização | Descrição |
|---------|-------------|-----------|
| `detection_engine.py` | `core/` | Engine de inferência. Android: cv2.dnn CPU. Desktop: ORT DirectML/CUDA. Suporta nodfl (DFL decode Python). |
| `sensor_manager.py` | `core/` | Gerencia sensores Android |
| `android_camera2.py` | `core/` | Camera2 API Android |

---

## Mobile (Android)

| Arquivo | Localização | Descrição |
|---------|-------------|-----------|
| `main.py` | `mobile/` | Entry point Kivy Android |
| `ui_tactical.py` | `mobile/` | UI tática do app |
| `style.kv` | `mobile/` | Layout Kivy. **ATENÇÃO: linha 84 tem HUD hardcoded "30 FPS \| GPU: 3090"** |
| `buildozer.spec` | raiz | Config build Android |

---

## Infraestrutura de IAs

| IA              | Modelo                            | Localização             | Status              |
|-----------------|-----------------------------------|-------------------------|---------------------|
| **Qwen Local**  | `qwen3-coder:heavy` (porta 11435) | RTX 3090 VRAM (~21GB)   | Ativo (Ollama D13)  |
| **Gemini CLI**  | gemini                            | sistema                 | Autenticado         |

- Delegador local: `qwen.py` (via Open Interpreter)

---

## Problemas Conhecidos

| Problema | Status | Solução |
|----------|--------|---------|
| HUD hardcoded ("30 FPS | GPU: 3090") | Resolvido | Substituído por placeholders dinâmicos ("CAM: -- | IA: -- FPS") |
| Fine-tune nc=1/nc=4 com só animal_wild → esquece outras classes | Resolvido | Usar COCO + BR juntos (treino atual) |
| `onnx.checker` crash após strip DFL | Resolvido | try/except no export_unified.py |
| OpenCV headless conflito | Resolvido | Reinstalar `opencv-python` 4.13.0 |
| `cache=True` trava RAM (87%+ RAM) | Resolvido | Remover cache=True do finetune |
| No-detection / Ghosting (Emulator) | Resolvido | Sincronização de resolução 320x320 → 640x640 no DetectionEngine |
| YUV Artifacts (Manchas verdes) | Resolvido | Pipeline vetorizado NumPy no android_camera2.py |
| **`export_unified.py` DFL_PREFIXES insuficiente com `simplify=False`** | Resolvido (TASK 13) | Sem `onnx-simplifier`, grafo mantém nós `Shape`, `Gather`, `Add`, `Mul` referenciando DFL removido → `InvalidArgument` no OnnxRuntime. Fix: ampliar `DFL_PREFIXES` de 19 → 24 nós cobrindo toda a cadeia de decode. Funcionava antes só porque exports anteriores usavam `simplify=True`. |
| **cv2.dnn 4.5.1 Android — INT8 não suportado** | Bloqueado | Op `DynamicQuantizeLinear` ausente no cv2.dnn (4.13 desktop e 4.5.1 Android). Quantização dinâmica via `onnxruntime.quantization.quantize_dynamic` descartada. Reativar só com onnxruntime + NNAPI (Opção C). |
| **cv2.dnn 4.5.1 Android — FP16 não suportado** | Bloqueado | `Unsupported data type: FLOAT16 in getMatFromTensor` (onnx_graph_simplifier.cpp:593). cv2.dnn 4.5.1 não aceita pesos FLOAT16 em nenhum op. Conversão via `onnxconverter_common.float16` descartada. Reativar só com onnxruntime + NNAPI (Opção C — NNAPI tem suporte nativo a FP16, esperado ~10+ fps). |
| **onnxruntime no APK — `libdl.so.2 not found`** | Bloqueado | Bundle import OK mas falha em runtime no Android → cai pra cv2.dnn. Solução: receita p4a personalizada com NDK target correto (Opção C). |
| **IA FPS no S24 (~1.67 fps)** | Aceito como gargalo | Dois YOLOv8n i416 FP32 em série em CPU ARM Cortex-A78 com cv2.dnn. Sem NNAPI/GPU. Speedup adicional só com Opção C. |

---

## Próximos Passos

**APK 1.0.27 (dual i320 FP32 + frame skip alternado) está em produção pra uso de campo.** IA ~9 fps real, COCO + BR ambos detectando, validado pelo Maicon em campo (10/05/2026). Fase de aceleração via `cv2.dnn` fechada.

### TASK ativa: T014 — PoC LiteRT + AICore

Decisão arquitetural 10/05/2026 noite: migrar runtime Android pra **Serviço Nativo Kotlin + LiteRT + AICore** (ver histórico). Backlog **T014→T017** ativo, T014 sendo a primeira (PoC PTQ INT8 + AAR LiteRT mínimo). Pedido escrito em `_handoff/TASK.md` pra Claude Code. APK 1.0.27 permanece em produção até T016 entregar 1.0.28.

### Backlog priorizado

| Item | Quando faz sentido | Custo estimado |
|------|-------------------|----------------|
| **T014 — PoC LiteRT + AICore (ATIVA)** | Imediato — pré-requisito do plano de migração | ~6-10h (sem treino) |
| **T015 — Skeleton Serviço Nativo Kotlin + IPC** | Após T014 ✅ | ~15-25h |
| **T016 — Pipeline completo + APK 1.0.28** | Após T015 ✅ | ~10-20h |
| **T017 — Re-treino v4 unificado + QAT INT8** *(condicional)* | Só se T016 mostrar cobertura insuficiente OU 30+ fps abrir espaço pra yolov8s | 1-2 overnights 3090 |
| **Ajuste de `conf_threshold` (0.25 → ?)** | Se Maicon perceber muitos falsos positivos/negativos em campo no 1.0.27 enquanto T014→T016 não entregam | 15-30 min — empírico |
| **NVMe 970 Pro chega (18/05)** | Migração `C:\datasets\` + `C:\training\` → `E:\` em ~5 min. SMART check obrigatório antes | 30-60 min |

---

## Comandos Úteis

```bash
# Testar webcam desktop
py -3.12 test_webcam.py

# Exportar modelo
py -3.12 scripts/export_unified.py --weights "caminho/best.pt"

# Ver log de treino
tail -f training_full.log

# Verificar GPU
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader

# Delegar tarefa ao Qwen local
py -3.12 qwen.py "tarefa aqui"
```

---

## Hardware real (descoberto em 08/05/2026 via `check_system.ps1` + inventário do Maicon)

### Computação
| Componente | Detalhe |
|------------|---------|
| **CPU** | Intel i7-9700F (8c/8t, sem HT, 3.0 GHz, L3 12 MB) |
| **RAM** | **64 GB DDR4-2400** (4× 16GB Kingston — 2 pentes HyperX `KHX2400C15/16G` + 2 pentes FURY Beast `KF3200C16D4/16GX`; upgrade 12/05/2026 adicionou os 2 últimos). Travado em 2400 porque o sistema sincroniza pela velocidade do mais lento; XMP não ativado. **Bate o teto da Z390** (64 GB max). |
| **Motherboard** | Gigabyte Z390 M GAMING-CF (microATX), BIOS F9 (11/2021). 4 slots DIMM, máx 64 GB. PCIe 3.0 nativo. 2 slots PCIe utilizáveis (x16 CPU + x4 chipset). 2 slots M.2 NVMe (1 livre). |
| **Gabinete** | Mid-tower ATX (marca não identificada). Comporta a placa Z390 microATX atual + 1 GPU dentro; 3080 #1 fica fora via riser cable. Comporta também placa ATX standard (suficiente pra plataforma futura X870E). |

### GPUs (3 unidades disponíveis — total 44 GB VRAM)
| GPU | VRAM | Status físico | Conexão |
|-----|------|---------------|---------|
| **RTX 3090 Zotac Trinity** | 24 GB | Dentro do gabinete | PCIe 3.0 ×16 direto (CPU lanes). Power-locked em 350W (BIOS Zotac, sem upside via Firestorm). |
| **RTX 3080 Zotac #1** | 10 GB | **Fora do gabinete** | PCIe 3.0 ×4 chipset, via riser cable x16-x4. |
| **RTX 3080 Zotac #2** | 10 GB | **Desligada / parada** | Sem slot disponível na Z390 microATX. Reserva pra plataforma nova. |

### Alimentação (dual-PSU sincronizado via Add2PSU)
| PSU | Modelo | Alimenta | Carga atual | Folga |
|-----|--------|----------|-------------|-------|
| **PSU 1** | Corsair RM 1000W | Placa-mãe + CPU + RAM + 3090 | ~500W (50%) | 500W |
| **PSU 2** | Corsair RM 850W | RTX 3080 #1 | ~320W (38%) | 530W |
| **Total** | 1850W disponíveis | — | ~820W | **1030W de folga** |

Sincronização via **Add2PSU adapter** (PSU 2 liga junto com a 1 via sinal Power-On). Migrável pra plataforma nova sem alteração.

### Storage
| Drive | Modelo | Tipo | Capacidade | Livre |
|-------|--------|------|------------|-------|
| **C:** | Kingston A400 SA400M8480G | **SATA SSD entry-level** (TLC, sem DRAM cache, HMB-less) | 446 GB | 158 GB |
| **D:** | MB2000GCWDA | **HDD SATA** | 1.86 TB | **880 GB** (pós-limpeza 10/05/2026 — apagados `D:\datasets\coco` redundante e `D:\wsl_backup\Ubuntu-24.04.tar`, +102 GB) |

**Implicações pro treino atual:**
- Sem NVMe — I/O é o gargalo principal do data loading.
- **RAM 64 GB DDR4-2400 (pós 12/05/2026):** `cache=True` agora viável + `workers=6` margem segura. Restrição anterior de `cache='disk' + 4 workers` (incidente OOM 08/05) **fica suspensa** — re-validar com 1 treino antes de declarar oficial.
- Multi-GPU DDP não vale na plataforma atual (3080 em x4 + 3090 power-locked = comm gargalo).
- 3ª GPU (3080 reserva) não tem onde encaixar — placa microATX só tem 2 slots PCIe utilizáveis.

---

## Próximo upgrade — plano em 2 etapas

### Etapa 1 (atualizada 12/05/2026) — NVMe substituto a pesquisar

**Histórico:** Samsung 970 Pro 2TB comprado 08/05/2026 (R$ 1200 com seguro) — **chegou FALSIFICADO. Devolvido 12/05/2026, seguro acionado.** Não compromete trabalho atual (Kingston A400 SATA SSD + HDD 2TB seguem); apenas adia o ataque ao gargalo de IOPS 4K aleatório do dataloader YOLO.

**Restrição da plataforma atual:** Z390 limita qualquer drive a **PCIe Gen3 ×4 (~3.5 GB/s)** — Gen4/Gen5 são desperdiçados em throughput sequencial. Mas o gargalo é IOPS 4K aleatório, e drives modernos Gen4/Gen5 com DRAM full e controllers melhores ainda ganham em IOPS aleatório mesmo limitados a Gen3.

**Alternativas pesquisadas em 12/05/2026 (WebSearch):**

| Drive | Geração | IOPS 4K leitura | DRAM cache | TBW (2TB) | Comentário |
|-------|---------|----------------|------------|-----------|------------|
| **Samsung 990 Pro 2TB** | Gen4 | **1.400.000** (recorde Gen4) | Full | 1200 | Referência Gen4 em IOPS aleatório. Em produção, anti-falsificação melhor que 970 Pro. |
| **WD Black SN850X 2TB** | Gen4 | 1.200.000 | Full | 1200 | Competidor direto do 990 Pro. Garantia 5 anos. Em produção. |
| **Kingston KC3000 2TB** | Gen4 | 1.000.000 | Full | 1600 | Boa relação custo/benefício. TBW alto. |
| **Samsung 9100 Pro 2TB** | Gen5 | **1.850.000** | Full | 1200 | Top tier 2026, mas desperdiçado na Z390 (Gen5 → Gen3 = corte ~70% throughput). Vale só se planejar usar na AM5 logo. |
| **WD Black SN8100 2TB** | Gen5 | **2.300.000** | Full | 1200 | Atualmente o mais rápido consumer. Mesmo argumento de desperdício na Z390. |

**Recomendação Cowork:** **Samsung 990 Pro 2TB** ou **WD Black SN850X 2TB** — ambos Gen4, ~1.2-1.4M IOPS aleatório, ainda em produção (anti-falsificação mais fácil), preço típico R$ 1.000-1.400. Reutilizáveis na AM5 fim de 2026 sem desperdício (Gen4 cabe em qualquer placa moderna).

**Verificação obrigatória ao receber (mantida do plano original):**
1. Inspecionar etiqueta e selo holográfico do fabricante.
2. Conferir serial no site da Samsung/WD pra autenticidade.
3. Rodar `CrystalDiskInfo` antes de uso pra ler SMART:
   - Total Bytes Written < 50 TB (drive novo).
   - Power-On Hours < 100h.
   - Health % = 100%.
4. Se SMART vier ruim ou serial não bater, acionar seguro/devolução imediato.

**Uso planejado pós-instalação:** mover `D:\datasets\coco` (HDD) + `C:\datasetsr_detection` (SATA SSD) pra novo NVMe (provavelmente `E:`). Cache `.npy` no NVMe. Speedup esperado: **10-25% no tempo de epoch** (gargalo principal hoje é CPU bound, não I/O bruto; com RAM 64GB e `cache=True` o IOPS importa menos pra treinos pequenos).

**Migração de plataforma:** Gen4 segue funcionando em AM5 com slot M.2 Gen4/Gen5 universal. Sem perda.

### Etapa 2 (fim de 2026) — Plataforma AM5 high-end
- **Investimento estimado:** R$ 8-12k (sem GPUs, PSUs, NVMe, gabinete — todos aproveitáveis)
- **Componentes a comprar:**
  - CPU: Ryzen 9 9950X (16c/32t)
  - Placa: X870E top com **3+ slots PCIe utilizáveis** (Asus ProArt X870E-Creator, MSI MEG X870E, Gigabyte X870E Aorus Master) — placa ATX standard
  - RAM: 64 GB DDR5-6000 (2×32 GB)
  - Cooler: AIO 360mm
  - Riser cable adicional pra 3ª GPU (R$ 150-300, riser x4-x16 de qualidade média basta)
- **Reaproveitado:** gabinete mid-tower ATX atual cabe placa X870E nova (não precisa trocar).
- **Layout PCIe esperado:**
  - Slot 1 (x16 CPU): RTX 3090 (dentro do gabinete ou riser curto)
  - Slot 2 (x4 chipset): RTX 3080 #1 via riser
  - Slot 3 (x4 chipset): RTX 3080 #2 via riser
- **Reaproveitado da máquina atual:** 2 PSUs (RM 1000+850 = 1850W, suficiente), Add2PSU, 3 GPUs, NVMe SN350 2TB, drives.

### NÃO comprar agora
- ❌ RAM DDR4 nova — não migra pra DDR5 da plataforma futura. Aceitar 2400 MHz atual até trocar.
- ❌ PSU adicional — as 2 atuais cobrem o setup futuro com folga (63% e 75% de carga máxima).
- ❌ HEDT/Threadripper — investimento R$ 22-32k+ sem ganho pro caso de uso (rodar IAs locais em paralelo NÃO requer PCIe x16 elétrico — vide histórico).

---

## Histórico de mudanças

### 12/05/2026 (tarde) — Hardware: RAM 32→64 GB (teto Z390) + SSD 970 Pro era falsificado

**RAM upgrade ✅:** Maicon instalou 2 pentes adicionais Kingston FURY Beast `KF3200C16D4/16GX` 16GB, totalizando **4× 16GB = 64 GB DDR4-2400**. Bate o teto da plataforma Z390 (64 GB max). Próximo upgrade de RAM só com AM5 + DDR5 fim 2026.

**Implicações imediatas pro treino:**
- `cache=True` (RAM full) agora viável.
- `workers=6` margem segura — restrição anterior (`cache='disk' + 4 workers` após OOM 08/05) **fica suspensa**.
- Re-validação obrigatória: rodar 1 treino curto pra confirmar antes de atualizar TASKs futuras com configs novas.

**SSD 970 Pro 2TB FALSIFICADO ❌:** o drive comprado 08/05/2026 por R$ 1200 chegou falso. Devolvido em 12/05/2026, seguro acionado, processo de reembolso em andamento. Não compromete trabalho atual.

**Pesquisa de substituto (12/05/2026 via WebSearch — Cowork):** 5 alternativas mapeadas (Samsung 990 Pro, WD SN850X, Kingston KC3000, Samsung 9100 Pro Gen5, WD SN8100 Gen5). Recomendação: Samsung 990 Pro 2TB **ou** WD Black SN850X 2TB — Gen4, ~1.2-1.4M IOPS aleatório, ainda em produção (anti-falsificação melhor que 970 Pro descontinuado), R$ 1.000-1.400. Detalhes na seção "Próximo upgrade — Etapa 1".

### 12/05/2026 — T015 fase 2 (D10/AAR) entregou smoke qualitativo no emulador; T015.b.ipc destrava o gate quantitativo via auto-trigger

**T015 fase 2 executada (D10 — AAR pré-compilado):**

Módulo Gradle `:detectionservice` criado dentro de `_research/litert_poc/`, AAR gerado (`detection_service.aar`), importado no APK principal via `android.add_aars` no `buildozer.spec` (com `android.add_gradle_repositories = flatDir { dirs 'libs' }`). APK `1.0.28-rc2` (universal arm64-v8a + x86_64, ~155 MB) instalado em AVD `google_apis` API 29 x86_64. App Kivy/Python/SDL2 sobe, Service Kotlin carrega no processo, PID 8612 vivo 35+ min com 245 MB RAM — **smoke qualitativo PASS**.

**Bloqueio descoberto no gate quantitativo:** `test_ipc_roundtrip.py` usa Pyjnius pra `bindService` + Messenger, mas **Pyjnius exige o JVM context do processo Android embarcado**. Tentativa de rodar o script via `adb shell run-as <pkg> python test_ipc_roundtrip.py` falha porque o shell não tem JVM context (não é o processo do app — é processo separado do shell). Resultado: `frames_success = 0`, métricas P50/P95/P99 não calculáveis. O gate emulador ficou em SKIP no quantitativo, mesmo com qualitativo PASS.

**Decisão Maicon (12/05/2026):** não pular pro S24. **Respeitar a política rigorosa "emulador antes do S24, sem exceção"** registrada no histórico do 11/05. Criar sub-task **T015.b.ipc** pra destravar o gate quantitativo no próprio emulador.

**Solução T015.b.ipc — auto-trigger via flag file:**

- Bloco condicional em `mobile/main.py` (em `on_start` do App ou fim do `__init__` do MainScreen) que checa `/sdcard/run_ipc_test`. Se a flag existe → thread interna invoca `run_benchmark(frames=100, report_path="/sdcard/ipc_emulator.json")`. Thread roda DENTRO do processo do app → Pyjnius tem JVM context válido → `bindService` funciona → roundtrip mensurável.
- Flag é setada externamente via `adb shell touch /sdcard/run_ipc_test` antes de abrir o app, e removida pelo próprio thread ao terminar (sinal de conclusão pra pipeline shell).
- Sem flag → app abre normal, sem disparar nada (zero impacto em produção, exceto bytes de código mortos).
- `test_ipc_roundtrip.py` refatorado pra expor `run_benchmark(frames, report_path)` reutilizável (não só `__main__`/argparse).
- APK alvo: `1.0.28-rc3`.

**Critério emulador (relaxado vs S24 por virtualization overhead):** P95 < 30 ms (preferível < 20), P99 < 80 ms (preferível < 50), `frames_success ≥ 95`. Critério S24 segue rígido (P95 < 10 ms, P99 < 30 ms).

**Tech debt rastreável:** bloco auto-trigger em `main.py` deve ser marcado com comentário "T015.b.ipc — REMOVER em produção final". Vira item de cleanup pra T016.

**Lição registrada (mobile/Pyjnius):** **testes que usam Pyjnius pra falar com componentes Android (Service, Activity, ContentProvider) NÃO rodam via `adb shell` — precisam estar dentro do processo do app Android.** Padrão de solução: flag file em `/sdcard/` + thread interno disparado pelo `main.py` em condição. Vale registrar em `_agent/memories/` na próxima passada.

**Origem:** Claude Code executou T015 fase 2 entre 11/05 noite e 12/05 manhã, identificou o bloqueio Pyjnius/JVM context, devolveu pro Cowork. Maicon decidiu pela continuação rigorosa (não pular pro S24).

---

### 11/05/2026 (tarde) — T015 fase 1 bloqueada no passo 0; decisão: **Opção C (AAR pré-compilado)** pra fase 2

**Bloqueio identificado pelo Claude Code:** o template p4a/SDL2 que gera o `build.gradle` do APK final **não inclui o Kotlin Gradle plugin** — sem `classpath 'org.jetbrains.kotlin:kotlin-gradle-plugin'` e sem `apply plugin: 'kotlin-android'`. Resultado: `android.add_src` no `buildozer.spec` aceita só Java (precedente: `CameraHelper.java` já presente no projeto). Compilar `.kt` direto na pasta de fontes do APK falharia no Gradle.

**Decisão Maicon:** ir com **Opção C — AAR pré-compilado**.

**Alternativas comparadas:**

| Opção | Custo extra | Risco | Alinhamento com PoC LiteRT (Kotlin) | Caminho pra T016 |
|---|---|---|---|---|
| A — Reescrever Service em Java | 0h | Baixo (precedente CameraHelper.java) | ❌ Divergência: Java no Service, Kotlin no PoC | Manter Java ou re-fazer em Kotlin (retrabalho) |
| B — Patch template p4a (injetar Kotlin plugin via `build_local.sh`) | 2-4h | Médio (acoplado ao template; quebra em update de p4a) | ✅ Mantém Kotlin | Dívida técnica permanente |
| **C — AAR pré-compilado** (compilar `.kt` no Android Studio, importar via `android.add_aars`) | **5-10h** | **Baixo** (fluxo independente do p4a) | ✅✅ Mesma stack do PoC | T016 já vai importar LiteRT como AAR — mesmo padrão |

**Racional:**

- T016 vai integrar **LiteRT real**, que **virá como AAR** de qualquer jeito (`com.google.ai.edge.litert:litert:1.4.0`). O PoC `_research/litert_poc/` já é Android Studio Kotlin.
- O custo extra de C **não é gasto a mais** — é antecipação obrigatória pra T016. Você paga upfront e o setup AAR já estará pronto pra integração real.
- Opção A criaria divergência lingüística no projeto (Java + Kotlin) e geraria retrabalho em T016.
- Opção B combina o pior dos dois mundos: fragilidade do patch p4a + complexidade.

**Plano operacional da fase 2 (T015 segue, não vira T015.b — mesmo ciclo):**

1. **Expandir `_research/litert_poc/`** com um novo módulo Gradle Android Library `:detectionservice` (não confundir com `:app`, que é o app de teste do PoC). Esse módulo hospeda `DetectionService.kt` + `DetectionDTO.kt` + manifesto do Service.
2. **Compilar:** `./gradlew :detectionservice:assembleRelease` → gera `_research/litert_poc/detectionservice/build/outputs/aar/detectionservice-release.aar`.
3. **Importar no APK principal:** copiar AAR pra `mobile/libs/detectionservice.aar` e adicionar `android.add_aars = libs/detectionservice.aar` no `buildozer.spec`. Declarar o `<service>` via `android.manifest_placeholders` ou `<manifest-extra>` no spec.
4. **Wrapper Python (`mobile/service_bridge.py`):** Pyjnius autoclass `com.maicon.animaldetector.DetectionService` + Messenger pra bind.
5. **Build APK 1.0.28-rc1** → **gate emulador (AVD, 100 frames)** → **S24 (1000 frames, P50/P95/P99)**.

**Caveat declarado:** durante esta T015, o AAR **NÃO inclui LiteRT** como dependency — só androidx.core mínimo. LiteRT entra no AAR (ou como AAR adicional) em T016.

**Origem:** Claude Code identificou o bloqueio em 11/05/2026 (tarde) na investigação obrigatória do passo 0 da T015. Cowork apresentou as 3 opções com tabela comparativa + ROI; Maicon escolheu C.

---

### 11/05/2026 — T014 fechada ✅ (fase 1 + T014.b), T015 promovida; nova política de validação: emulador antes de teste físico

**T014 concluída** em duas fases:

| Fase | Item | Resultado |
|---|---|---|
| Fase 1 | Conversão TFLite INT8 (PTQ) `coco_v0` + `fulldet_v3` | ✅ ambos `full_integer_quant` |
| Fase 1 | Pipeline `scripts/export_tflite_ptq.py` + `validate_tflite_quick.py` + `copy_models_to_poc.py` | ✅ |
| Fase 1 | Projeto Android Studio `_research/litert_poc/` (Kotlin + LiteRT 1.4.0 + AICore delegate) | ✅ compila |
| Fase 1 | mAP `coco_v0` INT8 vs FP32 (<3% perda) | ✅ 50.2% / perda 1.4% rel — **PASS** |
| Fase 1 | mAP `fulldet_v3` INT8 vs FP32 (<3% perda) | ✗ 62.5% / perda 9.23% rel — causa-raiz: calibração com apenas 4 imgs (`coco8.yaml`) |
| T014.b | Re-export `fulldet_v3` com 5.151 imgs (BR val completo) | ✅ INT8 **66.1%** (≥ 65.8% critério absoluto) — **PASS** |

**Lição PTQ registrada:** representative dataset INT8 precisa de **≥ 300 imagens do domínio alvo**. Default do Ultralytics (`coco8.yaml` = 4 imgs) engana e custou uma iteração inteira. Vale documentar em `_agent/memories/` na próxima passada.

**T015 promovida** de `_research/draft_task15_native_service.md` pra `_handoff/TASK.md` (status `pronto`). Escopo: Bound Service Kotlin + Messenger IPC + wrapper Python (Pyjnius), detecção mock, 1000 frames de roundtrip, critério P95 < 10 ms / P99 < 30 ms. **Não substitui cv2.dnn ainda** — APK gerado vira `1.0.28-rc1` (validação interna, 1.0.27 permanece em produção). Pesquisas pendentes 1 e 2 do draft (AAR LiteRT estável + AICore no Exynos 2400) resolvidas implicitamente pela T014 — PoC compila. Pesquisa pendente 3 (receita p4a/Buildozer pra módulo Kotlin custom) virou primeiro passo investigativo da própria T015, com plano B (AAR pré-buildado, ~5-10h) registrado.

**Nova política — validação em emulador antes de teste físico no S24:**

A partir desta entrada, **toda TASK que produzir APK ou módulo Android validado em runtime deve passar primeiro por teste em emulador** (AVD com imagem ARM64 ou x86_64 conforme o módulo) antes de ir pro Samsung S24 Ultra de campo. Racional: o S24 é o dispositivo de produção do Maicon — preservar evita ciclos de uninstall/reinstall por crash trivial, derrubar ANR no aparelho de trabalho, e poluir o logcat real com builds rc. Emulador serve de gate para crashes na inicialização, manifestos quebrados, smoke test do IPC, paridade visual mínima. Apenas builds que passam no emulador descem pro S24 pra medição final (latência, fps, AICore delegate real, validação em campo).

Consequências práticas:
- T014 teste físico no S24 (latência CPU vs AICore) — **segue pendente** e agora deve rodar em **AVD primeiro** (CPU baseline) e só depois no S24 (validação AICore real, que o emulador não cobre).
- T015 critério de sucesso passa a exigir: 1000 frames em emulador zerados de crash **antes** de medir latência IPC no S24.
- T016 (futura) idem: APK 1.0.28-rc1 → emulador → S24.

**Teste físico no S24 da T014 continua em paralelo com T015** (não-bloqueante) — Maicon roda quando puder, agora seguindo a nova política (AVD primeiro).

**Origem:** decisão Maicon, modo automático, sessão 11/05/2026 — após Cowork promover T015 e consultar sobre fluxo de teste.

---

### 10/05/2026 (noite) — Decisão arquitetural: migrar runtime Android para Serviço Nativo Kotlin + LiteRT/AICore

**Reversão informada da decisão anterior (mesma data, manhã) que arquivara a TASK 14 como backlog Fase 2.** O motivo da reversão não é fps insuficiente em campo (1.0.27 entrega 9 fps reais validados) — é a **obsolescência declarada da rota que estava arquivada**: a antiga TASK 14 previa **ORT + NNAPI**, e NNAPI foi **deprecado pelo Google no Android 15 (2024)** em favor de **AICore + LiteRT**. Investir 40-60h naquela direção agora vira dívida técnica imediata.

**Decisão:** abandonar `cv2.dnn` (OpenCV 4.5.1) como motor de inferência Android. Implementar **Serviço Nativo Android (Kotlin) com LiteRT + AICore delegate** rodando os modelos via AAR oficial Google. UI Kivy/Python continua intacta, IPC Python↔Kotlin (Bound Service ou Messenger) pra envio de frame e retorno de detecções.

**Alternativas consideradas e descartadas:**

| Alternativa | Por que descartada |
|---|---|
| Status quo (`cv2.dnn`) | Congelado em 4.5.1 com bug >15 MB, sem acesso a NPU, teto ~9 fps. Caminho sem futuro. |
| ORT + NNAPI (TASK 14 antiga) | NNAPI deprecado pelo Google em 2024 — prazo de validade explícito. |
| LiteRT via ctypes/Pyjnius em Python puro | Sem wheel `android_aarch64` no PyPI (mesmo problema das TASKs 10 e 12). R&D inédito, teto ~15 fps. |
| Migração total pra Kotlin (UI + IA) | Dobra custo de horas, aposenta Kivy prematuramente sem ganho proporcional. |

**Racional:** LiteRT + AICore é a stack oficial Google daqui pra frente, com aceleração NPU/GPU nativa no S24 (Exynos 2400). Único caminho com 30+ fps comprovado mantendo Kivy é o Serviço Nativo Kotlin (já rascunhado em `_research/draft_task14_native_service.md` — pré-condição de validar exemplo oficial do AAR continua válida, agora aplicada ao AAR LiteRT em vez de ORT). A lição arquitetural arquivada na entrada anterior ("ROI do paliativo bateu R&D ambicioso") permanece válida: o paliativo TASK 13 está em produção e segue cobrindo o uso real até a nova stack subir.

**Descoberta usada no escopo do PoC:** o `fulldet_yolov8n_nc95_v3` sofreu catastrophic forgetting das classes COCO 0-79 — só as 15 BR (80-94) são funcionais. PoC LiteRT não pode adotar single-engine via v3 isolado; precisa converter os **dois** ONNX ativos do 1.0.27 (`coco_v0_i320` + `fulldet_v3_i320`) e manter o frame skip alternado **no novo runtime**, alvo de paridade funcional com 1.0.27. Single-engine real só vira possível após v4 unificado funcional (gate condicional na T017).

**Backlog T014→T017 (sequenciado, com gate condicional):**

| ID | Escopo | Critério de sucesso | Dependência |
|---|---|---|---|
| **T014** | PoC pipeline LiteRT: conversão dos 2 ONNX → TFLite INT8 via Post-Training Quantization + projeto Android Studio mínimo (não-Buildozer) carregando AAR LiteRT + AICore delegate + 1 inferência síncrona em `bus.jpg`. | mAP50 desktop pós-PTQ ≥ 67% (perda <3% vs FP32) **e** `.tflite` roda no AAR sem crash, detecções coerentes em `bus.jpg`. | — |
| **T015** | Skeleton Serviço Nativo Kotlin (Bound Service ou Messenger) + IPC Python↔Kotlin com detecção mock. Roundtrip dummy 1000 frames. | Latência IPC <10 ms/frame, sem crash. | T014 ✅ |
| **T016** | Pipeline completo: LiteRT + AICore real no Service, frame skip alternado (paridade funcional 1.0.27), APK 1.0.28. | IA fps ≥ **20** no S24, cobertura visual ≥ 1.0.27, sem crash, câmera fps mantido. | T015 ✅ |
| **T017** *(condicional)* | Re-treino v4 unificado funcional com QAT INT8 (corrige catastrophic forgetting). Dispara apenas se T016 mostrar cobertura insuficiente OU se fps ≥ 30 abrir espaço pra modelo maior. | mAP50 INT8 ≥ 70% **e** IA fps ≥ 20 no S24. | T016 ✅ + decisão Maicon |

**Consequências da migração:**
- Stack agora bi-linguagem (Python + Kotlin). Buildozer continua, precisa empacotar AAR + `.tflite` no APK.
- `_research/draft_task14_native_service.md` permanece referência, mas precisa ser re-anotado: trocar ORT→LiteRT, manter pré-condição de validação do AAR oficial.
- 1.0.27 (`cv2.dnn`) permanece em produção até T016 entregar 1.0.28 funcional. Rollback garantido.

**Origem da decisão:** orquestração Cowork (modo automático, sessão 10/05/2026 noite) — Maicon revisitou o backlog após perceber que NNAPI estava na rota descontinuada. Confirmou as 4 escolhas no menu de briefing (Serviço Nativo Kotlin recomendado; PoC primeiro com PTQ; imgsz 320 mantido pra paridade; nc95 atual).

---

### 10/05/2026 — APK 1.0.27 em produção: TASK 13 fecha fase de aceleração com 9 fps reais (5.4× speedup)

**Resultado consolidado:**

| Métrica | 1.0.26 base | 1.0.27 entregue | Previsão Cowork | Comentário |
|---|---|---|---|---|
| IA FPS | 1.67 | **9.0** | 5.5 real / 10 percebido | Bateu acima — alternância contou como real |
| Câmera FPS | 30 | 28-30 | igual | Inalterado |
| Cobertura COCO+BR | ✅ | ✅ (cache alternado) | ✅ | Cada modelo a ~4.5 Hz |
| Tamanho APK | 93 MB | 94 MB | 70-90 MB | Marginal |
| Speedup vs 1.0.26 | 1× | **5.4×** | 3.3× | Acima do projetado |

**Validação em campo (Maicon, 10/05/2026):** APK instalado no S24, animais e pessoas reconhecidos. App em produção pra uso de campo.

**Stack final consolidada:**
- Runtime: cv2.dnn 4.5.1 (OpenCV CPU ARM, sem NNAPI/GPU — confirmado teto definitivo após TASKs 10 e 12).
- Modelos ativos: `coco_yolov8n_nc80_v0_i320_nodfl.onnx` (par) + `fulldet_yolov8n_nc95_v3_m692_i320_nodfl.onnx` (ímpar).
- Pipeline: frame skip alternado (`engine_idx = frame_count % 2`) + cache `last_dets_by_model[2]` + união como `last_detections`.
- Refactor mínimo no `core/detection_engine.py`: extração de `_process_single_engine()` (lógica compartilhada) + novo método `detect_one(frame, engine_idx)`. `detect()` original preservado pra desktop.

**Bug latente corrigido em `scripts/export_unified.py`:** `DFL_PREFIXES` cobria só 19 nós, deixando `Shape`, `Gather`, `Add`, `Mul`, `Mul_1` órfãos no grafo quando export rodava com `simplify=False` → `InvalidArgument` no OnnxRuntime. Fix: ampliar pra 24 nós cobrindo toda a cadeia de decode. Antes funcionava só por sorte porque exports anteriores usavam `simplify=True`. Arquivado em "Problemas Conhecidos".

**Decisão arquitetural — TASK 14 (Serviço Nativo Kotlin + ORT NNAPI) arquivada como backlog Fase 2:**

Com 9 fps reais entregues, o custo de comprometer 40-60h pra subir pra 30+ fps via Foreground Service Kotlin + ORT NNAPI **não se justifica agora**. Decisão consolidada: arquivar `_research/draft_task14_native_service.md` como backlog ativado apenas se:
- App virar produção em escala (não só uso pessoal do Maicon), OU
- Fase 2 v4 unificado pós-AM5 exigir mais throughput pra refinamento de campo, OU
- Aparecer caso de uso que torne 30+ fps requisito real (não cosmético).

Pré-condição crítica registrada no draft: antes de qualquer comprometimento futuro, validar exemplo oficial `microsoft/onnxruntime-inference-examples/android` (compila + roda + smoke test no S24).

**Lição arquitetural arquivada — ROI do paliativo bateu R&D ambicioso:**

Sequência das últimas TASKs (9→10→12→13) mostra o padrão:
- TASK 9 (imgsz 416 + INT8/FP16): 1.67 fps, paliativo parcial.
- TASKs 10 + 12 (trocar runtime via wheel Python): bloqueadas — ecossistema não suporta.
- **TASK 13 (frame skip alternado + i320): 9 fps, paliativo total dentro do cv2.dnn.**

Tentativas de trocar runtime gastaram ~2-3h de Claude Code em duas TASKs bloqueadas (premissas erradas de Cowork sobre wheels Android). O caminho que de fato resolveu foi otimizar dentro da stack existente. Lição: **quando o ecossistema externo trava, voltar pro paliativo dentro da stack atual antes de assumir que a estrutura precisa mudar.**

Investigação não foi gasto perdido — gerou `_research/2026-05-10_inference_runtimes_android.md` com 2 pesquisas Gemini + análise crítica completa. Documento serve como referência cruzada permanente pra Fase 2.

### 10/05/2026 — TASK 12 (TFLite+NNAPI) também bloqueada; volta pra Opção C refinada (TASK 13)

**Premissa errada de Cowork derrubada:** afirmei como fato que `tflite-runtime` tinha wheel oficial Android arm64-v8a no PyPI. Claude Code validou e descobriu que (a) `tflite-runtime` foi **descontinuado pelo Google em 2024**, (b) não existe wheel pra Python 3.12 em nenhuma plataforma, (c) o substituto oficial `ai-edge-litert` também não tem wheel Android. Lição arquivada na memória persistente do Cowork: **antes de recomendar troca de runtime na stack Buildozer/Kivy, validar com `pip download --platform android_aarch64 <pacote>`**. Foram 2 TASKs (10 e 12) bloqueadas em sequência por causa dessa premissa.

**Realidade do ecossistema confirmada:** Google e Microsoft distribuem runtimes ML pra Android via C++ + AAR Java/Kotlin, não via Python wheel. Python-on-Android (p4a) não é target oficial deles. Nenhum runtime ML mainstream tem wheel `android_aarch64` no PyPI (`onnxruntime`, `onnxruntime-mobile`, `tflite-runtime`, `ai-edge-litert`, `tflite-support` — todos sem wheel Android).

**Caminhos NNAPI/GPU restantes (todos custosos):**
- Compilar onnxruntime/tflite do source com NDK (4-8h Bazel cross-compile, frágil).
- AAR Microsoft + `pyjnius` bridge (refactor profundo do DetectionEngine, 6-10h).
- ncnn (Tencent) — receita p4a unofficial, exige converter ONNX→ncnn via `pnnx`.
- MNN (Alibaba) — wheel unofficial Android, doc escassa.

Marcados como "investigação futura" — não justificam o custo agora quando o paliativo cv2.dnn entrega a meta de 5-7 fps em 30 min.

**Decisão consolidada — TASK 13: Opção C refinada (frame skip alternado + i320), mantendo dual coverage:**

| Sub-otimização | Custo | Speedup percebido | Trade-off |
|---|---|---|---|
| Frame skip N=2 + alternância de modelos (frame par→COCO, ímpar→BR) | 15 min | ~4× → ~6.7 fps | Cada classe atualiza ~3.3 Hz (suficiente pra detecção em campo) |
| imgsz 416→320 (sozinho) | 10 min | ~1.65× | -3-5% mAP em objetos pequenos |
| **Combinado (TASK 13)** | 30 min | **~10 fps percebido** | Mantém COCO + BR; perda mAP marginal |

**Por que rejeitamos a sugestão original do Claude Code (frame skip + single model):** abandonar o modelo BR no Android perderia fauna brasileira no app — diferencial profissional do Maicon (Policial Penal, foco em segurança pública). Trade-off inaceitável. Alternância preserva ambas as famílias de classe a custo de latência extra (~150 ms) por classe.

**Cross-suppression entre modelos:** quando os 2 rodavam juntos, `DetectionEngine` suprimia detecções BR sobrepostas a person/veículo do COCO. Com alternância, a supressão passa a ser "entre frames" via cache — menos precisa. Pode introduzir ocasionais falsos positivos (ex: pessoa classificada como anta). Aceitar como trade-off; ajuste fino fica pra TASK 14 se aparecer em campo.

### 10/05/2026 — Opção C (onnxruntime+NNAPI) descartada; migração pra TFLite escolhida (TASK 12)

**TASK 10 bloqueada:** receita p4a do onnxruntime falhou no Passo 2 — PyPI não publica wheels Android (`android_aarch64`) nem pra `onnxruntime` nem pra `onnxruntime-mobile`. O erro `libdl.so.2 not found` era só sintoma; a causa-raiz é incompatibilidade **glibc (manylinux) vs Bionic libc (Android)** que afeta toda a cadeia (`libdl.so.2`, `libc.so.6`, `libm.so.6`). Microsoft distribui onnxruntime pra Android apenas via AAR Java/JNI, não como wheel Python.

**Caminhos avaliados (com ROI):**

| Opção | Custo | FPS esperado | Risco | ROI |
|-------|-------|--------------|-------|-----|
| A — onnxruntime do source (Bazel + NDK cross-compile) | 4-8h primeira build + tuning | 5-10 fps NNAPI / 10+ FP16 | Alto (toolchain frágil) | Médio |
| B — AAR + pyjnius bridge | 6-10h refactor | 5-10 fps | Alto (refactor profundo do DetectionEngine) | Baixo |
| C — Otimizações em cv2.dnn (i320 + alternar modelos) | 60 min | ~5.5 fps | Baixo | Altíssimo (mas paliativo) |
| **D — TFLite com NNAPI delegate** | 3-5h re-export + refactor | 5-10 fps NNAPI / 10+ INT8 | Médio | **Alto (definitivo)** |

**Decisão consolidada — Opção D pulando o paliativo C:**

Maicon optou por ir direto na D (TFLite) em vez de gastar 60 min na C e ainda assim ter que migrar runtime depois. Justificativa:
- `tflite-runtime` tem **wheel oficial pra Android arm64-v8a** no PyPI — receita p4a estável, sem o hack glibc/Bionic.
- TFLite tem **NNAPI delegate nativo** (NPU Exynos 2400) + GPU delegate + XNNPACK (3 caminhos de aceleração).
- Ultralytics exporta YOLOv8 → TFLite direto (`m.export(format='tflite', int8=True)` com calibração automática).
- Desbloqueia INT8 real — TFLite usa quantização estática com `Int8Quantizer` que funciona em runtime mobile, diferente do `DynamicQuantizeLinear` do ORT que cv2.dnn rejeita.
- 3-5h é pagamento único: depois libera Fase 2 inteira (re-treino unificado pós-AM5) sem precisar mexer em runtime de novo.

**Opções A e B descartadas:** ROI ruim quando TFLite entrega o mesmo resultado com ferramental nativo do Android.

**Lições arquivadas:**
- **PyPI não tem wheels Android** pra projetos que dependem de C++ extensions (onnxruntime, scipy, etc.). Buildozer puxa wheel `manylinux_aarch64` que é Linux/glibc — incompatível com Bionic. Antes de planejar uma TASK que dependa de uma lib nativa Python no Android, validar com `pip download --platform android_aarch64`.
- **Receita p4a custom só vale a pena se há wheel ou source build viável.** Sem isso, qualquer receita vira tentativa de criar stubs de libs do sistema operacional — incompatibilidade é estrutural, não de configuração.
- **TFLite é o caminho canônico pra IA on-device no Android.** Foi o que a Google projetou e é o que tem suporte oficial em Buildozer/p4a + delegates de NNAPI/GPU.

### 10/05/2026 — APK 1.0.26: aceleração IA via imgsz 416 (TASK 9, parcialmente concluída)

**Objetivo:** subir FPS de IA de ~1 fps (APK 1.0.24, i640 FP32) pra 5-7 fps via combinação imgsz 640→416 + quantização (INT8/FP16).

**Resultado consolidado:** APK 1.0.26 estável no S24 com **~1.67 fps de IA** (speedup ~1.67× vs 1.0.24). Meta de 5-7 fps **não atingida** — quantização bloqueada pelo cv2.dnn 4.5.1 Android.

**Cronologia da TASK:**

| Passo | O que foi feito | Resultado |
|-------|-----------------|-----------|
| 1 | `core/detection_engine.py`: `input_width = input_height = 416` | 3549 anchors (52² + 26² + 13²) confirmados em logcat. ✅ |
| 2 | INT8 via `onnxruntime.quantization.quantize_dynamic` (`scripts/quantize_models.py`) | ❌ `DynamicQuantizeLinear` op ausente no cv2.dnn (4.13 desktop e 4.5.1 Android). |
| 3 | FP16 via `onnxconverter_common.float16` (`scripts/convert_fp16.py`). APK 1.0.25 construído (83.4 MB). | ❌ `Unsupported data type: FLOAT16 in getMatFromTensor` (onnx_graph_simplifier.cpp:593). |
| 4 | Fallback FP32 i416 — `mobile/main.py` revertido, `buildozer.spec` 1.0.26 com FP32 i416 (FP16/INT8 excluídos). APK 93.4 MB. | ✅ Estável. |

**Métricas no S24 (APK 1.0.26):**
- Câmera: ~20 fps (CV-PULSE) — inalterado.
- Engines: 2/2 carregadas (COCO 80cl + BR 95cl).
- Formato: OpenCV CPU, FP32, i416.
- max_score: até 0.970.
- Hits/ciclo: 10–23.
- IA FPS estimado: ~1.67 fps.
- Erros cv2.dnn: nenhum.
- [CV-PAD] buffer fix: ativo.

**Por que 1.67× e não os 2.37× teóricos (416²/640²):** dois modelos rodam em série no mesmo frame, então parte do ganho de cada inferência é consumida pela soma. Gargalo de fundo é CPU ARM Cortex-A78 do S24 com cv2.dnn (sem NNAPI, sem GPU). onnxruntime importa no bundle mas falha em runtime com `libdl.so.2 not found` → cai pro cv2.dnn.

**Decisões consolidadas (incompatibilidades cv2.dnn 4.5.1 Android — definitivas até trocar runtime):**

| Formato | Erro | Decisão |
|---------|------|---------|
| INT8 (`quantize_dynamic`) | `DynamicQuantizeLinear` op ausente | Descartado pra cv2.dnn. Reativar só com onnxruntime + NNAPI. |
| FP16 (`onnxconverter_common`) | `Unsupported data type: FLOAT16` | Descartado pra cv2.dnn. NNAPI tem suporte nativo → reativar com Opção C (esperado ~10+ fps). |
| FP32 | Compatível | **Padrão do APK 1.0.26.** |

**Arquivos gerados:**
- `models/coco_yolov8n_nc80_v0_i416_nodfl.onnx` (~12 MB, ativo)
- `models/fulldet_yolov8n_nc95_v3_m692_i416_nodfl.onnx` (~12 MB, ativo)
- `models/coco_yolov8n_nc80_v0_i416_fp16_nodfl.onnx` + `models/fulldet_..._i416_fp16_nodfl.onnx` (bloqueados, mantidos pra Opção C)
- `models/coco_yolov8n_nc80_v0_i416_int8_nodfl.onnx` + `models/fulldet_..._i416_int8_nodfl.onnx` (bloqueados, mantidos pra Opção C)
- `scripts/convert_fp16.py` (referência futura)
- `scripts/quantize_models.py` (referência futura)
- `bin/animaldetector-1.0.26-arm64-v8a-debug.apk` (APK estável)

**Próximo passo:** **Opção C — onnxruntime + NNAPI (NPU Exynos 2400).** Bloqueio atual a resolver: `libdl.so.2 not found` → exige receita p4a personalizada para onnxruntime com NDK target correto. Com NNAPI ativo: FP32 ~5 fps, FP16 ~10+ fps esperados. Maicon vai delegar ao Claude Code.

**Lições arquivadas:**
- **cv2.dnn 4.5.1 Android é teto definitivo pra otimização** — nem INT8 nem FP16 funcionam. FPS adicional exige trocar de runtime.
- **Speedup teórico de imgsz nunca bate em 100%** quando há múltiplos modelos em série — overhead de pré/pós-processamento + DFL decode em Python consome parte do ganho.
- **`onnxruntime` import OK ≠ funcional no Android** — bundling do p4a precisa de receita específica pra carregar `libdl.so.2`.

### 10/05/2026 — APK 1.0.24: tela branca resolvida + reorganização filesystem completa (TASKs 7B + 8)

**TASK 7B — diagnóstico tela branca no S24:**

APK 1.0.23 instalou e os modelos carregaram OK no S24, mas a tela ficava 100% branca. App vivo (PID 27054), screenshot 100 KB com conteúdo gráfico, sem crash/SIGABRT/HWUI. Logcat revelou erro recorrente:

```
[CV-ERROR] Falha na conversão: cannot reshape array of size 153599 into shape (240,640)
```

**Causa-raiz:** Samsung S24 entrega buffer YUV do Camera2 com **off-by-one** (153.599 bytes quando reshape espera 153.600). Bug provável no `CameraHelper.java` ou no `ImageReader` do Camera2 com chipset Exynos 2400. `_yuv_to_bgr` em `core/android_camera2.py` lançava exception silenciosa via callback pyjnius (`@java_method` engole exceptions) → frame nunca chegava ao Kivy → tela branca.

**TASK 8 — reorganização filesystem + fix YUV + APK 1.0.24:**

Maicon decidiu unir 2 trabalhos numa execução só, na ordem certa: reorganização primeiro (pra que `m.val()` rode com paths corretos durante validação), depois fix YUV.

**Parte A — reorganização filesystem:**
- COCO movido pra `C:\datasets\coco\images\<split>\` (NTFS rename, instantâneo, 118.287 train + 10.000 val).
- `D:\datasets\br_detection\` → `C:\datasets\br_detection\` (11.852 arquivos, robocopy SHA-validated).
- `D:\training\runs\` → `C:\training\runs\` (SHA `493D…F856` íntegro).
- `D:\datasets\african-wildlife\` apagado (Maicon não usa).
- `datasets/full_detection.yaml` + 8 scripts atualizados (paths C: + subdir `images/`).

**Sanity confirmou correção do yaml bug:**
- `m.val()` reproduziu **mAP50 = 10.90%, mAP50-95 = 8.06%** (vs 69.21% enganoso anterior). A queda confirma que labels COCO agora estão sendo lidos como GT real (antes eram backgrounds). Fauna BR específica: jaguatirica 94%, lobo_guara 94.5%, anta 91%. Modelo BR sólido.
- `m.predict('bus.jpg')` retornou 0 detecções (modelo BR-only não detecta COCO urbana — sanity de cópia íntegra).

**Parte B — fix YUV:**
Adicionada função `_safe_extract(buf, expected_size, label)` em `core/android_camera2.py` que pad com zeros se buffer veio curto, trunca se veio longo, loga 1x por label pra rastreabilidade. 3 substituições no `_yuv_to_bgr` (Y, U, V).

**APK 1.0.24 (`bin/animaldetector-1.0.24-arm64-v8a-debug.apk`, 127.1 MB, build 22 min):** instalado no S24, validação confirmou:

```
[CV-PAD] Buffer U: 153599 bytes recebido, 153600 esperado (delta=+1)
[CV-PAD] Buffer V: 153599 bytes recebido, 153600 esperado (delta=+1)
[CV-PULSE] FPS: 27.9 | Conv: 27.1ms                       (32 pulsos em 30s)
detect [global]: shape=(8400, 84) max_score=0.671 hits=26
```

**Achado interessante:** o off-by-one apareceu nos planos **U e V** (não Y como originalmente reportado pelo erro `(240,640)`). UV intercalado em NV21 tem `v_rs = 1280` (2 bytes/pixel), então `(h//2) * v_rs = 153.600` — e o S24 manda 153.599. O `_safe_extract` cobriu os 3 planos preventivamente, então o fix funcionou independente de qual plano estava com o problema em cada frame.

**Estado real do app no S24 (pós-1.0.24):**
- ✅ Imagem da câmera renderizando.
- ✅ Reconhecimento detectando (max_score 0.671 com 26 hits no logcat).
- ⚠️ **CAM ~20 fps, IA ~1 fps** — gargalo conhecido. 2 modelos YOLOv8n sequenciais em OpenCV DNN CPU ARM custam ~800-1000 ms/frame. Plano de aceleração (TASK futura): combinar imgsz 640→416 + skip frames de IA pra ~2.5 fps efetivos. Solução final = Opção C (NNAPI no NPU Exynos 2400) ou Fase 2 (re-treino unificado pós-AM5).

**Lições arquivadas hoje:**
- Off-by-one silencioso em pyjnius callbacks: `@java_method` engole exceptions sem aparecer no logcat. Sempre usar try/except explícito + log de erro **dentro** do callback.
- "Tela branca" no Kivy frequentemente é frame `None` chegando no `update_ui`, não bug gráfico. Investigar pipeline de frames antes de SDL2/HWUI.
- Diagnóstico via logcat ADB filtrado por PID é cirúrgico — `adb logcat -d --pid=$pid` + filtros por padrão de print é o padrão pra tracking de bugs Python no Android.

### 10/05/2026 — APK 1.0.23 dual model + reorganização de filesystem (TASKs 6 + 7)

**TASK 6 — APK 1.0.23 com modelo dual (Fase 1 do plano de 2 fases):**

`mobile/main.py` editado pra carregar `models/yolov8n_nodfl.onnx` (COCO 80 classes pré-treinado da Ultralytics) + `models/fulldet_yolov8n_nc95_v3_m692_nodfl.onnx` (fauna BR 15 classes funcionais). `DetectionEngine` já suporta multi-modelo + cross-suppression nativamente (linha 283-294 de `core/detection_engine.py`).

Buildozer.spec ajustes:
- `version` 1.0.22 → 1.0.23.
- `android.archs` `arm64-v8a, x86_64` → `arm64-v8a` only (S24 não precisa x86_64).
- **Fix crítico:** `yolov8n_nodfl.onnx` estava em `source.exclude_patterns` — sem o fix, COCO nunca empacotaria. Achado do Claude Code.
- Mudança de archs invalidou cache p4a (`build-arm64-v8a/` ≠ `build-arm64-v8a_x86_64/`) — packages copiados manualmente do antigo pro novo. Lição: trocar `android.archs` exige migrar cache p4a.

**APK 1.0.23 final:** `bin/animaldetector-1.0.23-arm64-v8a-debug.apk`, **127.1 MB** (-23,7% vs 1.0.22 de 166.5 MB). Inclui ainda 2 modelos legados (~25 MB) — `animal_wild_br_nodfl.onnx` e `full_detection_v2_nodfl_cv451_noattn.onnx` — vão pro `exclude_patterns` na TASK 7. APK 1.0.22 mantido como rollback.

**TASK 7 — reorganização de filesystem (em andamento):**

Eliminar a "dívida estrutural" do path quebrado antes que ela morda outro treino. Padrão Ultralytics enforced: `<dataset>/images/<split>/` + `<dataset>/labels/<split>/`. Migração do HDD (D:) pro SSD (C:) acelera I/O do dataloader em qualquer teste futuro nesses 8 dias até o NVMe 970 Pro chegar.

| Item | Origem | Destino |
|------|--------|---------|
| COCO imgs | `C:\datasets\coco\<split>\` | `C:\datasets\coco\images\<split>\` (NTFS rename, instantâneo) |
| BR detection | `D:\datasets\br_detection\` | `C:\datasets\br_detection\` (cópia HDD→SSD, ~1-2 GB) |
| Training runs (todas) | `D:\training\runs\` | `C:\training\runs\` (cópia HDD→SSD, ~200 MB) |
| African wildlife | `D:\datasets\african-wildlife\` | (apagar — Maicon não usa) |

Atualização de paths hardcoded em 9 arquivos: `datasets/full_detection.yaml`, `scripts/train_full_nano.py`, `scripts/train_full.py`, `scripts/prepare_dataset.py`, `scripts/train_unified.py`, `scripts/auto_label_br.py`, `monitor_training.py`, `check_disks.ps1`, `check_system.ps1`.

Sanity checks pós-reorganização:
- `m.val()` em path novo → mAP50 esperado **cair pra ~10-20%** (confirma que labels COCO agora estão sendo lidos como GT real, antes eram backgrounds).
- `m.predict('bus.jpg')` → 0 detecções (modelo BR-only não detecta COCO urbana — sanity de cópia íntegra).

Quando 970 Pro chegar (18/05), migra `C:\datasets\` + `C:\training\` → `E:\` em ~5 min (SSD→SSD, mesma estrutura).

### 10/05/2026 — Catastrophic forgetting do COCO descoberto + plano dual em 2 fases

Validação do `fulldet_yolov8n_nc95_v3_m692_nodfl.onnx` no desktop revelou que o modelo **detecta apenas as 15 classes BR (80-94)**. As 80 classes COCO (0-79) foram esquecidas durante o treino. Em `bus.jpg` (imagem padrão da Ultralytics com person+bus): 0 detecções. Em `anta_imagem_091.jpg`: anta detectada com `conf=0.7979`, mas COCO max score = 0.000006.

**Causa raiz** (refinada após inspeção do Claude Code na TASK 6 passo 5): os labels COCO **existem** em `C:\datasets\coco\labels\` em 99,1% (117.266 train + 4.952 val). O problema é o **path malformado** no yaml: aponta `C:/datasets/coco/train2017` (sem subdir `images/`), mas YOLOv8 deriva o caminho dos labels **substituindo `/images/` por `/labels/`** no path das imagens. Sem `/images/` no path, a substituição falha → trainer não acha labels → 117k imagens viram "background". O scan reportou **199 imagens anotadas + 5009 backgrounds** porque só o BR detection (que tinha `/images/` no path) funcionou. Treino interpretou COCO como "fundo onde nada deve ser detectado" durante 135 epochs → catastrophic forgetting ativa das classes 0-79.

**O mAP50=69.21% reportado na TASK 4 é enganoso.** Foi calculado num val set com o mesmo bug do yaml — imagens COCO entraram como backgrounds (sem GT) onde `confidence=0` é a resposta correta. Por isso o número saiu alto. Top-5 do val (`truck` 94%, `person` 91%) é artefato. Métrica real do modelo treinado é "boa em fauna BR (anta conf 0.8 em img real), zero em COCO".

**Falso positivo no diagnóstico (lição arquivada):** o `diag_onnx.py` reportou "scores all-zero" no ONNX exportado, e eu (Cowork) interpretei como bug de `model.export()` sem confirmar com imagem real. Era frame sintético random gerado quando a câmera ficou bloqueada por outro processo (MSMF -1072875772). Modelo especializado em fauna BR produz scores ≈ 0 em ruído puro — indistinguível de bug de export sem imagem real do domínio.

**Decisão consolidada — plano em 2 fases:**

| Fase | Quando | O quê | Custo |
|------|--------|-------|-------|
| **1 — modelo dual no APK** | Imediato (TASK 6) | Combinar `yolov8n_nodfl.onnx` (COCO 80) + `fulldet_..._m692_nodfl.onnx` (BR 15). Edição em `mobile/main.py` linha 49-52, rebuild APK 1.0.23 arm64-v8a only. | 0h treino, ~10 min build |
| **2 — re-treino unificado v4** | Após upgrade AM5 (fim 2026) | Corrigir `full_detection.yaml` + gerar labels COCO em formato YOLO. Re-treino do zero com 95 classes funcionais. | ~30h hoje, ~12-18h em AM5 |

**Racional da Fase 2 ser pós-AM5:** plataforma AM5 (Ryzen 9 9950X + 64 GB DDR5) elimina gargalo de RAM, permite `cache='ram'` ou `workers=8`, NVMe Gen4/5 acelera I/O — corta o tempo de treino quase pela metade. Em paralelo, Fase 1 cobre o uso-alvo do app no S24 com qualidade aceitável.

**Lições arquivadas:**
- **Catastrophic forgetting silencioso:** dataset YAML mal-configurado → YOLOv8 trata imagens sem labels como "backgrounds" sem aviso explícito. Sintoma: no scan, `imgs anotadas << backgrounds` (199 vs 5009 no nosso caso). Validar count de labels antes de iniciar treino longo.
- **Validação não pode depender só de `m.val()`:** se o val tem o mesmo bug do yaml, métricas saem infladas. Sempre validar adicionalmente em imagens fora do dataset (ex: `bus.jpg` Ultralytics).
- **Diagnóstico com frame sintético é traiçoeiro** — testar com imagem real do domínio do modelo antes de concluir bug de export.

### 10/05/2026 — Nova convenção de nomes pra modelos ONNX

A partir desta data, modelos ONNX seguem o padrão: `<escopo>_<arch>_nc<NN>_v<N>_m<MMM>_<flags>.onnx`. Detalhes completos no `CLAUDE.md` (seção "Convenções deste projeto").

**Motivação:** o nome antigo (`<escopo>_v<N>_<arch>_nodfl_<flags>`) não codificava (a) número de classes — confundia v3 nano-1-classe vs v3 nano-95-classes; (b) métrica do modelo — comparação entre versões obrigava abrir results.csv. Padrão novo embute ambos no nome (`nc95`, `m692`), tornando filename ordenável e auto-explicativo.

**Aplicação:**
- `unified_animal_detector_nodfl.onnx` (saída da TASK 4) → renomeado pra `fulldet_yolov8n_nc95_v3_m692_nodfl.onnx`.
- `mobile/main.py` atualizado pra apontar pro nome novo.
- Modelos legados (`animal_wild_br_nodfl.onnx`, `full_detection_v2_nodfl_cv451_noattn.onnx`, `yolov8n_nodfl.onnx`) **não foram renomeados** — manter rastreabilidade de tudo que já rodou em release. Equivalência em formato novo está documentada na seção "Modelos ONNX exportados" como referência.

**APK 1.0.22 não é afetado pelo rename** — Buildozer empacota o ONNX dentro do APK (auto-contido), com o `mobile/main.py` e o ONNX já compilados como resources. O rename no `models/` afeta apenas builds futuros e scripts desktop (`test_webcam.py`). Pra testar o APK 1.0.22 no S24, instalar normalmente.

### 10/05/2026 — APK 1.0.22 gerado + limpeza D: completa + RAM máx Z390 confirmada (TASK 4)

Claude Code executou TASK 4 com sucesso. Validação reproduziu **mAP50 = 69.21% / mAP50-95 = 51.15%** (batch=64 vs 128 do treino, diferença marginal esperada). Export ONNX nodfl saiu em **12.79 MB** (safe < 15 MB pra OpenCV 4.5.1 Android), com 16 nós DFL removidos e opset 12.

**APK gerado:** `bin/animaldetector-1.0.22-arm64-v8a_x86_64-debug.apk` (166.5 MB, ~43 min de build — primeira no WSL novo, baixou NDK). Inclui x86_64 desnecessariamente — pode encolher pra ~120 MB no release final restringindo `android.archs = arm64-v8a` no buildozer.spec.

**Métricas — pontos de atenção:**
- Top 5 classes (≥ 90% AP50): truck, train, traffic light, motorcycle, person.
- Bottom 5: stop sign 20.10%, airplane 45.19%, **car 54.60%** ⚠️, bench 58.30%, bus 59.03%.
- `car` baixo é o ponto crítico — classe core, provável confusão com truck/bus por sobreposição de features. Monitorar nos testes de campo; se der falsos cruzados (caminhão↔carro), pode justificar fine-tune balanceando essas classes.
- Fauna BR (classes 80-94) não aparece no top/bottom — provável faixa 60-80% AP50, consistente com mAP50 global. **Validação em campo é prioridade.**

**Detalhe do export:** Claude Code esqueceu de passar `--out` no `export_unified.py` → ONNX saiu como `fulldet_yolov8n_nc95_v3_m692_nodfl.onnx` (nome genérico) em vez de `full_detection_v3_nano_nodfl.onnx`. `mobile/main.py` foi atualizado consistente com o nome genérico, então funciona. Renomear no próximo rebuild quando houver outra razão pra rebuildar (não vale 45 min só por convenção).

**Limpeza D: completa** (verificada via PowerShell): apagados `D:\datasets\coco` (cópia HDD redundante, COCO em C:\ tem 118.287 train + 10.000 val íntegros) e `D:\wsl_backup\Ubuntu-24.04.tar` (backup WSL antigo). **+102.6 GB liberados** (acima dos 88 esperados — sobra de cache residual). D: agora com **880 GB livres** de 1.86 TB.

**Hardware — Z390 aceita até 64 GB DDR4 (4 slots)** — confirmado via `Get-CimInstance Win32_PhysicalMemoryArray`. Está com 32 GB hoje (2× 16 GB Kingston mismatched). **Decisão: NÃO upgradar RAM.** DDR4 não migra pra AM5 (DDR5) → capital morto em ~6 meses. Se aparecer necessidade de RAM em treino antes de novembro/2026, considerar 32 GB DDR4 usado de marketplace (R$ 300-500), descartável sem dor. Caso contrário, manter 32 GB e ir direto pra 64 GB DDR5 no AM5.

**Próxima ação humana:** instalar APK no S24 (`adb install bin/animaldetector-1.0.22-arm64-v8a_x86_64-debug.apk`) e validar no campo: (1) app abre sem crash, (2) `max_score > 0` no log (confirma OpenCV DNN processando ONNX corretamente, antes era o bug do modelo > 15 MB), (3) detecção de person, (4) detecção de fauna BR, (5) car vs truck (ponto de atenção).

### 10/05/2026 — Crash do `full_detection_v3_nano` no epoch 136 + Opção A (aceitar best.pt)

Treino concluiu **135 de 150 epochs** com sucesso. Crash no epoch 136 por **CUDA OOM no pin_memory thread**: o `close_mosaic=15` desativou mosaic augmentation a partir do epoch 135, e sem mosaic (que funde 4→1 imagens) o DataLoader passou a processar imagens individuais maiores → spike VRAM de 16.6 GB → 17.3 GB com `batch=128`, estourando os 24 GB.

**Pesos íntegros:**
- `best.pt` (epoch 128): mAP50 = **69.5%**, mAP50-95 = **50.9%**.
- `last.pt` (epoch 135): mAP50 = 69.0%.
- Plateau confirmado desde epoch 127 (ganhos < 0.1% nos últimos 8 epochs).

**Decisão consolidada — Opção A:** aceitar `best.pt` e exportar agora, sem retomar treino. Comparativo das opções (com ROI):

| Opção | Tempo extra | Ganho mAP50 | Risco | ROI |
|-------|-------------|-------------|-------|-----|
| **A** — Exportar best.pt agora | **0 h** | 0% (já 69.5%) | Nenhum | **Altíssimo** |
| B — Resume com `batch=64` | ~3.5 h | +0.3-0.8% | Médio (LR efetivo cai) | Baixo |
| C — Resume com `batch=96` | ~3.5 h | +0.5-1.0% | Baixo | Médio |

Razão: ganho marginal de B/C não compensa 3.5h quando o modelo já está em qualidade de produção. Desbloqueia o ciclo APK → S24 imediatamente. Se necessário refinar, retomada vira segunda rodada com lições aprendidas.

**Lição arquivada (não repetir):** `close_mosaic=15` perto do final do treino + `batch=128` em 24 GB VRAM = risco de OOM no pin_memory thread. Mitigações pra próximos treinos:
- Usar `close_mosaic=5` em vez de 15 (menos exposição).
- Ou reduzir batch proativamente nos últimos epochs (`batch=96` quando close_mosaic ativa).
- Ou `--gpu-mem-fraction 0.9` pra reservar margem.

Resultado é **excepcional** pra YOLOv8n nano com 95 classes — comparável/melhor que YOLOv8n oficial em COCO 80 classes (~52% mAP50). TASK 4 ativa pro Claude Code: validação + export ONNX nodfl + atualizar `mobile/main.py` + rebuild APK + limpeza D: (~88 GB).

### 08/05/2026 — Samsung 970 Pro 2TB comprado (R$ 1200 + seguro)

Após análise comparativa de 7 SSDs (NV3 500GB, SN350 2TB, T500 1TB, SN850X 2TB, 990 Pro 2TB, KC3000 2TB, T710 2TB Gen5, 970 Pro 2TB), **escolhido o Samsung 970 Pro 2TB por R$ 1200** — última peça em estoque, descontinuado em 2019.

Justificativa final pelo MLC:
- Workload do projeto (dataloader YOLO + carregamento LLM local) é **leitura aleatória 4K dominante**, não sequencial sustentada.
- MLC NAND é tecnicamente uma geração acima de TLC (1.5× IOPS aleatório, 2× endurance) e duas acima de QLC.
- Gen3 do drive bate o teto da plataforma atual (Z390) — qualquer Gen4/5 daria mesma performance hoje.
- R$ 1200 = R$ 0,60/GB pra MLC + DRAM + 1200 TBW = melhor relação IOPS-aleatório-por-real da lista.
- Risco de "última em estoque" mitigado por seguro.

Ao receber: rodar SMART (CrystalDiskInfo) antes de uso. Se TBW > 200 ou Power-On Hours > 5000h, acionar seguro.

### 08/05/2026 — Plano de upgrade definido: NVMe agora + AM5 fim do ano (HEDT descartado)

Conversa de planejamento de hardware com base no inventário completo do setup atual + objetivo do Maicon de rodar 3 GPUs simultâneas pra IAs locais em paralelo (Qwen3-Coder + modelos de visão pra câmeras de segurança).

**Inventário descoberto:** o Maicon já tem 2 PSUs Corsair (RM 1000W + RM 850W = 1850W) sincronizadas via Add2PSU, 3 GPUs (1× 3090 + 2× 3080), e setup riser-based (3090 dentro, 3080 #1 fora via riser x16-x4, 3080 #2 desligada por falta de slot). A limitação atual é **slots PCIe da Z390 microATX**, não power.

**Decisão consolidada:**

1. **Imediato:** comprar **NVMe WD SN350 2TB** (R$ 1531). PCIe Gen3 nativo, casa com Z390 sem desperdício. Migra pra plataforma futura.

2. **Fim de 2026:** trocar **só placa-mãe + CPU + RAM + cooler** (AM5 high-end com Ryzen 9 9950X + X870E topo + 64 GB DDR5). Custo R$ 8-12k. Aproveita PSUs, GPUs, NVMe, Add2PSU, risers existentes.

3. **NÃO comprar:** RAM DDR4 (não migra pra DDR5), PSU nova (as 2 atuais cobrem setup de 3 GPUs com folga), Threadripper (R$ 22-32k+ sem ganho real).

**Lição arquivada — confusão técnica corrigida:**

PCIe x16 elétrico **NÃO é necessário** pra rodar IAs locais em paralelo. O modelo é transferido pra VRAM uma vez no carregamento (segundos a minutos); depois disso, **toda inferência é GPU-internal e não usa PCIe**. PCIe x4 do chipset entrega tokens/segundo idênticos a PCIe x16 pra qualquer LLM/CNN/Transformer rodando inferência local.

PCIe x16 importa em: (a) treino multi-GPU com all-reduce intenso em modelos grandes; (b) renderização em tempo real (jogos, streaming); (c) certos workloads de profissionais com CPU↔GPU constante. **Nada disso bate no escopo "modelos pequenos pra câmeras de segurança"** do projeto.

Conclusão técnica: HEDT (Threadripper, Xeon W) é **overkill** pra esse caso de uso. Plataforma consumer high-end com 3 slots PCIe (x16/x4/x4 misto) entrega 100% do mesmo throughput em inferência paralela por 1/3 do custo.

### 08/05/2026 — Crash por OOM no mixup com `cache='disk' + workers=6` (lição aprendida)

> ⚠️ **Reconstrução parcial (Cowork, 10/05/2026 noite).** O conteúdo desta entrada e das duas seguintes (Diagnóstico de hardware + Limpeza extensa do C:) foi perdido em edit anterior do `PROJECT_STATE.md` neste mesmo dia (10/05 noite, durante gravação do D09 LiteRT/AICore). Reconstrução abaixo é best-effort baseada em `system_report.txt`, na seção "Hardware real" deste arquivo e em sinais indiretos. Se notar fato errado, corrigir manualmente. Versão original do PROJECT_STATE.md **não estava versionada no git** até esta sessão.

Re-lançamento do `full_detection_v3_nano` com a config "otimizada" (`cache='disk'` + `WORKERS=6`) crashou no início do epoch 1 — kernel OOM-killer derrubou o processo de treino. Combinação do mixup (que duplica tensores em RAM durante augmentação) com 6 workers paralelos saturou a RAM 32 GB DDR4-2400 dual-channel da Z390.

**Diagnóstico:**
- Cada worker carrega buffer próprio de imagens + cópias do mixup. Com `cache='disk'` o overhead por worker é menor que `cache=True` (RAM full), mas ainda significativo.
- 6 workers × overhead do mixup × batch atual estourou o limite seguro.
- Sem swap configurado adequadamente (NVMe ausente em 08/05; só SATA SSD KINGSTON 480 GB + HDD 2 TB).

**Lição aprendida:** na plataforma atual (Z390 + 32 GB DDR4-2400), limite seguro com `cache='disk'` é **4 workers**, não 6. Documentado também na seção "Próximo upgrade" como motivador da plataforma AM5 + 64 GB DDR5 (fim 2026). `cache=True` (RAM full) permanece proibido até upgrade.

**Próxima ação:** rebaixar workers de 6 → 4. Re-test passou (treino `v3_nano` que rodou até crash do epoch 136 — separado deste OOM — usou 4 workers).

---

### 08/05/2026 — Diagnóstico completo de hardware via `check_system.ps1` (RECONSTRUÍDO)

> ⚠️ **Reconstrução parcial (Cowork, 10/05/2026 noite).** Conteúdo original perdido em edit prévio. Reconstruído a partir de `system_report.txt` (presente no projeto) e da seção "Hardware real" deste arquivo.

Maicon rodou `check_system.ps1` em 08/05/2026 16:10:54 (após dia inteiro lutando com OOMs e crashes intermitentes) pra mapear definitivamente o estado da plataforma. Output salvo em `system_report.txt`. Combinado com inventário manual das 3 GPUs e PSUs sincronizadas, esse diagnóstico foi o que destravou a decisão de upgrade.

**Achados-chave (do `system_report.txt`):**
- **OS:** Windows 11 Pro 64 bits (build 26200), hostname DESK-MAICON, uptime 21.5h.
- **CPU:** Intel Core i7-9700F @ 3.0 GHz, 8 cores físicos / 8 threads (sem HT), L3 12 MB. Soquete LGA1151 — fim de linha, sem upgrade no soquete.
- **RAM:** 32 GB DDR4-2400 dual-channel (2× 16 GB Kingston — KHX2400C15/16G + KF3200C16D4/16GX rodando subclocked). Plataforma máxima Z390: 64 GB.
- **Motherboard:** Gigabyte Z390 M GAMING-CF (microATX), BIOS F9 de 2021. Slots PCIe utilizáveis na prática: 2 (limitação do form factor — terceira GPU sem onde encaixar).
- **Storage:** SSD Kingston SA400 480 GB (SATA, sistema) + HDD 2 TB SATA (datasets). **Sem NVMe** — gargalo confirmado no IOPS aleatório 4K do dataloader YOLO.
- **GPUs (inventário separado):** 1× RTX 3090 24 GB (slot principal) + 1× RTX 3080 10 GB (riser PCIe x16→x4) + 1× RTX 3080 10 GB **desligada** (sem slot disponível).
- **PSUs:** Corsair RM 1000W + RM 850W = 1850W, sincronizadas via Add2PSU. Sobra suficiente pra 3 GPUs.

**Decisões disparadas por este diagnóstico (entradas seguintes mais abaixo no arquivo):**
1. Comprar NVMe Samsung 970 Pro 2TB **imediato** (R$ 1200) — ataca gargalo IOPS sem precisar mexer em plataforma.
2. Plataforma nova **só fim 2026** (AM5 high-end, R$ 8-12k) — aproveita PSUs/GPUs/NVMe existentes.
3. **HEDT (Threadripper/Xeon W) descartado** — overkill pra workload de inferência paralela.
4. **Não comprar:** DDR4 extra (não migra pra DDR5), PSU nova (atuais bastam), Threadripper.

Ver também a seção "Hardware real" deste arquivo (linhas 181+) para o resumo persistente que ficou após a decisão.

---

### 08/05/2026 — Limpeza extensa do C: (feita pelo Claude Code além da TASK 4) (RECONSTRUÍDO)

> ⚠️ **Reconstrução parcial (Cowork, 10/05/2026 noite).** Conteúdo original perdido em edit prévio. Recuperação limitada — descrição genérica baseada em sinais indiretos (referência cruzada à TASK 4 na entrada "APK 1.0.22 gerado + limpeza D: completa + RAM máx Z390 confirmada").

Durante TASK 4 (limpeza do **D:** + verificação RAM máx Z390), Claude Code também executou limpeza ad-hoc no **C:** além do escopo original — liberou espaço de logs antigos, caches de build Buildozer, downloads expirados de WSL e outros temporários. Detalhamento exato dos arquivos limpos **foi perdido** na edit do 10/05 noite; se for crítico recuperar, consultar histórico de comandos do Antigravity da sessão 08/05 ou logs em `_agent/logs/` (`CLAUDE_SURGERY.log` pode ter pistas).

**Lição que ainda vale:** Claude Code expandir escopo além da TASK pré-acordada pode ser bom (libera espaço crítico) mas precisa registrar **exatamente** o que mudou no `RESULT.md`, pra não perder rastro caso o STATE seja editado depois.

---
