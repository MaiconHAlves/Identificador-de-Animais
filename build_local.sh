#!/usr/bin/env bash
# Build local do APK — Identificador de Animais
# Executa no WSL Ubuntu 24.04

WINDOWS_PROJECT="/mnt/c/Users/alves/E:/Projetos/Identificador de Animais"
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
    "platforms;android-33" "platforms;android-36" \
    "build-tools;34.0.0" "build-tools;35.0.0" \
    "ndk;25.1.8937393" \
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

# Atualizar p4a para versão com correções Android 15/16 (SDL2 threading fix)
P4A_DIR="$BUILD_DIR/.buildozer/android/platform/python-for-android"
if [ -d "$P4A_DIR/.git" ]; then
    log "  Atualizando p4a para versão mais recente..."
    cd "$P4A_DIR"
    git fetch --quiet origin develop 2>/dev/null || git fetch --quiet origin master 2>/dev/null || true
    git reset --hard origin/develop 2>/dev/null || git reset --hard origin/master 2>/dev/null || true
    P4A_VER=$(grep '__version__' pythonforandroid/__init__.py 2>/dev/null | head -1)
    log "  p4a: $P4A_VER"
    cd "$BUILD_DIR"
    # Forçar rebuild do dist (bootstrap Java) mantendo .so compilados
    rm -rf "$BUILD_DIR/.buildozer/android/platform/build-arm64-v8a/dists/animaldetector"
    log "  Dist removida — será regeada com p4a atualizado (bootstrap ~5min)"
fi

# Patch 1: Desativar HWUI no AndroidManifest (nível de Application)
# O template p4a NÃO contém hardwareAccelerated por padrão — sem isso o sed de
# substituição é um no-op e HWUI inicia normalmente, causando SIGABRT em hwuiTask0.
# Solução: remover qualquer valor existente e INSERIR hardwareAccelerated="false"
# no elemento <application>, que cobre todas as activities da app.
log "  Patcheando AndroidManifest template: inserindo hardwareAccelerated=false..."
TMPL="$BUILD_DIR/.buildozer/android/platform/python-for-android/pythonforandroid/bootstraps/sdl2/build/templates/AndroidManifest.tmpl.xml"
if [ -f "$TMPL" ]; then
    sed -i -E 's/ android:hardwareAccelerated="[^"]*"//g' "$TMPL"
    sed -i -E 's/<application( |>)/<application android:hardwareAccelerated="false"\1/' "$TMPL"
    log "    Patched: AndroidManifest.tmpl.xml"
fi

# Patch 2: clearFlags(FLAG_HARDWARE_ACCELERATED) em PythonActivity.java
# Samsung Android 16 ignora android:hardwareAccelerated="false" no manifest e ainda
# inicializa HWUI (hwuiTask threads). O clearFlags programático antes de super.onCreate()
# é mais robusto: o WindowManager recebe o window sem o flag e não inicializa RenderThread.
#
# CRÍTICO: patchear o TEMPLATE do p4a (não a dist), porque a dist é deletada e
# recriada a cada build — patchear só a dist seria um no-op no próximo build.
log "  Patcheando PythonActivity.java: System.loadLibrary(hwuifix) + clearFlags no template p4a..."
P4A_ACT="$P4A_DIR/pythonforandroid/bootstraps/sdl2/build/src/main/java/org/kivy/android/PythonActivity.java"
if [ -f "$P4A_ACT" ]; then
    if ! grep -q "hwuifix" "$P4A_ACT"; then
        sed -i 's/Log\.v(TAG, "About to do super onCreate");/try { System.loadLibrary("hwuifix"); } catch (UnsatisfiedLinkError e) { android.util.Log.w("hwuifix", "libhwuifix.so not found, HWUI workaround disabled"); }\n        getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED);\n        Log.v(TAG, "About to do super onCreate");/' "$P4A_ACT"
        log "    Patched template: PythonActivity.java (hwuifix try-catch + clearFlags)"
    else
        log "    Já patcheado: PythonActivity.java (template)"
    fi
else
    log "    AVISO: PythonActivity.java template não encontrado em $P4A_ACT"
fi
# Também patchar na dist se já existir (builds incrementais sem remoção da dist)
while IFS= read -r -d '' ACT; do
    if ! grep -q "hwuifix" "$ACT"; then
        # Remove patch anterior (clearFlags sozinho) se presente, para não duplicar
        sed -i '/getWindow()\.clearFlags(android\.view\.WindowManager\.LayoutParams\.FLAG_HARDWARE_ACCELERATED);/d' "$ACT"
        sed -i 's/Log\.v(TAG, "About to do super onCreate");/try { System.loadLibrary("hwuifix"); } catch (UnsatisfiedLinkError e) { android.util.Log.w("hwuifix", "libhwuifix.so not found, HWUI workaround disabled"); }\n        getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED);\n        Log.v(TAG, "About to do super onCreate");/' "$ACT"
        log "    Patched dist: $ACT"
    else
        log "    Já patcheado dist: $(basename $(dirname "$ACT"))/$(basename "$ACT")"
    fi
