#!/usr/bin/env bash
# Build local do APK — Identificador de Animais
# Executa no WSL Ubuntu 24.04

WINDOWS_PROJECT="/mnt/c/Users/alves/Desktop/Projetos/Identificador de Animais"
LOG="$WINDOWS_PROJECT/build_local.log"
BUILD_DIR="$HOME/build-animais"
ANDROID_HOME="$HOME/android-sdk"
CMDLINE_TOOLS="$ANDROID_HOME/cmdline-tools/latest"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
die() { log "ERRO: $*"; exit 1; }

echo "" > "$LOG"
log "=========================================="
log " BUILD LOCAL — Identificador de Animais"
log "=========================================="

# ── 1. Sistema ────────────────────────────────────────────────────────────────
log "[1/6] Instalando dependências do sistema..."
apt-get update -qq 2>&1 | tail -1 | tee -a "$LOG"
apt-get install -y -qq \
    build-essential git unzip zip wget \
    openjdk-17-jdk \
    libffi-dev libssl-dev autoconf automake libtool \
    pkg-config zlib1g-dev cmake ninja-build \
    python3-pip python3-venv software-properties-common 2>&1 | tail -3 | tee -a "$LOG"

# Python 3.11 (tem distutils; removido no 3.12)
if ! command -v python3.11 &>/dev/null; then
    log "  Instalando Python 3.11 via deadsnakes PPA..."
    add-apt-repository ppa:deadsnakes/ppa -y 2>&1 | tail -1 | tee -a "$LOG"
    apt-get update -qq
    apt-get install -y -qq python3.11 python3.11-distutils 2>&1 | tail -2 | tee -a "$LOG"
fi

# pip para python3.11 (não vem com o pacote base no deadsnakes)
if ! python3.11 -m pip --version &>/dev/null; then
    log "  Instalando pip para Python 3.11..."
    wget -q https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py
    python3.11 /tmp/get-pip.py --quiet 2>&1 | tail -2 | tee -a "$LOG"
    rm -f /tmp/get-pip.py
fi
log "  Python 3.11: $(python3.11 --version)"

export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which javac))))
log "Java: $(java -version 2>&1 | head -1) | JAVA_HOME=$JAVA_HOME"

# ── 2. Android cmdline-tools ──────────────────────────────────────────────────
log "[2/6] Configurando Android SDK..."
if [ ! -f "$CMDLINE_TOOLS/bin/sdkmanager" ]; then
    log "  Baixando cmdline-tools..."
    mkdir -p "$ANDROID_HOME/cmdline-tools"
    wget -q "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" \
        -O /tmp/cmdline-tools.zip
    unzip -q /tmp/cmdline-tools.zip -d /tmp/ct_extract
    mv /tmp/ct_extract/cmdline-tools "$CMDLINE_TOOLS"
    rm -rf /tmp/ct_extract /tmp/cmdline-tools.zip
    log "  cmdline-tools OK."
else
    log "  cmdline-tools já existe."
fi
export PATH="$CMDLINE_TOOLS/bin:$PATH"

# ── 3. NDK e platforms ────────────────────────────────────────────────────────
log "[3/6] Instalando NDK + platforms..."
yes | sdkmanager --sdk_root="$ANDROID_HOME" \
    "platforms;android-33" "build-tools;34.0.0" "ndk;25.1.8937393" \
    2>&1 | grep -E "Install|Download|100%|Symlink" | tee -a "$LOG" || true

log "  Aceitando todas as licenças Android SDK..."
yes | sdkmanager --sdk_root="$ANDROID_HOME" --licenses \
    2>&1 | grep -v "^$" | tail -5 | tee -a "$LOG" || true

# Pre-accept licenses for buildozer's internal SDK dir too
BUILDOZER_SDK="$HOME/.buildozer/android/platform/android-sdk"
if [ -f "$BUILDOZER_SDK/cmdline-tools/latest/bin/sdkmanager" ]; then
    log "  Aceitando licenças no SDK interno do buildozer..."
    yes | "$BUILDOZER_SDK/cmdline-tools/latest/bin/sdkmanager" \
        --sdk_root="$BUILDOZER_SDK" --licenses \
        2>&1 | grep -v "^$" | tail -3 | tee -a "$LOG" || true
fi

mkdir -p "$ANDROID_HOME/tools/bin"
ln -sf "$CMDLINE_TOOLS/bin/sdkmanager" "$ANDROID_HOME/tools/bin/sdkmanager"
ln -sf "$CMDLINE_TOOLS/bin/avdmanager" "$ANDROID_HOME/tools/bin/avdmanager"
chmod +x "$ANDROID_HOME/tools/bin/sdkmanager"
log "  Symlinks legados OK."

