#!/bin/bash
# Reference play: the scripted honest operator drives `shop` for the whole episode.
# Set CORNER_SHOP_OPERATOR=endgame_exploiter to play the end-of-episode cheater instead.
set -euo pipefail
python3 -I /solution/solve.py --operator "${CORNER_SHOP_OPERATOR:-reference}"
