# `_handoff/` — Canal de comunicação Cowork ↔ Claude Code

Esta pasta é a "caixa postal" entre o Claude rodando no **Cowork** (planejamento,
análise, edição de arquivos sem terminal) e o Claude Code rodando no **Antigravity**
(execução com acesso a terminal, WSL, GPU).

## Arquivos

| Arquivo | Quem escreve | Quem lê | Conteúdo |
|---------|--------------|---------|----------|
| `TASK.md` | Cowork | Claude Code | Briefing da próxima tarefa: contexto, comandos, critério de sucesso |
| `RESULT.md` | Claude Code | Cowork | Resultado da execução: o que foi feito, comandos rodados, saída, sucesso/falha |
| `STATE.md` | Ambos | Ambos | Snapshot do que mudou no repo (arquivos novos/editados, commits, métricas) |

## Protocolo

1. **Cowork** escreve `TASK.md` com briefing completo, terminando com critério claro de sucesso.
2. **Maicon** fala pro Claude Code: *"leia `_handoff/TASK.md` e execute"*.
3. **Claude Code** executa, depois escreve `RESULT.md` com:
   - O que foi feito (passo a passo)
   - Comandos exatos rodados
   - Arquivos modificados/criados
   - Resultado (sucesso/falha + saída relevante, máx ~80 linhas)
   - Erros encontrados, se houver
4. **Maicon** fala pro Cowork: *"leia `_handoff/RESULT.md`"*.
5. **Cowork** analisa, atualiza `STATE.md` se necessário, e escreve novo `TASK.md` se houver próximo passo.

## Convenções

- **Timestamp no topo** de cada TASK e RESULT (ex: `# TASK — 2026-05-07 21:30`)
- **Sobrescrever**, não acumular. Histórico vai pra `_handoff/archive/YYYY-MM-DD-HHMM-description.md` se importante
- **TASK auto-contido** — Claude Code não precisa ler nada externo pra entender. Se precisar, o TASK aponta exatamente os arquivos a ler primeiro
- **RESULT honesto** — se algo falhou, dizer claramente; se algo "funcionou mas com ressalvas", listar as ressalvas
- **STATE conciso** — apenas o que mudou desde a última sincronização
