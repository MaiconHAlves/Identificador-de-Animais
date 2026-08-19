# Identificador de Animais

App Android (Kivy + Buildozer) que detecta animais, humanos e veículos em tempo real via câmera, usando YOLOv8 → ONNX → OpenCV DNN no Android e ONNX Runtime no Desktop.

## Onde olhar primeiro

| Arquivo | Pra quê |
|---------|---------|
| `PROJECT_STATE.md` | **Estado completo do projeto** — modelos ativos, datasets, scripts, problemas resolvidos, histórico de mudanças. Ler primeiro. |
| `WORKFLOW_APK_S24.md` | **Fonte da verdade do plano de execução** — Opções A/B/C, comandos, tabela de status dos APKs. |
| `SUCCESS.md` | Marcos atingidos. |
| `RESOURCES.md` | Links e materiais externos. |
| `_handoff/` | Canal Cowork ↔ Claude Code (Antigravity). `STATE.md` resume o handoff atual; `TASK.md` é o pedido pra quem está no terminal. |

## Estado em 1 frase (08/05/2026)

Treino do **`full_detection_v3_nano`** (YOLOv8n, 95 classes — 80 COCO + 15 espécies BR) rodando overnight em RTX 3090 (~8-12h, 150 epochs). Próxima ação humana: amanhã.

## Stack rápida

- **Linguagem/runtime:** Python 3.12, Kivy, Buildozer, OpenCV 4.13 (desktop) / OpenCV 4.5.1 (Android via cv2.dnn).
- **Treino:** PyTorch + Ultralytics YOLOv8 em RTX 3090 (24 GB VRAM).
- **Inferência:**
  - Android: OpenCV DNN CPU (modelos `nodfl`, < ~15 MB por causa do bug do OpenCV 4.5.1 com modelos maiores).
  - Desktop: ONNX Runtime DirectML/CUDA (com DFL nativo).
- **Build:** WSL → `build_local.sh` → APK arm64-v8a.
- **Dispositivo-alvo:** Samsung S24 Ultra (NPU Exynos 2400 ainda inativa — chega na Opção C).

## Datasets

- `D:/datasets/coco/` — COCO 2017 (80 classes, 118k+5k imgs)
- `D:/datasets/br_detection/` — 15 espécies BR (1.008 imgs, labels v3 via auto-label)
- `D:/datasets/african-wildlife/` — auxiliar
- `datasets/full_detection.yaml` — combina COCO + BR, nc=95

## Convenções deste projeto

- **Decisões importantes** vão pra seção "Histórico de mudanças" do `PROJECT_STATE.md`, com data.
- **Nomes de modelos (padrão a partir de 10/05/2026):** `<escopo>_<arch>_nc<NN>_v<N>_m<MMM>_<flags>.onnx`
  - `escopo` = domínio (`fulldet` = COCO+BR, `wildbr` = só fauna BR, `coco` = só COCO).
  - `arch` = `yolov8n`/`yolov8s`/`yolov8m`.
  - `nc<NN>` = nº de classes (ex: `nc95`).
  - `v<N>` = versão da run.
  - `m<MMM>` = mAP50 × 1000 (ex: `m692` = 69.2%). Omitir em modelos legados sem métrica registrada.
  - `flags` (alfabéticas, no fim): `nodfl` (DFL stripped — obrigatório pro OpenCV DNN Android), `cv451` (compat OpenCV 4.5.1), `fp16`, `int8`, `noattn`, `i320`/`i1280` (imgsz não-default).
  - Exemplo: `fulldet_yolov8n_nc95_v3_m692_nodfl.onnx`.
  - Modelos antigos não serão renomeados (rastreabilidade do que já rodou).
- **Treinos longos** vão pra `D:/training/runs/<run-name>/`; pesos em `weights/best.pt` e `last.pt` (resume automático).
- **Mobile (Kivy):** modelo é selecionado em `mobile/main.py` (linha ~52). HUD em `mobile/style.kv` linha 84 já não tem mais valores hardcoded.

## Compactar sessão Cowork (herda D16 do meta — 12/05/2026)

Quando Maicon fala "compacta sessão" / "resume essa conversa" — ou Cowork detecta sessão pesada (>30 turnos, várias decisões D??, trabalho substancial) — Cowork escreve `_handoff/SESSAO_YYYY-MM-DD_resumo.md` com 6 seções: conversa em bullets, decisões D??, arquivos modificados, trabalho aplicado, pendências, como retomar. Em conversa nova, "retoma sessão de <data>" → Cowork lê o resumo e segue. Detalhes da convenção em `../Equipe de Trabalho/_agent/memories/Fluxos.md` § "Compactar sessão Cowork (D16)".

## Stack de IAs do Maicon (referência)

- **Claude Code** — codificação principal.
- **Qwen3 local** (D13 multi-tier, atualizado pela **D118/D119** em 19/08: `qwen3.8:27b` @ 11435 na RTX 3090, `qwen3-coder:light` @ 11434 na RTX 3080 — **as 2 quentes**, `keep_alive=-1`) — `qwen.py` invoca via REST.
- **Gemini CLI** — pesquisa e brainstorming.

## Regra de papel — [COWORK] vs [CODE] (D24 — obrigatório)

Olhe o título da janela onde você está e obedeça estritamente:

