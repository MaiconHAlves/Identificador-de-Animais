#!/bin/bash
set -e

echo "🚀 Iniciando Build Blindada do Road Sentinel 2.1..."

# 1. Limpeza de rastro (Resolve Erro #9)
echo "🧹 Limpando resíduos de builds anteriores..."
rm -f bin/*.apk
rm -rf .buildozer/android/app
rm -rf .buildozer/android/platform/build/dists

# 2. Garantir dependências do sistema (Resolve Erro #4)
echo "📦 Verificando dependências do sistema..."
sudo apt-get update
sudo apt-get install -y zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# 3. Aceitar licenças automaticamente (Resolve Erro #3)
if [ -d "$HOME/.buildozer/android/platform/android-sdk" ]; then
    echo "📜 Aceitando licenças do Android SDK..."
    yes | $HOME/.buildozer/android/platform/android-sdk/cmdline-tools/latest/bin/sdkmanager --licenses || true
fi

# 4. Executar Buildozer
echo "🏗️ Compilando APK (Log Level 2)..."
buildozer -v android debug

echo "✅ Build concluída! Verifique a pasta bin/"
