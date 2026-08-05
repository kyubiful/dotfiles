/**
 * Editor Enhancements: popup flotante de autocompletado + resaltado de
 * paths agregados con `@`.
 *
 * Todo vive en un único `CustomEditor` (y por lo tanto en un único archivo,
 * a propósito): `ctx.ui.setEditorComponent` solo admite un "dueño" de editor
 * a la vez (la última extensión que lo llama en `session_start` gana y las
 * demás quedan pisadas en silencio). Además, el loader de extensiones de pi
 * usa jiti con `moduleCache: false` y crea un contexto nuevo por cada
 * extensión cargada (`dist/core/extensions/loader.js`), por lo que un
 * import relativo entre dos carpetas de extensiones NO comparte instancias
 * de módulo (cada una re-ejecuta el archivo importado por su cuenta). Un
 * singleton compartido entre dos extensiones "separadas" simplemente no
 * sería singleton: por eso todo el estado compartido vive acá, en un solo
 * módulo, con un único punto de entrada.
 *
 * ---
 *
 * ## 1) Popup flotante para `@archivo` / `/comando`
 *
 * Por defecto, el menú de sugerencias de autocompletado se dibuja DENTRO
 * del propio bloque del editor (después del borde inferior), lo que empuja
 * el resto del layout hacia abajo a medida que crece. Acá se saca de ese
 * flujo y se muestra en un overlay flotante justo arriba del input, con el
 * ancho completo del editor (no sigue al cursor: queda fijo arriba de todo
 * el bloque de texto para que el contenido de arriba no salte de lugar).
 *
 * Cómo funciona (sin reimplementar nada de la lógica de selección):
 * `super.render(width)` ya agrega, al final del array, las líneas del
 * `SelectList` interno de autocompletado. Como ese `SelectList` vive en una
 * propiedad de instancia accesible en runtime (`autocompleteList`, aunque
 * TypeScript la marque `private`; no hay campos `#` reales en la clase
 * base), se le vuelve a pedir el render (función pura del estado de
 * selección/scroll actual, sin efectos secundarios) para saber cuántas
 * líneas agregó el editor base, y se recortan del array devuelto. Esas
 * líneas se muestran en un overlay (`ctx.ui.custom(..., { overlay: true })`)
 * anclado con `anchor: "bottom-left"` + `offsetY` negativo.
 *
 * La parte interesante es cómo se calcula ese `offsetY` para que funcione
 * TANTO en sesiones largas (chat que ya llena la pantalla) COMO en
 * sesiones recién empezadas. El motor de overlays de pi solo soporta
 * anclar relativo al viewport (`anchor: "bottom-left"`), asumiendo que
 * editor+footer están pegados al fondo real de la terminal —cierto en
 * sesiones largas, pero FALSO en sesiones cortas: ahí el motor rellena con
 * líneas vacías el FINAL del contenido real para completar el alto de
 * pantalla (no reparte el relleno en el medio), así que editor+footer
 * quedan más arriba de lo que ese anclaje asume. No hay ninguna API de
 * extensiones que exponga la posición real del cursor o la altura real del
 * contenido para corregir esto matemáticamente.
 *
 * La solución (`CursorRowProbe`): preguntarle directamente a la terminal.
 * Se manda una consulta DSR/CPR estándar (`ESC[6n`, "Cursor Position
 * Report") con `tui.terminal.write(...)`, y la respuesta (`ESC[fila;colR`)
 * se intercepta con `ctx.ui.onTerminalInput(...)`. Esa fila es la posición
 * REAL en pantalla del cursor, válida sin importar si la sesión es corta o
 * larga. Con esa fila (y sabiendo cuántas filas del bloque del editor
 * quedan por ENCIMA del cursor, típicamente 1: el borde superior) se
 * calcula la fila real del borde superior del bloque, y de ahí el
 * `offsetY` exacto. La consulta es asíncrona (hay que esperar la
 * respuesta), así que solo se dispara una vez por cada apertura del
 * autocompletado (no en cada tecla), y mientras no haya respuesta se usa
 * un fallback aproximado (asumiendo bloque+footer pegados al fondo) para
 * esa apertura puntual —en la práctica la respuesta suele llegar antes de
 * que terminen de cargar las sugerencias, así que el fallback casi nunca
 * llega a mostrarse.
 *
 * Sobre el resto de `overlayOptions` (ancho): también queda congelado al
 * crear el overlay —se comprobó leyendo `showExtensionCustom` en
 * `dist/modes/interactive/interactive-mode.js`: `resolveOptions()` se llama
 * una sola vez, nunca de nuevo. Por eso `FloatingListOverlay` separa dos
 * cosas:
 * - **Contenido** (qué líneas mostrar): se actualiza en cada render vía un
 *   objeto mutable que el `render()` del overlay lee en vivo, sin recrear
 *   nada. Esto es lo que cambia en cada tecla mientras se filtran
 *   sugerencias.
 * - **Posición/ancho** (offsetY, width): solo si cambian de verdad (p. ej.
 *   el input pasa a ocupar más líneas, o llegó la respuesta de
 *   `CursorRowProbe` y corrige el fallback inicial) se cierra el overlay
 *   viejo (`handle.hide()`) y se crea uno nuevo.
 * - **Mostrar/ocultar** usa `handle.setHidden(...)`, nunca `handle.hide()`
 *   final: `hide()` saca la entrada del `overlayStack`, y mientras el stack
 *   está vacío el motor de overlays no aplica el relleno de líneas vacías
 *   que necesita para posicionar overlays (`compositeOverlays` corta antes
 *   si `overlayStack.length === 0`). Si abriéramos y cerráramos el overlay
 *   por completo en cada aparición/desaparición del autocompletado, ese
 *   relleno aparecería y desaparecería cada vez, haciendo saltar el
 *   contenido de arriba. Dejando la entrada siempre viva (oculta cuando no
 *   hace falta) ese relleno se estabiliza una sola vez.
 *
 * El overlay es `nonCapturing`: no roba el foco, todo el manejo de teclado
 * (flechas, Tab, Enter, Escape) lo sigue haciendo el `Editor` base de
 * siempre.
 *
 * Validado con una pty real (Python + `pyte` simulando la terminal,
 * incluyendo respuestas DSR) en terminales de 15 y 30 filas: sin
 * superposición con el input en ningún caso, y sin saltos del contenido de
 * arriba al abrir/cerrar/reabrir el autocompletado.
 *
 * Limitación conocida y aceptada:
 * - `ASSUMED_FOOTER_HEIGHT_ROWS` solo se usa como fallback aproximado
 *   mientras `CursorRowProbe` todavía no respondió (asume 3 líneas de
 *   footer, la altura actual de `kyubi-footer`). Si en ese breve instante
 *   se llega a mostrar el fallback y tu footer tiene otra altura, quedaría
 *   levemente desalineado hasta que la respuesta real llegue y lo corrija.
 *
 * ## 2) Resaltado de paths agregados con `@`
 *
 * Cuando agregás un archivo O CARPETA con el autocompletado `@` y lo
 * seleccionás (Tab/Enter), el path insertado queda pintado con el color
 * "accent" del tema mientras siga presente en el editor. En el caso de
 * carpetas (que no llevan espacio final porque el autocompletado sigue
 * abierto para poder seguir navegando adentro), el resaltado cubre el
 * token de la carpeta mientras el usuario siga escribiendo a mano a
 * continuación (p.ej. "@src/" queda resaltado aunque a mano se agregue
 * "index.ts" después, porque "@src/" sigue siendo substring exacto del
 * texto). Si en cambio se TERMINA completando un archivo puntual adentro
 * de esa carpeta usando de nuevo el autocompletado (p.ej. seleccionando
 * "@src/index.ts"), el token viejo de la carpeta se descarta a favor del
 * nuevo (ver `HighlightTracker.add`): mantener ambos trackeados a la vez
 * pintaría el path completo Y, anidado adentro, el prefijo de carpeta otra
 * vez, cortando por un `reset` de más el color del resto del path. Si
 * editás el texto a mano de forma que ya no coincida exactamente con lo
 * insertado, deja de resaltarse.
 *
 * `ctx.ui.addAutocompleteProvider` envuelve el proveedor de autocompletado
 * activo para detectar en `applyCompletion` cuándo pasa esto y guarda el
 * texto exacto insertado (`item.value`, p.ej. "@src/index.ts"). En cada
 * `render()`, buscamos esos textos dentro de las líneas ya renderizadas
 * (una vez separada la lista flotante, para no tocar sus renglones) y los
 * reemplazamos por su versión coloreada con `theme.fg("accent", ...)`.
 *
 * Es un enfoque de post-procesado: no reescribe el layout/word-wrap ni el
 * cursor del editor base. Si el path se parte en dos líneas por word-wrap,
 * o el cursor queda exactamente encima, el resaltado puede no aplicarse en
 * ese render puntual (se recupera solo en el próximo).
 */

