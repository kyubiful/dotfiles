# Fix: la vista de un subagente queda "pegada" (Esc no la cierra)

## Objetivo

El usuario tiene pi (`@earendil-works/pi-coding-agent` 0.83.0) con la extensión
de terceros `@tintinweb/pi-subagents` (FleetView). Al abrir la vista de un
subagente (overlay flotante centrado) y presionar Esc, a veces la ventana
queda pegada en pantalla y Esc deja de tener cualquier efecto.

Causa raíz confirmada (lectura de código + validación por un `plan-architect`
en modo solo lectura, sin reproducir en vivo): una interacción entre dos
piezas independientes de código de terceros/plataforma y la extensión propia
del usuario `editor-enhancements`. El fix se acota **exclusivamente** al
archivo de la extensión propia — no se toca ningún `node_modules` de
`pi-coding-agent` ni de `pi-subagents` (son dependencias externas, un parche
ahí se perdería en el próximo update y no es el punto de intervención
correcto).

## Cadena causal (evidencia con archivo:línea)

1. **`interactive-mode.js` (`showExtensionCustom`, dentro de
   `@earendil-works/pi-coding-agent/dist/modes/interactive/interactive-mode.js`,
   líneas ~1921-1946)**: cualquier overlay abierto vía `ctx.ui.custom(..., {overlay:true})`
   se cierra así:
   ```js
   const close = (result) => {
     if (closed) return;      // `closed` es local a esta clausura
     closed = true;
     if (isOverlay) this.ui.hideOverlay();   // no sabe "cuál" overlay cerrar
     ...
   };
   ```
   Una segunda invocación de `done()`/`close()` sobre la MISMA vista es un
   no-op silencioso para siempre (el guard `closed` ya quedó en `true`).

2. **`hideOverlay()` (`@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-tui/dist/tui.js`,
   líneas ~387-400)**: hace `pop()` del **último elemento** del `overlayStack`
   — compartido por TODAS las extensiones — sin ninguna referencia a cuál
   overlay disparó el cierre.

3. **`showOverlay()` (mismo archivo, líneas ~289-341)**: confirmado que un
   overlay creado con `overlayOptions.nonCapturing: true` **nunca recibe
   foco** (`if (!options?.nonCapturing ...) this.setFocus(component)`), pero
   **sí se apila igual** (`this.overlayStack.push(entry)` es incondicional).
   Es decir: un overlay "invisible/de fondo" puede terminar en el tope físico
   del stack sin que nadie lo esté mirando.

4. **`editor-enhancements/index.ts`** (extensión propia del usuario, en
   `/Users/sergio/.config/pi/agent/extensions/editor-enhancements/index.ts`)
   implementa un popup flotante de autocompletado `@archivo`/`/comando`
   mediante exactamente ese patrón: `ctx.ui.custom(..., {overlay:true,
   overlayOptions:{anchor:"bottom-left", nonCapturing:true, ...}})`
   (clase `FloatingListOverlay`, líneas ~203-266). Por diseño **deliberado**
   (documentado en el propio archivo y en el README de la extensión, para
   evitar un salto de layout), ese overlay se mantiene "parqueado" para
   siempre una vez creado — solo se oculta con `handle.setHidden(true/false)`,
   nunca se remueve del stack con `handle.hide()` final.

5. `FloatingListOverlay.update()` (índice ~215) **sí** recrea el overlay
   entero (`handle.hide()` real + `create()` nuevo → nuevo `push` al final
   del `overlayStack` compartido) cada vez que `width` o `aboveRows` cambian
   respecto de la última vez.

6. En `@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-tui/dist/components/editor.js`:
   - `focused = false;` (línea 198) es un campo público plano, **sin ningún
     hook de "blur"** (confirmado por grep: no existe `blur`/`onBlur` en todo
     el archivo) — nada limpia el estado de autocompletado cuando el editor
     pierde el foco.
   - `isShowingAutocomplete()` (líneas ~1941-1942) = `this.autocompleteState
     !== null` — **no depende del foco**.
   - El marcador de cursor que `EnhancedEditor.render()` usa para calcular
     `cursorLineIndex` solo se emite `emitCursorMarker = this.focused` (línea
     ~419) — deja de emitirse en el instante en que el editor pierde el foco.
   - `super.render(width)` (línea ~467) sigue agregando las líneas del
     dropdown de autocompletado al array **siempre**, con foco o sin foco.

