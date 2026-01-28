#!/usr/bin/env bash
set -euo pipefail

ROOT="obd/legacy_kline"

if [[ ! -d "$ROOT" ]]; then
  echo "ERROR: directory not found: $ROOT" >&2
  exit 1
fi

# Extensiones incluidas (ajustá aquí si querés)
EXT_REGEX='\.(py|md|txt)$'

# Si querés incluir TODO (incluyendo __pycache__ o binarios), cambia el find.
find "$ROOT" -type f \
  ! -path "*/__pycache__/*" \
  ! -path "*/.pytest_cache/*" \
  ! -path "*/.mypy_cache/*" \
  -print0 \
| sort -z \
| while IFS= read -r -d '' file; do
    if [[ "$file" =~ $EXT_REGEX ]]; then
      echo ""
      echo "============================================================"
      echo "FILE: $file"
      echo "============================================================"
      cat "$file"
      echo ""
    fi
  done
echo "=== END OF DUMP ==="