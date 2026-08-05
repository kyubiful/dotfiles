# editor-enhancements

Dos mejoras al input, combinadas en un único `CustomEditor`:

1. **Popup flotante de autocompletado** para `@archivo` y `/comando`: en vez
   de dibujarse dentro del propio bloque del editor (empujando el resto del
   layout hacia abajo, como hace el `Editor` base), se muestra flotando
   justo arriba de todo el bloque de input, con su ancho completo. No sigue
   al cursor: queda fijo arriba del bloque para que el chat de arriba nunca
   salte de lugar.
2. **Resaltado de paths agregados**: cuando terminás de agregar un archivo
   con `@` (lo seleccionás del autocompletado, no es un directorio abierto
   para seguir escribiendo), el path insertado queda pintado con el color
   `accent` del tema mientras siga intacto en el editor.

## Por qué está todo en un solo archivo

`ctx.ui.setEditorComponent` solo admite un "dueño" de editor a la vez: la
última extensión que lo llama en `session_start` gana y las demás quedan
pisadas en silencio, sin error. Además, el loader de extensiones de pi
(`dist/core/extensions/loader.js`) usa `jiti` con `moduleCache: false` y
crea un contexto nuevo por cada extensión cargada — un import relativo entre
dos carpetas de extensiones separadas **no** comparte instancias de módulo
(cada una re-ejecuta el archivo importado por su cuenta), así que un
"singleton" compartido entre dos extensiones distintas no sería tal. Por
eso todo el estado compartido (tracker de paths agregados + popup flotante)
vive en un solo módulo con un único punto de entrada.

## Cómo funciona el popup flotante

Sin reimplementar la lógica de selección: `super.render(width)` ya agrega,
al final del array, las líneas del `SelectList` interno de autocompletado.
Ese `SelectList` vive en una propiedad de instancia accesible en runtime
(`autocompleteList`, `private` solo a nivel de tipos de TypeScript — la
clase base no tiene campos `#` reales). Se le vuelve a pedir el render
(función pura del estado de selección/scroll actual, sin efectos
secundarios) para saber cuántas líneas agregó el editor base, y se recortan
del array devuelto. Esas líneas se muestran en un overlay
(`ctx.ui.custom(..., { overlay: true })`) anclado con `anchor: "bottom-left"`
+ `offsetY` negativo y ancho completo.

### El truco para que la posición sea exacta en cualquier sesión (`CursorRowProbe`)

El motor de overlays de pi solo soporta anclar relativo al viewport visible,
asumiendo que editor+footer están pegados al fondo real de la terminal.
Eso es cierto en sesiones largas (el chat ya llena la pantalla), pero
**falso en sesiones recién empezadas**: ahí el motor rellena con líneas
vacías el *final* del contenido real para completar el alto de pantalla (no
reparte ese relleno en el medio), así que editor+footer terminan más arriba
de lo que ese anclaje asume — el popup podía aparecer superpuesto al input
en vez de arriba suyo.

No hay ninguna API de extensiones que exponga la posición real del cursor o
la altura real del contenido para corregir esto matemáticamente. La
solución: preguntarle directamente a la terminal. Se manda una consulta
DSR/CPR estándar (`ESC[6n`, "Cursor Position Report") con
`tui.terminal.write(...)`, y la respuesta (`ESC[fila;colR`) se intercepta
con `ctx.ui.onTerminalInput(...)`. Esa fila es la posición **real** en
pantalla del cursor, válida sin importar si la sesión es corta o larga. Con
esa fila (y sabiendo cuántas filas del bloque del editor quedan por encima
del cursor, típicamente 1: el borde superior) se calcula la fila real del
borde superior del bloque, y de ahí el `offsetY` exacto.

La consulta es asíncrona (hay que esperar la respuesta de la terminal), así
que solo se dispara una vez por cada apertura del autocompletado (no en
cada tecla). Mientras no haya respuesta se usa un fallback aproximado
(asumiendo bloque+footer pegados al fondo) para esa apertura puntual — en la
práctica la respuesta suele llegar antes de que terminen de cargar las
sugerencias, así que el fallback casi nunca llega a mostrarse.

Validado con una pty real (Python + `pyte` simulando la terminal, incluida
la respuesta al DSR) en terminales de 15 y 30 filas: sin superposición con
el input en ningún caso, y sin saltos del contenido de arriba al
abrir/cerrar/reabrir el autocompletado.

### Por qué el overlay separa "contenido" de "posición/ancho"

`overlayOptions` (posición/ancho) queda congelado al crear el overlay — se
comprobó leyendo `showExtensionCustom` en
`dist/modes/interactive/interactive-mode.js`: `resolveOptions()` se llama
una sola vez, nunca de nuevo. Por eso `FloatingListOverlay`:

- **Actualiza el contenido** (qué líneas mostrar) en cada render vía un
  objeto mutable que el `render()` del overlay lee en vivo, sin recrear
  nada — esto es lo que cambia en cada tecla mientras se filtran
  sugerencias.
- **Solo recrea** el overlay si la posición/ancho cambiaron de verdad (p.
  ej. el input pasó a ocupar más líneas, o llegó la respuesta de
  `CursorRowProbe` y corrige el fallback inicial).
- **Muestra/oculta** con `handle.setHidden(...)`, nunca con `handle.hide()`
  final: `hide()` saca la entrada del `overlayStack`, y mientras el stack
  está vacío el motor de overlays no aplica el relleno de líneas vacías que
  necesita para posicionar overlays. Abrir y cerrar el overlay por completo
  en cada aparición/desaparición del autocompletado haría que ese relleno
  apareciera y desapareciera cada vez, haciendo saltar el contenido de
  arriba. Dejando la entrada siempre viva (oculta cuando no hace falta) ese
  relleno se estabiliza una sola vez.

El overlay es `nonCapturing`: no roba el foco, así que flechas / Tab / Enter
/ Escape los sigue procesando el `Editor` base de siempre.

## Cómo funciona el resaltado de paths

`ctx.ui.addAutocompleteProvider` envuelve el proveedor de autocompletado
activo para detectar en `applyCompletion` cuándo la selección es un archivo
(`prefix` empieza con `@`) y no un directorio (`item.label` no termina en
`/`). Cuando pasa, guarda el texto exacto insertado (p. ej. `@src/index.ts`).
En cada `render()`, sobre las líneas ya sin la lista flotante, busca esos
textos y los reemplaza por su versión coloreada con `theme.fg("accent", ...)`.

## Limitaciones conocidas (aceptadas conscientemente)

- **`ASSUMED_FOOTER_HEIGHT_ROWS`** solo se usa como fallback aproximado
  mientras `CursorRowProbe` todavía no respondió (asume 3 líneas de footer,
  la altura actual de `kyubi-footer`). Si en ese brevísimo instante se
  llega a mostrar el fallback y tu footer tiene otra altura, quedaría
  levemente desalineado hasta que la respuesta real llegue y lo corrija
  (típicamente milisegundos).
- **Resaltado de paths**: post-procesado sobre las líneas ya renderizadas,
  no integrado al layout/word-wrap del editor. Si el path se parte en dos
  líneas por word-wrap, o el cursor queda exactamente encima, el resaltado
  puede no aplicarse en ese render puntual (se recupera solo en el
  próximo).

## Ubicación

`~/.pi/agent/extensions/editor-enhancements/index.ts` → físicamente vive en
`~/.config/pi/agent/extensions/editor-enhancements/` (symlink existente).
