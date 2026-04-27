import sys
import os

# Adiciona o diretório atual ao path para garantir que core e mobile sejam encontrados
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mobile.main import AnimalDetectorApp

if __name__ == "__main__":
    AnimalDetectorApp().run()
