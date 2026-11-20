# Corner Shop

Ten small-business environments where an AI agent runs a shop for 13 simulated weeks, scored by a **going-concern reward** that resists the usual end-of-episode cheats.

Most business simulations score cash on the last day. Agents learn to game that: they stop paying suppliers, stop restocking, draw the credit line and fire-sell stock. The going-concern reward instead **freezes the firm at the end, keeps running it with scripted operators, and values what's left**. A firm stripped for cash scores badly.

In our experiments, the same honest starting model (Qwen3-1.7B) was RL-trained on each reward, then evaluated on unseen firms:
- the **cash-trained** models learned to stop paying suppliers (74% of firms), and firm value fell by $5.8k;
- the **going-concern-trained** models improved the business (+$3.1k) and kept restocking.

(3 seeds per reward, 60 held-out firms. This is a small model with short training runs, validated against the simulator rather than real businesses.)

![Held-out result](docs/heldout_result.png)

## Quickstart
```bash
pip install -e .
python examples/run_reference.py
```
```python
from going_concern import GoingConcernEnv, load_firm
from going_concern.rewards import going_concern, cash_reward

env = GoingConcernEnv()
obs = env.reset(config=load_firm(1))           # firms 1..10
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
The firm generator, the harder tiers (2 and 3), and the hack ledger regression suite are part of the full Going Concern packs.

## License
Apache-2.0. See `LICENSE`.
