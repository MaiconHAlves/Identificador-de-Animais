# QWEN_TASK: Build APK Android v1.0.21

## Objetivo
Gerar o APK `animaldetector-1.0.21-arm64-v8a_x86_64-debug.apk` rodando build_local.sh no WSL.

## Passo 1 — Iniciar o build em background

```wsl
nohup sudo bash /mnt/c/Users/alves/Desktop/Projetos/Identificador\ de\ Animais/build_local.sh > /tmp/build_1021.log 2>&1 &
echo "PID: $!"
```

## Passo 2 — Verificar se está rodando (rodar após ~30s)

```wsl
pgrep -a buildozer 2>/dev/null && echo RODANDO || echo PARADO
tail -10 /tmp/build_1021.log
```

## Passo 3 — Monitorar progresso (repetir a cada 5 min)

```wsl
tail -20 /tmp/build_1021.log
ls /root/build-animais/bin/*.apk 2>/dev/null && echo APK_PRONTO || echo sem_apk
```

## Passo 4 — Quando APK gerado (GREEN LIGHT no log)

```wsl
ls -la /root/build-animais/bin/
cp /root/build-animais/bin/animaldetector-1.0.21-*.apk /mnt/c/Users/alves/Desktop/Projetos/Identificador\ de\ Animais/bin/ 2>/dev/null && echo COPIADO || echo "Falha ao copiar"
```

```powershell
Set-Content "SUCCESS.md" -Value "APK 1.0.21 gerado com sucesso e copiado para bin/" -Encoding UTF8
```

## Passo 5 — Se der erro de compilacao C/C++

Mostrar as últimas 60 linhas do log:
```wsl
tail -60 /tmp/build_1021.log
```

Depois escalar:
```powershell
$err = wsl -d Ubuntu-24.04 -e bash -c "tail -60 /tmp/build_1021.log"
Set-Content "ESCALATE.md" -Value "# Build 1.0.21 falhou`n`n$err" -Encoding UTF8
```

## Contexto
- build_local.sh: auto-contido, instala deps, configura SDK/NDK r26b, copia projeto para ~/build-animais e roda buildozer
- APK esperado: animaldetector-1.0.21-arm64-v8a_x86_64-debug.apk
- package_name: com.maiconalves
- Fixes de sessao anterior (podem ser necessarios se o buildozer limpar cache):
  - harfbuzz: APP_CPPFLAGS += -Wno-cast-function-type-strict -DHB_NO_PRAGMA_GCC_DIAGNOSTIC_ERROR
  - kivy: env['CFLAGS'] += ' -Wno-incompatible-function-pointer-types'
  - numpy: CFLAGS += ' -Wno-maybe-uninitialized -Wno-error=maybe-uninitialized'
  - Scripts de fix: /mnt/c/tmp/fix_hb.sh e /mnt/c/tmp/fix_kivy.sh
