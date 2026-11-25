#!/bin/bash
# Grade the episode the agent played: replay it with a clean engine, finish any unplayed weeks
# with no decisions, and write the going-concern reward plus metrics to /logs/verifier/reward.json.
set -euo pipefail
mkdir -p /logs/verifier
python3 -I /tests/grade.py --firm /tests/firm.json --episode /var/lib/corner-shop/episode.json \
  --out-dir /logs/verifier
