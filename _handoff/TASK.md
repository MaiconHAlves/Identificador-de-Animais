# TASK — Identificador de Animais

---

## Cabeçalho

- **Status:** pronto
- **ID do ciclo:** T015.b.ipc Sessão 4 — Fix #4 (Opção A: isolar Pyjnius por thread)
- **Vinculado a:** D10 (AAR pré-compilado) + RESULT.md seção "T015.b.ipc — Sessão 3"
- **Branch:** `feat/t015-native-service`
- **Criado em:** 2026-05-14

> O Claude Code só executa quando `Status: pronto`.

## Tarefa

Aplicar o **Fix #4 (Opção A)** no caminho IPC do app: isolar todos os objetos Pyjnius dentro da thread que os usa. Rebuildar `1.0.285`, redeployar no AVD, executar o benchmark IPC e validar P95/P99 contra o gate emulador.

A causa-raiz da Sessão 3 foi `CheckJNI::DeleteRef` em `jnius.so` na thread do benchmark (tid=10544). Os três fixes anteriores (bind na main, kotlin-stdlib 2.1.0, ref forte no `_ResultHandler`) seguem corretos, mas ainda há objeto Pyjnius cruzando thread — provavelmente `_reply_messenger` (criado na main thread em `bind()`) sendo referenciado por `Message`/`Bundle` criados na thread do benchmark dentro de `send_frame()`. Quando esses objetos saem de escopo, Pyjnius dispara `DeleteRef` num JNIEnv inconsistente entre threads, e o CheckJNI do emulador aborta.

## Contexto

- **Sessão 3 (13/05):** APK `1.0.284` buildou GREEN LIGHT, IPC trigger disparou, `onBind` OK, benchmark começou os 100 frames — SIGABRT 1s depois. Detalhes em `_handoff/RESULT.md` seção "T015.b.ipc — Sessão 3".
- **Decisão Maicon (14/05):** Fix #4 = **Opção A**. Opção D (pular pro S24) está fora — política emulador→S24 mantida e endurecida.
- **`gradle.properties` da Etapa 0 da Sessão 3 continua válido.** Não mexer — só confirmar com grep antes do build.

## Diretriz arquitetural (Opção A)

**Regra:** todo objeto Pyjnius (instância de `autoclass`, instância de `PythonJavaClass`, retorno de `java_method`) deve ser **criado e destruído na mesma thread Python** que o utiliza. Cross-thread sharing via atributo do bridge é **proibido**.

Implementação proposta (Claude Code pode ajustar os detalhes desde que respeite a regra acima):

1. **Em `mobile/service_bridge.py`** — quebrar `bind()` em duas etapas:
   - `bind_service()` — registra `ServiceConnection` e chama `ctx.bindService(...)`. **Roda na main thread**. NÃO cria `_reply_messenger` aqui.
   - `setup_reply_in_current_thread()` — cria `_result_handler`, `Handler(Looper.getMainLooper(), …)` e `_reply_messenger`. Roda **na thread que vai chamar `send_frame()`** (no caso, a thread do benchmark). Mantém todas as refs como atributos da própria thread (via `threading.local()`), não como atributos do bridge.

2. **Em `mobile/service_bridge.py` → `send_frame()`** — ler `_reply_messenger` do `threading.local()` corrente. Se não existir → raise `RuntimeError("setup_reply_in_current_thread() não foi chamado nesta thread")`. Criar `Message`/`Bundle` localmente como já faz hoje.

3. **Em `mobile/main.py` → `_run_ipc_benchmark()`** — envolver o corpo da thread em:
   ```python
   from jnius import detach  # cleanup explícito do JNIEnv no fim da thread
   try:
       bridge.setup_reply_in_current_thread()
       # … loop dos 100 frames com bridge.send_frame() …
   finally:
       detach()
   ```

