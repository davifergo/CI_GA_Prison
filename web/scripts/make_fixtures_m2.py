"""Writes src/lib/model/__fixtures__/python_m2.json from main_memory2.py (memory 2).

Run from the repository root:  .venv/bin/python web/scripts/make_fixtures_m2.py
"""
import json
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.getcwd())
import main_memory2 as m2  # noqa: E402

OUT = os.path.join("web", "src", "lib", "model", "__fixtures__", "python_m2.json")


def g(s):
    """'ab | CC CD DC DD' or plain bits -> list of 18 ints."""
    return [int(ch) for ch in s if ch in "01"]


fx = {}
rnd = random.Random(5)
pairs = [[rnd.randint(0, 1) for _ in range(18)] for _ in range(120)]
pairs = [(pairs[i], pairs[i + 1]) for i in range(0, 120, 2)]
named = {"PAV2": "10|0110 1111 1111 0110", "PAV2D": "11|0111 1111 1111 0110",
         "GRIM1": "11|0111 0111 0111 0000", "GRIM1b": "11|0111 0111 0111 0001",
         "ALLD": "11|1111 1111 1111 1111"}
for a, b in [("PAV2", "PAV2"), ("ALLD", "PAV2"), ("PAV2D", "PAV2D"), ("GRIM1", "GRIM1"),
             ("GRIM1b", "GRIM1"), ("GRIM1b", "GRIM1b")]:
    pairs.append((g(named[a]), g(named[b])))
fx["pairs"] = []
for p in (0.0, 0.01, 0.05):
    G1 = np.array([a for a, _ in pairs]); G2 = np.array([b for _, b in pairs])
    f1, f2 = m2.expected_matches(G1, G2, 150, p)
    fx["pairs"].append({"p": p, "g1": ["".join(map(str, a)) for a, _ in pairs],
                        "g2": ["".join(map(str, b)) for _, b in pairs],
                        "f1": [float(x) for x in f1], "f2": [float(x) for x in f2]})

fx["classify"] = [["".join(map(str, gg)), m2.classify(gg)] for gg in
                  [g(named["PAV2"]), list(m2.TF2T)] +
                  [[m1[0], 1] + [m1[1 + s % 4] for s in range(16)] for m1 in m2.MEMORY1.values()]]

fx["runs"] = []
for seed, p, n_gen in ((100, 0.01, 500), (200, 0.05, 500), (0, 0.0, 120)):
    hist = m2.run_ga(seed, p, n_gen=n_gen)
    fx["runs"].append({"seed": seed, "p_noise": p,
                       "mean_payoff": [r["mean_payoff"] for r in hist],
                       "n_distinct": [r["n_distinct"] for r in hist],
                       "top_genome": [r["top_genome"] for r in hist],
                       "top_freq": [r["top_freq"] for r in hist]})
    print("run", seed, p, "done")

with open(OUT, "w") as f:
    json.dump(fx, f)
print("wrote", OUT)