import {
	CustomEditor,
	type ExtensionAPI,
	type ExtensionUIContext,
	type KeybindingsManager,
} from "@earendil-works/pi-coding-agent";
import {
	CURSOR_MARKER,
	truncateToWidth,
	type AutocompleteProvider,
	type EditorTheme,
	type OverlayHandle,
	type TUI,
} from "@earendil-works/pi-tui";

/** Ajustá esto si tu footer no tiene 3 líneas (hoy: kyubi-footer). Se usa
 *  solo como fallback mientras la consulta DSR de la fila real del cursor
 *  todavía no respondió (ver `CursorRowProbe`). */
const ASSUMED_FOOTER_HEIGHT_ROWS = 3;

const MAX_TRACKED_TOKENS = 50;

/**
 * Pregunta a la terminal en qué fila visible está realmente el cursor,
 * usando DSR/CPR (`ESC[6n`, un estándar de terminal: "Cursor Position
 * Report"). La terminal responde con `ESC[<fila>;<col>R` por la entrada
 * estándar, que interceptamos con `ctx.ui.onTerminalInput`.
 *
 * Por qué hace falta: el motor de overlays de pi solo permite anclar
 * relativo al viewport (`anchor: "bottom-left"` + `offsetY`), que asume que
 * el editor+footer están pegados al fondo real de la terminal. Eso es
 * cierto una vez que el chat ya llena la pantalla, pero NO en una sesión
 * recién empezada (el motor rellena líneas vacías al FINAL del contenido
 * real para completar el alto de pantalla, no al medio, así que el
 * editor+footer quedan más arriba de lo que ese anclaje asume). No hay API
 * de extensiones que exponga la posición real del cursor o la altura real
 * del contenido, así que la única forma de saber la posición verdadera es
 * preguntárselo directamente a la terminal.
 */
