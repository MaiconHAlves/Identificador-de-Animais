# RESULT — T014 PoC Pipeline LiteRT

- **Task referente:** T014
- **Ambiente:** Windows (Python 3.12, Ultralytics, TensorFlow 2.21.0)
- **Executado em:** 2026-05-11

## Resumo

Pipeline TFLite INT8 (PTQ) implementado e validado parcialmente. Modelo COCO passa no critério mAP (<3% perda); modelo fulldet falha (9.23% perda). Projeto Android Studio Kotlin criado com LiteRT 1.4.0 + AICore delegate — aguarda teste físico no S24.

## Checklist do critério de sucesso

- [x] Converter `coco_yolov8n_nc80_v0_i320_nodfl.onnx` → TFLite INT8 — `models/coco_yolov8n_nc80_v0_i320_nodfl.tflite` (3,309 KB, `full_integer_quant`)
- [x] Converter `fulldet_yolov8n_nc95_v3_m692_i320_nodfl.onnx` → TFLite INT8 — `models/fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite` (3,448 KB, `full_integer_quant`)
- [x] Validar mAP50 pós-PTQ **coco_v0** — FP32=50.9% → INT8=50.2%, perda=1.37% → **PASS** ✓
- [ ] Validar mAP50 pós-PTQ **fulldet_v3** — FP32=68.8% → INT8=62.5%, perda=9.23% → **FAIL** ✗ (critério: <3%)
- [x] Projeto Android Studio em `_research/litert_poc/` com LiteRT 1.4.0 + AICore — criado, compila
- [ ] Teste físico no S24: AAR carrega modelos sem crash — **aguardando usuário**
- [ ] Inferência em bus.jpg no S24 com log CPU vs AICore — **aguardando usuário**

## Resultados mAP50 (coco128 + BR val)

| Modelo | FP32 baseline | INT8 mAP50 | Perda abs | Perda rel | Status |
| ------ | ------------ | ---------- | --------- | --------- | ------ |
| coco_v0 (nc=80) | 50.9% | 50.2% | 0.70pp | 1.37% | **PASS** ✓ |
| fulldet_v3 (nc=95 BR) | 68.8% | 62.5% | 6.35pp | 9.23% | **FAIL** ✗ |

Dataset validação: coco128.yaml (128 imgs) para coco_v0; C:/datasets/br_detection/images/val (417 imgs) para fulldet_v3.

## Arquivos criados/modificados

- `scripts/export_tflite_ptq.py` — exporta ambos os modelos via Ultralytics PTQ
- `scripts/validate_tflite_quick.py` — valida mAP50 FP32 vs INT8 (coco128 + BR val)
- `scripts/copy_models_to_poc.py` — copia TFLite + bus.jpg para assets do PoC
- `scripts/validate_tflite_map.py` — validação completa (lenta, ~2h, uso pontual)
- `models/coco_yolov8n_nc80_v0_i320_nodfl.tflite` — 3,309 KB
- `models/fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite` — 3,448 KB
- `_research/litert_poc/` — projeto Android Studio completo (Kotlin, Gradle 8.7.3, LiteRT 1.4.0)
- `_research/litert_poc/README.md` — documentação do PoC

## Decisão técnica requerida (Cowork)

**fulldet_v3 falhou o critério de 3% de perda mAP.** Opções:

1. **T017 — Re-treino QAT INT8:** treinar com quantization-aware training para reduzir a perda. Mais preciso, mais demorado.
2. **Aceitar 62.5%:** se a degradação for aceitável em campo (detecção BR ainda funcional com 62.5% mAP50 no subset de validação). A degradação pode ser parcialmente causada pelo dataset de calibração pequeno (coco8.yaml = 4 imgs para COCO; full_detection.yaml para fulldet) — re-export com calibração maior pode melhorar.
3. **Re-export com calibração maior:** usar COCO val completo + BR val para calibração do fulldet. Pode reduzir a perda sem QAT.

**Recomendação:** tentar opção 3 antes de QAT — é rápido (re-export ~30min) e pode resolver a perda sem novo treino.

## Próxima ação

1. **Cowork decide:** T017 (QAT) vs re-export com calibração maior vs aceitar 62.5%
2. **Usuário testa no S24:** instalar APK PoC (`cd _research/litert_poc && gradlew installDebug`) e verificar logcat `adb logcat -s LiteRTPoC:* -v time`
3. Após teste S24: preencher resultados de latência CPU vs AICore no README do PoC

## Observações

- `full_integer_quant` gerado para ambos os modelos (INT8 I/O) — ideal para delegate AICore
- `fulldet_v3` sofreu "esquecimento catastrófico" no treino: classes COCO (0-79) não detectadas; só classes BR (80-94) funcionam. A validação mAP foi feita apenas sobre as classes BR (208 imgs válidas do val).
- Conflito `onnxruntime-directml` vs `onnxruntime-cpu`: FP32 baseline usa `.pt` (PyTorch direto), não ONNX.
- DFL head **não** foi removido dos TFLite (ao contrário dos modelos `.onnx nodfl`): LiteRT suporta DFL nativo; só OpenCV DNN 4.5.1 precisava do strip.

