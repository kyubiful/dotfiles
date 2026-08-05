#!/usr/bin/env bash
#
# check-symlinks.sh
#
# Escanea un directorio en busca de symlinks rotos o auto-referenciados
# (el típico bug de "ln -s nombre nombre" que crea un bucle infinito).
#
# Uso:
#   ./check-symlinks.sh [directorio]     # por defecto: ~/.pi
#
set -euo pipefail

DIR="${1:-$HOME/.pi}"
found_issues=0

if [[ ! -d "$DIR" ]]; then
  echo "El directorio $DIR no existe" >&2
  exit 1
fi

echo "Escaneando symlinks en: $DIR"
echo ""

while IFS= read -r -d '' link; do
  if [[ ! -e "$link" ]]; then
    echo "❌ ROTO: $link -> $(readlink "$link")"
    found_issues=$((found_issues + 1))
    continue
  fi

  # Detecta auto-referencia: el destino resuelto es el mismo archivo
  resolved=$(readlink -f "$link" 2>/dev/null || true)
  if [[ "$resolved" == "$link" ]]; then
    echo "❌ AUTO-REFERENCIADO (bucle): $link -> $(readlink "$link")"
    found_issues=$((found_issues + 1))
  fi
done < <(find "$DIR" -type l -print0 2>/dev/null)

echo ""
if [[ $found_issues -eq 0 ]]; then
  echo "✅ Sin problemas detectados"
else
  echo "⚠️  $found_issues problema(s) encontrado(s)"
  exit 1
fi
