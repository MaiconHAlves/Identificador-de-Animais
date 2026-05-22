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
| D09 | **Migrar runtime: cv2.dnn → Serviço Nativo Kotlin + LiteRT/AICore** (10/05/2026 noite) | (a) Manter cv2.dnn 4.5.1; (b) ORT + NNAPI (TASK 14 antiga); (c) LiteRT via ctypes/Pyjnius em Python puro; (d) Migração total Kotlin (UI + IA). | cv2.dnn congelado com bug >15 MB e sem NPU; NNAPI deprecado pelo Google em 2024; sem wheel `android_aarch64` no PyPI (TASKs 10 e 12 bloqueadas); migração total dobra custo. Stack bi-linguagem (Python + Kotlin) é risco aceito. | LiteRT + AICore é stack oficial Google daqui pra frente, com NPU/GPU nativa no S24. Único caminho com 30+ fps comprovado mantendo Kivy. PoC PTQ INT8 antes de QAT (T014 → T017). Single-engine só após v4 unificado funcional (catastrophic forgetting do v3 nas COCO 0-79). |
| D10 | **Empacotar Service Kotlin como AAR pré-compilado** (11/05/2026, gate da T015) | (a) Reescrever em Java — risco zero, custo zero, mas perde-se Kotlin; (b) Patch template p4a com Kotlin Gradle plugin — risco médio, ~2-4h extra; (c) **AAR pré-compilado** (escolhida). | p4a/SDL2 bootstrap NÃO inclui Kotlin Gradle plugin no `build.gradle` gerado. `android.add_src` com `.kt` falharia. Bloqueio descoberto pelo Claude Code no passo 0 (pesquisa obrigatória) da T015 original. | AAR isola a stack Kotlin do template p4a — Android Studio compila o módulo (estendendo `_research/litert_poc/`), gera `.aar`, Buildozer importa via `android.add_aars`. Quando T016 integrar LiteRT real, o Android Studio já estará envolvido. Custo: +5-10h vs Java, mas ganha Kotlin idiomático + isolamento futuro de mudanças do p4a. |

## Objeções Pendentes
- [x] Risco de incompatibilidade do ONNX com Android 16 (Resolvido com D08).
- [x] Impacto térmico do GLES 3 + IA em tempo real (Resolvido com D07).
- [x] Fluxo de permissões de Câmera no Android 16 (Resolvido com D06).
- [ ] **D09:** validar versão estável do AAR LiteRT + AICore delegate em mai/2026 antes de T015 — ✓ resolvido em T014 (LiteRT 1.4.0).
- [ ] **D09:** confirmar suporte AICore no Exynos 2400 do S24 (Pixel-first, Samsung pode ter limitações). Gate da T016 — teste físico ainda pendente.
- [ ] **D10:** validar que `android.add_aars` do Buildozer aceita AAR multi-módulo gerado pelo Android Studio sem quebrar build do APK (passo 0 da T015 ajustada).
- [ ] **D10:** confirmar que o AAR compilado expõe o `DetectionService` corretamente via Pyjnius (sem proguard/R8 obfuscation no debug build).
