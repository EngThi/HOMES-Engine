# VideoLM HOMES-Engine Terminal Handoff

Este arquivo e para passar ao lado VideoLM. O foco e a pagina `/engine-demo`, o contrato de render publico e os cuidados para o reviewer nao ver falso sucesso nem player quebrado.

## Objetivo

`/engine-demo` deve parecer o HOMES-Engine em si: um terminal-first reviewer surface.

Nao deve parecer SaaS dashboard.
Nao deve parecer painel generico do VideoLM.
Nao deve prometer "completed" antes de validar o MP4.

O reviewer ja rejeitou antes porque a demo dizia que estava pronta, mas o player nao tocava. Entao o requisito principal e:

```text
so mostrar sucesso depois de HEAD 200/206 + content-type video/mp4
```

## URL Base

```text
https://54-162-84-165.sslip.io
```

Pagina:

```text
https://54-162-84-165.sslip.io/engine-demo
```

Title obrigatorio:

```html
<title>HOMES-Engine</title>
```

O teste atual confirmou que `/engine-demo` retorna:

```text
<title>HOMES-Engine</title>
```

## Visual Obrigatorio da Pagina

A pagina deve parecer terminal.

Usar:

- fundo preto/dark;
- monospace em tudo;
- prompt `$`;
- logs compactos;
- texto verde/branco/ambar;
- comando clicavel como command chip;
- output em linhas de terminal;
- player inline apenas depois de validacao.

Evitar:

- hero;
- cards grandes;
- SaaS dashboard;
- grid de stats visual;
- forms grandes na primeira tela;
- marketing copy;
- "Operational dashboard";
- "Deterministic render";
- "Pre-rendered fallback";
- "Terminal-first video generation through VideoLM" como headline grande.

Se mencionar VideoLM, manter pequeno em output:

```text
videolm: connected
```

## Primeira Tela Recomendada

```text
HOMES-Engine

$ homes-engine health
engine: online
videolm: online
notebooklm: ready
queue: 1 render lane

$ homes-engine demo --style paper_craft
```

Nada de dashboard copy grande.

## Comandos Visiveis/Clicaveis

Usar estes comandos principais:

```text
$ homes-engine health
$ homes-engine demo
$ homes-engine notebooklm --url https://hackclub.com --style paper_craft --format brief
$ homes-engine gallery
$ homes-engine capabilities
$ homes-engine outputs
$ open output.mp4
```

Opcional se a pagina tambem quiser mostrar o lado modular:

```text
$ homes-engine manifest
$ homes-engine status
$ homes-engine recipes
$ homes-engine run engine_smoke
```

## Reviewer Happy Path

O primeiro comando seguro deve ser:

```text
$ homes-engine demo
```

Comportamento:

1. cria render curto deterministico;
2. mostra `queued`;
3. mostra `progress`;
4. mostra `verifying mp4...`;
5. resolve URL relativa contra `https://54-162-84-165.sslip.io`;
6. faz HEAD;
7. exige status 200 ou 206;
8. exige `content-type` contendo `video/mp4`;
9. so depois mostra sucesso;
10. so depois injeta `src` no player.

Output final:

```text
mp4 verified: https://54-162-84-165.sslip.io/videos/...
$ open output.mp4
```

## Contrato Publico de Demo Render

Endpoint:

```text
POST https://54-162-84-165.sslip.io/api/video/demo/assemble
```

Tipo:

```text
multipart/form-data
```

Campos aceitos:

```text
projectId  optional
audio      required file
images     required file[]
script     optional string
duration   optional number|string
bgMusic    optional file
bgMusicId  optional string
```

Resposta esperada:

```json
{
  "message": "Video assembly queued - use /status to track progress",
  "projectId": "terminal_dash_1777670483",
  "videoUrl": "/videos/terminal_dash_1777670483_1777670483410.mp4",
  "statusUrl": "/api/video/terminal_dash_1777670483/status"
}
```

Polling:

```text
GET https://54-162-84-165.sslip.io/api/video/{projectId}/status
```

Resposta completed:

```json
{
  "status": "completed",
  "progress": 100,
  "stage": "completed",
  "videoUrl": "/videos/terminal_dash_1777670483_1777670483410.mp4",
  "videoPath": "/videos/terminal_dash_1777670483_1777670483410.mp4"
}
```

Importante:

- `videoUrl` pode ser relativo;
- resolver relativo contra base URL;
- nao esperar `/downloads/...`;
- o app serve `/videos/...`;
- status pode ter `progress`, mas a UI deve tolerar ausencia de progress em alguns fluxos.

## MP4 Publico Verificado

Este MP4 foi gerado em teste real e validado:

```text
https://54-162-84-165.sslip.io/videos/terminal_dash_1777670483_1777670483410.mp4
```

Validacao:

```text
HEAD 200
content-type: video/mp4
content-length: 783759
```

Pode usar como exemplo seguro de gallery/fallback, desde que tambem valide via HEAD antes de mostrar player.

## Links Antigos Que Nao Devem Ser Usados

Estes links retornaram 404 durante teste:

```text
https://54-162-84-165.sslip.io/videos/research_community_1777566704645.mp4
https://54-162-84-165.sslip.io/videos/research_codex_notebooklm_hackclub.mp4
```

Nao usar esses links hardcoded no player ou README.

Se forem exibidos em galeria, a pagina deve validar e esconder/remarcar como unavailable.

