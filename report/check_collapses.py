"""Why do some memory-2 runs without noise have a low payoff?

Run from the project root:  python report/check_collapses.py > report/check_collapses.txt
(about 30 s)

In some runs without noise the mean payoff suddenly falls from about 2.9 to about 1 (a
"collapse") and later recovers. The history CSV only stores a summary of each generation
(mean payoff, most frequent genome, ...), not the whole population, so it cannot tell us
why. Since the runs are reproducible from their seed, we rerun four of them with the same
code as main_memory2.run_ga and keep the whole population in the 25 generations before
and the 7 generations after each collapse. Then, for every generation, we look at who
plays against whom and what each one obtains.

Output: one table per collapse, one row per generation. Example row:

 gen  payoff (csv)    nonretal exploit mutualD  top                      share | grown
 177  2.712 (2.712)    0.00    0.01    0.01  11|0111011000110110 0.07 | 11|0111010001111110 +3 fit 2.89 (vs top 2.99/0.52, ALLD gets 2.97)

  gen       generation
  payoff    mean payoff of the population; in brackets the value saved in the CSV. They
            must be equal, which shows that the rerun is the same run.
  nonretal  share of the population that does NOT retaliate: ALLD obtains 4 or more against
            it (5 = it always cooperates against ALLD). 0.00 means that ALLD cannot exploit
            anyone.
  exploit   share of all the matches in the population where one player exploits the
            other (one gets more than 3.2 and the other less than 2.8).
  mutualD   share of all the matches where both players get less than 2, i.e. they
            mostly defect against each other (DD gives 1 per round).
  top       most frequent genome (first two moves | 16 responses) and its share.
  grown     genome that gained most copies since the previous generation:
              +3          number of copies gained
              fit 2.89    its fitness (mean payoff against the population)
              vs top a/b  it obtains a against the top genome, which obtains b against it
              ALLD gets   payoff of ALLD against it (how exploitable it is by ALLD)

Reading the example: at generation 177 almost no one plays DD (mutualD 0.01) and ALLD
cannot exploit anyone (nonretal 0.00), but a new genome appears that obtains 2.99 against
the top genome while the top genome obtains only 0.52 against it: a particular mutant
exploits the residents. In the next rows mutualD grows to about 0.9 and the payoff falls
to about 1: the population ends up defecting.
"""
import csv
import os
import random
import sys
from collections import Counter

import numpy as np
from deap import algorithms, base, creator, tools

sys.path.insert(0, os.getcwd())
import main_memory2 as m    # noqa: E402

ALLD = (1,) * m.N_BITS  # 18 bits set to 1 = always defect
# Collapses found in history_noise_0.0.csv: (seed, first generation with payoff < 2.6)
CASES = [(5, 178), (5, 253), (17, 456), (28, 174)]


def snapshots(seed, gens):
    """Rerun one run without noise (same steps as main_memory2.run_ga) and return
    {generation: [(genome, fitness) for each individual]} for the generations in gens."""
    random.seed(seed)  # same seed -> same random numbers -> same run
    cache = {}
    tb = base.Toolbox()
    tb.register("bit", random.randint, 0, 1)
    tb.register("individual", tools.initRepeat, creator.Individual, tb.bit, n=m.N_BITS)
    tb.register("population", tools.initRepeat, list, tb.individual)
    tb.register("mate", tools.cxUniform, indpb=0.5)
    tb.register("mutate", tools.mutFlipBit, indpb=m.MUT_INDPB)
    tb.register("select", tools.selTournament, tournsize=m.TOURN_SIZE)

    def evaluate_pop(pop):
        if len(cache) > m.MAX_CACHE:
            cache.clear()
        for ind, f in zip(pop, m.evaluate(pop, cache, m.ROUNDS, 0.0)):
            ind.fitness.values = (f,)

    pop = tb.population(n=m.N_POP)
    evaluate_pop(pop)
    snaps = {}
    for gen in range(1, max(gens) + 1):
        elite = tb.clone(tools.selBest(pop, m.ELITISM))
        off = algorithms.varAnd(tb.select(pop, len(pop)), tb, cxpb=m.CXPB, mutpb=1.0)
        pop = elite + off[m.ELITISM:]
        evaluate_pop(pop)
        if gen in gens:  # keep a copy of the population of this generation
            snaps[gen] = [(tuple(ind), ind.fitness.values[0]) for ind in pop]
    return snaps


