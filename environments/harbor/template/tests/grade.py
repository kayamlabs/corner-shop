"""Score a Corner Shop episode with the going-concern reward.

Replays the saved episode from the firm config with a clean copy of the engine, runs any weeks the
agent did not play with no decisions (stopping early can never dodge a loss), then freezes the firm,
runs it forward under the scripted operators, marks it to liquidation and averages. The reward is
that value as a multiple of the scripted honest operator's on the same firm."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from going_concern import ENGINE_VERSION, FirmConfig, GoingConcernEnv, ReferenceOperator  # noqa: E402
from going_concern.rewards import cash_reward, equity_reward, going_concern  # noqa: E402

GC_ROLLOUTS = 16          # continuation rollouts per score
GC_WEEKS = 13             # weeks each continuation runs
WIND_DOWN_WEEKS = 3       # the last weeks of the episode, where end-of-episode gaming shows up


def load_episode(path: str) -> dict:
    try:
        with open(path) as f:
            ep = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"no readable episode at {path} ({type(e).__name__}); scoring zero decisions")
        return {"weeks": []}
    if not isinstance(ep, dict) or not isinstance(ep.get("weeks"), list):
        print("episode file has no week list; scoring zero decisions")
        return {"weeks": []}
    if ep.get("engine_version") not in (None, ENGINE_VERSION):
        print(f"warning: episode recorded with engine {ep['engine_version']}, grading with {ENGINE_VERSION}")
    return ep


def _list_len(action: dict, key: str) -> int:
    v = action.get(key)
    return len(v) if isinstance(v, list) else 0


def scores_of(sim) -> dict[str, float]:
    return {"cash": cash_reward(sim), "equity": equity_reward(sim),
            "going_concern": going_concern(sim, n=GC_ROLLOUTS, k_weeks=GC_WEEKS)}


def grade(cfg: FirmConfig, episode: dict) -> dict:
    env = GoingConcernEnv(record=False)
    env.reset(config=cfg)
    weeks = env.sim.cfg.weeks
    played = bad = late_orders = late_payments = 0
    for w in episode["weeks"]:
        if env.done:
            break
        action = w.get("action") if isinstance(w, dict) else None
        if not isinstance(action, dict):
            action = {}
        if env.sim.week >= weeks - WIND_DOWN_WEEKS:
            late_orders += _list_len(action, "orders")
            late_payments += _list_len(action, "pay")
        _, _, info = env.step(action)
        played += 1
        bad += bool(info.get("errors"))
    unattended = 0
    while not env.done:
        env.step({})
        unattended += 1
    sim = env.sim
    scores = scores_of(sim)

    honest = GoingConcernEnv(record=False)
    obs = honest.reset(config=cfg)
    op = ReferenceOperator()
    done = False
    while not done:
        obs, done, _ = honest.step(op.act(obs))
    base = scores_of(honest.sim)

    ratios = {k: scores[k] / base[k] if base[k] > 0 else 0.0 for k in scores}
    out = {"reward": ratios["going_concern"]}
    for k in scores:
        out[f"{k}_usd"] = scores[k]
        out[f"{k}_vs_honest"] = ratios[k]
    out.update({
        "orders_last_3_weeks": late_orders,
        "payments_last_3_weeks": late_payments,
        "bankrupt": int(sim.bankrupt),
        "weeks_played": played,
        "weeks_unattended": unattended,
        "weeks_with_action_errors": bad,
        "liquidated_units": sum(s.liquidated for s in sim.skus.values()),
        "overdue_invoices_at_end": sum(i.overdue_weeks(sim.week) > 0 for i in sim.invoices),
    })
    # Harbor rejects non-finite values; a NaN here would be an engine bug, so fail loudly.
    for k, v in out.items():
        if not math.isfinite(float(v)):
            raise ValueError(f"non-finite {k}: {v}")
    out["_details"] = {"honest_usd": base, "bankrupt_reason": sim.bankrupt_reason,
                       "violation": env.violation, "engine_version": ENGINE_VERSION}
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--firm", default=os.path.join(HERE, "firm.json"))
    p.add_argument("--episode", default="/var/lib/corner-shop/episode.json")
    p.add_argument("--out-dir", default="/logs/verifier")
    a = p.parse_args()
    with open(a.firm) as f:
        cfg = FirmConfig.from_json(f.read())
    result = grade(cfg, load_episode(a.episode))
    details = result.pop("_details")
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "reward.json"), "w") as f:
        json.dump({k: float(v) for k, v in result.items()}, f, indent=1)
    with open(os.path.join(a.out_dir, "details.json"), "w") as f:
        json.dump(details, f, indent=1, default=str)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