done < <(find \
    "$BUILD_DIR/.buildozer/android/platform/build-arm64-v8a/dists" \
    -name "PythonActivity.java" -print0 2>/dev/null)

# Compilar libhwuifix.so para arm64-v8a (workaround SIGABRT Samsung HWUI CommonPool race)
log "  Compilando libhwuifix.so para arm64-v8a (Samsung HWUI SIGABRT fix)..."
NDK_CLANG="$ANDROID_HOME/ndk/25.1.8937393/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android24-clang"
HWUI_C="$BUILD_DIR/hwui_fix.c"
HWUI_LIBS="$BUILD_DIR/libs/arm64-v8a"
mkdir -p "$HWUI_LIBS"
if [ -f "$NDK_CLANG" ] && [ -f "$HWUI_C" ]; then
    "$NDK_CLANG" -shared -fPIC -O2 \
        -Wl,-z,max-page-size=16384 \
        -o "$HWUI_LIBS/libhwuifix.so" "$HWUI_C" \
        -llog 2>&1 | tee -a "$LOG"
    if [ -f "$HWUI_LIBS/libhwuifix.so" ]; then
        log "    libhwuifix.so OK"
    else
        log "    ERRO: falha ao compilar libhwuifix.so — build continuará sem o fix"
    fi
else
    [ ! -f "$NDK_CLANG" ] && log "    AVISO: NDK clang não encontrado: $NDK_CLANG"
    [ ! -f "$HWUI_C" ]    && log "    AVISO: hwui_fix.c não encontrado: $HWUI_C"
fi

# libc++_shared.so — necessária para numpy e extensões C++ compiladas com NDK c++_shared
NDK_LIBCXX="$ANDROID_HOME/ndk/25.1.8937393/toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so"
if [ -f "$NDK_LIBCXX" ]; then
    cp "$NDK_LIBCXX" "$HWUI_LIBS/libc++_shared.so"
    log "    libc++_shared.so copiado do NDK OK"
else
    log "    AVISO: libc++_shared.so não encontrado no NDK: $NDK_LIBCXX"
fi

log "  Patcheando SDLSurface.java: LAYER_TYPE_NONE (fix hwuiTask SIGABRT Android 14+)..."
PATCH_SDL_COUNT=0
# Busca nos dois locais reais: bootstrap_builds (fonte do SDL2 compilado) e dists (projeto Android)
# Usa -print0 + read -d '' para lidar com espaços em nomes de diretório
while IFS= read -r -d '' SURF; do
    if ! grep -q "LAYER_TYPE_NONE" "$SURF"; then
        if grep -q "setFocusableInTouchMode(true)" "$SURF"; then
            sed -i 's/setFocusableInTouchMode(true);/setFocusableInTouchMode(true);\n        setLayerType(android.view.View.LAYER_TYPE_NONE, null);/' "$SURF"
            log "    Patched: $SURF"
            PATCH_SDL_COUNT=$((PATCH_SDL_COUNT + 1))
        fi
    else
        log "    Já patcheado: $(basename $(dirname "$SURF"))/$(basename "$SURF")"
        PATCH_SDL_COUNT=$((PATCH_SDL_COUNT + 1))
    fi
done < <(find \
    "$BUILD_DIR/.buildozer/android/platform/build-arm64-v8a/build/bootstrap_builds" \
    "$BUILD_DIR/.buildozer/android/platform/build-arm64-v8a/dists" \
    -name "SDLSurface.java" -print0 2>/dev/null)
if [ "$PATCH_SDL_COUNT" -eq 0 ]; then
    log "    AVISO: SDLSurface.java não encontrado (será aplicado após o primeiro build completo)"
fi

# Patch buildozer.spec: garante caminhos locais do WSL
# Garante que sdk_path e ndk_path existam no spec (substitui se existir, insere se não existir)
if grep -q "android.sdk_path" buildozer.spec; then
    sed -i "s|android.sdk_path = .*|android.sdk_path = $ANDROID_HOME|" buildozer.spec
else
    sed -i "/^\[app\]/a android.sdk_path = $ANDROID_HOME" buildozer.spec
fi
if grep -q "android.ndk_path" buildozer.spec; then
    sed -i "s|android.ndk_path = .*|android.ndk_path = $ANDROID_HOME/ndk/25.1.8937393|" buildozer.spec
