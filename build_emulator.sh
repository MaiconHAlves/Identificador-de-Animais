#!/usr/bin/env bash
# Build APK x86_64 para emulador Android (Pixel6_API34)
# Baseado em build_local.sh — mesma infraestrutura, arch diferente

WINDOWS_PROJECT="/mnt/c/Users/alves/E:/Projetos/Identificador de Animais"
LOG="$WINDOWS_PROJECT/build_emulator.log"
BUILD_DIR="$HOME/build-animais-emu"
ANDROID_HOME="$HOME/android-sdk"
CMDLINE_TOOLS="$ANDROID_HOME/cmdline-tools/latest"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
die() { log "ERRO: $*"; exit 1; }

echo "" > "$LOG"
log "=========================================="
log " BUILD EMULADOR x86_64 — Identificador de Animais"
log "=========================================="

# ── 1. Sistema ────────────────────────────────────────────────────────────────
log "[1/6] Verificando dependências..."
export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which javac))))
log "  Java: $(java -version 2>&1 | head -1) | JAVA_HOME=$JAVA_HOME"

export PATH="$CMDLINE_TOOLS/bin:$PATH"
BUILDOZER=$(which buildozer 2>/dev/null)
[ -z "$BUILDOZER" ] && BUILDOZER=$(find /usr/local/bin /usr/bin "$HOME/.local/bin" -name buildozer 2>/dev/null | head -1)
[ -z "$BUILDOZER" ] && die "buildozer não encontrado — rode build_local.sh primeiro"
log "  buildozer: $($BUILDOZER --version 2>&1)"

# ── 2. SDK ────────────────────────────────────────────────────────────────────
log "[2/6] Android SDK..."
export ANDROID_SDK_PATH="$ANDROID_HOME"
export ANDROID_NDK_PATH="$ANDROID_HOME/ndk/25.1.8937393"

# Pré-aceitar licenças no SDK do buildozer
BLDZ_LICENSES="$HOME/.buildozer/android/platform/android-sdk/licenses"
mkdir -p "$BLDZ_LICENSES"
printf '\n8933bad161af4178b1185d1a37fbf41ea5269c55\nd56f5187479451eabf01fb78af6dfcb131a6481e\n24333f8a63b6825ea9c5514f83c2829b004d1fee' \
    > "$BLDZ_LICENSES/android-sdk-license"
printf '\n84831b9409646a918e30573bab4c9c91346d8abd' \
    > "$BLDZ_LICENSES/android-sdk-preview-license"
log "  Licenças pré-aceitas."

# ── 3. Copiar projeto ─────────────────────────────────────────────────────────
log "[3/6] Copiando projeto para $BUILD_DIR..."
# Preserva cache do buildozer entre runs
if [ -d "$BUILD_DIR/.buildozer" ]; then
    mv "$BUILD_DIR/.buildozer" /tmp/buildozer-emu-cache
fi
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
# Excluir .buildozer (cache gigante) e bin/ — ambos são recriados durante build
rsync -a \
    --exclude='.buildozer' \
    --exclude='bin' \
    --exclude='.idea' \
    --exclude='datasets' \
    --exclude='data' \
    --exclude='runs' \
    --exclude='__pycache__' \
    --exclude='*.log' \
    --exclude='*.bak*' \
    --exclude='*.pyc' \
    --exclude='.git' \
    "$WINDOWS_PROJECT/" "$BUILD_DIR/"
log "  rsync concluído (datasets/ e runs/ excluídos — não necessários para APK)"
if [ -d /tmp/buildozer-emu-cache ]; then
    mv /tmp/buildozer-emu-cache "$BUILD_DIR/.buildozer"
fi
cd "$BUILD_DIR"

# ── 4. Ajustar spec para x86_64 ───────────────────────────────────────────────
log "[4/6] Ajustando buildozer.spec para x86_64 (emulador)..."
# Força x86_64
sed -i "s|android.archs = .*|android.archs = x86_64|" buildozer.spec
# Garante p4a.local_recipes ativo (necessário para numpy + python3 no x86_64)
if grep -q "p4a.local_recipes" buildozer.spec; then
    sed -i "s|.*p4a.local_recipes = .*|p4a.local_recipes = ./p4a-recipes|" buildozer.spec
