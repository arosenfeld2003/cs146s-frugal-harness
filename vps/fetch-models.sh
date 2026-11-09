#!/usr/bin/env bash
# Download pinned GGUF models listed in vps/models.lock and verify sha256.
# Same script on macOS and Linux. Usage: vps/fetch-models.sh [models_dir]
set -euo pipefail
# macOS: keep the machine awake (idle sleep) for the duration of this script.
if [[ "$(uname)" == Darwin && -z "${CAFFEINATED:-}" ]] && command -v caffeinate >/dev/null; then
  CAFFEINATED=1 exec caffeinate -i "$0" "$@"
fi
cd "$(dirname "$0")/.."
dir="${1:-models}"
mkdir -p "$dir"

sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

while read -r repo rev file expected; do
  [[ -z "$repo" || "$repo" == \#* ]] && continue
  out="$dir/$file"
  if [[ -f "$out" && "$(sha256 "$out")" == "$expected" ]]; then echo "ok (cached) $file"; continue; fi
  echo "fetching $repo@${rev:0:8} $file"
  curl -fL --retry 20 --retry-all-errors --retry-delay 5 -C - -o "$out.part" "https://huggingface.co/$repo/resolve/$rev/$file"
  actual="$(sha256 "$out.part")"
  if [[ "$actual" != "$expected" ]]; then echo "SHA MISMATCH $file: $actual" >&2; rm -f "$out.part"; exit 1; fi
  mv "$out.part" "$out"; echo "ok $file"
done < vps/models.lock