7. **Consecuencia**: si el usuario tiene el autocompletado abierto (tipeó
   `@algo` o `/comando`, sin cerrarlo con Tab/Enter/Escape) y algo le saca el
   foco al editor sin que el autocompletado se haya cerrado antes — p. ej. el
   flujo `/agents → Running agents` de `pi-subagents`, o directamente el
   Enter de FleetView que abre la vista de un subagente — entonces en el
   siguiente render de `EnhancedEditor`:
   - `isShowingAutocomplete()` sigue devolviendo `true` (nadie lo limpió).
   - `this.focused` ahora es `false` → no se emite el marcador de cursor →
     `cursorLineIndex` da `-1` → se toma la rama de fallback
     (`aboveRows = lines.length + ASSUMED_FOOTER_HEIGHT_ROWS`), que casi
     siempre difiere del `currentAboveRows` cacheado de la última vez que sí
     hubo foco.
   - Esa diferencia dispara `FloatingListOverlay.update()` → recreación
     completa → un overlay **nuevo** se apila al tope del `overlayStack`
     compartido, por encima de la vista del subagente que en ese momento sí
     tiene el foco real.

8. El usuario presiona Esc sobre la vista del subagente (que procesa Escape
   correctamente): `done(undefined)` → `close()` de `showExtensionCustom` →
   `hideOverlay()` → `pop()` del elemento que quedó arriba de todo: el popup
   de autocompletado recién re-creado, **no** la vista del subagente. Esta
   última queda huérfana en pantalla, con foco, pero el `closed` de esa
   clausura ya es `true` — cualquier Esc posterior sobre esa misma vista
   vuelve a llamar `done()`/`close()`, que ahora es un no-op silencioso.
   Resultado observado: la ventana queda atascada para siempre, Esc deja de
   tener efecto.

Esta cadena fue confirmada de forma independiente por un `plan-architect` en
modo solo lectura, que releyó los cuatro archivos involucrados y no encontró
errores en el razonamiento ni casos borde que la invaliden (ver sección
"Casos borde" abajo).

## Archivo a modificar

**`/Users/sergio/.config/pi/agent/extensions/editor-enhancements/index.ts`**
— único archivo a tocar. Método `EnhancedEditor.render()` (líneas ~391-456).
No se modifica ni `FloatingListOverlay`, ni `CursorRowProbe`, ni el bloque de
resaltado de paths (sección 2 del `render()`), ni el constructor, ni ningún
otro archivo del repo.

## Diseño del fix

Congelar toda mutación del overlay de autocompletado mientras
`EnhancedEditor` **no tiene el foco** (`this.focused === false`): en ese
estado el popup no es visible/relevante para el usuario de todos modos (está
detrás de la vista que sí tiene foco), así que no hay ninguna razón para
recrearlo/reposicionarlo — y hacerlo es exactamente lo que causa el bug.

Reglas concretas dentro de `render()`:
- El recorte de las líneas de autocompletado del array `lines` (para que no
  aparezcan mezcladas dentro del bloque del editor) se sigue haciendo
  **siempre**, con foco o sin foco — el `Editor` base las agrega
  incondicionalmente.
- Solo si `this.focused === true` (además de `isShowingAutocomplete() &&
  listInstance`): correr la lógica actual de `CursorRowProbe` +
  cálculo de `aboveRows` + `this.overlay.update(...)`.
- Si `isShowingAutocomplete()` es `true` pero `this.focused === false`:
  **nunca** llamar a `update()`/`create()` — solo `this.overlay.hide()`
  (que es `handle.setHidden(true)`, no remueve la entrada del stack,
  consistente con el diseño anti-salto-de-layout ya documentado) y resetear
  `wasShowingAutocomplete`/`lastResolvedCursorRow` para que, si el usuario
  vuelve a enfocar el editor con el autocompletado todavía "abierto", se
  dispare una consulta `CursorRowProbe` fresca en vez de reusar una fila de
  cursor potencialmente obsoleta.

