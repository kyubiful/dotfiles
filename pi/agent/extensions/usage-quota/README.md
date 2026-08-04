# usage-quota

Comando `/usage` que muestra la cuota restante de las suscripciones de Codex
(OpenAI) y GitHub Copilot, con barra de progreso y tiempo hasta el reset.

## Cómo funciona

### Codex

1. **Intento en vivo**: lanza `codex app-server` como subproceso y le habla
   JSON-RPC por stdin/stdout: `initialize` → `initialized` →
   `account/rateLimits/read`. Si responde dentro de 6s
   (`fetchCodexLive`), usa esos datos (`source: "live"`).
2. **Fallback a logs locales**: si el proceso no está disponible, falla o
   tarda demasiado, busca el rollout de sesión más reciente en
   `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` (o `$CODEX_HOME/sessions`),
   lee solo la cola del archivo (últimos ~2MB) y busca hacia atrás la última
   línea con un payload `rate_limits` (`source: "session-log"`).
3. De ambas fuentes se extraen dos ventanas: `primary` (~5h) y `secondary`,
   y `pickWeekly()` se queda con la de mayor `windowMinutes` (normalmente la
   semanal) para mostrarla como cifra principal.

### Copilot

1. Obtiene un token en este orden: `gh auth token` (GitHub CLI) → si falla,
   lee el token guardado por la Copilot CLI en `~/.copilot/config.json`
   (con un mini parser que soporta comentarios `//` y `/* */` en el JSON).
2. Llama al endpoint interno/no documentado
   `GET https://api.github.com/copilot_internal/user` (el mismo que usan los
   clientes oficiales) con headers `Copilot-Integration-Id` y
   `X-GitHub-Api-Version`. **Puede romperse sin aviso** si GitHub cambia ese
   endpoint.
3. Del payload extrae `quota_snapshots.premium_interactions`: si es
   `unlimited`, lo marca como tal; si trae `percent_remaining` o
   `remaining`/`entitlement`, calcula el porcentaje usado.

### Render

- Registra un renderer de entrada custom (`pi.registerEntryRenderer`) para el
  tipo `"usage-report"`, que dibuja una `Box` con:
  - Codex: `X% used` coloreado (verde <70%, amarillo <90%, rojo ≥90% vía
    `colorForUsage`) + barra `█░` (`bar()`) + tiempo hasta el reset
    (`fmtDuration`); indica si el dato viene de logs locales y no en vivo.
  - Copilot: mismo formato para "premium requests", o `unlimited`.
  - En modo expandido, muestra el timestamp de la última consulta.
- El comando `/usage` pone un status temporal ("Fetching Codex/Copilot
  usage...") mientras hace ambas consultas en paralelo
  (`Promise.all`) y luego persiste el resultado con
  `pi.appendEntry("usage-report", ...)`, que dispara el renderer.

## Requisitos

- Acceso a red.
- Codex: CLI `codex` instalada y logueada con ChatGPT (para el modo "live");
  si no, basta con haber usado Codex localmente para tener logs de sesión.
- Copilot: `gh` CLI autenticada, o la Copilot CLI logueada
  (`~/.copilot/config.json`).
- Si ninguna de las dos integraciones está disponible, el comando igual
  corre y muestra mensajes de "no data" explicando qué falta configurar.

## Uso

```text
/usage
```

## Archivos

- `index.ts` — todo en un archivo: helpers compartidos, integración Codex,
  integración Copilot, renderer y comando.

## Notas

- La integración de Copilot depende de un endpoint interno no documentado de
  GitHub; puede dejar de funcionar en cualquier momento.
- No persiste histórico: cada `/usage` hace una consulta nueva y crea una
  entrada de sesión independiente.