4. **Manter `_check_ipc_trigger` e `_start_ipc_after_bind`** intactos — só o conteúdo da thread do benchmark muda. `bind_service()` continua sendo chamado via `Clock.schedule_once` na main (Fix #1 preservado).

5. **Comentários TODO** — marcar trechos novos com `# T015.b.ipc Fix #4 — REMOVER em produção final` (vira cleanup pra T016, conforme convenção do auto-trigger).

## Critério de sucesso (verificável)

### Etapa 0 — Pré-flight

- [ ] `grep -E "Xmx22g|kotlin\.daemon|workers\.max|caching|configureondemand" gradle.properties` retorna **5 matches** (Etapa 0 da Sessão 3 ainda válida — não recriar).
- [ ] `adb devices` mostra `emulator-5554` como `device`. Se não, subir `gate_api29` conforme bloco "Comandos típicos" da Sessão 3 (vide TASK histórica em `_handoff/RESULT.md`).
- [ ] Confirmar fixes 1-3 ainda no código (grep do passo "Comandos típicos" abaixo): `fix1 ok`, `fix2 ok`, `fix3 ok`.

### Etapa 1 — Implementar Fix #4

- [ ] `mobile/service_bridge.py` contém método `bind_service()` (sem criar `_reply_messenger`).
- [ ] `mobile/service_bridge.py` contém método `setup_reply_in_current_thread()` que usa `threading.local()` pra guardar `_result_handler`, `_handler`, `_reply_messenger`.
- [ ] `mobile/service_bridge.py` → `send_frame()` lê `_reply_messenger` do `threading.local()` corrente e levanta `RuntimeError` se ausente.
- [ ] `mobile/main.py` → `_run_ipc_benchmark()` chama `bridge.setup_reply_in_current_thread()` no início e `from jnius import detach; detach()` no `finally`.
- [ ] `mobile/main.py` → `_check_ipc_trigger` segue chamando `bridge.bind_service()` (não `bind()` antigo).
- [ ] Nenhuma referência a `bridge._reply_messenger` ou `bridge._result_handler` permanece como atributo direto do bridge (grep deve voltar vazio).
- [ ] Comentário `# T015.b.ipc Fix #4 — REMOVER em produção final` nos blocos novos.

### Etapa 2 — Build

- [ ] Bump `version = 1.0.285` no `buildozer.spec`. **Não usar `1.0.28-rc5`** — p4a rejeita sufixo (vide Sessão 3).
- [ ] `bash build_local.sh 2>&1 | tee build_t015b_ipc_s4.log` → `bin/animaldetector-1.0.285-arm64-v8a_x86_64-debug.apk` (~160 MB).
- [ ] `GREEN LIGHT` no fim do log.
- [ ] Header do log mostra Gradle daemon com `-Xmx22g` (confirma que `gradle.properties` ativo).
- [ ] `aapt dump badging bin/animaldetector-1.0.285-*.apk | grep native-code` mostra `arm64-v8a` e `x86_64`.

### Etapa 3 — Deploy

- [ ] `adb install -r bin/animaldetector-1.0.285-arm64-v8a_x86_64-debug.apk` → `Success`.
- [ ] `adb shell pm grant com.maiconalves.animaldetector android.permission.CAMERA`.
- [ ] `adb shell pm grant com.maiconalves.animaldetector android.permission.RECORD_AUDIO`.
- [ ] `adb shell touch /sdcard/ipc_bench.flag`.
- [ ] `adb shell am force-stop com.maiconalves.animaldetector`.
- [ ] `adb shell am start -n com.maiconalves.animaldetector/org.kivy.android.PythonActivity`.
- [ ] `sleep 35`.

### Etapa 4 — Validação IPC

- [ ] `adb pull /data/data/com.maiconalves.animaldetector/files/ipc_emulator.json _research/litert_poc/results/ipc_emulator_s4.json` (ou `/sdcard/ipc_emulator.json` conforme implementação).
- [ ] JSON contém `frames_total: 100`, `frames_success ≥ 95`, `p50_ms`, `p95_ms`, `p99_ms` numéricos.
- [ ] **Gate emulador (binário):**
  - **P95 < 30 ms** ✓/✗
  - **P99 < 80 ms** ✓/✗
- [ ] `adb logcat -d -s python:V DetectionService:* AndroidRuntime:E > _research/litert_poc/results/logcat_s4.txt`: zero `FATAL EXCEPTION`, zero `NoClassDefFoundError`, zero `ClassNotFoundException`, zero `JNI DETECTED ERROR`, zero `SIGABRT`, zero `CheckJNI::DeleteRef`.

### Etapa 5 — Smoke negativo (sem flag, app abre normal)

- [ ] `adb shell rm /sdcard/ipc_bench.flag`.
- [ ] `adb shell am force-stop com.maiconalves.animaldetector`.
- [ ] `adb shell am start -n com.maiconalves.animaldetector/org.kivy.android.PythonActivity`.
- [ ] App abre, logcat NÃO mostra `[IPC-TRIGGER]`, sem crash em 20s.

### Etapa 6 — Documentação

- [ ] Acrescentar em `_handoff/RESULT.md` a seção **"T015.b.ipc — Sessão 4: Fix #4 Opção A (isolar Pyjnius por thread)"** com:
  - Diff resumido das mudanças em `service_bridge.py` e `main.py` (5-15 linhas centrais).
  - Tabela P50 / P95 / P99 (frames=100, frames_success=N).
  - Comandos exatos usados.
  - Trecho relevante do logcat (`[IPC-TRIGGER]`, mensagens do `DetectionService`, ausência de SIGABRT).
  - Decisão final do gate emulador: **PASS** ou **FAIL** baseada nos critérios binários.
- [ ] Marcar `Status: concluído` no cabeçalho do RESULT.md (ou `Status: falha` se crashar de novo).

## Arquivos relevantes

- `mobile/service_bridge.py` (refactor principal)
- `mobile/main.py` (`_check_ipc_trigger`, `_start_ipc_after_bind`, `_run_ipc_benchmark`)
- `buildozer.spec` (apenas bump de versão)
- `gradle.properties` (somente verificação)
- `_handoff/RESULT.md` (escrever Sessão 4)

## Comandos típicos

```bash
# Workspace (WSL)
cd "/mnt/c/Users/alves/Desktop/Projetos/Identificador de Animais"

# Pré-flight
grep -E "Xmx22g|kotlin\.daemon|workers\.max|caching|configureondemand" gradle.properties  # esperado: 5 matches
adb devices
grep -q "self._result_handler = _ResultHandler()" mobile/service_bridge.py && echo "fix3 ok (será refatorado)"
grep -q "kotlin-stdlib:2.1.0" buildozer.spec && echo "fix2 ok"
grep -q "_check_ipc_trigger" mobile/main.py && echo "fix1 ok"

# Após implementar Fix #4 — verificações de regra
grep -n "bridge\._reply_messenger\|bridge\._result_handler" mobile/  # esperado: vazio
grep -n "setup_reply_in_current_thread\|threading\.local()\|from jnius import detach" mobile/  # esperado: matches em ambos os arquivos

# Bump version
sed -i 's/^version = .*/version = 1.0.285/' buildozer.spec
grep "^version" buildozer.spec

# Build
bash build_local.sh 2>&1 | tee build_t015b_ipc_s4.log
ls -la bin/animaldetector-1.0.285*
aapt dump badging bin/animaldetector-1.0.285-arm64-v8a_x86_64-debug.apk | grep native-code

# Deploy
adb install -r bin/animaldetector-1.0.285-arm64-v8a_x86_64-debug.apk
adb shell pm grant com.maiconalves.animaldetector android.permission.CAMERA
adb shell pm grant com.maiconalves.animaldetector android.permission.RECORD_AUDIO
adb shell touch /sdcard/ipc_bench.flag
adb shell am force-stop com.maiconalves.animaldetector
adb shell am start -n com.maiconalves.animaldetector/org.kivy.android.PythonActivity
sleep 35

# Coleta
adb logcat -d -s python:V DetectionService:* AndroidRuntime:E > _research/litert_poc/results/logcat_s4.txt
adb pull /data/data/com.maiconalves.animaldetector/files/ipc_emulator.json _research/litert_poc/results/ipc_emulator_s4.json 2>/dev/null \
  || adb pull /sdcard/ipc_emulator.json _research/litert_poc/results/ipc_emulator_s4.json
cat _research/litert_poc/results/ipc_emulator_s4.json

# Smoke negativo
adb shell rm /sdcard/ipc_bench.flag
adb shell am force-stop com.maiconalves.animaldetector
adb shell am start -n com.maiconalves.animaldetector/org.kivy.android.PythonActivity
sleep 20
adb logcat -d -s python:V AndroidRuntime:E | tail -100
```

## Restrições

- **NÃO pular pro S24.** Política emulador→S24 mantida e endurecida. Opção D (testar no S24 antes do emulador passar) está fora — não considerar.
- **NÃO refatorar Messenger/Binder pra socket/pipe.** Essa é a Opção C, fica reservada pra eventual D11 caso a Opção A também falhe.
- **NÃO mexer no AAR** `detection_service.aar` — validado na T015.b.
- **NÃO mexer no `gradle.properties`** da Etapa 0 — só verificar com grep.
- **NÃO usar imagem** `google_apis_playstore` no AVD — SELinux crasha `shutil.copytree` dos ícones Kivy.
- **NÃO usar sufixo `-rcN`** no `version`. p4a rejeita (ver Sessão 3, `ValueError`). Usar `1.0.285`.
- **NÃO publicar `1.0.285` como release** — build de validação apenas. APK 1.0.27 segue em produção.
- **NÃO alterar comportamento default** do app — sem flag, app abre normal (cv2.dnn detection do 1.0.27).
- **Manter Fix #1, #2 e #3 vivos.** Fix #4 *complementa* — não substitui.
- Se aparecer **crash novo distinto** de `CheckJNI::DeleteRef` (ex: `JNI WeakGlobalRef`, `ANR`, segfault em outro lib), marcar `Status: falha`, capturar logcat, **parar**. Decisão fica com Maicon (provável escalonamento pra Opção B ou C).
- Se **o mesmo crash `CheckJNI::DeleteRef` voltar**, marcar `Status: falha`, anotar qual objeto Pyjnius está envolvido no novo stacktrace (pode ter migrado de `_reply_messenger` pra `Bundle`/`Message`), **parar**. Decisão arquitetural com Maicon.
- Se **P99 ficar entre 80 e 150 ms**, registrar como `PASS condicional` com nota sobre virtualization overhead do AVD — não bloqueia T015.c (S24 dá números mais limpos).
- Se **P95 > 30 ms ou P99 > 150 ms**, marcar `FAIL` — decisão de próximos passos com Maicon.
- Se **AVD não subir** via WSL, marcar `Status: bloqueado-avd` no RESULT.md e parar — Maicon sobe AVD manualmente.

## Próxima ação (após esta TASK)

Cowork (Loop B):
1. Lê `_handoff/RESULT.md` seção Sessão 4.
2. Se **PASS** (gate emulador): registra entrada no histórico de mudanças do PROJECT_STATE.md (Fix #4 Opção A consolidado), escreve **T015.c** — Gate S24 (1000 frames + câmera real + USB).
3. Se **FAIL** ou crash novo: sinal proativo D16, pausa autônomo, aguarda decisão Maicon (provável escalonamento Opção B/C ou abertura de D11).