Esto absorbe también, sin código adicional, la carrera de
`CursorRowProbe.query()` resolviendo después de haber perdido el foco: el
`.then()` solo asigna `lastResolvedCursorRow` y pide un render; ese render
subsiguiente, al ver `this.focused === false`, entra en la rama "sin foco" y
descarta el valor sin haber llegado a llamar `overlay.update()`.

## Paso de implementación (diff exacto)

Reemplazar, dentro de `EnhancedEditor.render()`, el bloque que va desde el
comentario "Recién se abre el autocompletado" hasta el `else` que llama a
`this.overlay.hide()`:

**Texto actual** (a buscar tal cual, con tabs, para el `edit`):

```ts
			// Recién se abre el autocompletado: pedile a la terminal la fila
			// REAL del cursor (válida tanto en sesiones cortas como largas, a
			// diferencia de cualquier cálculo basado en "el editor+footer están
			// pegados al fondo"). Mientras no haya respuesta, se usa el
			// fallback de abajo para esta apertura puntual.
			if (!this.wasShowingAutocomplete) {
				this.wasShowingAutocomplete = true;
				this.lastResolvedCursorRow = undefined;
				void this.probe.query(this.tui.terminal).then((row) => {
					this.lastResolvedCursorRow = row;
					this.tui.requestRender();
				});
			}

			let aboveRows: number;
			if (this.lastResolvedCursorRow !== undefined && cursorLineIndex !== -1) {
				// Fila real (viewport-relativa) del borde superior del bloque =
				// fila real del cursor menos las filas del bloque que están por
				// encima suyo (border superior + líneas envueltas previas).
				const topBorderRow = this.lastResolvedCursorRow - cursorLineIndex;
				aboveRows = this.tui.terminal.rows - topBorderRow;
			} else {
				// Fallback aproximado mientras no tenemos la fila real (primeros
				// milisegundos tras abrir el autocompletado): asume que el
				// bloque+footer están pegados al fondo de la terminal.
				aboveRows = lines.length + ASSUMED_FOOTER_HEIGHT_ROWS;
			}

			this.overlay.update(listLines, width, aboveRows);
		} else {
			this.wasShowingAutocomplete = false;
			this.lastResolvedCursorRow = undefined;
			this.overlay.hide();
		}
```

**Texto nuevo:**

```ts
			if (!this.focused) {
				// El editor perdió el foco (p.ej. se abrió la vista de un
				// subagente, un ctx.ui.select, o cualquier otro overlay con
				// foco propio) mientras el autocompletado seguía "abierto":
				// `isShowingAutocomplete()` no depende del foco en el Editor
				// base, así que nadie lo cerró. En ese estado el popup no es
				// visible/relevante para el usuario — está detrás de quien
				// tenga el foco ahora. Congelamos toda mutación del overlay:
				// llamar a `update()`/`create()` acá haría un `push` nuevo al
				// TOPE del overlayStack compartido, por encima de la vista que
				// sí tiene foco, y el próximo Escape sobre esa vista cerraría
				// (`hideOverlay()` hace `pop()` del último elemento) este popup
				// recién apilado en vez de la vista real — dejándola huérfana
				// en pantalla, con foco, pero con el `closed` interno de
				// `showExtensionCustom` ya consumido (Escape deja de tener
				// efecto para siempre en esa vista).
				//
				// Solo ocultamos (sin sacar la entrada del stack, para no
				// reintroducir el salto de layout que este diseño ya evita) y
				// reseteamos el estado de "recién abierto": si el usuario
				// vuelve a enfocar el editor con el autocompletado todavía
				// abierto, se dispara un CursorRowProbe.query() fresco en vez
				// de reusar una fila de cursor potencialmente obsoleta.
				this.wasShowingAutocomplete = false;
				this.lastResolvedCursorRow = undefined;
				this.overlay.hide();
			} else {
				// Recién se abre el autocompletado: pedile a la terminal la fila
				// REAL del cursor (válida tanto en sesiones cortas como largas, a
				// diferencia de cualquier cálculo basado en "el editor+footer están
				// pegados al fondo"). Mientras no haya respuesta, se usa el
				// fallback de abajo para esta apertura puntual.
				if (!this.wasShowingAutocomplete) {
					this.wasShowingAutocomplete = true;
					this.lastResolvedCursorRow = undefined;
					void this.probe.query(this.tui.terminal).then((row) => {
						this.lastResolvedCursorRow = row;
						this.tui.requestRender();
					});
				}

				let aboveRows: number;
				if (this.lastResolvedCursorRow !== undefined && cursorLineIndex !== -1) {
					// Fila real (viewport-relativa) del borde superior del bloque =
					// fila real del cursor menos las filas del bloque que están por
					// encima suyo (border superior + líneas envueltas previas).
					const topBorderRow = this.lastResolvedCursorRow - cursorLineIndex;
					aboveRows = this.tui.terminal.rows - topBorderRow;
				} else {
					// Fallback aproximado mientras no tenemos la fila real (primeros
					// milisegundos tras abrir el autocompletado): asume que el
					// bloque+footer están pegados al fondo de la terminal.
					aboveRows = lines.length + ASSUMED_FOOTER_HEIGHT_ROWS;
				}

				this.overlay.update(listLines, width, aboveRows);
			}
		} else {
			this.wasShowingAutocomplete = false;
			this.lastResolvedCursorRow = undefined;
			this.overlay.hide();
		}
```