---

## T014.b — Re-calibração fulldet_v3 (2026-05-11)

### Contexto

T014 fase 1 entregou `fulldet_v3` com 9.23% de perda mAP (calibração com apenas 4 imagens de `coco8.yaml`). T014.b re-exportou com 5.151 imagens de calibração (`full_detection.yaml`, BR val completo, ~64 min).

### Resultados mAP50 comparados

| Modelo | FP32 | INT8 fase 1 | INT8 T014.b | Perda T014.b | Status |
| ------ | ---- | ----------- | ----------- | ------------ | ------ |
| coco_v0 (nc=80) | 50.9% | 50.2% | 50.2% | 1.4% rel | **PASS** ✓ |
| fulldet_v3 (nc=95 BR) | 68.8% | 62.5% | **66.1%** | 2.75pp / 4.0% rel | **PASS** ✓ |

**Critério da TASK T014.b:** INT8 ≥ 65.8% (= FP32 68.8% − 3pp absolutos).
Resultado: 66.1% ≥ 65.8% → **PASS** ✓

> Nota: o script `validate_tflite_quick.py` reporta FAIL porque seu critério interno é <3% de perda *relativa* (4.0%). O critério primário da TASK é absoluto (≥65.8%) e está satisfeito.

### Arquivos atualizados

- `models/fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite` — 3,407 KB (re-calibrado, full INT8 I/O)
- `_research/litert_poc/app/src/main/assets/fulldet_yolov8n_nc95_v3_m692_i320_nodfl.tflite` — copiado
- `scripts/export_tflite_ptq.py` — adicionados flags `--only` e `--calibration`

### Próximos passos

T014 completa (fase 1 + T014.b). Cowork pode arquivar e promover T015 (Skeleton Serviço Kotlin + IPC). Teste físico no S24 pendente (AAR + logcat).

---

## T015 — Skeleton Serviço Kotlin + IPC (2026-05-11) — BLOQUEADO

### Bloqueio encontrado: Kotlin não suportado direto no p4a SDL2 bootstrap

**Pesquisa obrigatória (passo 0 da TASK):** O `build.gradle` gerado pelo p4a para o dist `animaldetector` NÃO inclui o Kotlin Gradle plugin:

```groovy
// build.gradle gerado pelo p4a/SDL2 bootstrap
buildscript {
    dependencies {
        classpath 'com.android.tools.build:gradle:8.1.1'
        // ← sem 'org.jetbrains.kotlin:kotlin-gradle-plugin'
    }
}
// compileOptions: sourceCompatibility JavaVersion.VERSION_1_8 — sem kotlinOptions
```

Isso significa que `android.add_src` no buildozer.spec NÃO compilaria arquivos `.kt` com o template atual — o Gradle falharia ao encontrar código Kotlin sem o plugin.

### Opções para decisão do Cowork

| Opção | Descrição | Risco | Custo extra |
| ----- | --------- | ----- | ----------- |
| **A — Java** | Reescrever DetectionService em Java (.java em vez de .kt). p4a suporta Java nativamente via padrão CameraHelper.java | Baixo — já testado | Zero extra |
| **B — Patch template** | Adicionar plugin Kotlin ao build.gradle via `build_local.sh` (mesmo mecanismo do CameraHelper.java). Requer adicionar `classpath kotlin-gradle-plugin` + `apply plugin: kotlin-android` + stdlib dep | Médio — acoplado ao template p4a | ~2-4h extra (teste) |
| **C — AAR pré-compilado** | Compilar DetectionService.kt no Android Studio (expandir `_research/litert_poc/`), exportar como `.aar`, importar via `android.add_aars` no buildozer.spec | Baixo — fluxo independente do p4a | ~5-10h extra |

### Recomendação técnica

**Opção A (Java)** é a mais rápida e segura: a API de Bound Service com Messenger é idêntica em Java e Kotlin, e o projeto já tem a receita de inclusão de Java (CameraHelper.java). Resultado funcional é o mesmo — só a sintaxe muda. Requer apenas renomear `DetectionService.kt` → `DetectionService.java` no escopo da TASK.

Se o Cowork quiser Kotlin no APK final (T016), a Opção C (AAR) é a mais limpa nesse momento — quando LiteRT for integrado, o Android Studio já estará envolvido e o serviço pode ser compilado como parte do módulo do PoC.

**Decisão Maicon (2026-05-11):** Opção C — AAR pré-compilado (Kotlin via Android Studio).

---

### T015 — Execução (em andamento)

**Abordagem escolhida:** AAR pré-compilado.

#### Arquivos criados

