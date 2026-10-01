#!/usr/bin/env bash
# Quran PWA launcher — serves the app over HTTP so the service worker and
# manifest work (they need http(s), not file://).
#
# Usage:  ./quran.sh              (fixed port 7860)
#         PORT=8000 ./quran.sh
set -euo pipefail

PORT="${PORT:-7860}"
# The port is FIXED (no fallback) so the app's origin never shifts — the
# service worker, caches and installed PWA all key off host:port.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

if [[ ! -f index.html ]]; then
  echo "✗ index.html not found in $HERE" >&2
  exit 1
fi

# Pick a python that has the http.server module.
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1;   then PY=python
else
  echo "✗ No python interpreter found (need python3 for http.server)" >&2
  exit 1
fi

# Some sandboxes/carriers refuse low ports. Probe with a real socket bind for
# the exact port; there is no fallback — a fixed origin matters more than
# convenience.
probe_port() {
  "$PY" - "$1" <<'PYEOF'
import socket, sys
p = int(sys.argv[1])
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("0.0.0.0", p)); s.close(); print(p)
except OSError:
    try: s.close()
    except Exception: pass
    sys.exit(1)
PYEOF
}

ACTUAL_PORT="$(probe_port "$PORT" || true)"
if [[ -z "$ACTUAL_PORT" ]]; then
  echo "✗ Port $PORT is unavailable (blocked or in use)." >&2
  echo "  The app uses a FIXED port so its origin never changes;" >&2
  echo "  free port $PORT or launch with PORT=<other> ./quran.sh" >&2
  exit 1
fi

# Best-effort LAN IP (first non-loopback global IPv4 address).
# Serve over HTTPS so the app is a SECURE CONTEXT: browsers only offer PWA
# install from secure origins, and plain http://192.168.x.x is not one. The
# self-signed cert (cert.pem/key.pem) is generated on first run and refreshed
# automatically if the LAN IP changes. Devices must accept the certificate
# warning once — unavoidable without a public domain.
LAN_IP="$(
  { ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -n1; } \
  || { ifconfig 2>/dev/null | awk '/inet / && $2 != "127.0.0.1"{print $2; exit}'; }
)"
export PORT="$ACTUAL_PORT"

"$PY" serve.py > "$TMPDIR/serve.log" 2>&1 &
SERVER_PID=$!

# Shut the server down cleanly on Ctrl-C / exit.
trap 'kill "$SERVER_PID" 2>/dev/null || true; echo; echo "Server stopped."; exit 0' INT TERM

# Wait for the server to actually accept connections before printing URLs.
for _ in $(seq 1 50); do
  if (echo > "/dev/tcp/127.0.0.1/$ACTUAL_PORT") >/dev/null 2>&1; then break; fi
  sleep 0.1
done

echo " Quran app is running"
echo
echo "  Local:      https://localhost:$ACTUAL_PORT/"
echo "  Local (IP): https://127.0.0.1:$ACTUAL_PORT/"
if [[ -n "${LAN_IP:-}" ]]; then
  echo "  Network:    https://$LAN_IP:$ACTUAL_PORT/   ← use this from another device"
fi
echo
echo "  First visit on a new device: accept the certificate warning"
echo "  (Advanced → Proceed). That is what makes the app installable."
echo
echo "  Serving:  $HERE"
echo "  Stop:     Ctrl-C"
echo

# Keep the script in the foreground so the trap can fire on Ctrl-C.
wait "$SERVER_PID"