Nada más cambia: el bloque anterior a este (búsqueda de `cursorLineIndex` vía
`CURSOR_MARKER`, cálculo de `contentWidth`, `listLines =
listInstance.render(contentWidth)`, recorte `lines.length -=
listLines.length`) sigue ejecutándose siempre, con foco o sin foco — eso es
correcto y no debe tocarse, porque el `Editor` base agrega esas líneas al
array incondicionalmente.

También conviene actualizar el comentario de cabecera del archivo (la sección
larga que empieza en la línea ~1, donde se documenta el diseño del popup) con
un párrafo breve mencionando esta salvaguarda de foco, para que quede
registrado el motivo igual que el resto de las decisiones de diseño ya
documentadas ahí. No es obligatorio pero es consistente con el estilo del
archivo (cada decisión no obvia está explicada in situ).

## Casos borde ya evaluados (por el `plan-architect`, sin objeciones)

- **Primer render antes de que `focused` tenga valor**: arranca en `false`
  (declaración de clase). No es problema: en ese primer render
  `isShowingAutocomplete()` es necesariamente `false` (no hay overlay
  abierto todavía), la rama nueva nunca se alcanza sin autocompletado activo.
- **`this.handle` de `FloatingListOverlay` aún `undefined` al perder el
  foco**: solo pasaría si `isShowingAutocomplete()` ya fuera `true` sin que
  el popup se haya creado antes — imposible en la práctica (el
  autocompletado solo se abre por tipeo, que requiere foco). Aun si pasara,
  `hide()` (`this.handle?.setHidden(true)`) ya es no-op seguro con `handle`
  undefined.
- **Race de `CursorRowProbe.query()` resolviendo después de perder el
  foco**: absorbida sin código adicional (ver diseño arriba).

## Riesgos / efectos secundarios aceptados

1. Si el usuario nunca vuelve a enfocar el editor con el autocompletado
   todavía "abierto" (p. ej. cierra la sesión), el popup queda oculto para
   siempre — aceptable, es el mismo estado estable que ya existe hoy cuando
   el autocompletado se cierra normalmente.
2. Al recuperar el foco con el autocompletado todavía "abierto" (nada en
   `editor.js` lo cierra al perder/recuperar foco), el fix lo trata como
   recién abierto y vuelve a apilar una entrada nueva en el overlay stack.
   Esto es correcto siempre que en ese momento el stack ya no tenga overlays
   de foco por encima — supuesto razonable (el editor solo recupera el foco
   legítimamente vía `restoreEditor()`/`setFocus` de pi-coding-agent cuando
   la vista que lo tenía se cerró), pero no verificado en vivo por lectura
   estática. Se valida en el paso de verificación manual (b) de abajo.
