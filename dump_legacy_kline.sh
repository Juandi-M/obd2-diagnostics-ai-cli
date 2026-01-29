#!/bin/bash
set -euo pipefail

# folder donde vive este script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ROOT_DIR="$SCRIPT_DIR/obd/legacy_kline"
OUTPUT="$SCRIPT_DIR/legacy_kline_dump.txt"

if [[ ! -d "$ROOT_DIR" ]]; then
  echo "ERROR: No existe el directorio: $ROOT_DIR" >&2
  echo "Tip: tu repo tiene 'obd/legacy_kline', no 'legacy_kline' en root." >&2
  exit 1
fi

> "$OUTPUT"

{
  echo "===== LEGACY_KLINE FULL DUMP ====="
  echo "Generated at: $(date)"
  echo "Root: $ROOT_DIR"
  echo ""
} >> "$OUTPUT"

find "$ROOT_DIR" -type f | sort | while read -r file; do
  rel="${file#"$SCRIPT_DIR/"}"
  {
    echo ""
    echo "========================================"
    echo "FILE: $rel"
    echo "========================================"
    echo ""
    cat "$file"
    echo ""
  } >> "$OUTPUT"
done

echo "Done. Output -> $OUTPUT"
