[app]
title = Identificador de Animais
package.name = animaldetector
package.domain = com.nexo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,onnx,wav
source.exclude_dirs = datasets, fauna_br, thermal-animal-1, road-animals-2, runs, _agent, research, scratch
version = 1.0.2

# Requisitos Estabilizados (OpenCV DNN em vez de ONNX)
requirements = python3, kivy, opencv, numpy, pillow

# Configurações de Elite para S24 e Android 16
android.api = 34
android.minapi = 24
android.ndk = 25c
android.build_tools = 34.0.0
android.enable_androidx = True
android.archs = arm64-v8a

# Prevenir SIGABRT no SDL2 (Hints para o motor de renderização)
android.meta_data = SDL_ANDROID_TRAP_SIG_CRITICALS=1
android.meta_data = SDL_RENDER_DRIVER=opengles2

# Otimização de Build
p4a.branch = master
p4a.bootstrap = sdl2
warn_on_root = 0

[buildozer]
log_level = 2
warn_on_root = 0