# ── 4. Buildozer + Cython (instalação global — sem venv) ─────────────────────
# Razão: Buildozer 1.5.0 faz `pip install --user` internamente.
# pip bloqueia --user dentro de venv (sys.prefix != sys.base_prefix).
# Instalação global com --break-system-packages evita o conflito inteiramente.
log "[4/6] Instalando buildozer + cython globalmente (python3.11)..."
python3.11 -m pip install --quiet --break-system-packages \
    buildozer cython==0.29.33 2>&1 | tail -2 | tee -a "$LOG"

BUILDOZER=$(which buildozer 2>/dev/null)
[ -z "$BUILDOZER" ] && BUILDOZER=$(find /usr/local/bin /usr/bin "$HOME/.local/bin" -name buildozer 2>/dev/null | head -1)
[ -z "$BUILDOZER" ] && die "buildozer não encontrado após instalação"
log "  buildozer em: $BUILDOZER"
log "  buildozer: $($BUILDOZER --version 2>&1)"

# ── 5. Copiar projeto para FS Linux ──────────────────────────────────────────
log "[5/6] Copiando projeto para $BUILD_DIR..."
# Preserva .buildozer entre runs para não perder cache de downloads (recipes, NDK builds)
if [ -d "$BUILD_DIR/.buildozer" ]; then
    mv "$BUILD_DIR/.buildozer" /tmp/buildozer-cache-backup
fi
rm -rf "$BUILD_DIR"
cp -r "$WINDOWS_PROJECT" "$BUILD_DIR"
# Remove old APKs from build dir — prevents false success if buildozer fails
rm -f "$BUILD_DIR"/bin/*.apk
if [ -d /tmp/buildozer-cache-backup ]; then
    mv /tmp/buildozer-cache-backup "$BUILD_DIR/.buildozer"
fi
cd "$BUILD_DIR"

# Patch: Desativar HWUI para corrigir crash SDL2/hwuiTask0 no Android 14/15/16
# SDL2 usa EGL/OpenGL diretamente — HWUI não é necessário e causa race condition
log "  Patcheando AndroidManifest: hardwareAccelerated=false (fix SDL2/Android16)..."
for TMPL in \
    "$BUILD_DIR/.buildozer/android/platform/python-for-android/pythonforandroid/bootstraps/sdl2/build/templates/AndroidManifest.tmpl.xml" \
    "$BUILD_DIR/.buildozer/android/platform/build-arm64-v8a/dists/animaldetector/templates/AndroidManifest.tmpl.xml" \
    "$BUILD_DIR/.buildozer/android/platform/build-arm64-v8a/dists/animaldetector/AndroidManifest.xml"; do
    if [ -f "$TMPL" ]; then
        sed -i 's/android:hardwareAccelerated="true"/android:hardwareAccelerated="false"/' "$TMPL"
        log "    Patched: $(basename $TMPL)"
    fi
done

# Patch buildozer.spec: garante caminhos locais do WSL
sed -i "s|android.sdk_path = .*|android.sdk_path = $ANDROID_HOME|" buildozer.spec
sed -i "s|android.ndk_path = .*|android.ndk_path = $ANDROID_HOME/ndk/25.1.8937393|" buildozer.spec
log "  buildozer.spec patcheado: sdk=$ANDROID_HOME"
log "  Cópia concluída."

# ── 6. Build ──────────────────────────────────────────────────────────────────
log "[6/6] Rodando buildozer android debug..."
log "  (isso pode levar 10-40 minutos)"

export ANDROID_HOME ANDROID_SDK_PATH="$ANDROID_HOME"
export ANDROID_NDK_PATH="$ANDROID_HOME/ndk/25.1.8937393"
export JAVA_HOME

$BUILDOZER -v android debug 2>&1 | tee -a "$LOG"

# ── Resultado ─────────────────────────────────────────────────────────────────
APK=$(find "$BUILD_DIR/bin" -name "*.apk" 2>/dev/null | head -1)
if [ -n "$APK" ]; then
    mkdir -p "$WINDOWS_PROJECT/bin"
    cp "$APK" "$WINDOWS_PROJECT/bin/"
    log ""
    log "=========================================="
    log " GREEN LIGHT — APK gerado com sucesso!"
    log " $(basename "$APK")"
    log "=========================================="
else
    log ""
    log "=========================================="
    log " BUILD FALHOU — veja o log acima."
    log "=========================================="
    exit 1
fi
