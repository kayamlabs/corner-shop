"""Play the episode through the `shop` command with a scripted operator from the engine."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from going_concern import EndgameExploiter, ReferenceOperator  # noqa: E402

OPERATORS = {"reference": ReferenceOperator, "endgame_exploiter": EndgameExploiter}


def shop(*args: str, stdin: str | None = None) -> str:
    return subprocess.run(["shop", *args], input=stdin, text=True, capture_output=True,
                          check=True).stdout


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--operator", choices=sorted(OPERATORS), default="reference")
    op = OPERATORS[p.parse_args().operator]()
    while True:
        obs = json.loads(shop("status", "--json"))
        if obs["done"]:
            break
        shop("act", "-", stdin=json.dumps(op.act(obs)))
    shop("done")
    print(shop("status"))


if __name__ == "__main__":
    main()
