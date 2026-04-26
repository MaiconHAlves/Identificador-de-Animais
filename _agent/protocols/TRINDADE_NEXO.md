# 🏛️ Protocolo Trindade NEXO (V2.2 - Auditoria Ativa)

Este documento define a interação obrigatória entre as IAs neste projeto, conforme diretriz global em `C:\Users\alves\.nexo\GLOBAL_CONFIG.json`.

## 1. Hierarquia e Papéis
- **Antigravity (Gerente)**: Responsável pelo planejamento, orquestração e interface com o Usuário.
- **Claude (Cirurgião)**: Responsável por implementações críticas, revisões de código e auditoria de segurança. **Detém o Poder de Veto**.
- **Qwen (Operário)**: Responsável por scripts auxiliares, refatoração em massa e prototipagem rápida.

## 2. Fluxo de Trabalho (Loop de Ouro)
1. **Solicitação**: O Usuário faz um pedido ao Antigravity.
2. **Desenho**: Antigravity desenha a solução (Brainstorming).
3. **Execução**:
    - Tarefa Técnica: Claude executa via CLI.
    - Tarefa Repetitiva: Qwen executa.
4. **Auditoria Obrigatória**: 
    - Toda alteração técnica de Antigravity ou Qwen exige auditoria do Claude.
    - **Checklist**: (1) Segurança, (2) Tratamento de Erros, (3) Performance, (4) Regressões.
5. **Veredito**: 
    - `APROVADO`: Antigravity sincroniza/aplica.
    - `VETO`: Claude trava a tarefa e registra justificativa; o time deve refazer.

## 3. Protocolo de Debug Automático
Sempre que uma Build falhar:
1. Antigravity captura o erro (Log completo).
2. Antigravity anexa o `git diff` e envia para o Claude.
3. Claude diagnostica e prescreve a correção.
4. Qwen prototipa a solução conforme a receita do Claude.
5. Claude valida a eficácia da correção.
6. Antigravity aplica a solução final no repositório.
