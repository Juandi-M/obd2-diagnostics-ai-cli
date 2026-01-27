cat > smoke.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

echo "== Grep zombies =="
grep -RIn --exclude-dir=.git --exclude-dir=__pycache__ \
  -E "obd_parse|obd\.scanner|from\s+\.\.obd_parse|from\s+obd_parse|import\s+obd_parse" . && exit 1 || true
grep -RIn --exclude-dir=.git --exclude-dir=__pycache__ \
  -E "from\s+obd\.scanner|import\s+obd\.scanner" . && exit 1 || true

echo "== Compileall =="
python3 -m compileall -q .

echo "== Import all modules =="
python3 -c "import pkgutil, obd; [__import__(m.name) for m in pkgutil.walk_packages(obd.__path__, obd.__name__ + '.')]; print('OK all modules')"

echo "== Demo CLI =="
python3 obd_scan.py --demo

echo "✅ SMOKE OK"
SH

chmod +x smoke.sh
./smoke.sh
