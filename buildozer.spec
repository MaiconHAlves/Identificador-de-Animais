[app]
title = Identificador de Animais
package.name = animaldetector
package.domain = com.nexo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,onnx,wav
source.exclude_dirs = datasets, fauna_br, thermal-animal-1, road-animals-2, runs, _agent, research, scratch
version = 1.0.2

# Requisitos de base estável para Android
requirements = python3, kivy, opencv, numpy, pillow

# Configurações de Orientação
orientation = landscape

# Permissões Android
android.permissions = CAMERA, RECORD_AUDIO, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET

# Configurações de Elite para S24 e Android Moderno (14/15/16)
android.api = 34
android.minapi = 24
android.ndk = 25c
android.ndk_api = 24
android.build_tools = 34.0.0
android.archs = arm64-v8a
android.allow_backup = True
android.sdk_path = /root/android-sdk
android.ndk_path = /root/android-sdk/ndk/25.1.8937393

# Performance Visual para Telas High-End (S24)
android.meta_data = android.max_aspect=2.4, android.notch_support=True

# Gráficos de Alta Performance
# Requerido para dispositivos modernos com telas de alta taxa de atualização
p4a.services = 
p4a.bootstrap = sdl2
p4a.extra_args = --use-opengl-es3

[buildozer]
log_level = 2
warn_on_root = 0
