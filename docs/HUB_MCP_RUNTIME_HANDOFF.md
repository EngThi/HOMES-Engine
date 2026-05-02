# HOMES Hub / MCP Handoff

Este arquivo e para passar ao lado HOMES Hub/MCP. O objetivo e deixar claro o que o HOMES-Engine ja expoe, quais tools MCP fazem sentido, quais comandos o Hub deve enviar ao worker e quais dados o dashboard deve mostrar.

## Estado Atual

O HOMES-Engine agora deve ser tratado como um runtime modular de capacidades, nao apenas como um worker de video.

O caminho principal continua:

```text
HOMES Hub MCP -> Engine worker -> VideoLM renderer -> public MP4 -> Hub dashboard
```

Mas o Engine tambem expoe:

- capability manifest;
- recipes/workflows;
- state/event log;
- profile/policy summary;
- system status;
- remembered outputs;
- local render index;
- comandos remotos via Hub poller.

## Enderecos

Hub:

```text
https://homes.chefthi.hackclub.app
```

VideoLM base usado pelo Engine:

```text
https://54-162-84-165.sslip.io
```

Demo page do Engine no VideoLM:

```text
https://54-162-84-165.sslip.io/engine-demo
```

MP4 publico verificado em 2026-05-01:

```text
https://54-162-84-165.sslip.io/videos/terminal_dash_1777670483_1777670483410.mp4
```

Validacao desse MP4:

```text
HEAD 200
content-type: video/mp4
content-length: 783759
```

## Variaveis Necessarias no Worker

O worker VideoLM/Engine na VM deve ter:

```env
HOMES_HUB_URL=https://homes.chefthi.hackclub.app
HUB_SECRET=<secret HMAC real do Hub>
ENGINE_ID=videolm-engine-1

VIDEOLM_URL=https://54-162-84-165.sslip.io
VIDEOLM_POLL_INTERVAL=5
VIDEOLM_POLL_TIMEOUT=900
```

Os POSTs assinados usam:

```text
X-Homes-Signature: <hmac_sha256_hex>
```

A assinatura e HMAC SHA256 do JSON compacto enviado exatamente no body.

## Endpoints que o Worker Usa no Hub

```text
GET  /api/projects/pending
POST /api/projects/:id/status
POST /api/projects/:id/complete
POST /api/sensors
GET  /api/actuators/mobile/poll
```

Os POSTs precisam HMAC.

## Completion Payload Esperado

Todo job de video concluido deve mandar o maximo de metadata possivel:

```json
{
  "status": "completed",
  "video_path": "/local/path/output.mp4",
  "video_url": "https://54-162-84-165.sslip.io/videos/file.mp4",
  "videoUrl": "https://54-162-84-165.sslip.io/videos/file.mp4",
  "size_bytes": 1603736,
  "duration_seconds": 20,
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "codec": "h264",
  "engine_id": "videolm-engine-1"
}
```

O Hub deve preferir `video_url` ou `videoUrl` para download/playback publico. `video_path` sozinho pode ser path local do Engine e nao deve ser assumido como publico.

## Comandos que o Hub Pode Enviar ao Engine

### Rodar Capability

Formato recomendado:

```json
{
  "command": "run_capability",
  "args": [
    {
      "capability_id": "system.status",
      "args": {},
      "profile": "default"
    }
  ]
}
```

Formato legado aceito:

```json
{
  "command": "run_capability",
  "args": ["system.status", {}]
}
```

### Rodar Recipe

Formato recomendado:

```json
{
  "command": "run_recipe",
  "args": [
    {
      "recipe_id": "engine_smoke",
      "inputs": {},
      "profile": "default"
    }
  ]
}
```

Tambem pode rodar recipe via capability:

```json
{
  "command": "run_capability",
  "args": [
    {
      "capability_id": "agent.recipe_run",
      "args": {
        "recipe_id": "engine_smoke",
        "inputs": {}
      },
      "profile": "default"
    }
  ]
}
```

### Gerar Video Legado

Ainda existe:

```json
{
  "command": "generate_video",
  "args": ["HOMES demo"]
}
```

Mas para o MVP novo, prefira jobs formais do Hub ou `run_recipe`.

## Capabilities Atuais do Engine

O runtime manifest mostrou 15 capabilities:

```text
agent.output_forget
agent.output_list
agent.output_remember
agent.profile_summary
agent.recipe_list
agent.recipe_run
agent.runtime_manifest
agent.state_summary
integration.hosted_demo_url
integration.videolm_health
integration.videolm_manifest
production.notebooklm_poll
production.notebooklm_submit
production.video_render
system.status
```

### Capabilities Mais Importantes para o Dashboard

`agent.runtime_manifest`

- retorna nome, tipo de runtime, engine_id, plataforma, contrato Hub, capabilities, recipes e policy do profile;
- boa base para `get_engine_runtime_manifest`.

`system.status`

- retorna engine_id, sistema, Python, disco, memoria e quantidade de renders;
- boa base para `get_engine_health` ou painel terminal de status.

`agent.profile_summary`

- retorna preferences, goals, devices e policies;
- demonstra que o Engine nao esta hardcoded em um unico perfil.

`agent.state_summary`

- retorna namespaces do state store e eventos recentes;
- bom para dashboard terminal mostrar logs reais.

`agent.output_list`

- lista MP4s locais em `output/renders`;
- lista outputs lembrados no state store, inclusive URLs publicas.

`agent.output_remember`

- salva artifact publico/local no state store.

`agent.output_forget`

- remove artifact quebrado/antigo do state store.

`agent.recipe_list`

- lista workflows declarativos disponiveis.

`agent.recipe_run`

- executa workflow declarativo.

`integration.hosted_demo_url`

- retorna `https://54-162-84-165.sslip.io/engine-demo`.

`integration.videolm_health`

- checa o VideoLM Engine Bridge.

`integration.videolm_manifest`

- le o contrato publico do VideoLM.

`production.video_render`

- render local/VideoLM a partir de script/path.

`production.notebooklm_submit`

- submete job NotebookLM video ao VideoLM.

`production.notebooklm_poll`

- consulta projectId NotebookLM e resolve URL publica.

## Recipes Atuais

### `engine_smoke`

Nao exige inputs.

Passos:

```text
integration.hosted_demo_url
integration.videolm_health
```

Uso recomendado para reviewer/dashboard:

```json
{
  "command": "run_recipe",
  "args": [
    {
      "recipe_id": "engine_smoke",
      "inputs": {},
      "profile": "default"
    }
  ]
}
```

Resultado esperado:

```json
{
  "status": "completed",
  "id": "engine_smoke",
  "steps": [
    {
      "id": "demo_url",
      "status": "completed"
    },
    {
      "id": "health",
      "status": "ok"
    }
  ]
}
```

### `video_render_demo`

Inputs obrigatorios:

```text
topic
script
```

Default:

```json
{
  "brand": "demo"
}
```

Uso:

```json
{
  "command": "run_recipe",
  "args": [
    {
      "recipe_id": "video_render_demo",
      "inputs": {
        "topic": "HOMES demo",
        "script": "Short reviewer-safe HOMES-Engine demo.",
        "brand": "demo"
      },
      "profile": "default"
    }
  ]
}
```

Importante: se faltar `script`, a recipe deve falhar cedo. Isso e intencional para evitar mock silencioso.

## Tools MCP Recomendadas no Hub

As tools antigas podem continuar:

```text
create_engine_job
get_engine_job
list_engine_jobs
retry_engine_job
get_engine_health
list_engine_outputs
get_engine_video_url
test_notify
```

Compatibilidade que ja existia:

```text
create_engine_video_job
get_engine_status
publish_engine_artifact
get_mobile_status
send_mobile_command
get_hardware_capabilities
```

Novas tools recomendadas para o MVP modular:

```text
get_engine_runtime_manifest
list_engine_capabilities
run_engine_capability
list_engine_recipes
run_engine_recipe
get_engine_state
list_engine_events
remember_engine_output
forget_engine_output
get_engine_system_status
get_engine_profile
```

