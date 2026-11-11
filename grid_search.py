"""Grid search: every combination of noise level x rounds per match x seed.

Output (in tables/):
  grid/noise_<p>_rounds_<r>_seed_<s>.csv  one file per run (one row per generation)
  grid_all_runs.csv                       all runs together, long format (for plots)
  grid_summary.csv                        one row per run: last generation + mean of the last 100
"""
import csv
from itertools import product
from multiprocessing import Pool

import numpy as np

from main import TABLES_PATH, NOISE_LEVELS, run_ga, save_csv

SEEDS = range(10)
ROUNDS_LIST = [150, 1000]
LAST_GENS = 100  # generations averaged in the summary (a single generation is noisy)

GRID_PATH = TABLES_PATH / "grid"


def run_one(config):
    p_noise, rounds, seed = config
    history = run_ga(p_noise=p_noise, rounds=rounds, seed=seed)
    save_csv(history, GRID_PATH / f"noise_{p_noise}_rounds_{rounds}_seed_{seed}.csv")
    print(f"done: noise={p_noise} rounds={rounds} seed={seed}", flush=True)
    # add the configuration to every row so all runs can go in a single table
    return [{"p_noise": p_noise, "rounds": rounds, "seed": seed, **row} for row in history]


if __name__ == "__main__":
    GRID_PATH.mkdir(parents=True, exist_ok=True)
    configs = list(product(NOISE_LEVELS, ROUNDS_LIST, SEEDS))

    with Pool() as pool:  # runs are independent: one per CPU core
        results = pool.map(run_one, configs)

    all_rows = [row for run in results for row in run]
    save_csv(all_rows, TABLES_PATH / "grid_all_runs.csv")

    summary = []
    for run in results:
        last = dict(run[-1])
        last[f"mean_payoff_last{LAST_GENS}"] = float(np.mean([r["mean_payoff"] for r in run[-LAST_GENS:]]))
        summary.append(last)
    save_csv(summary, TABLES_PATH / "grid_summary.csv")

    # quick look: mean +- std over seeds of the payoff in the last generations
    print("\np_noise  rounds  payoff (last 100 gens, mean +- std over seeds)")
    for p_noise, rounds in product(NOISE_LEVELS, ROUNDS_LIST):
        vals = [s[f"mean_payoff_last{LAST_GENS}"] for s in summary
                if s["p_noise"] == p_noise and s["rounds"] == rounds]
        print(f"{p_noise:<8} {rounds:<7} {np.mean(vals):.3f} +- {np.std(vals):.3f}")