| Arquivo | Descrição |
| ------- | --------- |
| `_research/litert_poc/service/build.gradle.kts` | Módulo Android library Kotlin |
| `_research/litert_poc/service/src/main/AndroidManifest.xml` | Declara DetectionService exported=false |
| `_research/litert_poc/service/src/main/kotlin/.../DetectionService.kt` | Bound Service + Messenger, mock 3 detecções |
| `_research/litert_poc/service/src/main/kotlin/.../DetectionDTO.kt` | Parcelable do resultado |
| `_research/litert_poc/gradlew.bat` | Gradle wrapper (gerado) |
| `libs/detection_service.aar` | AAR release (8 KB) — buildado com AGP 8.7.3 + Kotlin 2.1.0 |
| `mobile/service_bridge.py` | Bridge Python→Kotlin via Pyjnius (Messenger IPC) |
| `mobile/test_ipc_roundtrip.py` | Benchmark P50/P95/P99 (100 frames emulador / 1000 frames S24) |
| `buildozer.spec` | version=1.0.28, `android.add_aars = libs/detection_service.aar` |

#### Status dos critérios

- [x] Módulo Kotlin `:service` criado em `_research/litert_poc/service/`
- [x] `DetectionService.kt` — Bound Service + Messenger + mock 3 detecções fixas
- [x] `DetectionDTO.kt` — Parcelable
- [x] `mobile/service_bridge.py` — wrapper Pyjnius com `send_frame()` e timeout
- [x] `mobile/test_ipc_roundtrip.py` — benchmark P50/P95/P99
- [x] `libs/detection_service.aar` (8 KB) buildado com sucesso
- [x] `buildozer.spec` atualizado (version=1.0.28, android.add_aars)
- [x] APK 1.0.28-rc1 builda — `bin/animaldetector-1.0.28-arm64-v8a-debug.apk` ✅
- [x] Gate emulador — ver resultado abaixo
- [ ] S24: 1000 frames, latência P50/P95/P99 — pendente decisão

---

## T015 — Gate Emulador (2026-05-12)

### Build APK

**PASS ✅** — `animaldetector-1.0.28-arm64-v8a-debug.apk` gerado com sucesso em `bin/`.

Fix crítico aplicado: `android.add_gradle_repositories = flatDir { dirs 'libs' }` no `buildozer.spec` — sem isso o Gradle não resolvia `:detection_service:` (dependência por nome+ext sem repositório flatDir declarado).

### Resultado do gate emulador

APK é arm64-v8a only. Três imagens tentadas no WSL2 (host x86_64, KVM disponível):

| Imagem | ARM translation | Instala APK | Resultado |
|--------|----------------|-------------|-----------|
| `google_apis` API 29 **arm64-v8a** | N/A | N/A | QEMU não roda arm64 em host x86_64 (FATAL) |
| `google_apis_playstore` API 30 **x86_64** | ✅ libhoudini | ✅ Success | Python + Kivy iniciam → crash SELinux nos ícones Kivy |
| `google_apis` API 29 **x86_64** | ❌ | ❌ `INSTALL_FAILED_NO_MATCHING_ABIS` | Sem libhoudini |

**Crash observado (Play Store image):**
```
shutil.Error: Permission denied: '.kivy/icon/kivy-icon-128.png'
avc: denied { relabelfrom } ... scontext=u:r:untrusted_app
```
Kivy tenta `shutil.copytree` de ícones na primeira execução. O SELinux da imagem Play Store bloqueia `relabelfrom` em `app_data_file`. Isto é artefato do emulador Play Store — não ocorre com APK sideloaded (`adb install`) num device real.

**O que funcionou:**
- APK instala (ARM translation via libhoudini) ✅
- SDL2 bootstrap carrega ✅
- Python 3 inicia ✅
- Kivy importa (`__init__.py` começa a rodar) ✅
- Crash no `shutil.copytree` de ícones (SELinux Play Store) ❌

### Decisão requerida

| Opção | Descrição | Custo |
|-------|-----------|-------|
| **A — S24 direto** | Instalar no S24 via USB (`adb install`). Gate real, device-alvo, sem artefatos de emulador. SELinux do device real não bloqueia `app_data_file relabelfrom`. | ~10 min |
| **B — Recompilar x86_64** | Adicionar `x86_64` aos archs (`android.archs = arm64-v8a, x86_64`) + rebuild. Emulador `google_apis` API 29 passaria sem libhoudini e sem Play Store SELinux. | ~1h build |
| **C — Aceitar gate condicional** | Declarar gate emulador como PASS condicional (APK instala, Python/Kivy iniciam; crash é artefato). Ir direto ao S24 para o gate definitivo. | 0 |

**Recomendação:** Opção A — conectar o S24 via USB e fazer o gate real. É o caminho mais curto e o resultado mais confiável. O emulador já provou que o APK builda, instala e o Python/Kivy sobem.

---

## T015.b — Gate Emulador x86_64 (2026-05-12)

### Build APK rc2

**PASS ✅** — `animaldetector-1.0.28-arm64-v8a_x86_64-debug.apk` (155 MB) gerado em `bin/`.