## NotebookLM Flow

NotebookLM deve existir como comando secundario, nao como primeiro caminho do reviewer.

Comando:

```text
$ homes-engine notebooklm --url https://hackclub.com --style paper_craft --format brief
```

Endpoint:

```text
POST https://54-162-84-165.sslip.io/api/engine/notebooklm/video
```

Campos:

```text
projectId      optional
title          optional
theme          optional
urls           optional, https:// URL(s)
assets         optional, file[]
style          classic | whiteboard | watercolor | anime | kawaii | retro_print | heritage | paper_craft | custom
format         brief | explainer | cinematic, default brief
stylePrompt    required if style=custom
liveResearch   optional
notebookId     optional existing NotebookLM notebook id
profileId      default
```

Polling:

```text
GET https://54-162-84-165.sslip.io/api/research/{projectId}/download
```

Expected wait text:

```text
expected wait: 8-12 minutes
```

Nao colocar NotebookLM como primeiro clique porque pode demorar.

## Gallery

Gallery deve parecer filesystem:

```text
$ ls outputs/
terminal_dash_1777670483_1777670483410.mp4
```

Antes de listar/abrir qualquer item:

1. resolver URL absoluta;
2. HEAD;
3. exigir 200/206;
4. exigir `video/mp4`;
5. se falhar, nao mostrar como playable.

## Player

O player deve aparecer inline abaixo do terminal output apenas depois de:

```text
status === completed
videoUrl || videoPath exists
HEAD returns 200 or 206
content-type includes video/mp4
```

Antes:

```text
verifying mp4...
```

Depois:

```text
mp4 verified
$ open output.mp4
```

Deve haver link `Open MP4` para abrir direto em nova aba.

## Health e Manifest

Health:

```text
GET https://54-162-84-165.sslip.io/api/engine/health
```

Resposta atual:

```json
{
  "status": "ok",
  "service": "VideoLM Engine Bridge",
  "baseUrl": "https://54-162-84-165.sslip.io"
}
```

Manifest:

```text
GET https://54-162-84-165.sslip.io/api/engine/manifest
```

O frontend deve usar `baseUrl` do manifest quando possivel.

## Terminal Output Exemplo

```text
HOMES-Engine

$ homes-engine health
engine: online
videolm: connected
notebooklm: ready
queue: 1 render lane

$ homes-engine demo
queued: terminal_dash_1777670483
stage: rendering
progress: 100%
verifying mp4...
head: 200
content-type: video/mp4
mp4 verified: https://54-162-84-165.sslip.io/videos/terminal_dash_1777670483_1777670483410.mp4

$ open output.mp4
```

## O Que Remover da UI

Remover como copy grande:

```text
Terminal-first video generation through VideoLM
VideoLM: https://54-162-84-165.sslip.io
Operational dashboard
Deterministic render
Pre-rendered fallback
NotebookLM video
```

Substituir por terminal output pequeno:

```text
videolm: connected
mode: reviewer-safe demo
queue: 1 render lane
```

## Integracao com HOMES Hub

O Hub/MCP e o plano de controle.
VideoLM e a pagina `/engine-demo` sao a superficie hosted/visual do Engine.

A pagina VideoLM nao precisa listar todo o site do Hub. Mas pode mostrar capabilities do Engine se receber ou hardcodar de forma minima:

```text
system.status
agent.runtime_manifest
agent.recipe_run
agent.output_list
production.video_render
production.notebooklm_submit
```

Se possivel, a pagina deve ter comandos:

```text
$ homes-engine capabilities
$ homes-engine recipes
$ homes-engine outputs
```

Mas a acao principal para reviewer continua:

```text
$ homes-engine demo
```

## Acceptance Test da Pagina

Antes de considerar pronto:

1. abrir `/engine-demo` em incognito;
2. browser title e `HOMES-Engine`;
3. primeira tela parece terminal, nao dashboard;
4. nao ha hero/marketing/card-grid dominante;
5. rodar health;
6. rodar demo;
7. logs mostram queued/progress/verifying;
8. sucesso nao aparece antes de HEAD validation;
9. player aparece so depois de `video/mp4`;
10. `Open MP4` abre MP4 real, nao HTML/JSON;
11. gallery nao mostra link 404 como playable;
12. NotebookLM aparece como comando secundario;
13. VideoLM main app nao precisa linkar para Engine demo;
14. se render falhar, terminal mostra erro claro e nao player quebrado.

## Resultado do Teste Real

Teste feito:

```text
POST /api/video/demo/assemble
projectId=terminal_dash_1777670483
audio=cache/test_render_v18_audio.wav
images=assets/broll/i1.jpg
script=Terminal dashboard smoke test from HOMES-Engine.
duration=5
```

Resposta:

```json
{
  "projectId": "terminal_dash_1777670483",
  "videoUrl": "/videos/terminal_dash_1777670483_1777670483410.mp4",
  "statusUrl": "/api/video/terminal_dash_1777670483/status"
}
```

Polling retornou:

```json
{
  "status": "completed",
  "progress": 100,
  "videoUrl": "/videos/terminal_dash_1777670483_1777670483410.mp4"
}
```

HEAD final:

```text
HTTP/2 200
content-type: video/mp4
content-length: 783759
```

Conclusao: o fluxo publico atual funciona quando a pagina valida o MP4 correto e nao usa links antigos.
