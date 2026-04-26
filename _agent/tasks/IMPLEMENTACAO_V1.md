# 🛠️ Task List: Implementação V1 (Mobile MVP)
**Projeto: Identificador de Animais**

Este documento rastreia o progresso da implementação técnica do MVP.

## 🟢 Fase 1: Fundação do Core (Python)
- [ ] `core/sensor_manager.py`: Implementação do Ring Buffer e Captura Assíncrona.
- [x] `core/detection_engine.py`: Integração com YOLOv8 via ONNX Runtime. (Refinado por Claude)
- [x] `core/fusion_engine.py`: Lógica de sincronização por Monotonic Clock. (Refinado por Claude)

## 🔵 Fase 2: Interface Mobile (Kivy)
- [x] `mobile/main.py`: Estrutura base da aplicação. (Refinado por Claude)
- [x] `mobile/ui_tactical.py`: Overlay visual e Bounding Boxes. (Refinado por Claude)
- [x] `mobile/audio_manager.py`: Sistema de alertas sonoros progressivos. (Refinado por Claude)

## 🟡 Fase 3: Integração e Testes
- [ ] Simulação de sensores via arquivos de vídeo.
- [ ] Teste de latência ponta-a-ponta.
- [ ] Otimização de performance (Numba/Cython).
