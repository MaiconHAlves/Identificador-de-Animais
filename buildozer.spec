[app]
title = Identificador de Animais
package.name = animaldetector
package.domain = com.nexo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,onnx,wav
source.exclude_dirs = datasets, fauna_br, thermal-animal-1, road-animals-2, runs, _agent, research, scratch
version = 1.0.3
orientation = landscape

# Requisitos Estabilizados (OpenCV DNN em vez de ONNX)
requirements = python3, kivy, opencv, numpy, pillow

# Android SDK/NDK (Caminhos automáticos para evitar PermissionError)
# Deixar em branco para o Buildozer usar o diretório local do projeto
android.ndk_api = 24

# Configurações para S24 e Android 16
android.api = 34
android.minapi = 24
android.ndk = 25c
android.build_tools = 34.0.0
android.enable_androidx = True
android.archs = arm64-v8a
android.allow_backup = True
android.permissions = CAMERA, RECORD_AUDIO, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET

# Metadados: Estabilidade SDL2 + Performance S24 (Tudo em uma linha para evitar DuplicateOptionError)
android.meta_data = SDL_ANDROID_TRAP_SIG_CRITICALS=1, SDL_RENDER_DRIVER=opengles2, android.max_aspect=2.4, android.notch_support=True

# Recipes locais (numpy fix)
p4a.local_recipes = ./p4a-recipes

# Build
p4a.branch = master
p4a.bootstrap = sdl2
warn_on_root = 0

[buildozer]
log_level = 2
warn_on_root = 0
