[app]
title = Identificador de Animais
package.name = animaldetector
package.domain = com.nexo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,onnx,wav
version = 1.0.1

# Requisitos refinados para IA Móvel (Numpy 1.21.0 para estabilidade Android)
requirements = python3, kivy==2.3.0, opencv, numpy==1.21.0, pillow, onnxruntime

# Configurações de Orientação
orientation = landscape

# Permissões Android (Câmera + Áudio Tático)
android.permissions = CAMERA, RECORD_AUDIO, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET

# Configurações de Compilação (Estabilizadas para Compilação de IA)
android.api = 31
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.build_tools = 31.0.0
android.archs = arm64-v8a
android.allow_backup = False

# Otimização de Build
p4a.branch = master
p4a.local_recipes = ./p4a-recipes
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 0
