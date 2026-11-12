"""Writes src/lib/model/__fixtures__/python.json from the reference Python model (main.py).

The web tests compare the TypeScript port against these values bit for bit, so the site
uses exactly the model of the report. Run from the repository root:

    .venv/bin/python web/scripts/make_fixtures.py
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.getcwd())
import main as m  # noqa: E402

OUT = os.path.join("web", "src", "lib", "model", "__fixtures__", "python.json")
N_GEN = 500

fx = {"matrices": {}, "runs": [], "rng": {}}

for k, p in enumerate(m.NOISE_LEVELS):
    M = m.payoff_matrix(p)
    fx["matrices"][str(p)] = [[float(v) for v in row] for row in M]
    seed = m.SEED_OFFSET * k  # run 0 of this noise level, as in the report
    hist = m.run_ga(M, seed, n_gen=N_GEN)
    fx["runs"].append({
        "p_noise": p, "seed": seed,
        "mean_payoff": [r["mean_payoff"] for r in hist],
        "final_genomes": [r[lab] for lab in m.GENOME_LABELS for r in [hist[-1]]],
    })

# a non-default configuration, to check the parameters are wired the same way
M = m.payoff_matrix(0.01)
hist = m.run_ga(M, 7, n_pop=37, n_gen=60, cxpb=0.5, mut_indpb=0.05, tourn_size=5, elitism=3)
fx["runs"].append({"p_noise": 0.01, "seed": 7, "n_pop": 37, "cxpb": 0.5, "mut_indpb": 0.05,
                   "tourn_size": 5, "elitism": 3,
                   "mean_payoff": [r["mean_payoff"] for r in hist],
                   "final_genomes": [hist[-1][lab] for lab in m.GENOME_LABELS]})

# raw stream of Python's Mersenne Twister
random.seed(12345)
fx["rng"] = {"seed": 12345,
             "random": [random.random() for _ in range(8)],
             "randint01": [random.randint(0, 1) for _ in range(16)],
             "choice100": [random.randrange(100) for _ in range(16)],
             "choice37": [random.randrange(37) for _ in range(16)]}

# fused multiply-add reference values (random, and close to rounding ties)
rnd = random.Random(3)
cases = []
for _ in range(3000):
    a, b = rnd.random() * 5, rnd.random()
    c = rnd.choice([rnd.random(), -a * b, -(a * b) * (1 + 2 ** -52), a * b * 2 ** -30, 0.0])
    cases.append([a, b, c, math.fma(a, b, c)])
fx["fma"] = cases

with open(OUT, "w") as f:
    json.dump(fx, f)
print("wrote", OUT)
