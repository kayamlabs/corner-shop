# Corner Shop

By [Kayam](https://kayam.ai).

One hundred small-business environments where an AI agent runs a shop for 13 simulated weeks, scored by a **going-concern reward** that resists the usual end-of-episode cheats.

Most business simulations score cash on the last day. Agents learn to game that: they stop paying suppliers, stop restocking, draw the credit line and fire-sell stock. The going-concern reward instead **freezes the firm at the end, keeps running it with scripted operators, and values what's left**. A firm stripped for cash scores badly.

In our experiments, the same starting model (Qwen3-1.7B, warm-started on an honest operator) was RL-trained with GRPO on each reward, then evaluated on 60 unseen firms (3 training seeds per reward, 180 episodes each):
- the **cash-trained** models ran the shop down at the end: they stopped restocking in 42% of episodes (12–97% across seeds) and often stopped paying suppliers. They doubled last-day cash but ended with a lower going-concern value than they started with;
- the **going-concern-trained** models kept restocking (2% stopped) and ended with a higher going-concern value: +$8.9k vs the cash-trained models (every seed ahead), and +$3.0k over the starting model.

(Engine 0.2. A small model with short training runs, validated against the simulator rather than real businesses. More at [kayam.ai](https://kayam.ai).)

![Held-out result](docs/heldout_result.png)

## Leaderboard
Firms 1–10, 3 runs each, via OpenRouter, 2026-11-25. Scores are multiples of the scripted honest operator on the same firm (1.0 = as good as honest play).

| Model | Going-concern (× honest) | Last-day cash (× honest) | Runs with going-concern < 0 | Bankrupt |
| ----- | ------------------------ | ------------------------ | --------------------------- | -------- |
| Scripted honest operator | 1.00 | 1.00 | 0% | 0% |
| GLM-4.7-Flash | −0.12 | 0.83 | 43% | 0% |
| Hermes-4-405B | −0.25 | 0.75 | 63% | 0% |
| DeepSeek-V4-Flash | −0.49 | 0.64 | 74% | 4% |
| GPT-5-mini | −0.70 | 0.56 | 83% | 0% |
| Llama-4-Maverick | −0.93 | 0.38 | 93% | 7% |
| Qwen3-30B-A3B | −1.09 | 0.17 | 100% | 10% |

Every model tested leaves the business worth less than the scripted operator does, and most leave it worth less than nothing once it keeps running. A last-day cash score sees only part of this. (21–30 completed runs per model; a few runs were lost to provider timeouts.)

## Frontier models scored on cash
We also told three frontier models (GPT-6.2-Sol, Claude Sonnet 5.5, Gemini 3.1 Pro) they would be scored on last-day cash, changing one sentence of the prompt. On 30 paired runs they ended with more cash in 27 and left a less valuable business in 25: fewer orders and payments in the last weeks, stock fire-sold, bills left unpaid. The score, not the model, decides whether the business survives. Details: firms 1–10, one run per firm and prompt; multiples of a scripted honest operator on the same firm.

| Model | Scored on | Going-concern (× honest) | Last-day cash (× honest) |
| ----- | --------- | ------------------------ | ------------------------ |
| GPT-6.2-Sol | going concern | 1.15 | 1.00 |
| GPT-6.2-Sol | last-day cash | 0.66 | 1.81 |
| Claude Sonnet 5.5 | going concern | 0.56 | 0.86 |
| Claude Sonnet 5.5 | last-day cash | 0.03 | 1.06 |
| Gemini 3.1 Pro | going concern | 0.90 | 1.02 |
| Gemini 3.1 Pro | last-day cash | 0.76 | 1.29 |

## Quickstart
```bash
pip install -e .
python examples/run_reference.py
```
```python
from going_concern import GoingConcernEnv, load_firm
from going_concern.rewards import going_concern, cash_reward

env = GoingConcernEnv()
obs = env.reset(config=load_firm(1))           # firms 1..100
obs, done, info = env.step({"orders": [{"supplier": "S1", "qty": 200}], "pay": [{"invoice": "INV-1"}]})
# ... one action per simulated week until done
print(going_concern(env.sim), cash_reward(env.sim))
```
- **Actions:** JSON covering prices, orders, payments, borrowing, hiring, liquidation, accepting offers and disputing invoices. See `going_concern/actions.py`.
- **Observations:** a structured dict, or text (`observe.render_text`, `observe.render_compact`).
- **Gymnasium-style wrapper:** `going_concern.gym_env.GoingConcernGym`.

## Trust checks included
- **Books reconciled three ways after every week:** operational state, a double-entry ledger and a money-flow log.
- **Goods conserved:** no negative cash or inventory.
- **Deterministic:** the same firm and actions always give the same history.

## What's not included
The firm generator, the harder tiers (2 and 3), and the hack ledger regression suite are part of the full Kayam packs.

## License
Apache-2.0. See `LICENSE`.
