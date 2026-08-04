# personas

Selector de "personalidad" al estilo OpenCode para la sesión principal de pi.
Permite definir personas (system prompt + modelo + nivel de thinking +
subconjunto de tools + color de badge) como archivos markdown y cambiar entre
ellas en caliente con el comando `/persona` o el atajo `ctrl+space`.

## Cómo funciona

### Definición de personas

Cada persona es un archivo `.md` con frontmatter simple (no YAML real, un
parser propio con regex) y un cuerpo que se usa como system prompt:

```markdown
---
description: Orquestador para tareas de refactor grandes
tools: read, bash, grep, Agent
model: sonnet
thinking: high
color: accent
---

Eres un orquestador. Tu trabajo es descomponer la tarea en piezas y
delegarlas a subagentes ya configurados en .pi/agents/, normalmente con
run_in_background: true.
```

Todos los campos del frontmatter son opcionales:

| Campo | Efecto |
| --- | --- |
| `description` | Texto mostrado en el picker de `/persona` |
| `tools` | Lista separada por comas de tools built-in a las que restringir la sesión (si se omite, no toca el tool set actual) |
| `model` | `provider/modelId` o nombre difuso (`"sonnet"`, `"haiku"`) |
| `thinking` | `off\|minimal\|low\|medium\|high\|xhigh\|max` |
| `color` | Color del badge en el footer: token del tema (`"success"`, `"warning"`, `"accent"`, `"syntaxKeyword"`, ...) o hex (`"#ff8800"`) |

### Ubicaciones (con override)

- Global: `~/.pi/agent/personas/<nombre>.md` (todos los proyectos)
- Local de proyecto: `.pi/personas/<nombre>.md` (una persona local con el
  mismo nombre que una global la sobreescribe)

`discoverPersonas()` mezcla ambas fuentes en un `Map` por nombre para
resolver el override, y devuelve la lista ordenada alfabéticamente.

### Activación

- `applyPersona()` es el motor: guarda el tool set original la primera vez
  que se restringen tools, aplica `pi.setActiveTools()`, busca el modelo
  pedido en `ctx.modelRegistry.getAvailable()` (match exacto
  `provider/id` o búsqueda difusa por substring), aplica
  `pi.setThinkingLevel()`, actualiza el badge de estado
  (`ctx.ui.setStatus("persona", ...)`) y emite el evento `persona:changed`
  (consumido por la extensión `kyubi-footer` para pintar el nombre/color en
  el footer sin acoplarse directamente).
- `choosePersona()` es el único camino que además persiste el cambio: llama a
  `applyPersona()`, guarda una entrada custom `persona-active` vía
  `pi.appendEntry()` (para recordar la persona activa si se reabre la
  sesión) y notifica al usuario.
- En `before_agent_start`, si hay una persona activa, su `systemPrompt` se
  antepone al system prompt normal de pi (separado por `---`), así la
  persona "pega" en cada turno en vez de ser un prompt de un solo uso.
- En `session_start`, recorre las entradas de la sesión guardada buscando la
  última `persona-active` y, si existe, vuelve a aplicar esa persona
  (sin volver a persistir ni notificar).

### Interfaz de usuario

- **Comando `/persona [nombre]`**:
  - Sin argumento: abre un `ctx.ui.select()` con `none` + todas las personas
    descubiertas (marcando `[proyecto]` cuando aplica).
  - Con argumento `none`: desactiva la persona actual.
  - Con argumento `<nombre>`: activa esa persona directamente (o error si no
    existe).
  - Autocompletado de argumentos vía `getArgumentCompletions`.
- **Atajo `ctrl+space`**: cicla `none -> persona1 -> persona2 -> ... -> none`
  en el orden alfabético devuelto por `discoverPersonas()`. Se eligió
  `ctrl+space` porque no está en la lista de keybindings reservados de pi
  (a diferencia de `shift+tab`, que pi ignora si una extensión intenta
  bindearlo).

## Uso rápido

```bash
mkdir -p ~/.pi/agent/personas
cat > ~/.pi/agent/personas/reviewer.md <<'EOF'
---
description: Revisor de código estricto
tools: read, grep, find, bash
color: warning
---
Eres un revisor de código estricto y conciso. Señala bugs, code smells y
riesgos de seguridad antes que nada.
EOF
```

Luego, dentro de pi: `/persona reviewer` o `ctrl+space` para ciclar.

## Archivos

- `index.ts` — implementación completa (descubrimiento de personas, motor de
  aplicación/persistencia, comando `/persona`, atajo `ctrl+space`).

## Notas

- Se integra opcionalmente con `kyubi-footer` (evento `persona:changed`) y
  con `.pi/agents/<nombre>.md` de subagentes (paquete
  `@tintinweb/pi-subagents`) como destino típico de delegación desde el
  system prompt de una persona "orquestadora".
- El estado activo sobrevive a reinicios de sesión gracias a la entrada
  custom `persona-active` persistida con `pi.appendEntry()`.
