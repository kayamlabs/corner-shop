"""Corner Shop as a verifiers v1 taskset.

The simulator plays the user: each assistant reply is parsed into a JSON action and advances one
simulated week, and the next week's state comes back as the user turn. The episode ends after the
horizon (13 weeks by default) or on bankruptcy.

The reward is the going-concern value: freeze the firm at the end of the episode, keep running it
with scripted operators, mark it to liquidation and average. Last-day cash is logged as a metric
next to it, so you can see when an agent buys cash at the end by running the business down."""
from __future__ import annotations

import functools
import re
from collections.abc import Iterator
from typing import Literal

import verifiers.v1 as vf

from .going_concern import GoingConcernEnv as Sim
from .going_concern import ReferenceOperator, load_firm, run_episode
from .going_concern.prompting import SYSTEM_PROMPT, extract_action, first_prompt, next_prompt
from .going_concern.rewards import cash_reward, equity_reward, going_concern

FIRMS = list(range(1, 101))
WIND_DOWN_WEEKS = 3  # the last weeks of the episode, where end-of-episode gaming shows up


@functools.lru_cache(maxsize=None)
def honest_baseline(firm: int, gc_rollouts: int, gc_weeks: int, truth_weeks: int = 0) -> dict[str, float]:
    """Scores of the scripted honest operator on the same firm: the yardstick for normalizing."""
    sim = run_episode(ReferenceOperator(), firm).sim
    out = {"cash": cash_reward(sim), "equity": equity_reward(sim),
           "going_concern": going_concern(sim, n=gc_rollouts, k_weeks=gc_weeks)}
    if truth_weeks:
        out["truth"] = going_concern(sim, n=gc_rollouts, k_weeks=truth_weeks)
    return out


def _obs(text: str, hide_horizon: bool) -> str:
    """Observation text, optionally without the episode length ("week 5" instead of "week 5 of 13")."""
    return re.sub(r"(— week \d+) of \d+", r"\1", text) if hide_horizon else text


def _as_dict(action) -> dict:
    return action if isinstance(action, dict) else {}


def _count(action, key: str) -> int:
    """Items in a list field of the action; anything else counts as 0."""
    value = _as_dict(action).get(key)
    return len(value) if isinstance(value, list) else 0


class CornerShopConfig(vf.TasksetConfig):
    firms: list[int] = FIRMS             # which of the 100 firms to include
    repeats: int = 1                     # copies of each firm in the dataset
    reward: Literal["going_concern", "cash", "equity"] = "going_concern"
    gc_rollouts: int = 16                # continuation rollouts per score
    gc_weeks: int = 13                   # weeks each continuation runs
    hide_horizon: bool = False           # don't show the agent how many weeks the episode lasts
    truth_weeks: int = 0                 # if > 0, also log going-concern value over this longer continuation
    normalize: bool = True               # score as a multiple of the honest operator on the same firm
    reward_scale: float = 1e-3           # dollars -> thousands of dollars (only when normalize is off)


class CornerShopData(vf.TaskData):
    info: dict
    """firm and repeat index: everything needed to rebuild the episode."""


class CornerShopTask(vf.Task[CornerShopData, vf.State, vf.TaskConfig]):
    pass


class CornerShopEnvConfig(vf.EnvConfig):
    operator: vf.AgentConfig = vf.AgentConfig(harness={"id": "null"})


class CornerShopEnv(vf.Env[CornerShopEnvConfig]):
    async def run(self, task, agents):
        info = task.data.info
        cfg = self.taskset.config
        env = Sim(record=False)
        env.reset(config=load_firm(info["firm"]))
        weeks = env.sim.cfg.weeks
        bad_actions = 0
        late_orders = late_payments = 0
        async with agents.operator.interaction(task) as interaction:
            segment = await interaction.turn()  # the prompt holds week 0; the model moves first
            while not segment.terminated:
                action = extract_action(segment.last_reply)
                if env.sim.week >= weeks - WIND_DOWN_WEEKS:
                    late_orders += _count(action, "orders")
                    late_payments += _count(action, "pay")
                _, done, step_info = env.step(action)
                bad_actions += bool(step_info.get("errors"))
                if done:
                    break
                segment = await interaction.turn(next_prompt(_obs(env.observe_text(), cfg.hide_horizon)))
        # Weeks the agent never played (turn or token limit, provider error) still happen: the shop
        # runs unattended, so stopping early can never dodge a loss.
        unattended = 0
        while not env.done:
            env.step({})
            unattended += 1
        trace = interaction.trace
        sim = env.sim
        scores = {"cash": cash_reward(sim), "equity": equity_reward(sim),
                  "going_concern": going_concern(sim, n=cfg.gc_rollouts, k_weeks=cfg.gc_weeks)}
        if cfg.truth_weeks:
            scores["truth"] = going_concern(sim, n=cfg.gc_rollouts, k_weeks=cfg.truth_weeks)
        base = honest_baseline(info["firm"], cfg.gc_rollouts, cfg.gc_weeks, cfg.truth_weeks)
        ratios = {k: scores[k] / base[k] if base[k] > 0 else 0.0 for k in scores}
        if cfg.normalize:
            trace.record_reward(cfg.reward, ratios[cfg.reward], 1.0)  # "truth" is a metric, never the reward
        else:
            trace.record_reward(cfg.reward, scores[cfg.reward] * cfg.reward_scale, 1.0)
        for k, v in scores.items():
            trace.record_metric(f"{k}_usd", float(v))
            trace.record_metric(f"{k}_vs_honest", float(ratios[k]))
        trace.record_metric("orders_last_3_weeks", float(late_orders))
        trace.record_metric("payments_last_3_weeks", float(late_payments))
        trace.record_metric("bankrupt", float(sim.bankrupt))
        trace.record_metric("weeks_played", float(sim.week - unattended))
        trace.record_metric("weeks_unattended", float(unattended))
        trace.record_metric("weeks_with_action_errors", float(bad_actions))
        trace.record_metric("liquidated_units", float(sum(s.liquidated for s in sim.skus.values())))
        trace.record_metric("overdue_invoices_at_end",
                            float(sum(i.overdue_weeks(sim.week) > 0 for i in sim.invoices)))
        trace.info["corner_shop"] = {**info, "bankrupt_reason": sim.bankrupt_reason,
                                     "violation": env.violation}


class CornerShopTaskset(vf.Taskset[CornerShopTask, CornerShopConfig]):
    def load(self) -> Iterator[CornerShopTask]:
        c = self.config
        for r in range(c.repeats):
            for firm in c.firms:
                env = Sim(record=False)
                env.reset(config=load_firm(firm))
                yield CornerShopTask(
                    CornerShopData(
                        name=f"firm{firm:02d}-r{r}",
                        prompt=first_prompt(_obs(env.observe_text(), c.hide_horizon)),
                        system_prompt=SYSTEM_PROMPT,
                        info={"firm": firm, "repeat": r, "weeks": env.sim.cfg.weeks},
                    ),
                    self.config.task,
                )
