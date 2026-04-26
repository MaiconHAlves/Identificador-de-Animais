[app]
title = Identificador de Animais
package.name = animaldetector
package.domain = com.nexo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,onnx,wav
version = 1.0.0

# Requisitos do sistema
requirements = python3,kivy==2.3.0,opencv,numpy,onnxruntime,pillow

# Configurações de Orientação
orientation = landscape

# Permissões Android
android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET, RECORD_AUDIO

# Configurações de API e Arquitetura (Otimizado para celulares modernos)
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

# (str) Icon of the application
#icon.filename = assets/icon.png

# (str) Presplash of the application
#presplash.filename = assets/presplash.png

# (list) List of service to declare
#services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT2_TO_PY

[buildozer]
log_level = 2
warn_on_root = 1