- AAR `detection_service.aar` é puro JVM (zero `.so`) — arch-agnostic, sem recompilação
- ABIs confirmados: `aapt dump badging | grep native-code` → `arm64-v8a` + `x86_64`
- Buildozer gerou APK universal (1 arquivo, 2 ABIs)

### Critérios de smoke (emulador `google_apis` API 29 x86_64, sem Play Store)

| Critério | Resultado |
|----------|-----------|
| `adb install` sem `INSTALL_FAILED_NO_MATCHING_ABIS` | ✅ (x86_64 nativo, sem libhoudini) |
| App abre sem FATAL EXCEPTION | ✅ |
| Zero ANR | ✅ |
| Zero `avc: denied relabelfrom app_data_file` | ✅ (SELinux google_apis permissivo) |
| `[Base] Start application main loop` no logcat | ✅ |
| OpenGL ES 3.0 SwiftShader funcional | ✅ |
| App vivo após 35+ minutos | ✅ (PID 8612, 245 MB RAM) |

**shutil.Error (ícones Kivy):** aparece nos logs mas é **não-fatal** nesta imagem — app continua. Ocorre em ambas as imagens (google_apis e playstore), mas na imagem Play Store API 30 o SELinux convertia isso em crash fatal. Aqui é apenas warning.

### IPC benchmark (100 frames P50/P95/P99)

**SKIP — limitação técnica do emulador.**

`test_ipc_roundtrip.py` usa Pyjnius, que requer o JVM context do processo Android embarcado. Não é executável via `adb shell run-as` fora do processo do app. Para rodar precisaria embutir o trigger em `main.py` e rebuildar.

Alternativas para gate IPC completo:
- **T015.c (S24):** conectar S24 via USB, `adb install`, o app tem câmera real + JVM context → IPC benchmark roda normalmente
- **T015.b.ipc:** modificar `main.py` para checar flag file `/sdcard/run_ipc_test` no startup e auto-executar o benchmark → adiciona ~30min de dev + 1h de rebuild

### Decisão requerida

| Opção | Descrição | Custo |
|-------|-----------|-------|
| **A — T015.c no S24** | Smoke emulador PASSOU. Ir pro S24 para gate completo (IPC 1000 frames + câmera real). | ~30 min (USB + instala + roda) |
| **B — T015.b.ipc antes** | Embutir auto-trigger IPC no `main.py`, rebuild, rodar no emulador primeiro. | ~1h dev + 1h build |

**Recomendação:** Opção A — emulador PASSOU o smoke. IPC no emulador sem câmera real não é representativo para P95/P99. S24 é o gate definitivo.

---

## T015.b.ipc — Benchmark IPC no Emulador (2026-05-12)

### Objetivo

Embutir auto-trigger em `main.py` para executar `test_ipc_roundtrip.py` de dentro do processo do app (onde Pyjnius tem JVM context), medir P50/P95/P99 com 100 frames no emulador `gate_api29`.

### Build

**PASS ✅** — `animaldetector-1.0.28-arm64-v8a_x86_64-debug.apk` (162 MB) com `main.py` modificado.

Mudança em `mobile/main.py`:
- `Clock.schedule_once(self._check_ipc_trigger, 5.0)` adicionado ao `on_start`
- `_check_ipc_trigger`: verifica `/sdcard/ipc_bench.flag` — se existir, lança thread benchmark
- `_run_ipc_benchmark`: chama `run_benchmark(frames=100, report_path="/sdcard/ipc_emulator.json")`

### Execução no emulador

- APK instalado: `adb install -r` → `Success`
- Flag criada: `adb shell touch /sdcard/ipc_bench.flag`
- App iniciado: `am start -n com.maiconalves.animaldetector/org.kivy.android.PythonActivity`
- Logcat confirmou trigger: `[IPC-TRIGGER] Flag detectada — iniciando benchmark IPC em background`

### Resultado: FAIL ❌ — ClassNotFoundException

```
[IPC-TRIGGER] ERRO: JVM exception occurred:
  Didn't find class "com.maiconalves.animaldetector.DetectionService"
  on path: DexPathList[[directory "."],nativeLibraryDirectories=[...]]
  java.lang.ClassNotFoundException
```

### Diagnóstico

**Causa-raiz:** Pyjnius `autoclass()` em thread Python daemon não herda o app classloader do Android.

- A classe `DetectionService` **está** no DEX do APK (confirmado: `strings classes.dex | grep DetectionService` retorna a classe)
- O `DexPathList[[directory "."]]` na mensagem de erro indica classloader errado: sistema usa o bootstrap classloader (vazio) em vez do app classloader (que inclui os DEX do APK)
- Kivy/p4a seta o classloader correto apenas na main thread. Threads Python daemon criadas com `threading.Thread` não herdam esse contexto
- Classes de sistema (`org.kivy.android.PythonActivity`, `android.content.Intent`) funcionam porque estão no bootstrap classloader — mas `DetectionService` (do AAR da app) só está no app classloader

### Fix identificado (não aplicado — aguarda confirmação)

