# 📓 Decision Log: Identificador de Animais
**Status: Phase 1 (Understanding)**

Este log registra as decisões tomadas durante a fase de concepção e design do projeto.

---

## 🟢 Fase 1: Entendimento (Understanding)

### Decisões e Definições
1. **Estrutura de Memória**: Criada a pasta `_agent/` e o arquivo `MEMORIA_DESIGN_ANIMAIS.md`.
2. **Time de Desenvolvimento**: Confirmada a participação de Antigravity (Arquiteto), Qwen (Operário) e Claude (Cirurgião).
3. **Escopo**: Dispositivo veicular integrado (Hardware + Software) para detecção de animais em rodovias.
4. **Arquitetura**: Foco em Edge Computing (processamento local) para garantir baixa latência.
5. **Tecnologia de Visão**: Fusão de Sensores (Câmera Térmica + RGB) para operação 24/7 em qualquer condição climática.
6. **Estratégia de Desenvolvimento**: Bifurcação em V1 (Mobile/Smartphone) e V2 (Embedded/Industrial).
7. **Stack Tecnológica**: Python (Kivy/BeeWare) para garantir portabilidade total entre Mobile e Embedded.
8. **Organização**: Estrutura Monorepo com pastas separadas para `/core`, `/mobile`, `/embedded` e `/hardware`.
9. **Interface de Alerta**: Sistema híbrido com aviso sonoro (beeps progressivos) e interface visual (bounding boxes/HUD).
10. **Understanding Lock**: Confirmado pelo usuário em 26/04/2026.
11. **Abordagem Escolhida**: Híbrida (Core focado em B, com interface A opcional).
12. **Início do Design Inicial**: 26/04/2026.
13. **Revisão Multidisciplinar**: Concluída (Skeptic, Guardian, Advocate e Surgeon).
14. **Aprovação Final**: Design APROVADO para implementação.

### Objeções e Riscos Identificados
*   **Latência USB**: Mitigada com Ring Buffers e Monotonic Clock.
*   **Superaquecimento**: Mitigado com interface híbrida (Modo B padrão).
*   **Vibração/Obstrução**: Monitoramento de nitidez via IA adicionado.

### Objeções e Riscos Identificados
*   *Nenhuma até o momento.*

### Perguntas Pendentes
*   Qual o objetivo central do projeto? (Aguardando resposta do usuário).
