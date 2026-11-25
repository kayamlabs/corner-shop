"""Generate the Corner Shop Harbor dataset: one task per firm, built from template/ plus a vendored
copy of the engine and that firm's config.

    python3 build.py                       # all 100 firms into ./corner-shop
    python3 build.py --firms 1 2 3 --out /tmp/cs

Then `build.sh` (or `harbor init --dataset ...` by hand) writes dataset.toml with task digests."""
from __future__ import annotations

import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
TEMPLATE = os.path.join(HERE, "template")
sys.path.insert(0, ROOT)

from going_concern import ENGINE_VERSION, FirmConfig  # noqa: E402

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
DOCKERIGNORE = "__pycache__/\n*.pyc\n.DS_Store\n"


def firm_path(i: int) -> str:
    return os.path.join(ROOT, "firms", f"corner_shop_{i:02d}.json")


def copy_engine(dst: str) -> None:
    shutil.copytree(os.path.join(ROOT, "going_concern"), os.path.join(dst, "going_concern"), ignore=IGNORE)


def build_task(out: str, firm: int, org: str, version: str, author: str) -> str:
    with open(firm_path(firm)) as f:
        raw = f.read()
    cfg = FirmConfig.from_json(raw)
    fields = {"org": org, "firm": firm, "weeks": cfg.weeks, "version": version, "author": author,
              "engine_version": ENGINE_VERSION}
    task = os.path.join(out, f"corner-shop-firm-{firm:03d}")
    os.makedirs(task)
    for name in ("task.toml", "instruction.md"):
        with open(os.path.join(TEMPLATE, name)) as f:
            text = f.read()
        if name == "task.toml":
            text = text.format(**fields)
        else:  # the instruction has JSON braces in it; fill only the {weeks} slots
            text = text.replace("{weeks}", str(cfg.weeks))
        with open(os.path.join(task, name), "w") as f:
            f.write(text)
    for part in ("environment", "tests", "solution"):
        dst = os.path.join(task, part)
        shutil.copytree(os.path.join(TEMPLATE, part), dst, ignore=IGNORE)
        copy_engine(dst)
        if part != "solution":
            with open(os.path.join(dst, "firm.json"), "w") as f:
                f.write(raw)
            with open(os.path.join(dst, ".dockerignore"), "w") as f:
                f.write(DOCKERIGNORE)
    for script in ("environment/shop", "tests/test.sh", "solution/solve.sh"):
        os.chmod(os.path.join(task, script), 0o755)
    return task


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=os.path.join(HERE, "corner-shop"))
    p.add_argument("--firms", type=int, nargs="*", default=list(range(1, 101)))
    p.add_argument("--org", default="kayam", help="Harbor organization the tasks publish under")
    p.add_argument("--version", default="0.1.0")
    p.add_argument("--author", default="Kayam")
    a = p.parse_args()
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    for i in a.firms:
        build_task(a.out, i, a.org, a.version, a.author)
    print(f"wrote {len(a.firms)} tasks to {a.out}")


if __name__ == "__main__":
    main()
