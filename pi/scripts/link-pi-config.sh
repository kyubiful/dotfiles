#!/usr/bin/env bash
#
# link-pi-config.sh
#
# Crea (o repara) los symlinks de configuración de `pi` en ~/.pi
# apuntando siempre a las fuentes reales en ~/.config/pi (dotfiles).
#
# Idempotente: se puede ejecutar tantas veces como se quiera.
# Uso:
#   ./link-pi-config.sh           # crea/repara los enlaces
#   ./link-pi-config.sh --check   # solo verifica, no modifica nada
#
set -euo pipefail

SRC="$HOME/.config/pi"
DST="$HOME/.pi"
CHECK_ONLY=false

if [[ "${1:-}" == "--check" ]]; then
  CHECK_ONLY=true
fi

# Mapa "destino relativo a ~/.pi" -> "origen relativo a ~/.config/pi"
LINKS=(
  "subagents.json:subagents.json"
  "agent/settings.json:agent/settings.json"
  "agent/subagents.json:agent/subagents.json"
  "agent/agents:agent/agents"
  "agent/extensions:agent/extensions"
  "agent/personas:agent/personas"
  "agent/skills:agent/skills"
  "agent/themes:agent/themes"
)

status_ok=0
status_fixed=0
status_error=0

log() { printf '%s\n' "$*"; }

check_and_link() {
  local dst_rel="$1" src_rel="$2"
  local dst="$DST/$dst_rel"
  local src="$SRC/$src_rel"

  if [[ ! -e "$src" ]]; then
    log "❌ FALTA ORIGEN: $src no existe (revisa dotfiles)"
    status_error=$((status_error + 1))
    return
  fi

  # ¿Ya es un symlink correcto?
  if [[ -L "$dst" ]]; then
    local current_target
    current_target=$(readlink "$dst")
    local resolved
    resolved=$(readlink -f "$dst" 2>/dev/null || true)
    if [[ "$resolved" == "$src" ]]; then
      log "✅ OK: $dst -> $src"
      status_ok=$((status_ok + 1))
      return
    else
      log "⚠️  ENLACE INCORRECTO: $dst -> $current_target (esperado: $src)"
    fi
  elif [[ -e "$dst" ]]; then
    log "⚠️  EXISTE ARCHIVO REAL (no symlink) en $dst, no se sobreescribe automáticamente"
    status_error=$((status_error + 1))
    return
  else
    log "➕ FALTA ENLACE: $dst"
  fi

  if $CHECK_ONLY; then
    status_fixed=$((status_fixed + 1))
    return
  fi

  mkdir -p "$(dirname "$dst")"
  rm -rf "$dst"
  ln -s "$src" "$dst"
  log "   -> reparado: $dst -> $src"
  status_fixed=$((status_fixed + 1))
}

log "Sincronizando symlinks de configuración de pi"
log "  origen (dotfiles): $SRC"
log "  destino (pi runtime): $DST"
log ""

for entry in "${LINKS[@]}"; do
  dst_rel="${entry%%:*}"
  src_rel="${entry##*:}"
  check_and_link "$dst_rel" "$src_rel"
done

log ""
log "Resumen: $status_ok ok, $status_fixed reparados/pendientes, $status_error errores"

if $CHECK_ONLY && [[ $status_fixed -gt 0 || $status_error -gt 0 ]]; then
  exit 1
fi

if [[ $status_error -gt 0 ]]; then
  exit 1
fi
