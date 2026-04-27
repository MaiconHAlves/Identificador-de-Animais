[app]
title = Identificador de Animais
package.name = animaldetector
package.domain = com.nexo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,onnx,wav
version = 1.0.1

# Requisitos de base estável para Android
requirements = python3, kivy, opencv, numpy, pillow

# Configurações de Orientação
orientation = landscape

# Permissões Android
android.permissions = CAMERA, RECORD_AUDIO, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET

# Configurações de Compilação (Padrão para maior compatibilidade)
android.api = 31
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.build_tools = 31.0.0
android.archs = arm64-v8a
android.allow_backup = False

# Otimização de Build (Usando receitas oficiais do p4a)
p4a.branch = master
# p4a.local_recipes = ./p4a-recipes
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 0