- **`[COWORK] Identificador de Animais …`** (role `cowork-supervisor`, Opus 4.7) — você **PLANEJA, DECIDE, ESCREVE TASK.md**. Não execute implementação direto.

  **Você NÃO deve:**
  - Editar código do app: `*.py` (Kivy/UI/inferência), `main.py`, `buildozer.spec`
  - Editar dataset, modelo `*.onnx`, scripts de treino
  - Rodar `buildozer android debug/release`, treinamento YOLOv8, scripts de inferência, build APK, `git commit` de código

  **Você pode/deve:**
  - Atualizar `_handoff/STATE.md`, `_agent/DECISION_LOG.md`, `_agent/memories/*.md`
  - Escrever `_handoff/TASK.md` com `Status: pronto` no front-matter YAML
  - Aguardar `_handoff/RESULT.md` do [CODE] com `Status: concluído`

- **`[CODE] Identificador de Animais …`** (role `code-consumer`, Sonnet 4.6) — você **EXECUTA**: edita Python, roda `buildozer`, treina/infere, delega para Qwen via `qwen.py --task` quando aplicável. Lê TASK.md (dispatchada), escreve RESULT.md ao concluir.

- **Janela sem prefixo `[…]`** — meta/coordenação geral. Sem restrição rígida.

**Por quê:** [COWORK] tende a inerciar pra implementação quando ganha contexto de código — viola a separação de papéis, deixa [CODE] ocioso, queima quota Opus em trabalho de Sonnet. Se perceber que vai editar `.py` ou rodar `buildozer` como [COWORK], **PARE e escreva TASK.md**.

## Modos operacionais (D24) — per-projeto

`_handoff/mode.txt` deste projeto: `manual` (default) ou `autonomo`. Switch via palavra-chave (`manual`/`para`/`espera` → manual; `autonomo`/`vai sozinho` → autonomo). Em manual, extension Cowork-supervisor insere `@RESULT.md` sem Enter; em autonomo, auto-submete e Maestro pausa em 80% quota (PAUSE.flag → WAKE.md). Pra abrir par de janelas: criar `cowork.code-workspace` + `code.code-workspace` (copiar do Mercado como template). Detalhes em [Equipe de Trabalho/CLAUDE.md](../Equipe%20de%20Trabalho/CLAUDE.md) § "Modos operacionais".

## Delegação Qwen — gatilhos objetivos (D26)

**Code (Sonnet): pre-flight obrigatório em TODO RESULT.md.** Abra o RESULT.md
com um bloco `## Pre-flight Qwen` contendo 3 linhas: (1) gatilho exato da tabela,
(2) tier escolhido (light/heavy/solo), (3) justificativa em 1 linha. Sem pre-flight = RESULT incompleto.

### Tabela de gatilhos (escolha SEMPRE 1)

| Caso | Tier |
| ---- | ---- |
| Smoke test / sanity check (JSON simples) | **light** |
| Análise de log <500 linhas (grep/contagem/padrão) | **light** |
| Boilerplate isolado (docstring, fixture, header de função) | **light** |
| Refactor 1-2 arquivos com padrão repetitivo claro | **light** |
| Resposta factual sobre conteúdo de 1 arquivo | **light** |
| Análise de log >500 linhas (precisa context 32k) | **heavy** |
| Refactor 3+ arquivos com padrão repetitivo | **heavy** |
| Ciclo build→test→fix (qwen.py loopa até 12 iters) | **heavy** |
| Geração de testes pra módulo >100 linhas | **heavy** |
| Patch complexo de lógica isolada em 1-3 módulos | **heavy** |
| **Decisão arquitetural ou trade-off de design** | **solo** |
| **Execução de comando** (buildozer, adb, gradlew, git push) | **solo** |
| **Treino YOLO ao vivo** (ocupa 3090 — protocolo D15) | **solo** |
| **Tasks <5 linhas** (overhead QWEN_TASK > ganho) | **solo** |
| **Edição de arquivos protegidos** (lista abaixo) | **solo** |

### Arquivos protegidos do Animais (delegação só com OK explícito do Cowork)

- `core/detection_engine.py` — inferência principal
- `core/android_camera2.py` — bridge Android Camera2
- `buildozer.spec` — config build (regressão = APK quebra)
- `_research/litert_poc/` — POC LiteRT/AICore em iteração ativa (T015.b)
- `p4a-recipes/` — recipes customizadas python-for-android
- `data/unified.yaml`, `data/*.yaml` — config de treino

### Invocação

```powershell
py -3.12 qwen.py --light --task _handoff\QWEN_TASK.md   # light tier (RTX 3080, ~3-8s)
py -3.12 qwen.py --task _handoff\QWEN_TASK.md            # heavy tier (RTX 3090, ~15-60s; checar GPU lock D15 antes — treino YOLO ocupa)
```

Qwen escreve `_handoff/QWEN_RESULT.md` (resposta livre) ou `_handoff/SUCCESS.md`/`ESCALATE.md` (modo loop). **Code (você) aplica os patches no filesystem** — Qwen é LLM puro via Ollama, **não edita arquivos**, só responde texto.

### Conferência (obrigatório quando delegou)

1. Leia `QWEN_RESULT.md` integralmente.
2. Compare item-por-item com o critério de aceite da TASK.
3. Aplique patches no filesystem você mesmo — **nunca** confie no "feito" do Qwen sem inspecionar.
4. Se Qwen errou >2 critérios, refazer solo e marcar `pre-flight invalidado` no RESULT.
5. Cite explicitamente: `Delegado pro Qwen <tier>, validei X/Y critérios, output em _handoff/QWEN_RESULT.md.` (substitua `<tier>` por `light` ou `heavy`).

## Idioma

Sempre responder em **português (pt-BR)**.
