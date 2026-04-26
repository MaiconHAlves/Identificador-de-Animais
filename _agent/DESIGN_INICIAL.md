# 📐 Design Inicial: Identificador de Animais (V1 & V2)

Este documento detalha a arquitetura técnica para o sistema de detecção e alerta veicular.

---

## 1. Arquitetura de Alto Nível (Pipeline de Dados)

O sistema opera em um ciclo de **Pipeline Assíncrono** para garantir que a interface do usuário não trave enquanto a IA processa os quadros.

### Fluxo de Dados:
1.  **Ingestão**: Threads independentes capturando quadros via **Ring Buffer** (circular) de 5 posições para evitar perda de frames.
2.  **Sincronização (Surgical Sync)**: Alinhamento de quadros térmicos e visuais usando `time.monotonic_ns()`. A fusão seleciona o par com o menor delta temporal (jitter compensation).
3.  **Inferência Híbrida**: 
    *   Filtro de calor (Assinatura Térmica) define ROIs.
    *   YOLOv8 processa ROIs no quadro RGB (Habilitado para NNAPI/CoreML).
4.  **Orquestração de Alerta**: Filtro de Kalman para previsão de trajetória e redução de falsos positivos.

### Componentes do Core (Otimizados):
*   `SensorManager`: Gerencia a conexão.
*   `DetectionEngine`: Execução via ONNX Runtime com aceleração de hardware.
*   `FusionEngine`: Processamento de matrizes via **Numba/Cython** para máxima performance em Python.

---
> **"Esta estrutura de pipeline assíncrono faz sentido? Isso garante que, mesmo se a IA demorar 100ms, o vídeo na tela continue fluido."**