Mapeamento sugerido:

```text
get_engine_runtime_manifest -> run_capability agent.runtime_manifest
list_engine_capabilities    -> telemetry.capabilities ou agent.runtime_manifest
run_engine_capability       -> command run_capability
list_engine_recipes         -> telemetry.recipes ou run_capability agent.recipe_list
run_engine_recipe           -> command run_recipe
get_engine_state            -> run_capability agent.state_summary
list_engine_events          -> run_capability agent.state_summary
remember_engine_output      -> run_capability agent.output_remember
forget_engine_output        -> run_capability agent.output_forget
get_engine_system_status    -> run_capability system.status
get_engine_profile          -> run_capability agent.profile_summary
```

## Telemetry Esperada

`POST /api/sensors` agora deve receber:

```text
engine_id
platform
timestamp
capabilities_count
capabilities
recipes
recent_runtime_events
recent_command_results
storage_free_gb
storage_total_gb
ram_usage
ram_free_mb
renders_size_mb
renders_count
engine_active
```

O dashboard pode usar isso para renderizar uma tela terminal sem hardcode.

## Dashboard Terminal Sugerido no Hub

Mostrar algo como:

```text
HOMES-Engine

$ homes-engine status
engine: videolm-engine-1
hub: connected
videolm: online
queue: 1 render lane
capabilities: 15
recipes: 2

$ homes-engine capabilities
agent.runtime_manifest
agent.recipe_run
agent.output_list
system.status
production.video_render
production.notebooklm_submit

$ homes-engine run engine_smoke
demo_url: https://54-162-84-165.sslip.io/engine-demo
videolm: ok

$ homes-engine outputs
terminal_dash_1777670483_1777670483410.mp4
```

Nao precisa parecer SaaS dashboard. O valor visual e parecer um terminal vivo com comandos e output real.

## Criterios de Aceite para o Hub

1. Hub recebe telemetria com capabilities e recipes.
2. `get_engine_health` mostra Engine conectado.
3. `run_engine_capability(system.status)` retorna completed.
4. `run_engine_recipe(engine_smoke)` retorna completed.
5. `list_engine_outputs` mostra pelo menos o MP4 validado:
   `https://54-162-84-165.sslip.io/videos/terminal_dash_1777670483_1777670483410.mp4`
6. Jobs novos que completam devem ter `video_url` publico, nao apenas `video_path`.
7. O dashboard nao deve mostrar download quando o job so tem path local.
8. O dashboard deve distinguir:
   - pending;
   - processing;
   - completed com public URL;
   - completed sem public URL;
   - error.
9. MCP deve expor pelo menos as tools de job + health + outputs + runtime manifest.
10. Comando remoto deve registrar resultado em `recent_command_results`.

## Problemas Encontrados nos Testes

Links antigos de MP4 publico retornaram 404:

```text
https://54-162-84-165.sslip.io/videos/research_community_1777566704645.mp4
https://54-162-84-165.sslip.io/videos/research_codex_notebooklm_hackclub.mp4
```

Por isso o README foi atualizado para o MP4 novo validado:

```text
https://54-162-84-165.sslip.io/videos/terminal_dash_1777670483_1777670483410.mp4
```

O Hub nao deve assumir que URLs antigas continuam existindo. Sempre validar artifact publico com `HEAD` antes de mostrar player/download como sucesso.

## Resultado dos Testes Locais

Testado em 2026-05-01:

```text
105 passed
```

Fluxos testados:

```text
main.py --health
main.py --manifest
main.py --capabilities
main.py --recipes
main.py --runtime-manifest
main.py --run-capability system.status
main.py --run-capability agent.profile_summary
main.py --run-capability agent.output_list
main.py --run-capability agent.output_remember
main.py --run-capability agent.output_forget
main.py --run-recipe engine_smoke
Hub command: run_capability system.status
Hub command: run_recipe engine_smoke
VideoLM demo assemble -> status completed -> HEAD MP4 200 video/mp4
```
