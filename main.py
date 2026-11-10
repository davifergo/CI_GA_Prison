import csv
import random
from collections import Counter

import numpy as np
from deap import base, creator, tools, algorithms

SEED = 42

N_POP = 100
N_BITS = 5          # first action + response to CC, CD, DC, DD
N_GEN = 500
CXPB = 0.7          # uniform crossover
MUT_INDPB = 0.01    # bit-flip probability per bit
TOURN_SIZE = 3
ELITISM = 2
ROUNDS = 150        # rounds per match
NOISE_LEVELS = [0.0, 0.01, 0.05]

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
}
COLUMNS = list(NAMED.values()) + ["OTHER"]

creator.create("FitnessMax", base.Fitness, weights=(1.0,))  # we maximise
creator.create("Individual", list, fitness=creator.FitnessMax)


def noisy(action, p_noise):
    """Flip the intended action with probability p_noise."""
    return 1 - action if random.random() < p_noise else action


def play_match(s1, s2, rounds=ROUNDS, p_noise=0.0):
    """Average payoff per round of s1 and s2 playing `rounds` rounds."""
    a1, a2 = s1[0], s2[0]  # intended first actions
    total1 = total2 = 0
    for _ in range(rounds):
        a1, a2 = noisy(a1, p_noise), noisy(a2, p_noise)  # actions actually played
        total1 += PAYOFF[(a1, a2)]
        total2 += PAYOFF[(a2, a1)]
        # next action: look up the outcome (own, opponent) -> index 1..4 = CC, CD, DC, DD
        a1, a2 = s1[1 + 2 * a1 + a2], s2[1 + 2 * a2 + a1]
    return total1 / rounds, total2 / rounds


def evaluate(pop, rounds=ROUNDS, p_noise=0.0):
    """Round robin: every individual plays all the others.
    Fitness = average payoff per round (3 = full cooperation, 1 = full defection)."""
    strategies = [tuple(ind) for ind in pop]
    cache = {}  # only 32 strategies exist: play each pair of strategies once per generation
    fitness = np.zeros(len(pop))
    for i in range(len(pop)):
        for j in range(i + 1, len(pop)):
            pair = (strategies[i], strategies[j])
            if pair not in cache:
                cache[pair] = play_match(*pair, rounds, p_noise)
            f_i, f_j = cache[pair]
            fitness[i] += f_i
            fitness[j] += f_j
    return fitness / (len(pop) - 1)


def run_ga(p_noise=0.0, seed=SEED, n_pop=N_POP, n_gen=N_GEN, cxpb=CXPB,
           mut_indpb=MUT_INDPB, tourn_size=TOURN_SIZE, elitism=ELITISM, rounds=ROUNDS):
    """Evolve the population and return, for each generation, the mean payoff
    and the frequency of the named strategies."""
    random.seed(seed)

    tb = base.Toolbox()
    tb.register("bit", random.randint, 0, 1)
    tb.register("individual", tools.initRepeat, creator.Individual, tb.bit, n=N_BITS)
    tb.register("population", tools.initRepeat, list, tb.individual)
    tb.register("evaluate", evaluate, rounds=rounds, p_noise=p_noise)
    tb.register("mate", tools.cxUniform, indpb=0.5)  # indpb: prob. of swapping each bit
    tb.register("mutate", tools.mutFlipBit, indpb=mut_indpb)
    tb.register("select", tools.selTournament, tournsize=tourn_size)

    def evaluate_pop(pop):
        # coevolution: fitness depends on the population, so everyone is re-evaluated
        for ind, f in zip(pop, tb.evaluate(pop)):
            ind.fitness.values = (f,)

    def record(gen, pop):
        counts = Counter(NAMED.get(tuple(ind), "OTHER") for ind in pop)
        row = {"gen": gen,
               "mean_payoff": float(np.mean([ind.fitness.values[0] for ind in pop]))}
        row.update({name: counts[name] / len(pop) for name in COLUMNS})
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


def save_csv(history, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=history[0].keys())
        writer.writeheader()
        writer.writerows(history)


if __name__ == "__main__":
    for p_noise in NOISE_LEVELS:
        history = run_ga(p_noise=p_noise)
        save_csv(history, f"history_noise_{p_noise}.csv")
        last = history[-1]
        print(f"p_noise={p_noise}: mean payoff {last['mean_payoff']:.3f} | "
              + ", ".join(f"{name} {last[name]:.0%}" for name in COLUMNS))
