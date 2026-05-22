import sys
import os

# Instala handler SIGABRT para hwuiTask antes de qualquer import Android.
# Samsung Android 16 cria e destrói CommonPool imediatamente (hardwareAccelerated=false),
# causando race condition nos workers hwuiTask0/1. O handler faz pthread_exit(NULL)
# apenas nessas threads, preservando o processo inteiro.
try:
    import ctypes
    ctypes.cdll.LoadLibrary('libhwuifix.so')
except Exception:
    pass

# Adiciona o diretório atual ao path para garantir que core e mobile sejam encontrados
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mobile.main import AnimalDetectorApp

if __name__ == "__main__":
    AnimalDetectorApp().run()
