[app]
title = Identificador de Animais
package.name = animaldetector
package.domain = com.nexo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,onnx,wav
version = 1.0.1

# Requisitos refinados (Claude Prescribed)
# Removido hostpython3 para evitar conflitos nativos
# Requisitos refinados para IA Móvel
requirements = python3, kivy==2.3.0, opencv, numpy==1.26.4, pillow, onnxruntime

# Configurações de Orientação
orientation = landscape

# Permissões Android (Câmera + Áudio Tático)
android.permissions = CAMERA, RECORD_AUDIO, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET

# Configurações de Compilação (Gerenciadas pelo GitHub Actions)
# android.sdk_path = /usr/local/lib/android/sdk
# android.ndk_path = /usr/local/lib/android/sdk/ndk/25.1.8937393
# android.api = 33
# android.minapi = 21
# android.ndk = 25b
# android.ndk_api = 21
# android.build_tools = 34.0.0
android.archs = arm64-v8a
android.allow_backup = False

# Otimização de Build
p4a.branch = master
p4a.local_recipes = ./p4a-recipes
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 0