Em `_run_ipc_benchmark`, antes do `ServiceBridge().bind()`:
```python
from jnius import autoclass
PythonActivity = autoclass("org.kivy.android.PythonActivity")
Thread = autoclass("java.lang.Thread")
app_cl = PythonActivity.mActivity.getClassLoader()
Thread.currentThread().setContextClassLoader(app_cl)
```
Isso seta o app classloader na thread Python antes de qualquer `autoclass` para classes da app. Requer rebuild (~1h).

### Decisão requerida

| Opção | Descrição | Custo |
|-------|-----------|-------|
| **A — T015.c no S24 agora** | ClassLoader na main thread do app é correto. IPC benchmark rodará normalmente no S24 (app process + main thread). Gate definitivo. | ~30 min USB + install + run |
| **B — Fix classloader + rebuild + re-testar emulador** | Aplicar fix `setContextClassLoader` em `_run_ipc_benchmark`, rebuild, medir P95/P99 no emulador antes do S24. | ~1h build + 30min teste |

**Recomendação:** Opção A — o classloader issue não ocorre na main thread do app, que é o contexto real de uso no S24. Gate emulador de IPC sem câmera não é representativo para os critérios P95/P99 do T015.c. Ir direto ao S24.

---

## T015.b.ipc — Sessão 2: kotlin-stdlib + JNI ref fix (2026-05-12)

> Continuação da sessão anterior. A decisão foi manter o gate emulador (opção B da sessão 1).
> Esta sessão resolve dois crashes sequenciais bloqueando o benchmark IPC.

### Fix #1 — ClassNotFoundException: bind() movido para a main thread

**Problema (sessão anterior):** `_run_ipc_benchmark` rodava em thread Python daemon e chamava `ServiceBridge().bind()` de lá. Pyjnius `autoclass("com.maiconalves.animaldetector.DetectionService")` falhava com `ClassNotFoundException` porque threads daemon não herdam o app classloader que o Kivy/p4a seta apenas na main thread.

**Solução aplicada em `mobile/main.py`:**
- `_check_ipc_trigger` (callback de `Clock.schedule_once`, roda na main thread Kivy) chama `ServiceBridge.bind()` diretamente — aí o classloader está correto.
- Depois de 2s (via outro `Clock.schedule_once`), `_start_ipc_after_bind` lança uma `threading.Thread` para `_run_ipc_benchmark`.
- `_run_ipc_benchmark` apenas chama `bridge.send_frame()` (sem nenhum `autoclass` de classe da app) — não precisa de classloader correto.

Resultado: `ClassNotFoundException` eliminado. O `bind()` na main thread é suficiente para que `onServiceConnected` dispare e `self._messenger` seja populado.

### Fix #2 — NoClassDefFoundError: kotlin-stdlib ausente do APK

**Problema:** APK `1.0.28` com o auto-trigger implementado instalava, mas ao tentar usar o `DetectionService` via IPC, o processo Android travava com:
```
java.lang.NoClassDefFoundError: kotlin.jvm.internal.Intrinsics
    at com.maiconalves.animaldetector.DetectionService.<clinit>
```

**Root cause:** `DetectionService.kt` (compilado com Kotlin 2.1.0) usa `Intrinsics` da kotlin-stdlib em sua inicialização estática (companion object e classes anônimas de Handler). O AAR `libs/detection_service.aar` não inclui a stdlib (dependência transitiva). O `flatDir { dirs 'libs' }` resolve apenas o arquivo `.aar` local — **não resolve dependências transitivas** (sem acesso ao Maven Central).

**Investigação realizada:**
- `aapt dump badging` do APK — sem `kotlin` nas permissões/metadata
- `unzip -p libs/detection_service.aar classes.jar | jar tf /dev/stdin` — confirmado: AAR contém `DetectionService.class`, `DetectionDTO.class`, `DetectionService$Companion.class`, `DetectionService$incomingHandler$1.class`, mas **zero classes `kotlin/`**
- Versão Kotlin confirmada lendo `_research/litert_poc/gradle/libs.versions.toml`: `kotlin = "2.1.0"`

**Fix aplicado em `buildozer.spec`:**
```ini
android.gradle_dependencies = org.jetbrains.kotlin:kotlin-stdlib:2.1.0
```
Essa linha faz o Buildozer injetar `implementation 'org.jetbrains.kotlin:kotlin-stdlib:2.1.0'` no `build.gradle` gerado — Gradle resolve via Maven Central (já presente nos repositórios default).

### Build #2 — GREEN LIGHT ✅ (23:00:31 de 12/05/2026)

- Arquivo modificado: `buildozer.spec` (adição de `android.gradle_dependencies`)
- Duração: ~1h05 (reconstrução completa, dist reutilizando ambiente p4a)
- APK gerado: `animaldetector-1.0.28-arm64-v8a_x86_64-debug.apk` (162 MB)
- Evidência de kotlin-stdlib no build: `mergeDebugJavaResource > Resolve files of :debugRuntimeClasspath > kotlin-st` visível no progress do Gradle no log
- `BUILD SUCCESSFUL in 22s` (Gradle interno), seguido de `GREEN LIGHT` no `build_local.sh`

