# kyubi-header

Extensión que reemplaza la cabecera de bienvenida de la TUI de pi (por
defecto: mascota de pi + hints de atajos) por un logo ASCII propio
(wordmark "kyubi" en fuente de bloques + "kitsune" a su derecha) seguido
de una línea con el nombre de la carpeta del proyecto y la versión de pi.

## Cómo funciona

- En `session_start`, si `ctx.mode === "tui"`, llama a
  `ctx.ui.setHeader((tui, theme) => ({...}))` con un componente que:
  - Devuelve las 4 líneas de `KITSUNE_ART` en `index.ts`, cada una
    precedida por la línea correspondiente de `KYUBI_WORDMARK` (el
    wordmark "kyubi" en fuente de bloques, alineado a `WORDMARK_WIDTH`
    con `padEnd`), coloreadas enteras con el token de tema `"accent"`
    (`getKitsuneLogo`).
  - Agrega una línea de subtítulo con `basename(ctx.cwd)` (carpeta del
    proyecto actual, en `"muted"`) y la versión de pi (`VERSION` de
    `@earendil-works/pi-coding-agent`, en `"dim"`).
  - Centra el bloque del logo y, por separado, el subtítulo con
    `centerBlock`: calcula el ancho visible máximo del bloque (vía
    `visibleWidth` de `@earendil-works/pi-tui`, que ignora los códigos
    ANSI de color) y aplica el mismo padding izquierdo a todas sus
    líneas, para no distorsionar la forma del arte fila por fila.
  - Aplica `truncateToWidth(line, width)` de `@earendil-works/pi-tui` a
    cada línea para no romper el layout en terminales angostas.
- A diferencia de `kyubi-footer`, el header no recibe un tercer parámetro
  reactivo: la carpeta del proyecto y la versión de pi no cambian dentro
  de una misma sesión, así que `invalidate()` queda vacío y no hace falta
  `dispose()` ni suscribirse a ningún evento.
- Registra el comando `/builtin-header`, que llama a
  `ctx.ui.setHeader(undefined)` para restaurar la cabecera por defecto de
  pi (mascota + hints de atajos) en caliente, sin reiniciar la sesión.

## Requisitos

- Ninguno especial: el arte usa solo caracteres ASCII comunes, no Nerd
  Font.
- Un tema de pi que defina los tokens estándar `"accent"`, `"muted"` y
  `"dim"`.

## Archivos

- `index.ts` — implementación completa (`KITSUNE_ART`, `KYUBI_WORDMARK`,
  `getKitsuneLogo`, `centerBlock`, `setHeader` + comando
  `/builtin-header`).

## Notas

- No depende de `kyubi-footer` ni de `personas`, ni interfiere con ellas:
  cabecera y pie de página son componentes independientes en la API de pi.
- Para volver a la cabecera de pi por defecto sin editar código, usa
  `/builtin-header`.
