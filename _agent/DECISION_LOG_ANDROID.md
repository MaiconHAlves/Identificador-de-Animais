# Log de Decisões: Estabilização Android 16 (Samsung S24)

| ID | Decisão | Alternativas | Objeções | Resolução / Racional |
|:---|:---|:---|:---|:---|
| D01 | **API 34 (Target)** | API 31, API 33 | Android 16 pode rejeitar APIs < 34. | API 34 é o padrão atual para S24. |
| D02 | **Root Bridge (main.py)** | Mudar estrutura de pastas | Risco de quebrar imports locais. | Bridge preserva a organização atual. |
| D03 | **GLES 3.0** | GLES 2.0 (Legado) | Consumo de bateria no S24. | S24 é otimizado para GLES 3; evita flicker. |
| D04 | **Local SDK/NDK** | GitHub System SDK | Erros de Permissão (Permission Denied). | Local isola o ambiente e garante sucesso. |
| D05 | **Arquitetura arm64** | arm64 + armeabi-v7a | APK maior e build mais lenta. | S24 é 100% 64-bit; otimiza tempo de build. |
| D06 | **Mídia Moderno** | WRITE_STORAGE | Rejeição no Android 14+. | Substituir por READ_MEDIA permissions. |
| D07 | **FPS Lock (30)** | 60 ou ilimitado | Throttling Térmico no S24. | Preserva CPU para a IA (inferência). |
| D08 | **ONNX Fallback** | Crash Direto | Experiência ruim do usuário. | UI de aviso se a IA falhar no Android 16. |

## Objeções Pendentes
- [x] Risco de incompatibilidade do ONNX com Android 16 (Resolvido com D08).
- [x] Impacto térmico do GLES 3 + IA em tempo real (Resolvido com D07).
- [x] Fluxo de permissões de Câmera no Android 16 (Resolvido com D06).
