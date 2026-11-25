"""The `shop` command: drive one Corner Shop episode from the terminal, one week per `shop act`.

Inside the task container this file, the engine and the firm config live in a root-only directory.
The agent runs `shop`, which calls this script through sudo, so it can play the episode but cannot
read the engine state, rewind it or replay it to look ahead. Every call rebuilds the episode by
replaying the saved actions from the firm config (the engine is deterministic), so the saved
episode file is the only state, and it is what the verifier grades.

    shop status [--json]     this week's report (or the final report once the episode is over)
    shop act '<json>'        submit this week's decisions and advance one week ('-' reads stdin)
    shop history             the decisions submitted so far, with any refused parts
    shop done                stop playing; any remaining weeks run with no decisions"""
from __future__ import annotations

import fcntl
import json
import os
import sys

HOME = os.environ.get("CORNER_SHOP_HOME", "/opt/corner-shop")
STATE = os.environ.get("CORNER_SHOP_STATE", "/var/lib/corner-shop/episode.json")
sys.path.insert(0, HOME)

from going_concern import ENGINE_VERSION, FirmConfig, GoingConcernEnv  # noqa: E402
from going_concern.prompting import extract_action  # noqa: E402

MAX_INPUT = 64_000
USAGE = __doc__.split("\n\n", 2)[2]


def load_state() -> dict:
    try:
        with open(STATE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"engine_version": ENGINE_VERSION, "weeks": [], "finished": False}


def save_state(state: dict) -> None:
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, STATE)


def rebuild(state: dict) -> GoingConcernEnv:
    with open(os.path.join(HOME, "firm.json")) as f:
        cfg = FirmConfig.from_json(f.read())
    env = GoingConcernEnv(record=False)
    env.reset(config=cfg)
    for week in state["weeks"]:
        if env.done:
            break
        env.step(week["action"])
    return env


def report(env: GoingConcernEnv, state: dict) -> str:
    text = env.observe_text()
    if env.done:
        why = env.sim.bankrupt_reason if env.sim.bankrupt else "the episode is over"
        return text + f"\n\nNo more weeks to play ({why})."
    if state["finished"]:
        return text + "\n\nYou ended play with `shop done`; the remaining weeks run with no decisions."
    return text + "\n\nSubmit this week's decisions with: shop act '<json>'"


def cmd_act(env: GoingConcernEnv, state: dict, raw: str) -> int:
    if env.done or state["finished"]:
        print("The episode is over; no more decisions are accepted.")
        return 1
    if raw == "-":
        raw = sys.stdin.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
        print(f"Action too long (over {MAX_INPUT} characters). Nothing was submitted.")
        return 2
    action = extract_action(raw)
    if not isinstance(action, dict):
        print("Could not read a JSON object from that. Nothing was submitted; the week has not "
              "advanced. Example: shop act '{\"orders\": [{\"supplier\": \"S1\", \"qty\": 100}]}'")
        return 2
    week = env.sim.week
    _, done, info = env.step(action)
    state["weeks"].append({"week": week, "action": action, "errors": info.get("errors", [])})
    save_state(state)
    errors = info.get("errors") or []
    if errors:
        print("Parts of the action were refused:\n" + "\n".join(f"- {e}" for e in errors) + "\n")
    print(report(env, state))
    return 0


def cmd_history(state: dict) -> int:
    if not state["weeks"]:
        print("No decisions submitted yet.")
    for w in state["weeks"]:
        line = f"week {w['week']}: {json.dumps(w['action'], separators=(',', ':'))}"
        if w["errors"]:
            line += "\n  refused: " + "; ".join(w["errors"])
        print(line)
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    cmd, args = argv[0], argv[1:]
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        if not os.path.exists(STATE):
            save_state(state)
        env = rebuild(state)
        if cmd == "status":
            if args == ["--json"]:
                print(json.dumps(env.observe(), indent=1))
            else:
                print(report(env, state))
            return 0
        if cmd == "act":
            if len(args) != 1:
                print("Usage: shop act '<json>'   (or: echo '<json>' | shop act -)")
                return 2
            return cmd_act(env, state, args[0])
        if cmd == "history":
            return cmd_history(state)
        if cmd == "done":
            if not state["finished"]:
                state["finished"] = True
                save_state(state)
            left = 0 if env.done else env.sim.cfg.weeks - env.sim.week
            print(f"Play ended at week {env.sim.week}. {left} remaining week(s) will run with no "
                  "decisions before the shop is scored.")
            return 0
    print(f"Unknown command {cmd!r}.\n\n{USAGE}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
