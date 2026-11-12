"""Iterated prisoner's dilemma: evolution of memory-1 strategies with a GA.

Runs N_RUNS independent GA runs for every noise level and writes, per noise level:
  results/memory1/history_noise_<p>.csv   one row per (run, generation): mean payoff,
                                  frequency of the named strategies and of all 32 genomes
  results/memory1/payoff_matrix_noise_<p>.csv   expected payoff per round of every pair of genomes
"""
import csv
import itertools
import os
import random
from collections import Counter

import numpy as np
from deap import base, creator, tools, algorithms

N_POP = 100
N_BITS = 5          # first action + response to CC, CD, DC, DD
N_GEN = 500
CXPB = 0.7          # uniform crossover
MUT_INDPB = 0.01    # bit-flip probability per bit
TOURN_SIZE = 3
ELITISM = 2
ROUNDS = 150        # rounds per match
NOISE_LEVELS = [0.0, 0.01, 0.05]
N_RUNS = 30
# Independent (non-paired) seeds: noise level k uses seeds 100*k ... 100*k + N_RUNS - 1
SEED_OFFSET = 100

# project root (the folder that contains src/ and results/), so the scripts can be run from anywhere
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results", "memory1")

# Actions: 0 = C, 1 = D.  PAYOFF[(my action, opponent's action)] = my payoff
T, R, P, S = 5, 3, 1, 0
PAYOFF = {(0, 0): R, (0, 1): S, (1, 0): T, (1, 1): P}

# Genome: (first action, after CC, after CD, after DC, after DD), own action first
NAMED = {
    (0, 0, 0, 0, 0): "ALLC",
    (1, 1, 1, 1, 1): "ALLD",
    (0, 0, 1, 0, 1): "TFT",
    (0, 0, 1, 1, 0): "PAVLOV",
    (0, 0, 1, 1, 1): "GRIM",
    (1, 0, 1, 0, 1): "STFT",    # suspicious tit-for-tat: TFT that starts with D
}
COLUMNS = list(NAMED.values()) + ["OTHER"]

# All 32 genomes; a genome's index is its bit string read as a binary number
GENOMES = list(itertools.product((0, 1), repeat=N_BITS))
GENOME_LABELS = ["g" + "".join(map(str, g)) for g in GENOMES]


def genome_index(genome):
    # Binary basis
    return int("".join(map(str, genome)), 2)


creator.create("FitnessMax", base.Fitness, weights=(1.0,))  # we maximise
creator.create("Individual", list, fitness=creator.FitnessMax)


def expected_match(s1, s2, rounds=ROUNDS, p_noise=0.0):
    """Exact expected average payoff per round of s1 and s2 playing `rounds` rounds.

    Each intended action is flipped with probability p_noise, and each strategy reacts
    to the actions actually played. The outcome of a round (a1, a2) is a 4-state Markov
    chain (state 2*a1 + a2 = CC, CD, DC, DD), so the expectation is computed exactly
    instead of sampling a noisy match.
    """
    def played(intended):  # distribution of the action actually played
        return np.array([1 - p_noise, p_noise]) if intended == 0 else np.array([p_noise, 1 - p_noise])

    pay1 = np.array([PAYOFF[(a1, a2)] for a1 in (0, 1) for a2 in (0, 1)], dtype=float)
    pay2 = np.array([PAYOFF[(a2, a1)] for a1 in (0, 1) for a2 in (0, 1)], dtype=float)
    trans = np.zeros((4, 4))
    for a1 in (0, 1):
        for a2 in (0, 1):
            nxt1, nxt2 = s1[1 + 2 * a1 + a2], s2[1 + 2 * a2 + a1]
            # trans[s] has the probability distribution of the next outcome given that the
            # current outcome is s (based on the strategies and noise)
            trans[2 * a1 + a2] = np.outer(played(nxt1), played(nxt2)).ravel()
    # probability distribution of the first outcome (first actions + noise)
    dist = np.outer(played(s1[0]), played(s2[0])).ravel()
    total1 = total2 = 0.0
    for _ in range(rounds):
        # expected payoff of this round: payoff of each outcome weighted by its probability
        total1 += dist @ pay1
        total2 += dist @ pay2
        # distribution of the next outcome (law of total probability):
        #   P(next = i) = sum_j P(next = i | current = j) * P(current = j)
        # Column i of trans holds P(next = i | current = j) for every j, so this is dist @ trans.
        # Markov property: with memory 1 the next outcome depends only on the current one.
        dist = dist @ trans
    return total1 / rounds, total2 / rounds