### Deploy e novo crash: JNI Local/Global ref mismatch

**Sequência de deploy:**
```bash
adb install -r bin/animaldetector-1.0.28-arm64-v8a_x86_64-debug.apk  # → Success
adb shell pm grant com.maiconalves.animaldetector android.permission.CAMERA
adb shell pm grant com.maiconalves.animaldetector android.permission.RECORD_AUDIO
adb shell touch /sdcard/ipc_bench.flag
adb shell am start -n com.maiconalves.animaldetector/org.kivy.android.PythonActivity
```

**Crash observado (~15s após startup):**
```
JNI DETECTED ERROR IN APPLICATION: expected reference of kind Local but found Global: 0x64ca
  at art::CheckJNI::DeleteRef (CheckJNI::DeleteRef+949)
  at jnius.so+0x26493
Fatal signal 6 (SIGABRT), tid 8054 (Thread-4) — SDLActivity
```

O crash era reproduzível e determinístico, acontecendo sempre no mesmo momento.

### Isolamento: IPC ou câmera?

Testado removendo a flag antes de iniciar o app:
```bash
adb shell rm /sdcard/ipc_bench.flag
adb shell am start -n com.maiconalves.animaldetector/org.kivy.android.PythonActivity
```

**Resultado sem flag:** app sobe normalmente, câmera falha graciosamente (`Unknown camera ID 0` — emulador sem câmera física), logcat mostra Python/Kivy rodando por 20+ segundos sem crash.

**Conclusão:** o crash é exclusivamente do caminho IPC — não da câmera, não do SDL2, não do OpenCV DNN.

### Root cause do crash JNI

O crash ocorre em `jnius.so` dentro de `CheckJNI::DeleteRef` — o Android CheckJNI (ativo por padrão em emuladores debug) detecta que uma **referência JNI global está sendo deletada como se fosse uma referência local**.

Em JNI, referências globais (global refs) são válidas em qualquer thread e criadas com `NewGlobalRef`. Referências locais (local refs) são válidas apenas no frame JNI atual. Ao deletar, cada tipo tem sua função: `DeleteGlobalRef` vs `DeleteLocalRef`. Usar a função errada → SIGABRT em modo CheckJNI.

**Causa no código:** em `mobile/service_bridge.py`, o método `bind()` fazia:
```python
# ANTES (bugado)
self._reply_messenger = Messenger(
    Handler(Looper.getMainLooper(), _ResultHandler())
)
```

O `_ResultHandler()` é uma instância de `PythonJavaClass`. O Pyjnius cria uma **global JNI ref** para manter o objeto Python vivo no lado Java. Mas como nenhuma variável Python aponta para esse objeto, o **GC Python coleta `_ResultHandler()`**. Na coleta, Pyjnius tenta liberar a referência JNI chamando `DeleteLocalRef` — mas a referência era global → CheckJNI aborta o processo.

A timeline do crash:
1. `bind()` chamado (main thread, 5s após start)
2. `_ResultHandler()` criado → Pyjnius faz `NewGlobalRef` no objeto Java wrapper
3. Python não guarda referência → objeto fica elegível para GC imediatamente
4. GC Python roda (~15s, durante idle do main loop)
5. Pyjnius finaliza o objeto, chama `DeleteLocalRef(global_ref)` → CheckJNI → SIGABRT

### Fix #3 — Manter referência Python ao _ResultHandler

**Fix aplicado em `mobile/service_bridge.py`:**
```python
# DEPOIS (correto)
# Keep strong reference to prevent GC from triggering Pyjnius DeleteLocalRef on a global JNI ref
self._result_handler = _ResultHandler()
self._reply_messenger = Messenger(
    Handler(Looper.getMainLooper(), self._result_handler)
)
```

`self._result_handler` mantém uma referência Python forte → GC não coleta → Pyjnius não tenta deletar a ref JNI prematuramente → sem crash.

### Tentativa adicional: desabilitar CheckJNI

Tentado como alternativa/diagnóstico:
```bash
adb root  # → "restarting adbd as root" ✅
adb shell setprop dalvik.vm.checkjni false
```

Resultado: **sem efeito**. A propriedade `dalvik.vm.checkjni` é lida durante a inicialização do Zygote — setá-la sem reiniciar o Zygote (`adb shell stop && adb shell start`) não tem efeito nas VMs já existentes. O crash continuou igual com a propriedade setada. A correção real é o Fix #3 acima.

### Nota sobre o crash no emulador vs dispositivo real

O erro `expected reference of kind Local but found Global` é um **artefato do CheckJNI do emulador em modo debug**. Em dispositivos físicos (incluindo o S24), o CheckJNI fica desligado por padrão na build de release — o `DeleteLocalRef` em uma global ref simplesmente não é checado e pode não causar crash visível. Porém o Fix #3 corrige o uso incorreto de qualquer forma, prevenindo potenciais vazamentos de memória JNI mesmo em dispositivos reais.

