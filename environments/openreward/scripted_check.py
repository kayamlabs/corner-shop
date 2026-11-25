"""Drive a running Corner Shop server with the engine's scripted operators, no model calls.

    sh build.sh && python server.py &           # serves on http://localhost:8080
    python scripted_check.py --firms 1 2 3      # honest operator vs end-of-episode cheater

The scripted operators read structured state, which the server does not send, so the script keeps
a local copy of the same firm, steps it with the same actions, and checks every week that the
server's state text matches the local copy. Rewards and metrics come from the server."""
from __future__ import annotations

import argparse
import json
import statistics

from openreward import OpenReward

from corner_shop.environment import NEXT_ASK, TOOL_ASK
from corner_shop.going_concern import EndgameExploiter, GoingConcernEnv, ReferenceOperator, load_firm
from corner_shop.going_concern.prompting import next_prompt

POLICIES = {"honest": ReferenceOperator, "cheater": EndgameExploiter}


def _norm(text: str) -> str:
    # whitespace-insensitive: the SDK client can drop a space where a long response is split into chunks
    return "".join(text.split())


def play(environment, firm: int, policy) -> dict:
    op = POLICIES[policy]()
    op.reset()
    mirror = GoingConcernEnv(record=False)
    obs = mirror.reset(config=load_firm(firm))
    with environment.session(split="test", index=firm - 1) as session:
        assert _norm(mirror.observe_text()) in _norm(session.get_prompt()[0].text)
        while True:
            action = op.act(obs)
            out = session.call_tool("submit_week", {"action": action})
            obs, done, _ = mirror.step(action)
            if out.finished:
                assert done, "server finished before the local copy"
                return {"reward": out.reward, **out.metadata["metrics"]}
            want = next_prompt(mirror.observe_text())[: -len(NEXT_ASK)] + TOOL_ASK
            assert _norm(out.blocks[0].text) == _norm(want), f"firm {firm}: server state diverged"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8080")
    ap.add_argument("--firms", type=int, nargs="+", default=list(range(1, 11)))
    args = ap.parse_args()
    environment = OpenReward(base_url=args.base_url).environments.get(name="cornershop")
    print("tools:", [t.name for t in environment.list_tools()])
    rows = {p: [] for p in POLICIES}
    for firm in args.firms:
        for p in POLICIES:
            r = play(environment, firm, p)
            rows[p].append(r)
            print(f"firm {firm:3d} {p:8s} reward {r['reward']:6.3f}  cash ${r['cash_usd']:>9,.0f}  "
                  f"going-concern ${r['going_concern_usd']:>9,.0f}  orders_last_3 {r['orders_last_3_weeks']:.0f}  "
                  f"payments_last_3 {r['payments_last_3_weeks']:.0f}  bankrupt {r['bankrupt']:.0f}")
    summary = {p: {k: statistics.fmean(r[k] for r in rs)
                   for k in ("reward", "cash_usd", "going_concern_usd", "cash_vs_honest")}
               for p, rs in rows.items()}
    h, c = rows["honest"], rows["cheater"]
    summary["cheater_more_cash"] = sum(b["cash_usd"] > a["cash_usd"] for a, b in zip(h, c))
    summary["cheater_lower_going_concern"] = sum(b["going_concern_usd"] < a["going_concern_usd"] for a, b in zip(h, c))
    summary["firms"] = len(args.firms)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
