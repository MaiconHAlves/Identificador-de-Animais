[app]
title = Identificador de Animais
package.name = animaldetector
package.domain = com.nexo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,onnx,wav
version = 1.0.1

# Requisitos refinados pelo Cirurgião (Claude)
requirements = python3, kivy==2.3.0, opencv, numpy==1.26.4, pillow, hostpython3

# Configurações de Orientação
orientation = landscape

# Permissões Android (Rigor de Segurança)
android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET

# Configurações de Compilação
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = False

# Otimização de Build
p4a.branch = master
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