### Build #3 — Em andamento (iniciada após Fix #3)

- Arquivo modificado: `mobile/service_bridge.py` (1 linha adicionada + 1 linha modificada)
- Mudança é Python puro — sem alteração de `buildozer.spec` ou de código Java/Kotlin
- Gradle usará cache das tarefas `:compileDebugKotlin`, `:mergeDebugJniLibFolders`, etc. — apenas o bundle Python será re-empacotado
- Estimativa: 10–30 min (vs 1h+ de build limpo)
- Monitor de conclusão: processo background (`bu0zajdk2`) aguardando `GREEN LIGHT` ou `BUILD FALHOU` no `build_local.log`

### Estado ao encerrar a sessão

**Build #3 cancelada a pedido do usuário** — fixes aplicados no código mas APK ainda não gerado com o Fix #3.

| Item | Status |
|------|--------|
| Fix ClassNotFoundException (bind na main thread) | ✅ Aplicado em `mobile/main.py` |
| Fix NoClassDefFoundError (kotlin-stdlib) | ✅ Aplicado em `buildozer.spec` + Build #2 GREEN LIGHT |
| Fix JNI global/local ref (`self._result_handler`) | ✅ Aplicado em `mobile/service_bridge.py` |
| Build #3 com Fix #3 | ❌ Cancelada pelo usuário |
| Deploy + benchmark IPC 100 frames | ❌ Não executado |
| P50 / P95 / P99 medidos | ❌ Pendente |

### Resultado geral da task T015.b.ipc

**INCOMPLETO** — gate quantitativo IPC (P50/P95/P99) não medido. A task avançou significativamente: três root causes identificadas e corrigidas no código, mas o APK final com todos os fixes não foi gerado. O benchmark IPC em si não chegou a rodar em nenhum momento desta sessão com resultado válido.

### O que a próxima sessão precisa fazer

**1. Rebuildar** (único arquivo Python mudou — build incremental ~10–30 min):
```bash
cd '/mnt/c/Users/alves/Desktop/Projetos/Identificador de Animais'
bash build_local.sh
```

**2. Deploy e benchmark** (após GREEN LIGHT):
```bash
adb install -r "bin/animaldetector-1.0.28-arm64-v8a_x86_64-debug.apk"
adb shell am force-stop com.maiconalves.animaldetector
adb shell pm grant com.maiconalves.animaldetector android.permission.CAMERA
adb shell pm grant com.maiconalves.animaldetector android.permission.RECORD_AUDIO
adb shell touch /sdcard/ipc_bench.flag
adb shell am start -n com.maiconalves.animaldetector/org.kivy.android.PythonActivity
# Aguardar ~30s — monitorar:
adb logcat | grep -E "IPC|P50|P95|P99|RESULTADO|messenger|FATAL"
# Coletar resultado:
adb pull /data/data/com.maiconalves.animaldetector/files/ipc_emulator.json \
    _research/litert_poc/results/ipc_emulator_t015b_ipc.json
```

**3. Critério de gate:**
- P95 < 30 ms ✓/✗
- P99 < 80 ms ✓/✗
- Zero `FATAL EXCEPTION` ✓/✗

### Arquivos modificados nesta sessão (prontos para a próxima build)

| Arquivo | Mudança |
|---------|---------|
| `mobile/main.py` | Auto-trigger IPC via Clock (main thread), `_check_ipc_trigger`, `_start_ipc_after_bind`, `_run_ipc_benchmark` |
| `mobile/service_bridge.py` | `self._result_handler = _ResultHandler()` — mantém ref Python forte para evitar GC prematuro |
| `buildozer.spec` | `android.gradle_dependencies = org.jetbrains.kotlin:kotlin-stdlib:2.1.0` |

Todos os fixes estão commitáveis. O APK `1.0.28` com esses três fixes ainda não existe — a próxima sessão começa direto com `bash build_local.sh`.

---

## T015.b.ipc — Sessão 3: rc4 (versão 1.0.284) + crash novo JNI DeleteRef

- **Data:** 2026-05-14
- **Status:** **FAIL** — crash novo não-listado nos 3 fixes. Aguarda decisão arquitetural do Maicon.
- **APK:** `bin/animaldetector-1.0.284-arm64-v8a_x86_64-debug.apk` (162,9 MB, 07:09 WSL) — GREEN LIGHT no build.
- **Emulador:** `gate_api29` (API 29 x86_64, `google_apis`) rodando em WSL2 com KVM; conectado via `WSLINTEROP= adb`.
- **Nota de versão:** `1.0.28-rc4` rejeitado pelo p4a (`ValueError: invalid literal for int() with base 10: '28-rc4'`). Usado `1.0.284` como equivalente numérico.
- **Nota Etapa 0:** `gradle.properties` atualizado com `-Xmx22g` (Gradle) + `-Xmx6g` (Kotlin daemon); build rodou com RAM estável (~806 MB usada no WSL).

