@echo off
setlocal enabledelayedexpansion
title Instalador — Identificador de Animais

echo ==========================================
echo  Instalador — Identificador de Animais
echo ==========================================
echo.

:: Localiza o APK na pasta bin\
set APK=
for %%f in ("%~dp0bin\*.apk") do set APK=%%f

if "!APK!"=="" (
    echo [ERRO] Nenhum APK encontrado em bin\
    echo        Execute a build primeiro.
    echo.
    pause
    exit /b 1
)

echo APK encontrado: !APK!
echo.

:: Verifica se ADB esta disponivel
where adb >nul 2>&1
if errorlevel 1 (
    echo [ERRO] ADB nao encontrado no PATH.
    echo.
    echo  Opcoes para instalar o ADB:
    echo   1. Android Studio: ja vem incluso em platform-tools\
    echo   2. SDK standalone:  https://developer.android.com/tools/releases/platform-tools
    echo   3. Adicione a pasta platform-tools ao PATH do Windows.
    echo.
    echo  Apos instalar, rode este script novamente.
    echo.
    pause
    exit /b 1
)

:: Verifica dispositivo conectado
echo Verificando dispositivo USB...
adb devices
echo.

:: Conta dispositivos (exclui a linha "List of devices attached")
for /f "skip=1 tokens=1" %%d in ('adb devices 2^>nul') do (
    if not "%%d"=="" (
        set DEVICE_FOUND=1
    )
)

if not defined DEVICE_FOUND (
    echo [ERRO] Nenhum dispositivo encontrado.
    echo.
    echo  Verifique:
    echo   1. Cabo USB conectado
    echo   2. Depuracao USB ativada no celular
    echo      Configuracoes ^> Sobre o telefone ^> toque 7x em "Numero da versao"
    echo      Configuracoes ^> Opcoes do desenvolvedor ^> Depuracao USB
    echo   3. Autorize o computador na tela do celular
    echo.
    pause
    exit /b 1
)

echo Instalando...
adb install -r "!APK!"

if errorlevel 1 (
    echo.
    echo [ERRO] Instalacao falhou.
    echo        Tente: adb install -r -d "!APK!"  (para downgrade)
) else (
    echo.
    echo ==========================================
    echo  Instalacao concluida com sucesso!
    echo ==========================================
    echo.
    echo Iniciando o app...
    adb shell monkey -p com.maiconalves.animaldetector -c android.intent.category.LAUNCHER 1 2>nul
    if errorlevel 1 (
        echo (Nao foi possivel iniciar automaticamente — abra pelo launcher do celular)
    )
)

echo.
pause
