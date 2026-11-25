"""Drive full episodes through the client and a live server with the two scripted operators.

    ./build.sh && uv run python tests/smoke_test.py [--firms 1-100] [--url http://localhost:8000]

Without --url it starts the server in-process on a free port. No model calls: the honest
ReferenceOperator should score about 1.0 normalized, and the EndgameExploiter should end with more
cash and a lower going-concern value. Each episode is also replayed directly on the engine to check
the server reports the same numbers."""
from __future__ import annotations

import argparse
import json
import socket
import statistics
import threading
import time

import corner_shop as pkg  # noqa: E402  (installed by `uv sync` / `pip install .`)
from corner_shop.server import going_concern as gc  # noqa: E402
from corner_shop.server.going_concern import rewards  # noqa: E402

CornerShopAction, CornerShopEnv = pkg.CornerShopAction, pkg.CornerShopEnv


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server() -> str:
    import uvicorn
    from corner_shop.server.app import app
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    return f"http://127.0.0.1:{port}", server, thread


def play(env, operator, firm: int, as_message: bool = False):
    operator.reset()
    result = env.reset(firm=firm)
    obs = result.observation
    assert obs.system_prompt and obs.prompt and obs.week == 0 and result.reward == 0.0
    rewards_seen = []
    while not result.done:
        decision = operator.act(result.observation.shop)
        if as_message:  # the path a model takes: free text with a ```json block at the end
            action = CornerShopAction(message="Plan for the week.\n```json\n" + json.dumps(decision) + "\n```")
        else:
            action = CornerShopAction(decision=decision)
        result = env.step(action)
        rewards_seen.append(result.reward)
    assert all(r == 0.0 for r in rewards_seen[:-1]), "reward must be 0 until the final step"
    return result


def direct(operator, firm: int) -> dict:
    sim = gc.run_episode(operator, firm).sim
    return {"cash_usd": rewards.cash_reward(sim), "going_concern_usd": rewards.going_concern(sim)}


def parse_range(s: str) -> list[int]:
    a, _, b = s.partition("-")
    return list(range(int(a), int(b or a) + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--firms", default="1-100")
    ap.add_argument("--url", default=None)
    args = ap.parse_args()
    firms = parse_range(args.firms)
    server = thread = None
    if args.url:
        url = args.url
    else:
        url, server, thread = start_server()
    print(f"server: {url} ({'external' if args.url else 'in-process'})")
    ops = {"honest": gc.ReferenceOperator, "cheater": gc.EndgameExploiter}
    rows = {name: [] for name in ops}
    with CornerShopEnv(base_url=url).sync() as env:
        for firm in firms:
            for name, cls in ops.items():
                r = play(env, cls(), firm)
                m = r.observation.metrics
                ref = direct(cls(), firm)
                assert abs(m["cash_usd"] - ref["cash_usd"]) < 1e-6, (firm, name, m, ref)
                assert abs(m["going_concern_usd"] - ref["going_concern_usd"]) < 1e-6, (firm, name, m, ref)
                rows[name].append({"firm": firm, "reward": r.reward, **m})
        # The text path (what a model sends) gives the same episode as the structured path.
        t = play(env, gc.ReferenceOperator(), firms[0], as_message=True)
        assert abs(t.reward - rows["honest"][0]["reward"]) < 1e-9
        # Stopping early: the rest of the weeks run unattended and the episode is still scored.
        env.reset(firm=firms[0])
        e = env.step(CornerShopAction(end_episode=True))
        assert e.done and e.observation.metrics["weeks_unattended"] > 0
        st = env.state()
        print(f"state after early stop: firm={st.firm} week={st.week}/{st.weeks_total} done={st.done} "
              f"bankrupt={st.bankrupt}; reward={e.reward:.3f}, "
              f"weeks_unattended={e.observation.metrics['weeks_unattended']:.0f}")

    if server is not None:
        time.sleep(0.2)  # let the server finish closing the session
        server.should_exit = True
        thread.join()

    def mean(name, key):
        return statistics.fmean(r[key] for r in rows[name])

    print(f"\n{len(firms)} firms, reward = going_concern normalized by the honest operator")
    print(f"{'operator':<8} {'reward':>8} {'cash_usd':>10} {'gc_usd':>10} {'cash_vs_h':>9} "
          f"{'orders_l3':>9} {'pays_l3':>8} {'liq_units':>9} {'bankrupt':>8}")
    for name in ops:
        print(f"{name:<8} {mean(name, 'reward'):>8.3f} {mean(name, 'cash_usd'):>10,.0f} "
              f"{mean(name, 'going_concern_usd'):>10,.0f} {mean(name, 'cash_vs_honest'):>9.2f} "
              f"{mean(name, 'orders_last_3_weeks'):>9.2f} {mean(name, 'payments_last_3_weeks'):>8.2f} "
              f"{mean(name, 'liquidated_units'):>9.1f} {mean(name, 'bankrupt'):>8.2f}")
    h, c = rows["honest"], rows["cheater"]
    more_cash = sum(ci["cash_usd"] > hi["cash_usd"] for hi, ci in zip(h, c))
    lower_gc = sum(ci["going_concern_usd"] < hi["going_concern_usd"] for hi, ci in zip(h, c))
    print(f"cheater ends with more cash on {more_cash}/{len(firms)} firms, "
          f"lower going-concern value on {lower_gc}/{len(firms)}")
    print(f"honest reward range: {min(r['reward'] for r in h):.3f}..{max(r['reward'] for r in h):.3f}")
    print("server numbers match the engine run directly: yes")


if __name__ == "__main__":
    main()