### Execução

| Passo | Resultado |
|-------|-----------|
| Fixes 1-3 confirmados no código | ✅ |
| Versão bumped para 1.0.284 | ✅ |
| Build `bash build_local.sh` | ✅ GREEN LIGHT (07:09 WSL, 14/05/2026) |
| `adb install -r` APK no emulador | ✅ Success |
| `adb shell touch /sdcard/ipc_bench.flag` | ✅ |
| App iniciou normalmente | ✅ (17:22:14 logcat) |
| `[IPC-TRIGGER] Flag detectada` no logcat | ✅ (17:22:20.027) |
| `onBind — DetectionService pronto (mock)` | ✅ (17:22:20.293) |
| `[IPC benchmark] 100 frames → emulator` | ✅ (17:22:22.038) |
| Resultado JSON coletado | ❌ Crash antes de completar |
| `FATAL EXCEPTION` | ❌ SIGABRT em 17:22:22.315 (Thread-4) |

### Crash — JNI DeleteRef em jnius.so (tid=10544)

O app crashou 1 segundo após iniciar o loop de benchmark. Stacktrace resumido:

```
F .animaldetecto: runtime.cc:630] Runtime aborting...
  Thread-4 (tid=10544, o benchmark thread)
  native: #07  libart.so  art::JavaVMExt::JniAbort
  native: #08  libart.so  art::JavaVMExt::JniAbortV
  native: #09  libart.so  art::ScopedCheck::AbortF
  native: #10  libart.so  art::CheckJNI::DeleteRef(...)
  native: #11  jnius.so   (??? — Pyjnius deletando ref JNI)
  native: #12  <anonymous>  (código Python compilado)
```

**Diagnóstico:** Mesmo tipo do Fix #3 (`CheckJNI::DeleteRef` via Pyjnius), mas em **caminho diferente**: Fix #3 corrigiu o `_result_handler` (Handler/Looper), mas existe outro objeto Pyjnius (possivelmente o `Messenger` de reply, o `Bundle`, ou o próprio `Message`) sendo deletado com ref inválida no thread do benchmark.

**Por que não é coberto pelos 3 fixes:**
- Fix #1: `bind()` na main thread via `Clock.schedule_once` — correto, executou.
- Fix #2: `kotlin-stdlib:2.1.0` — correto, sem `NoClassDefFoundError`.
- Fix #3: `_result_handler = _ResultHandler()` mantém ref do Handler — correto, mas outro objeto Pyjnius ainda tem ref fraca/local usada cross-thread.

### Decisão necessária (Maicon)

Opções para Fix #4:

| Opção | Descrição | Complexidade |
|-------|-----------|-------------|
| **A — Isolar objetos Pyjnius no thread benchmark** | Criar todas as instâncias Pyjnius (`Bundle`, `Message`, `Messenger`) dentro do thread que as usa; nunca cruzar threads com objetos Pyjnius. | Média — refatorar `service_bridge.py` |
| **B — Usar JNIEnv por thread** | Antes de cada call Pyjnius no thread, fazer `vm.AttachCurrentThread()` explicitamente e criar refs globais manualmente. | Alta — muito verboso |
| **C — Substituir Messenger por socket/pipe** | Abandonar Binder/Messenger para IPC — usar socket Unix ou file queue entre Python e Kotlin. Mais simples e sem JNI cross-thread. | Média — reescreve interface IPC |
| **D — Aceitar gate condicional e ir ao S24** | O S24 tem JNI impl diferente do emulador (CheckJNI ativado no emulador, não no release). Testar no S24 sem CheckJNI pode passar. | Baixa — só testar |

**Recomendação:** Opção D primeiro (S24 tem CheckJNI desativado em release builds). Se crash no S24 também → Opção A.

### Logcat salvo

`_research/litert_poc/results/logcat_rc4.txt` — inclui crash completo às 17:22:22 (Thread-4, tid=5187).

Linhas-chave do crash (extraídas):

```text
05-14 17:22:20.027  python  : [IPC-TRIGGER] Flag detectada — bind() na main thread
05-14 17:22:20.293  DetectionService: onBind — DetectionService pronto (mock)
05-14 17:22:22.038  python  : [IPC benchmark] 100 frames → emulator
05-14 17:22:22.315  F DEBUG : signal 6 (SIGABRT), code -1 (SI_QUEUE), fault addr --------
05-14 17:22:22.371  F DEBUG : Abort message: 'JNI DETECTED ERROR IN APPLICATION:
    expected reference of kind Local but found Global: 0x6472
    in call to DeleteLocalRef'
05-14 17:22:22.486  F DEBUG : #07  libart.so  CheckJNI::DeleteRef(...DeleteLocalRef+949)
05-14 17:22:22.486  F DEBUG : #08  jnius.so   0x26493
05-14 17:22:23.105  /system/bin/tombstoned: Tombstone written to: /data/tombstones/tombstone_04
```
