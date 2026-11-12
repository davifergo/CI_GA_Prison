"""Robustness check for the Limitations section (not part of the core experiment).
Same GA and exact payoffs as main.py, 10 runs per configuration:
  - longer matches (1000 rounds) at the three core noise levels
  - higher noise levels (0.1, 0.25) at 150 rounds
Run from the project root:  python src/robustness.py   (a few minutes)
Writes results/memory1/robustness.txt
"""
import os
from multiprocessing import Pool
import numpy as np
import main as M

CONFIGS = [(p, 1000) for p in (0.0, 0.01, 0.05)] + [(p, 150) for p in (0.1, 0.25)]
N = 10

def one(args):
    p, rounds, seed, Mx = args
    h = M.run_ga(Mx, seed)[-100:]
    return {k: np.mean([r[k] for r in h]) for k in ["mean_payoff"] + M.COLUMNS}

if __name__ == "__main__":
    lines = []
    for p, rounds in CONFIGS:
        Mx = M.payoff_matrix(p, rounds)
        with Pool() as pool:
            res = pool.map(one, [(p, rounds, 1000 + s, Mx) for s in range(N)])
        pay = [r["mean_payoff"] for r in res]
        dom = {c: sum(r[c] > 0.5 for r in res) for c in M.COLUMNS}
        lines.append(f"p_noise={p:<5} rounds={rounds:<5} median payoff {np.median(pay):.3f} "
                     f"[{min(pay):.3f}, {max(pay):.3f}]  dominant: "
                     + ", ".join(f"{c} {n}/{N}" for c, n in dom.items() if n))
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(M.RESULTS_DIR, "robustness.txt"), "w") as f:
        f.write(text + "\n")
