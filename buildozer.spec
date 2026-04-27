[app]
title = Identificador de Animais
package.name = animaldetector
package.domain = com.nexo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,onnx,wav
source.exclude_dirs = datasets, fauna_br, thermal-animal-1, road-animals-2, runs, _agent, research, scratch
version = 1.0.1

# Requisitos de base estável para Android
requirements = python3, kivy, opencv, numpy, pillow

# Configurações de Orientação
orientation = landscape

# Permissões Android
android.permissions = CAMERA, RECORD_AUDIO, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET

# Configurações de Compilação para Android Moderno (14/15)
android.api = 33
android.minapi = 21
android.ndk = 25c
android.ndk_api = 21
android.build_tools = 33.0.1
android.archs = arm64-v8a
android.allow_backup = False

# Deixar o Buildozer gerenciar o SDK localmente para evitar erros de permissão no GitHub
# android.sdk_path = /usr/local/lib/android/sdk
# android.ndk_path = /usr/local/lib/android/sdk/ndk/25b

# Otimização de Build (Usando receitas oficiais do p4a)
p4a.branch = master
# p4a.local_recipes = ./p4a-recipes
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 0
