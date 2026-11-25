#!/bin/sh
# Build the Corner Shop Harbor dataset into ./corner-shop (generated; not checked in).
#   ./build.sh                 # all 100 firms, org "kayam"
#   ORG=myorg ./build.sh       # publish under another Harbor organization
# Needs the `harbor` CLI on PATH (pip install harbor) to write dataset.toml with task digests.
set -e
here=$(cd "$(dirname "$0")" && pwd)
org=${ORG:-kayam}
out="$here/corner-shop"
python3 "$here/build.py" --out "$out" --org "$org" "$@"
cd "$out"
harbor init --dataset "$org/corner-shop" --author "Kayam" \
  --description "Run a small shop for 13 weeks from the terminal. Scored by a going-concern reward that catches end-of-episode cheating."
cp "$here/README.md" "$out/README.md"
# harbor init writes version 1.0.0 and no keywords; match the task packages.
python3 - "$out/dataset.toml" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
s = s.replace('version = "1.0.0"', 'version = "0.1.0"', 1)
s = s.replace('keywords = []', 'keywords = ["long-horizon", "business", "simulation", "reward-hacking"]', 1)
open(p, "w").write(s)
PY
harbor lint "$out"/corner-shop-firm-*
