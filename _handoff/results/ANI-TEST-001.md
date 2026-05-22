# Resultado — ANI-TEST-001

- **Agente:** qwen_heavy (qwen3-coder:heavy)
- **GPU:** RTX 3090
- **Duração:** 40.7s
- **Status:** concluído
- **Validação:** ok

## Output

```python
def filtrar_vogais(lista):
    vogais = "aeiouAEIOU"
    return [animal for animal in lista if animal and animal[0] in vogais]

# Teste com a entrada fornecida
animais = ["Anta", "Capivara", "Onça", "Ema", "Urubu", "Tatu"]
resultado = filtrar_vogais(animais)
print(resultado)
```
```