class CursorRowProbe {
	private pending?: (row: number | undefined) => void;

	constructor(ui: ExtensionUIContext) {
		ui.onTerminalInput((data) => {
			const match = /\x1b\[(\d+);(\d+)R/.exec(data);
			if (!match || !this.pending) return undefined;

			const row = Number(match[1]) - 1; // CPR es 1-indexado
			const resolve = this.pending;
			this.pending = undefined;
			resolve(row);

			// Nunca dejamos pasar la respuesta CPR como si fuera tipeo real; el
			// resto del chunk (si había algo más mezclado) sí sigue su curso.
			const cleaned = data.slice(0, match.index) + data.slice(match.index + match[0].length);
			return cleaned.length > 0 ? { data: cleaned } : { consume: true };
		});
	}

	/** Fila absoluta (0-indexada, relativa al viewport visible) del cursor real. `undefined` si no hubo respuesta a tiempo. */
	query(terminal: { write(data: string): void }): Promise<number | undefined> {
		if (this.pending) return Promise.resolve(undefined); // ya hay una consulta en curso, no solapar

		return new Promise((resolve) => {
			const timeout = setTimeout(() => {
				this.pending = undefined;
				resolve(undefined);
			}, 250);
			this.pending = (row) => {
				clearTimeout(timeout);
				resolve(row);
			};
			terminal.write("\x1b[6n");
		});
	}
}

/**
 * Overlay persistente para el popup flotante. Ver comentario grande al
 * principio del archivo: contenido y posición/ancho se actualizan por
 * separado a propósito.
 */
class FloatingListOverlay {
	private handle?: OverlayHandle;
	/** Referencia estable: el render() del overlay la lee en vivo en cada frame. */
	private readonly content: { lines: string[] } = { lines: [] };
	private currentWidth = -1;
	private currentAboveRows = -1;

	constructor(private readonly ui: ExtensionUIContext) {}

	/** Actualiza contenido siempre; solo recrea el overlay si cambió posición/ancho. */
	update(lines: string[], width: number, aboveRows: number): void {
		this.content.lines = lines;

		if (!this.handle) {
			this.create(width, aboveRows);
			return;
		}

		if (width !== this.currentWidth || aboveRows !== this.currentAboveRows) {
			this.handle.hide();
			this.handle = undefined;
			this.create(width, aboveRows);
			return;
		}

		this.handle.setHidden(false);
	}

	hide(): void {
		this.handle?.setHidden(true);
	}