else
    sed -i "/^\[app\]/a android.ndk_path = $ANDROID_HOME/ndk/25.1.8937393" buildozer.spec
fi
log "  buildozer.spec patcheado: sdk=$ANDROID_HOME"

# Pré-aceitar licenças Android SDK no cache GERENCIADO do buildozer
# Razão: buildozer usa ~/.buildozer/android/platform/android-sdk/ como SDK próprio.
# Sem os arquivos de licença pré-escritos, o sdkmanager bloqueia ao tentar
# instalar build-tools (qualquer versão) e o build falha com "license not accepted".
BLDZ_LICENSES="$HOME/.buildozer/android/platform/android-sdk/licenses"
mkdir -p "$BLDZ_LICENSES"
printf '\n8933bad161af4178b1185d1a37fbf41ea5269c55\nd56f5187479451eabf01fb78af6dfcb131a6481e\n24333f8a63b6825ea9c5514f83c2829b004d1fee' \
    > "$BLDZ_LICENSES/android-sdk-license"
printf '\n84831b9409646a918e30573bab4c9c91346d8abd' \
    > "$BLDZ_LICENSES/android-sdk-preview-license"
printf '\n33b6ad264315f22bfab11723a4bc443c09e65f03' \
    > "$BLDZ_LICENSES/mips-android-sysimage-license"
log "  Licenças buildozer SDK pré-aceitas em $BLDZ_LICENSES"

log "  Cópia concluída."

# CameraHelper.java — encapsula CameraDevice.StateCallback (abstract) para pyjnius
# Copiado para o TEMPLATE p4a (mesma estratégia do patch PythonActivity) para que
# o Gradle compile automaticamente quando a dist for (re)criada.
CAMERA_HELPER_SRC="$BUILD_DIR/CameraHelper.java"
CAMERA_HELPER_TMPL="$P4A_DIR/pythonforandroid/bootstraps/sdl2/build/src/main/java/org/kivy/android/CameraHelper.java"
if [ -f "$CAMERA_HELPER_SRC" ]; then
    cp "$CAMERA_HELPER_SRC" "$CAMERA_HELPER_TMPL"
    log "  CameraHelper.java copiado para template p4a"
fi
# Também copia na dist se já existir (builds incrementais)
while IFS= read -r -d '' DIR; do
    cp "$CAMERA_HELPER_SRC" "$DIR/CameraHelper.java"
    log "  CameraHelper.java copiado para dist: $DIR"
done < <(find \
    "$BUILD_DIR/.buildozer/android/platform/build-arm64-v8a/dists" \
    -path "*/org/kivy/android" -type d -print0 2>/dev/null)

# Patch 3: flatDir no build.gradle template (fix para android.add_aars)
# p4a gera `implementation(name: 'detection_service', ext: 'aar')` mas NÃO adiciona
# flatDir ao allprojects { repositories { } } — Gradle trata como módulo e falha com
# "Could not find :detection_service:". Patch necessário no TEMPLATE para sobreviver
# à deleção da dist durante p4a update.
log "  Patcheando build.gradle template: adicionando flatDir para AAR local..."
# Patch via buildozer.spec: android.add_gradle_repositories = flatDir { dirs 'libs' }
# Belt-and-suspenders: patcha o Jinja2 template também, caso o spec seja sobrescrito
GRADLE_TMPL="$P4A_DIR/pythonforandroid/bootstraps/common/build/templates/build.tmpl.gradle"
if [ -f "$GRADLE_TMPL" ]; then
    if ! grep -q "flatDir" "$GRADLE_TMPL"; then
        sed -i "s/jcenter()/jcenter()\n        flatDir { dirs 'libs' }/" "$GRADLE_TMPL"
        log "    Patched template: build.tmpl.gradle (flatDir AAR local)"
    else
        log "    build.tmpl.gradle já tem flatDir"
    fi
else
    log "    AVISO: build.tmpl.gradle não encontrado: $GRADLE_TMPL"
fi
# Também patchar na dist se já existir (builds incrementais sem remoção da dist)
while IFS= read -r -d '' BGRADLE; do
    if ! grep -q "flatDir" "$BGRADLE"; then
        sed -i "s/mavenCentral()/mavenCentral()\n        flatDir { dirs 'libs' }/" "$BGRADLE"
        log "    Patched dist build.gradle: $(dirname "$BGRADLE" | xargs basename)"
    else
        log "    Dist build.gradle já tem flatDir"
    fi
done < <(find \
    "$BUILD_DIR/.buildozer/android/platform/build-arm64-v8a/dists" \
    -name "build.gradle" -maxdepth 3 -print0 2>/dev/null)

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