else
    sed -i "/^\[app\]/a p4a.local_recipes = ./p4a-recipes" buildozer.spec
fi
sed -i "s|android.sdk_path = .*|android.sdk_path = $ANDROID_HOME|" buildozer.spec 2>/dev/null || true
sed -i "s|android.ndk_path = .*|android.ndk_path = $ANDROID_HOME/ndk/25.1.8937393|" buildozer.spec 2>/dev/null || true
log "  Spec ajustado: archs=x86_64, p4a.local_recipes=./p4a-recipes"

# ── 5. Patches Java ───────────────────────────────────────────────────────────
log "[5/6] Patches Java..."

P4A_DIR="$BUILD_DIR/.buildozer/android/platform/python-for-android"

# PythonActivity: clearFlags(FLAG_HARDWARE_ACCELERATED)
while IFS= read -r -d '' ACT; do
    if ! grep -q "FLAG_HARDWARE_ACCELERATED" "$ACT"; then
        sed -i 's/Log\.v(TAG, "About to do super onCreate");/getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED);\n        Log.v(TAG, "About to do super onCreate");/' "$ACT"
        log "    Patched PythonActivity: $ACT"
    fi
done < <(find "$BUILD_DIR/.buildozer" -name "PythonActivity.java" -print0 2>/dev/null)

# SDLSurface: LAYER_TYPE_NONE
while IFS= read -r -d '' SURF; do
    if ! grep -q "LAYER_TYPE_NONE" "$SURF"; then
        if grep -q "setFocusableInTouchMode(true)" "$SURF"; then
            sed -i 's/setFocusableInTouchMode(true);/setFocusableInTouchMode(true);\n        setLayerType(android.view.View.LAYER_TYPE_NONE, null);/' "$SURF"
            log "    Patched SDLSurface: $SURF"
        fi
    fi
done < <(find \
    "$BUILD_DIR/.buildozer/android/platform/build-x86_64/build/bootstrap_builds" \
    "$BUILD_DIR/.buildozer/android/platform/build-x86_64/dists" \
    -name "SDLSurface.java" -print0 2>/dev/null)

# AndroidManifest: hardwareAccelerated=false
TMPL="$BUILD_DIR/.buildozer/android/platform/python-for-android/pythonforandroid/bootstraps/sdl2/build/templates/AndroidManifest.tmpl.xml"
if [ -f "$TMPL" ]; then
    sed -i 's/android:hardwareAccelerated="true"/android:hardwareAccelerated="false"/' "$TMPL"
    log "    Patched AndroidManifest template."
fi

# CameraHelper.java — Adicionado via --add-source src no buildozer (mais estável)
log "  CameraHelper será incluído via pasta src do projeto."

# ── 6. Build ──────────────────────────────────────────────────────────────────
log "[6/6] Rodando buildozer android debug (x86_64)..."
log "  Primeira build: ~30-60 min. Rebuilds: ~5 min."

export ANDROID_HOME ANDROID_SDK_PATH ANDROID_NDK_PATH JAVA_HOME
export MAKEFLAGS="-j$(nproc)"  # usa todos os cores disponíveis no NDK

log "  Parallelismo: MAKEFLAGS=$MAKEFLAGS ($(nproc) cores)"
$BUILDOZER -v android debug 2>&1 | tee -a "$LOG"

# ── Resultado ─────────────────────────────────────────────────────────────────
APK=$(find "$BUILD_DIR/bin" -name "*x86_64*.apk" -o -name "*debug*.apk" 2>/dev/null | head -1)
if [ -n "$APK" ]; then
    mkdir -p "$WINDOWS_PROJECT/bin"
    # Renomeia para identificar como build do emulador
    DEST="$WINDOWS_PROJECT/bin/animaldetector-emulator-x86_64-debug.apk"
    cp "$APK" "$DEST"
    log ""
    log "=========================================="
    log " GREEN LIGHT — APK emulador gerado!"
    log " animaldetector-emulator-x86_64-debug.apk"
    log "=========================================="
else
    log ""
    log "=========================================="
    log " BUILD FALHOU — veja o log acima."
    log "=========================================="
    exit 1
fi
