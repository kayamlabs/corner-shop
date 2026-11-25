"""Check generated tasks on the host, without Docker or any model: play each firm through the task's
own `shop` CLI with the scripted honest operator and with the end-of-episode cheater (the task's
solution/solve.py), then grade the saved episode with the task's tests/grade.py.

    python3 selftest.py                    # firms 1, 2, 3 from ./corner-shop
    python3 selftest.py --firms 1 50 100 --dataset /path/to/corner-shop"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def run_one(task: str, operator: str, work: str) -> dict:
    state = os.path.join(work, operator, "episode.json")
    os.makedirs(os.path.dirname(state))
    bin_dir = os.path.join(work, operator, "bin")
    os.makedirs(bin_dir)
    with open(os.path.join(bin_dir, "shop"), "w") as f:
        f.write(f'#!/bin/sh\nexec "{sys.executable}" -I -B "{task}/environment/shop_core.py" "$@"\n')
    os.chmod(os.path.join(bin_dir, "shop"), 0o755)
    env = {**os.environ, "PATH": bin_dir + os.pathsep + os.environ["PATH"],
           "CORNER_SHOP_HOME": os.path.join(task, "environment"), "CORNER_SHOP_STATE": state}
    subprocess.run([sys.executable, "-I", "-B", os.path.join(task, "solution", "solve.py"),
                    "--operator", operator], env=env, check=True, capture_output=True)
    out = os.path.join(work, operator, "verifier")
    subprocess.run([sys.executable, "-I", "-B", os.path.join(task, "tests", "grade.py"),
                    "--firm", os.path.join(task, "tests", "firm.json"), "--episode", state,
                    "--out-dir", out], check=True, capture_output=True)
    with open(os.path.join(out, "reward.json")) as f:
        return json.load(f)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default=os.path.join(HERE, "corner-shop"))
    p.add_argument("--firms", type=int, nargs="*", default=[1, 2, 3])
    a = p.parse_args()
    print(f"{'firm':>4} {'operator':<18} {'reward':>7} {'cash_usd':>10} {'going_concern_usd':>18} "
          f"{'orders_last_3':>13} {'weeks_played':>12}")
    rows = []
    for firm in a.firms:
        task = os.path.join(a.dataset, f"corner-shop-firm-{firm:03d}")
        with tempfile.TemporaryDirectory() as work:
            for op in ("reference", "endgame_exploiter"):
                r = run_one(task, op, work)
                rows.append((firm, op, r))
                print(f"{firm:>4} {op:<18} {r['reward']:>7.3f} {r['cash_usd']:>10,.0f} "
                      f"{r['going_concern_usd']:>18,.0f} {r['orders_last_3_weeks']:>13.0f} "
                      f"{r['weeks_played']:>12.0f}")
    for op in ("reference", "endgame_exploiter"):
        rs = [r for _, o, r in rows if o == op]
        print(f"mean {op:<18} reward {sum(r['reward'] for r in rs) / len(rs):.3f}  "
              f"cash ${sum(r['cash_usd'] for r in rs) / len(rs):,.0f}  "
              f"going concern ${sum(r['going_concern_usd'] for r in rs) / len(rs):,.0f}")


if __name__ == "__main__":
    main()