	private create(width: number, aboveRows: number): void {
		this.currentWidth = width;
		this.currentAboveRows = aboveRows;
		const content = this.content;

		// `ui.custom` es asíncrono y nunca lo resolvemos (no hay "done"): el
		// overlay recién queda visible en el próximo frame, no en este mismo
		// render. `render()` lee `content.lines` en vivo en cada frame, así que
		// las actualizaciones de contenido posteriores no necesitan recrearlo.
		void this.ui.custom<void>(
			(_tui, theme) => ({
				render(w: number): string[] {
					if (content.lines.length === 0) return [];
					const separator = theme.fg("accent", "─".repeat(Math.max(0, w)));
					const body = content.lines.map((line) => truncateToWidth(line, w));
					return [separator, ...body];
				},
				invalidate() {},
			}),
			{
				overlay: true,
				overlayOptions: {
					anchor: "bottom-left",
					offsetY: -aboveRows,
					width,
					nonCapturing: true,
				},
				onHandle: (handle) => {
					handle.setHidden(false);
					this.handle = handle;
				},
			},
		);
	}
}

/** Trackea qué paths de archivo se terminaron de agregar con `@`, para resaltarlos. */
class HighlightTracker {
	private tokens: string[] = [];
	private requestRender?: () => void;

	onRenderRequest(fn: () => void): void {
		this.requestRender = fn;
	}

	/**
	 * Llamado cuando se completó (terminó) la inserción de un archivo o
	 * carpeta. Si el nuevo token EXTIENDE uno ya trackeado (p.ej. primero se
	 * selecciona la carpeta "@src/" y después, sin salir de ese mismo token
	 * `@...`, se completa un archivo puntual adentro: "@src/index.ts"), el
	 * token viejo ya no es una selección independiente — se descarta. Si no
	 * se descartara, ambos quedarían trackeados a la vez y, al ser uno
	 * prefijo exacto del otro, el resaltado del más corto se aplicaría
	 * DENTRO del texto ya coloreado del más largo, anidando códigos ANSI y
	 * cortando el color del resto del path (el color de "index.ts" se
	 * perdía porque el reset del anidado interrumpía el span del externo).
	 */
	add(token: string): void {
		this.tokens = this.tokens.filter((t) => t !== token && !token.startsWith(t));
		this.tokens.push(token);
		if (this.tokens.length > MAX_TRACKED_TOKENS) this.tokens.shift();
		this.requestRender?.();
	}

	/**
	 * Devuelve los tokens que siguen presentes tal cual en `text`, más largos
	 * primero (para que un path no quede parcialmente tapado por otro que lo
	 * contiene como substring). También descarta los que ya no están.
	 */
	reconcile(text: string): string[] {
		if (text.trim() === "") {
			this.tokens = [];
			return [];
		}
		this.tokens = this.tokens.filter((t) => text.includes(t));
		return [...new Set(this.tokens)].sort((a, b) => b.length - a.length);
	}
}

/** Envuelve un AutocompleteProvider para detectar completions de archivo terminadas. */
function withFileHighlightTracking(current: AutocompleteProvider, tracker: HighlightTracker): AutocompleteProvider {
	return {
		triggerCharacters: current.triggerCharacters,
		getSuggestions: (lines, cursorLine, cursorCol, options) =>
			current.getSuggestions(lines, cursorLine, cursorCol, options),
		shouldTriggerFileCompletion: current.shouldTriggerFileCompletion
			? (lines, cursorLine, cursorCol) => current.shouldTriggerFileCompletion!(lines, cursorLine, cursorCol)
			: undefined,
		applyCompletion: (lines, cursorLine, cursorCol, item, prefix) => {
			const result = current.applyCompletion(lines, cursorLine, cursorCol, item, prefix);

			// Nos interesan los adjuntos de archivo o carpeta (prefix "@..."). Las
			// carpetas no llevan espacio final porque el autocompletado sigue
			// abierto para navegar adentro, pero igual se resaltan: `reconcile`
			// las sigue encontrando como substring exacto aunque el usuario
			// siga escribiendo a continuación (p.ej. "@src/" dentro de
			// "@src/index.ts").
			const isFileAttachment = prefix.startsWith("@");
			if (isFileAttachment) {
				tracker.add(item.value);
			}

			return result;
		},
	};
}

/** Replica el cálculo de contentWidth que hace el Editor base internamente. */
function computeContentWidth(width: number, paddingX: number): number {
	const maxPadding = Math.max(0, Math.floor((width - 1) / 2));
	const clampedPadding = Math.min(paddingX, maxPadding);
	return Math.max(1, width - clampedPadding * 2);
}

class EnhancedEditor extends CustomEditor {
	private overlay: FloatingListOverlay;
	private tracker: HighlightTracker;
	private accentColor: () => (text: string) => string;
	private probe: CursorRowProbe;
	private wasShowingAutocomplete = false;
	private lastResolvedCursorRow: number | undefined;

