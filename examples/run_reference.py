"""Run the reference operator and an end-game cheater on all 10 firms; compare cash vs going-concern."""
from going_concern import EndgameExploiter, ReferenceOperator, run_episode
from going_concern.rewards import cash_reward, going_concern

for i in range(1, 11):
    ref, cheat = run_episode(ReferenceOperator(), i).sim, run_episode(EndgameExploiter(), i).sim
    print(f"firm {i:2d}  cash: honest ${cash_reward(ref):>8,.0f} cheater ${cash_reward(cheat):>8,.0f}   "
          f"going-concern: honest ${going_concern(ref):>8,.0f} cheater ${going_concern(cheat):>8,.0f}")
