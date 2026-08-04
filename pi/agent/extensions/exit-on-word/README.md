# exit-on-word

Extensión mínima que permite salir de pi escribiendo la palabra `exit` en el
prompt, en lugar de tener que usar un comando o atajo de teclado.

## Cómo funciona

1. Se suscribe al evento `input`, que se dispara cada vez que el usuario
   envía un mensaje en el editor.
2. Compara el texto recibido (recortado y en minúsculas) contra la palabra
   `"exit"`.
   - Si **no coincide**, devuelve `{ action: "continue" }` para que pi procese
     el input con normalidad (no interfiere en nada más).
   - Si **coincide**, muestra una notificación de despedida (`ctx.ui.notify`),
     espera 500ms (para que la notificación alcance a pintarse en la TUI) y
     llama a `ctx.shutdown()` para cerrar la sesión, devolviendo
     `{ action: "handled" }` para indicar que el input ya fue procesado y no
     debe llegar al agente/modelo.

## Uso

Simplemente escribe:

```text
exit
```

en el prompt de pi y la sesión se cerrará mostrando `Good bye! 󱠡`.

## Archivos

- `index.ts` — implementación completa de la extensión (un solo listener).

## Notas

- Es un ejemplo de patrón "interceptar input antes de que llegue al modelo".
- No requiere dependencias externas ni estado persistente.
- Se corrigió un import incorrecto (`@aerendil-works/pi-code-agent` →
  `@earendil-works/pi-coding-agent`) que impedía que la extensión cargara.
