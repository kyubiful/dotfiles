# personas

Selector de "personalidad" al estilo OpenCode para la sesión principal de pi.
Permite definir personas (nombre visible + system prompt + modelo + nivel de
thinking + subconjunto de tools + color de badge) como archivos markdown y cambiar entre
ellas en caliente con el comando `/persona` o el atajo `ctrl+space`.

## Cómo funciona

### Definición de personas

Cada persona es un archivo `.md` con frontmatter simple (no YAML real, un
parser propio con regex) y un cuerpo que se usa como system prompt:

```markdown
---
name: Refactor Architect
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
| `name` | Nombre visible en el footer, estado y notificaciones. Si se omite, usa el nombre del archivo. |
| `description` | Texto mostrado en el picker de `/persona` |
| `tools` | Lista separada por comas de tools built-in a las que restringir la sesión (si se omite, no toca el tool set actual) |
| `model` | `provider/modelId` o nombre difuso (`"sonnet"`, `"haiku"`) |
| `thinking` | `off\|minimal\|low\|medium\|high\|xhigh\|max` |
| `color` | Color del badge en el footer: token del tema (`"success"`, `"warning"`, `"accent"`, `"syntaxKeyword"`, ...) o hex (`"#ff8800"`) |
| `permission` | Lista separada por comas de `tool=action` (p.ej. `bash=ask, edit=deny, write=deny`). `action` es `allow\|ask\|deny`. Ver detalle abajo. |

### Ubicaciones (con override)

- Global: `~/.pi/agent/personas/<id>.md` (todos los proyectos)
- Local de proyecto: `.pi/personas/<id>.md` (una persona local con el mismo
  id de archivo que una global la sobreescribe)

El nombre del archivo sigue siendo el identificador estable usado por
`/persona <id>`, los overrides y la persistencia. El campo `name` es solo el
nombre visible y puede contener espacios o cambiar sin romper sesiones.

`discoverPersonas()` mezcla ambas fuentes en un `Map` por id y devuelve la
lista ordenada alfabéticamente por id.

### Permisos por tool (`permission`)

A diferencia de `tools` (que **excluye por completo** una tool del set — el
modelo ni sabe que existe), `permission` deja la tool visible y llamable pero
la **gatea por invocación**, con dos formas de escritura:

**Forma plana** (solo defaults por tool):

```yaml
permission: bash=ask, edit=deny, write=deny
```

**Forma anidada** (defaults + reglas finas por patrón, estilo Claude Code /
`Bash(pattern)`):

```yaml
permission:
  bash: ask
  edit: deny
  write: deny
  allow:
    - Bash(git status*)
    - Bash(git diff*)
    - Bash(npm run *)
    - Bash(* --version)
    - Bash(* --help*)
  deny:
    - Bash(git push*)
    - Bash(rm *)
```

Acciones (`allow|ask|deny`):

- `allow`: sin cambios, pasa directo.
- `deny`: bloquea la llamada con un mensaje claro (`{ block: true, reason }`),
  pero el modelo puede seguir viendo/intentando la tool y entender por qué
  falló, en vez de no saber que existe.
- `ask`: antes de ejecutar, muestra `ctx.ui.confirm()` con el detalle de la
  llamada (el comando para `bash`, el `path` para `write`/`edit`, JSON crudo
  para el resto). Si el usuario rechaza, se bloquea. Sin UI disponible
  (modo `-p`/RPC), se bloquea por defecto.

Las reglas `Tool(pattern)` (`pattern` admite `*` como wildcard) se evalúan en
orden de aparición en el archivo y **la última que matchea gana**, tanto
entre sí como sobre el default plano del tool — misma convención que usa
OpenCode para sus patrones de `bash` ("the last matching rule takes
precedence"). Resolución del fallback cuando ninguna regla matchea:

1. Si el tool tiene un default explícito (`bash: ask`) — se usa ese.
2. Si no hay default pero el tool **sí** tiene alguna regla `allow`/`deny`
   declarada — el fallback implícito es `ask`. Declarar cualquier regla para
   un tool ya significa que te importa gatearlo, así que no hace falta
   escribir `bash: ask` a mano solo para eso.
3. Si el tool no tiene ni default ni reglas — no se gatea (`allow` implícito,
   igual que si `permission` no existiera para ese tool).

Tampoco hace falta declarar `edit: deny` / `write: deny` si esas tools ya
están excluidas del set con `tools:` — ni siquiera llegan a `tool_call`
porque el modelo no las tiene disponibles.

Esto permite, por ejemplo, combinar un default restrictivo con excepciones
muy concretas. La persona `plan.md` usa `bash: deny`, `write: deny` y
`edit: deny`, y después habilita únicamente consultas Git exactas y la ruta
relativa `.pi/plans/*.md`. Así las herramientas siguen visibles para el
modelo, pero cualquier llamada no incluida en la lista queda bloqueada sin
preguntar.

Se implementa enganchando el evento `tool_call` de pi (puede bloquear la
llamada) contra la persona `active` en el momento del call.

### Activación

- `applyPersona()` es el motor: guarda el tool set original la primera vez
  que se restringen tools, aplica `pi.setActiveTools()`, busca el modelo
  pedido en `ctx.modelRegistry.getAvailable()` (match exacto
  `provider/id` o búsqueda difusa por substring), aplica
  `pi.setThinkingLevel()`, actualiza el badge con el `name` visible
  (`ctx.ui.setStatus("persona", ...)`) y emite el evento `persona:changed`
  con `{ id, name, color }` (consumido por `kyubi-footer` para pintar el
  nombre/color sin acoplarse directamente).
- `choosePersona()` es el único camino que además persiste el cambio: llama a
  `applyPersona()`, guarda una entrada custom `persona-active` con el id
  estable, el nombre visible y el color vía `pi.appendEntry()` (para recordar
  la persona activa si se reabre la sesión) y notifica al usuario.
- En `before_agent_start`, si hay una persona activa, su `systemPrompt` se
  antepone al system prompt normal de pi (separado por `---`), así la
  persona "pega" en cada turno en vez de ser un prompt de un solo uso.
- En `session_start`, lee la última entrada `persona-active`: restaura la
  persona por su id estable, respeta una desactivación posterior y migra una
  entrada antigua al nuevo payload `{ id, name, color }` cuando hace falta.

### Interfaz de usuario

- **Comando `/persona [id]`**:
  - Sin argumento: abre un `ctx.ui.select()` con `none` + todas las personas,
    mostrando su id, nombre visible y descripción (y `[proyecto]` cuando
    aplica).
  - Con argumento `none`: desactiva la persona actual.
  - Con argumento `<id>`: activa esa persona directamente (o error si no
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
name: Code Reviewer
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
  custom `persona-active` persistida con `pi.appendEntry()`. Las entradas
  antiguas que guardaban el id en `name` siguen siendo compatibles.