def pay(A, B):
    """Exact payoffs (no noise) of the matches A[i] vs B[i].
    Returns two arrays: what A[i] obtains and what B[i] obtains."""
    return m.expected_matches(np.array(A), np.array(B), m.ROUNDS, 0.0)


def name(g):
    """Genome as text: first two moves | 16 responses, e.g. 11|0111011000110110."""
    return "".join(map(str, g[:2])) + "|" + "".join(map(str, g[2:]))


# Mean payoff of every (seed, generation) saved by main_memory2.py, to compare with the rerun
csv_payoff = {(int(r["seed"]), int(r["gen"])): float(r["mean_payoff"])
              for r in csv.DictReader(open(os.path.join(m.RESULTS_DIR, "history_noise_0.0.csv")))}

for seed, g0 in CASES:
    snaps = snapshots(seed, set(range(g0 - 25, g0 + 8)))
    print(f"\n== seed {seed}, collapse at generation {g0}")
    print(" gen  payoff (csv)    nonretal exploit mutualD  top                      share | grown")
    prev = None  # copies of each genome in the previous generation
    for gen in sorted(snaps):
        pop = [g for g, _ in snaps[gen]]
        fit = np.array([f for _, f in snaps[gen]])
        cnt = Counter(pop)       # genome -> number of copies
        uniq = list(cnt)         # distinct genomes
        w = np.array([cnt[u] for u in uniq], float)  # copies of each distinct genome

        # nonretal: share of individuals against which ALLD obtains 4 or more
        alld, _ = pay([ALLD] * len(uniq), uniq)
        nonretal = w[alld >= 4].sum() / w.sum()

        # Payoffs of every pair of distinct genomes: f1[i, j] = what uniq[i] obtains
        # against uniq[j], f2[i, j] = what uniq[j] obtains against uniq[i].
        I, J = np.meshgrid(range(len(uniq)), range(len(uniq)), indexing="ij")
        f1, f2 = pay([uniq[i] for i in I.ravel()], [uniq[j] for j in J.ravel()])
        f1, f2 = f1.reshape(I.shape), f2.reshape(I.shape)
        # W[i, j] = number of matches between an individual with uniq[i] and one with
        # uniq[j] (copies x copies; an individual does not play itself, hence - diag(w)).
        # Dividing by W.sum() gives shares of all the matches played in the generation.
        W = np.outer(w, w) - np.diag(w)
        exploit = W[(f1 > 3.2) & (f2 < 2.8)].sum() / W.sum()
        mutual_d = W[(f1 < 2) & (f2 < 2)].sum() / W.sum()

        top, top_count = cnt.most_common(1)[0]

        # grown: the genome that gained most copies since the previous generation
        grown = ""
        if prev:
            gain = {u: cnt[u] - prev.get(u, 0) for u in cnt}
            u = max(gain, key=gain.get)
            fu = fit[[i for i, g in enumerate(pop) if g == u]].mean()
            ut, tu = pay([u], [top])  # u against the top genome, and the reverse
            au, _ = pay([ALLD], [u])  # ALLD against u
            grown = (f"{name(u)} +{gain[u]} fit {fu:.2f} "
                     f"(vs top {ut[0]:.2f}/{tu[0]:.2f}, ALLD gets {au[0]:.2f})")
        print(f" {gen:3d}  {fit.mean():.3f} ({csv_payoff[(seed, gen)]:.3f})  {nonretal:6.2f} "
              f"{exploit:7.2f} {mutual_d:7.2f}  {name(top)} {top_count / len(pop):.2f} | {grown}")
        prev = cnt
