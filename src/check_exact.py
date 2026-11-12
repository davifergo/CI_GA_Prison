"""Check the exact expected-payoff computation against an independent Monte Carlo simulator.

Run from the project root:  python src/check_exact.py   (about 1 minute)
Writes results/check_exact.txt

- Without noise a match is deterministic, so the exact payoff must equal one simulated match.
- With noise, the exact payoff must agree with the mean of N_SIM simulated matches up to
  Monte Carlo error; we report the difference in standard-error units (z), which should
  mostly lie in [-2, 2].
"""
import os
import random

import numpy as np

import main as m1
import main_memory2 as m2

PAY = {(0, 0): 3, (0, 1): 0, (1, 0): 5, (1, 1): 1}
ROUNDS = 150
N_SIM = 20_000
rng = random.Random(2026)
lines = []  # printed and saved to results/check_exact.txt


def out(text):
    print(text)
    lines.append(text)


def flip(a, p):
    return 1 - a if rng.random() < p else a


def sim_m1(s1, s2, p):
    """One match between two memory-1 genomes; returns player 1's mean payoff per round."""
    a, b = flip(s1[0], p), flip(s2[0], p)
    total = 0
    for _ in range(ROUNDS):
        total += PAY[(a, b)]
        a, b = flip(s1[1 + 2 * a + b], p), flip(s2[1 + 2 * b + a], p)
    return total / ROUNDS


def sim_m2(g1, g2, p):
    """One match between two memory-2 genomes; returns player 1's mean payoff per round."""
    hist, total = [], 0
    for r in range(ROUNDS):
        if r < 2:
            i1, i2 = g1[r], g2[r]
        else:
            (ap, bp), (ac, bc) = hist[-2], hist[-1]
            i1 = g1[2 + 4 * (2 * ap + bp) + (2 * ac + bc)]
            i2 = g2[2 + 4 * (2 * bp + ap) + (2 * bc + ac)]
        a, b = flip(i1, p), flip(i2, p)
        hist.append((a, b))
        total += PAY[(a, b)]
    return total / ROUNDS


def z_scores(exact, sims):
    sims = np.asarray(sims)
    # Division by np.sqrt(sims.shape[1])) to correct the normalization of a mean.
    return (sims.mean(axis=1) - exact) / (sims.std(axis=1) / np.sqrt(sims.shape[1]))


if __name__ == "__main__":
    # ---- memory 1: all 1024 pairs without noise, 6 pairs with noise ----
    M0 = m1.payoff_matrix(0.0)
    d = max(abs(M0[i, j] - sim_m1(m1.GENOMES[i], m1.GENOMES[j], 0.0))
            for i in range(32) for j in range(32))
    out(f"memory 1, p_noise=0: max |exact - simulated| over 1024 pairs = {d:.2e}")
    pairs = [(5, 5), (5, 7), (6, 31), (7, 7), (0, 6), (21, 13)]
    for p in (0.01, 0.05):
        M = m1.payoff_matrix(p)
        sims = [[sim_m1(m1.GENOMES[i], m1.GENOMES[j], p) for _ in range(N_SIM)] for i, j in pairs]
        exact = np.array([M[i, j] for i, j in pairs])
        out(f"memory 1, p_noise={p}: z = {np.round(z_scores(exact, sims), 1)}")

    # ---- memory 2: 300 random pairs without noise, 8 random pairs with noise ----
    G1 = np.array([[rng.randint(0, 1) for _ in range(18)] for _ in range(300)])
    G2 = np.array([[rng.randint(0, 1) for _ in range(18)] for _ in range(300)])
    f1, _ = m2.expected_matches(G1, G2, ROUNDS, 0.0)
    d = max(abs(f1[k] - sim_m2(G1[k], G2[k], 0.0)) for k in range(300))
    out(f"memory 2, p_noise=0: max |exact - simulated| over 300 random pairs = {d:.2e}")
    for p in (0.01, 0.05):
        f1, _ = m2.expected_matches(G1[:8], G2[:8], ROUNDS, p)
        sims = [[sim_m2(G1[k], G2[k], p) for _ in range(N_SIM)] for k in range(8)]
        out(f"memory 2, p_noise={p}: z = {np.round(z_scores(f1, sims), 1)}")

    with open(os.path.join(m1.ROOT, "results", "check_exact.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