def payoff_matrix(p_noise, rounds=ROUNDS):
    """M[i, j] = expected payoff per round of genome i against genome j."""
    n = len(GENOMES)
    M = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):  # one match gives both M[i, j] and M[j, i]
            M[i, j], M[j, i] = expected_match(GENOMES[i], GENOMES[j], rounds, p_noise)
    return M


def evaluate(pop, M):
    """Round robin: every individual plays all the others (not itself).
    Fitness = average payoff per round (3 = full cooperation, 1 = full defection)."""
    idx = np.array([genome_index(ind) for ind in pop])
    counts = np.bincount(idx, minlength=len(GENOMES))
    total = M[idx] @ counts - M[idx, idx]   # remove the game against itself
    return total / (len(pop) - 1)


def run_ga(M, seed, n_pop=N_POP, n_gen=N_GEN, cxpb=CXPB, mut_indpb=MUT_INDPB,
           tourn_size=TOURN_SIZE, elitism=ELITISM):
    """Evolve one population with payoff matrix M. Returns one row per generation."""
    random.seed(seed)

    tb = base.Toolbox()
    tb.register("bit", random.randint, 0, 1)
    tb.register("individual", tools.initRepeat, creator.Individual, tb.bit, n=N_BITS)
    tb.register("population", tools.initRepeat, list, tb.individual)
    tb.register("mate", tools.cxUniform, indpb=0.5)  # indpb: prob. of swapping each bit
    tb.register("mutate", tools.mutFlipBit, indpb=mut_indpb)
    tb.register("select", tools.selTournament, tournsize=tourn_size)

    def evaluate_pop(pop):
        # coevolution: fitness depends on the population, so everyone is re-evaluated
        for ind, f in zip(pop, evaluate(pop, M)):
            ind.fitness.values = (f,)

    def record(gen, pop):
        named = Counter(NAMED.get(tuple(ind), "OTHER") for ind in pop)
        genomes = Counter(genome_index(ind) for ind in pop)
        row = {"seed": seed, "gen": gen,
               "mean_payoff": float(np.mean([ind.fitness.values[0] for ind in pop]))}
        row.update({name: named[name] / len(pop) for name in COLUMNS})
        row.update({lab: genomes[i] / len(pop) for i, lab in enumerate(GENOME_LABELS)})
        return row

    pop = tb.population(n=n_pop)
    evaluate_pop(pop)
    history = [record(0, pop)]
    for gen in range(1, n_gen + 1):
        elite = tb.clone(tools.selBest(pop, elitism))  # best of the previous generation
        # mutpb=1.0: every child goes through mutFlipBit, and mut_indpb decides each bit
        off = algorithms.varAnd(tb.select(pop, len(pop)), tb, cxpb=cxpb, mutpb=1.0)
        pop = elite + off[elitism:]
        evaluate_pop(pop)
        history.append(record(gen, pop))
    return history


def save_csv(rows, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def save_matrix(M, path):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["row_vs_col"] + GENOME_LABELS)
        for lab, row in zip(GENOME_LABELS, M):
            writer.writerow([lab] + [f"{v:.6f}" for v in row])


if __name__ == "__main__":
    os.makedirs(RESULTS_DIR, exist_ok=True)
    for k, p_noise in enumerate(NOISE_LEVELS):
        M = payoff_matrix(p_noise)
        save_matrix(M, os.path.join(RESULTS_DIR, f"payoff_matrix_noise_{p_noise}.csv"))
        rows = []
        for run in range(N_RUNS):
            seed = SEED_OFFSET * k + run
            rows += [{"run": run, **r} for r in run_ga(M, seed)]
        save_csv(rows, os.path.join(RESULTS_DIR, f"history_noise_{p_noise}.csv"))
        finals = [r for r in rows if r["gen"] == N_GEN]
        print(f"p_noise={p_noise}: median final mean payoff "
              f"{np.median([r['mean_payoff'] for r in finals]):.3f} over {N_RUNS} runs | "
              + ", ".join(f"{c} {np.mean([r[c] for r in finals]):.0%}" for c in COLUMNS))
