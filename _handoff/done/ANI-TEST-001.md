---
id: ANI-TEST-001
project: animais
parent_task: null
complexity: low
scope: isolated
tools: none
estimated_loc: 20
created: 2026-05-14
priority: normal
retry_count: 1
max_retries: 2
assigned_by: antigravity
---
# Task de teste: validar Maestro v4

## Objetivo
Criar uma função Python simples que recebe uma lista de nomes de animais
e retorna apenas os que começam com vogal.

## Entrada
```python
animais = ["Anta", "Capivara", "Onça", "Ema", "Urubu", "Tatu"]
```

## Saída esperada
```python
["Anta", "Onça", "Ema", "Urubu"]
```

## Critérios de sucesso
- [ ] Função `filtrar_vogais(lista)` implementada
- [ ] Case-insensitive (funciona com maiúsculas e minúsculas)
- [ ] Retorna lista vazia se nenhum animal começar com vogal
