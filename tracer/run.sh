#!/usr/bin/env bash
# Run one command with its HTTPS traffic captured by mitmproxy (redacted JSONL).
#
#   tracer/run.sh <label> <command> [args...]
#   tracer/run.sh cc-hello claude -p "say hi"
#   tracer/run.sh cc-interactive claude
#
# Writes traces/<YYYY-MM-DD>/<label>.jsonl (traces/ is gitignored).
# The mitmproxy CA is trusted only by the child process (NODE_EXTRA_CA_CERTS),
# never installed into the system keychain.
set -euo pipefail

[ $# -ge 2 ] || { sed -n '2,10p' "$0"; exit 1; }
label=$1; shift

root=$(cd "$(dirname "$0")/.." && pwd)
port=${TRACE_PORT:-18080}
out="$root/traces/$(date +%F)/$label.jsonl"
ca="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"
log="$root/traces/$(date +%F)/$label.mitm.log"
mkdir -p "$(dirname "$out")"

TRACE_OUT="$out" mitmdump --listen-host 127.0.0.1 -p "$port" -s "$root/tracer/capture.py" \
  --set flow_detail=0 >"$log" 2>&1 &
mitm=$!
trap 'kill $mitm 2>/dev/null; wait $mitm 2>/dev/null; echo "trace: $out ($(wc -l <"$out" 2>/dev/null || echo 0) flows)" >&2' EXIT

for _ in $(seq 50); do
  nc -z 127.0.0.1 "$port" 2>/dev/null && [ -f "$ca" ] && break
  sleep 0.1
done
nc -z 127.0.0.1 "$port" || { echo "mitmdump failed to start; see $log" >&2; exit 1; }

HTTPS_PROXY="http://127.0.0.1:$port" HTTP_PROXY="http://127.0.0.1:$port" \
NO_PROXY="localhost,127.0.0.1" NODE_EXTRA_CA_CERTS="$ca" NODE_USE_ENV_PROXY=1 \
  "$@"
