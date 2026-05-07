[app]
title = Identificador de Animais
package.name = animaldetector
package.domain = com.nexo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,onnx,wav
source.exclude_dirs = datasets, fauna_br, thermal-animal-1, road-animals-2, runs, _agent, research, scratch
source.exclude_patterns = models/global_animal_detector.onnx, models/hybrid_animal_detector.onnx, models/global_animal_detector_cv451.onnx, models/hybrid_animal_detector_cv451.onnx
version = 1.0.17
orientation = landscape

# Requisitos Estabilizados (OpenCV DNN em vez de ONNX)
requirements = python3, kivy, opencv, numpy, pillow

# Android SDK/NDK (Caminhos automáticos para evitar PermissionError no GitHub)
android.api = 36
android.minapi = 26
android.ndk = 26b
android.ndk_api = 26
android.build_tools = 35.0.0
android.enable_androidx = True
android.archs = arm64-v8a, x86_64
android.allow_backup = True
android.permissions = CAMERA, RECORD_AUDIO, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET
android.add_src = src
# android.add_libs_arm64_v8a = libs/arm64-v8a/libhwuifix.so, libs/arm64-v8a/libc++_shared.so

# Otimização de Build e Stripping (Evita erro na libopencv_videoio.so)
android.no_strip = libopencv_videoio.so, libopencv_highgui.so, libopencv_objdetect.so

# Metadados: Estabilidade SDL2 + Performance S24
android.meta_data = SDL_ANDROID_TRAP_SIG_CRITICALS=1, SDL_RENDER_DRIVER=opengles2, android.max_aspect=2.4, android.notch_support=True, SDL_JOYSTICK_HIDAPI=0

# Recipes locais
p4a.local_recipes = ./p4a-recipes

# Build
p4a.branch = master
p4a.bootstrap = sdl2
warn_on_root = 0

[buildozer]
log_level = 2
warn_on_root = 0
