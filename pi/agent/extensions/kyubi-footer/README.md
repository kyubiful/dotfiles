# kyubi-footer

Extensión que reemplaza el footer por defecto de la TUI de pi por un footer
personalizado de 3 líneas con: carpeta del proyecto + persona activa (si la
extensión `personas` está instalada), métricas de tokens/costo/uso de
contexto, y rama git + modelo activo.

## Cómo funciona

- En `session_start`:
  - Lee las entradas de la sesión buscando una entrada custom
    `persona-active` (escrita por la extensión `personas`) para recuperar el
    nombre/color de la persona activa al reabrir una sesión guardada.
  - Llama a `ctx.ui.setFooter(...)` con una función de render que pi invoca
    cada vez que hay que repintar el footer.
- El footer se suscribe a dos fuentes de cambio para pedir un re-render
  (`tui.requestRender()`):
  - `footerData.onBranchChange` — cambios de rama git.
  - El evento custom `persona:changed`, emitido por la extensión `personas`
    cuando el usuario cambia de persona (así el footer no depende de
    recargar la sesión).
- El render calcula, en cada llamada:
  - **Línea 1**: nombre de la carpeta actual (`basename(ctx.cwd)`) alineado a
    la izquierda y, si hay una persona activa, su nombre coloreado alineado a
    la derecha (con `colorizePersona`, que acepta colores hex `#rrggbb` o
    tokens del tema como `"success"`/`"accent"`).
  - **Línea 2**: tokens de entrada/salida acumulados en la rama de mensajes
    del assistant (`ctx.sessionManager.getBranch()`), costo total en USD, y
    uso de contexto actual vs. ventana del modelo (`ctx.getContextUsage()` /
    `ctx.model.contextWindow`) con porcentaje, alineados a la izquierda; y si
    el modelo activo soporta razonamiento (`ctx.model.reasoning`), el nivel
    de thinking actual (`pi.getThinkingLevel()`) alineado a la derecha del
    todo, coloreado según el nivel (`THINKING_COLORS` en `index.ts`, uno de
    off/minimal/low/medium/high/xhigh/max).
  - **Línea 3**: rama git actual (`footerData.getGitBranch()`) alineada a la
    izquierda y el id del modelo activo (`ctx.model.id`) alineado a la
    derecha, con padding calculado según el ancho disponible (`width`).
- Usa `truncateToWidth` y `visibleWidth` de `@earendil-works/pi-tui` para que
  el texto (incluyendo iconos Nerd Font y colores ANSI) no rompa el layout
  cuando la terminal es angosta.

## Colores de thinking y borde del editor

pi por defecto colorea el borde superior e inferior del editor de entrada
según el nivel de thinking activo (`theme.getThinkingBorderColor`, usando
los tokens de tema `thinkingOff`/`thinkingMinimal`/.../`thinkingMax`). Como
este footer ya muestra el nivel de thinking coloreado en la línea 2, en
`~/.pi/agent/themes/solarized-osaka.json` esos tokens se han igualado todos
a `"base01"` (el mismo valor que `border`), de forma que el borde del editor
ya no cambia de color con el thinking — solo lo hace el indicador del
footer. Si usas otro tema, aplica el mismo ajuste (todos los `thinking*` al
valor de `border`) para obtener el mismo efecto.

## Requisitos

- Una terminal con fuente [Nerd Font](https://www.nerdfonts.com/) instalada,
  ya que usa glifos como  (tokens), (costo), 󰍛 (contexto), 󰚩 (modelo) y
  󰧑 (thinking, `md-brain`, U+F09D1).
- Integración opcional (no obligatoria) con la extensión `personas`: si no
  está presente, simplemente no se muestra ninguna persona en la línea 1 y el
  footer funciona igual con las otras dos líneas.

## Archivos

- `index.ts` — implementación completa (helpers de color + `setFooter`).

## Notas

- No registra comandos, tools ni shortcuts: solo cambia la presentación del
  footer.
- El estado de la persona activa se guarda vía el bus de eventos interno de
  pi (`pi.events`), no vía props/contexto compartido, por lo que esta
  extensión puede vivir en su propio archivo sin importar directamente
  `personas/index.ts`.
