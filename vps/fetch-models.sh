#!/usr/bin/env bash
# Download pinned GGUF models listed in vps/models.lock and verify sha256.
# Same script on macOS and Linux. Usage: vps/fetch-models.sh [models_dir]
set -euo pipefail
cd "$(dirname "$0")/.."
dir="${1:-models}"
mkdir -p "$dir"

sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

while read -r repo rev file expected; do
  [[ -z "$repo" || "$repo" == \#* ]] && continue
  out="$dir/$file"
  if [[ -f "$out" && "$(sha256 "$out")" == "$expected" ]]; then echo "ok (cached) $file"; continue; fi
  echo "fetching $repo@${rev:0:8} $file"
  curl -fL --retry 3 -C - -o "$out.part" "https://huggingface.co/$repo/resolve/$rev/$file"
  actual="$(sha256 "$out.part")"
  if [[ "$actual" != "$expected" ]]; then echo "SHA MISMATCH $file: $actual" >&2; rm -f "$out.part"; exit 1; fi
  mv "$out.part" "$out"; echo "ok $file"
done < vps/models.lock