3. **No corrige la causa de fondo** (que `pi-subagents` y `pi-coding-agent`
   comparten un `overlayStack` global sin un mecanismo de "cerrar mi propio
   overlay, no el del tope"): si en el futuro otra extensión de terceros usa
   el mismo patrón (overlay `nonCapturing` que se recrea en segundo plano),
   el problema podría reaparecer por otra vía. Fuera de alcance (no se puede
   tocar `node_modules` de forma sostenible) — vale dejarlo anotado como
   limitación conocida en el comentario del archivo.
4. Cambio de bajo riesgo de regresión: no toca el cálculo de
   `aboveRows`/`CursorRowProbe` en sí, solo agrega una condición de guarda
   alrededor de código ya existente y probado.

## Alternativa considerada y descartada

Además de congelar el overlay, se evaluó cerrar explícitamente el
autocompletado del `Editor` base al perder el foco (vía un método interno
tipo `cancelAutocomplete()`, marcado `private` en el `.d.ts`, accesible solo
con el mismo tipo de cast `as unknown as {...}` que ya usa el código para
`autocompleteList`). Se descarta: cerrar el autocompletado del usuario "por
sorpresa" en cuanto pierde el foco (p. ej. al abrir brevemente otra vista) es
una sorpresa de UX no deseada si vuelve enseguida a seguir escribiendo. El
fix elegido no necesita tocar ningún campo privado adicional.

## Verificación de punta a punta

No hay tests automatizados para esta extensión (solo `index.ts` +
`README.md`); la validación original del popup se hizo con una PTY real
(Python + `pyte` simulando la terminal, incluida la respuesta al DSR). Se
recomienda el mismo enfoque para validar el fix:

**(a) No regresión del posicionamiento normal (con foco, sin interferencia):**
1. Sesión corta (terminal ~15 filas) y sesión larga (~30+ filas, chat ya
   lleno). Tipear `@` o `/` para abrir el popup en ambos casos y confirmar
   que sigue apareciendo arriba del bloque del editor, sin superposición,
   igual que antes del fix (la rama `this.focused === true` no cambia).
2. Redimensionar la terminal con el popup abierto (con foco) y confirmar que
   se recalcula correctamente (comportamiento sin cambios).

**(b) Reproducción del bug original y confirmación del fix:**
1. En la PTY: escribir `@algo` (o `/comando`) para abrir el popup y dejarlo
   abierto — **sin** confirmarlo (Tab/Enter) ni cerrarlo (Escape).
2. Sin cerrar el popup, disparar un flujo que le saque el foco al editor:
   `/agents → Running agents` → Enter sobre un subagente en ejecución (o,
   si hay uno corriendo, activar FleetView con la flecha ↓/← en un prompt
   vacío — en este caso hay que soltar el `@algo` tipeado primero solo para
   activar FleetView, y luego volver a abrir el autocompletado antes del
   paso siguiente para simular el estado real; alternativamente, cualquier
   `ctx.ui.select` de una extensión de prueba sirve igual para el repro).
3. Mientras esa vista tiene el foco, forzar el recálculo de `aboveRows`/`width`
   del popup (p. ej. redimensionando la PTY) para ejercitar la rama que antes
   causaba el `push` extra al `overlayStack`.
4. Presionar Escape sobre la vista/diálogo que tiene el foco: confirmar que
   se cierra correctamente y el editor recupera el foco y el control del
   teclado (antes del fix, este paso es el que fallaba — la vista quedaba
   pegada).
5. Como prueba adicional del riesgo #2: después de cerrar esa vista con el
   autocompletado aún "lógicamente abierto", reenfocar el editor y confirmar
   que el popup reaparece bien posicionado (nueva consulta `CursorRowProbe`
   fresca, sin usar la fila de cursor obsoleta).

**Comando de referencia para correr la extensión modificada:** no hay build
step para las extensiones personales de `~/.config/pi/agent/extensions`
(pi las carga directo con `jiti`); basta reiniciar la sesión de pi
(`/new` o reabrir la terminal) para que recoja el cambio en `index.ts`.