	constructor(
		tui: TUI,
		theme: EditorTheme,
		keybindings: KeybindingsManager,
		overlay: FloatingListOverlay,
		tracker: HighlightTracker,
		accentColor: () => (text: string) => string,
		probe: CursorRowProbe,
	) {
		super(tui, theme, keybindings);
		this.overlay = overlay;
		this.tracker = tracker;
		this.accentColor = accentColor;
		this.probe = probe;
		this.tracker.onRenderRequest(() => this.tui.requestRender());
	}

	override render(width: number): string[] {
		let lines = super.render(width);

		// --- 1) Popup flotante: separar la lista de autocompletado del flujo ---
		const listInstance = (this as unknown as { autocompleteList?: { render(w: number): string[] } })
			.autocompleteList;

		if (this.isShowingAutocomplete() && listInstance) {
			// Ubicar la línea del cursor DENTRO del bloque (antes de recortar la
			// lista): la necesitamos para saber cuántas filas del bloque quedan
			// POR ENCIMA del cursor (típicamente 1: el borde superior), y así
			// ubicar el popup arriba de TODO el bloque, no solo arriba del
			// cursor. Es de solo lectura: no se quita el marcador, así que la
			// extracción global de cursor del TUI (para el cursor de
			// hardware/IME) sigue intacta.
			let cursorLineIndex = -1;
			for (let i = 0; i < lines.length; i++) {
				if (lines[i]!.includes(CURSOR_MARKER)) {
					cursorLineIndex = i;
					break;
				}
			}

			const contentWidth = computeContentWidth(width, this.getPaddingX());
			const listLines = listInstance.render(contentWidth);

			// Desconecta la lista del flujo del editor: el editor base la agregó
			// como las últimas `listLines.length` entradas del array.
			if (listLines.length > 0 && lines.length >= listLines.length) {
				lines.length -= listLines.length;
			}

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

		// --- 2) Resaltado de paths agregados (sobre las líneas ya sin la lista) ---
		const tokens = this.tracker.reconcile(this.getText());
		if (tokens.length > 0) {
			const colorize = this.accentColor();

			// Se calculan todas las posiciones ANTES de tocar ninguna línea (en
			// vez de mutar y recolorizar de a un token por vez): si dos tokens
			// trackeados llegasen a solaparse en el texto (uno substring del
			// otro en la misma posición), aplicar el color del segundo sobre el
			// resultado ya coloreado del primero anida códigos ANSI y corta el
			// color del resto del texto (el `reset` interno interrumpe el span
			// externo). Acá, en cambio, un token que se solaparía con un match
			// ya reservado simplemente se descarta (se procesan más largos
			// primero, así que el más largo/específico gana) y las líneas se
			// reconstruyen en una única pasada al final.
			type Match = { start: number; end: number; token: string };
			const matchesByLine = new Map<number, Match[]>();

			for (const token of tokens) {
				for (let i = 0; i < lines.length; i++) {
					const line = lines[i]!;
					const idx = line.indexOf(token);
					if (idx === -1) continue;
					const end = idx + token.length;
					const existing = matchesByLine.get(i) ?? [];
					const overlaps = existing.some((m) => idx < m.end && m.start < end);
					if (overlaps) continue;
					existing.push({ start: idx, end, token });
					matchesByLine.set(i, existing);
					break;
				}
			}

			for (const [i, matches] of matchesByLine) {
				matches.sort((a, b) => a.start - b.start);
				const line = lines[i]!;
				let result = "";
				let cursor = 0;
				for (const m of matches) {
					result += line.slice(cursor, m.start) + colorize(m.token);
					cursor = m.end;
				}
				result += line.slice(cursor);
				lines[i] = result;
			}
		}

		return lines;
	}
}

export default function (pi: ExtensionAPI) {
	pi.on("session_start", (_event, ctx) => {
		const overlay = new FloatingListOverlay(ctx.ui);
		const tracker = new HighlightTracker();
		const probe = new CursorRowProbe(ctx.ui);

		ctx.ui.addAutocompleteProvider((current) => withFileHighlightTracking(current, tracker));

		ctx.ui.setEditorComponent(
			(tui, theme, keybindings) =>
				new EnhancedEditor(
					tui,
					theme,
					keybindings,
					overlay,
					tracker,
					() => (text: string) => ctx.ui.theme.fg("accent", text),
					probe,
				),
		);
	});
}
