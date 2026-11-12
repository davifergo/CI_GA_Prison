"""Iterated prisoner's dilemma: evolution of memory-2 strategies with a GA.

Genome (18 bits, 0 = C, 1 = D):
  bit 0        action in round 1
  bit 1        action in round 2 (unconditional: "2 bits for the first two actions")
  bits 2..17   action after the last two outcomes: bit 2 + 4*o_prev + o_cur,
               where an outcome is o = 2*own + opponent (0 = CC, 1 = CD, 2 = DC, 3 = DD)

There are 2^18 = 262144 genomes, so the full payoff matrix (~550 GB) cannot be
precomputed as in main.py: the expected payoff of a pair is computed only when the pair
appears in the population, and it is cached for the rest of the run.

Runs N_RUNS independent GA runs for every noise level and writes, per noise level:
  results/memory2/history_noise_<p>.csv   one row per (run, generation)
"""
import csv
import os
import random
from collections import Counter

import numpy as np
from deap import base, creator, tools, algorithms

# ---------------------------------------------------------------- parameters
N_POP = 100
N_BITS = 18         # 2 first actions + response to the 16 pairs of last two outcomes
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
MAX_CACHE = 2_000_000  # cached pairs per run before the cache is emptied (memory limit)

# project root (the folder that contains src/ and results/), so the scripts can be run from anywhere
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results", "memory2")

# ---------------------------------------------------------------- game
# Actions: 0 = C, 1 = D.  An outcome is o = 2*a1 + a2, so o = 0, 1, 2, 3 = CC, CD, DC, DD
# (written from player 1's point of view: own action first).
T, R, P, S = 5, 3, 1, 0
PAY1 = np.array([R, S, T, P], dtype=float)  # payoff of player 1 for CC, CD, DC, DD
PAY2 = np.array([R, T, S, P], dtype=float)  # payoff of player 2 for the same outcomes

# The same outcome seen by the other player: CC and DD do not change, CD <-> DC
# (if I see "I cooperated, you defected" = CD, you see "I defected, you cooperated" = DC).
SWAP = [0, 2, 1, 3]
# A state is the pair of the last two outcomes, encoded as s = 4*o_prev + o_cur (0..15).
# STATE_SWAP[s] = the same state seen by player 2: both outcomes are swapped.
# Example: s = 4*1 + 2 = 6 (player 1 saw CD then DC) -> player 2 saw DC then CD
#          -> 4*2 + 1 = 9, so STATE_SWAP[6] = 9.
STATE_SWAP = np.array([4 * SWAP[s // 4] + SWAP[s % 4] for s in range(16)])

# ---------------------------------------------------------------- named strategies
# Memory-1 strategies (first action, after CC, CD, DC, DD). A memory-2 genome "behaves
# like" one of them if it has the same first action and, from round 3 on, only looks at
# the last outcome (the round-2 bit is ignored).
MEMORY1 = {
    "ALLC": (0, 0, 0, 0, 0),
    "ALLD": (1, 1, 1, 1, 1),
    "TFT": (0, 0, 1, 0, 1),
    "PAVLOV": (0, 0, 1, 1, 0),
    "GRIM": (0, 0, 1, 1, 1),
    "STFT": (1, 0, 1, 0, 1),
}
# Tit-for-two-tats: cooperates unless the opponent defected in both of the last two rounds.
# The opponent's action is the last bit of each outcome (o % 2 == 1 means it defected), so
# the 16 entries are D only when both o_prev and o_cur are odd (CD or DD).
TF2T = (0, 0) + tuple(int(o_prev % 2 == 1 and o_cur % 2 == 1)
                      for o_prev in range(4) for o_cur in range(4))
COLUMNS = list(MEMORY1) + ["TF2T", "OTHER"]

# Exponents used to turn a genome index (an int) back into its 18 bits; see evaluate().
# SHIFTS = [17, 16, ..., 1, 0]: the first bit of the genome is the most significant one.
SHIFTS = np.arange(N_BITS - 1, -1, -1)

# DEAP classes: an individual is a list of bits with a fitness that we maximise
# (main.py defines the same classes; the check avoids a warning when both are imported)
if not hasattr(creator, "Individual"):
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMax)


def genome_index(genome):
    """The 18 bits read as a binary number, e.g. [0, ..., 1, 0, 1] -> 5.
    Used as a compact, hashable key for the cache."""
    return int("".join(map(str, genome)), 2)


def classify(genome):
    """Name of the strategy the genome behaves like, or "OTHER"."""
    g = tuple(genome)
    if g == TF2T:
        return "TF2T"
    for name, m1 in MEMORY1.items():
        # same first action, and for every state s the answer depends only on the
        # current outcome s % 4, exactly as in the memory-1 strategy
        if g[0] == m1[0] and all(g[2 + s] == m1[1 + s % 4] for s in range(16)):
            return name
    return "OTHER"


# ---------------------------------------------------------------- expected payoff of a match
def expected_matches(G1, G2, rounds=ROUNDS, p_noise=0.0):
    """Exact expected average payoff per round for a batch of B pairs of genomes.
    G1, G2: (B, 18) arrays of bits; row b is the pair (G1[b], G2[b]).
    Returns two arrays of length B (payoff of player 1 and of player 2).

    Each intended action is flipped with probability p_noise. With memory 2 the state of
    the match is the pair (previous outcome, current outcome): a 16-state Markov chain.
    All B pairs are computed at the same time with numpy (the first axis is always b).
    """
    def p_defect(intended):
        # probability that the action actually played is D: 1 - p_noise if D was
        # intended, p_noise if C was intended (works element-wise on whole arrays)
        return np.where(intended == 1, 1 - p_noise, p_noise)

    def outcome_dist(q1, q2):
        # q1, q2 = probability that each player plays D (the two players' noise is
        # independent). Returns the probability of CC, CD, DC, DD in a new last axis.
        # If we had 0, in p_defect we transformed it into p_noise, this is the reason that we
        # want them to be 1-p_noise when it matches the result or p_noise when not.
        # Thus, in CC, we want to do 1-q1 and 1-q2 to have the 0s as 1-p_noise in both players. With the other combinations
        # we do the same.
        return np.stack([(1 - q1) * (1 - q2), (1 - q1) * q2, q1 * (1 - q2), q1 * q2], axis=-1)

    B = len(G1)
    d1 = outcome_dist(p_defect(G1[:, 0]), p_defect(G2[:, 0]))  # (B, 4) outcome of round 1
    d2 = outcome_dist(p_defect(G1[:, 1]), p_defect(G2[:, 1]))  # (B, 4) outcome of round 2
    # nxt[b, s, o] = probability that the next outcome is o when the current state is s.
    # G1[:, 2:] are player 1's 16 answers in state order. Player 2 sees state s as
    # STATE_SWAP[s], so its answer is bit 2 + STATE_SWAP[s]: G2[:, 2 + STATE_SWAP] picks
    # those 16 bits, already reordered to player 1's state order. Result: (B, 16, 4).
    nxt = outcome_dist(p_defect(G1[:, 2:]), p_defect(G2[:, 2 + STATE_SWAP]))

    # round 1: expected payoff = probability of each outcome times its payoff
    total1, total2 = d1 @ PAY1, d1 @ PAY2
    # state after round 2 = (o_prev, o_cur) = (round 1, round 2). The first two actions do
    # not depend on anything, so P(o1, o2) = P(o1) * P(o2): an outer product per pair,
    # (B, 4, 1) * (B, 1, 4) -> (B, 4, 4), flattened to (B, 16) with index 4*o_prev + o_cur.
    dist = (d1[:, :, None] * d2[:, None, :]).reshape(B, 16)
    for _ in range(rounds - 1):  # rounds 2 .. rounds
        # distribution of the current outcome: view dist as (B, o_prev, o_cur) and add up
        # over o_prev. Expected payoff of this round = that distribution times the payoffs.
        cur = dist.reshape(B, 4, 4).sum(axis=1)
        total1 += cur @ PAY1
        total2 += cur @ PAY2
        # next state (o_cur, o_next), law of total probability:
        #   P(o_cur, o_next) = sum_{o_prev} P(o_prev, o_cur) * P(o_next | o_prev, o_cur)
        # dist[:, :, None] * nxt multiplies P(state) by P(o_next | state): (B, 16, 4),
        # seen as (B, o_prev, o_cur, o_next); adding up over o_prev leaves (B, o_cur, o_next),
        # which flattened is the new state index 4*o_cur + o_next.
        joint = (dist[:, :, None] * nxt).reshape(B, 4, 4, 4)
        dist = joint.sum(axis=1).reshape(B, 16)
    return total1 / rounds, total2 / rounds


# ---------------------------------------------------------------- fitness
def evaluate(pop, cache, rounds=ROUNDS, p_noise=0.0):
    """Round robin: every individual plays all the others (not itself).
    Fitness = average payoff per round (3 = full cooperation, 1 = full defection).
    cache[(u, v)] = expected payoff of genome u against genome v (u, v = genome indices)."""
    keys = [genome_index(ind) for ind in pop]  # genome of each individual, as an int
    uniq = sorted(set(keys))                    # distinct genomes in the population
    # pairs of distinct genomes (u <= v, including u against itself) not computed yet
    missing = [(u, v) for a, u in enumerate(uniq) for v in uniq[a:] if (u, v) not in cache]
    if missing:
        # Turn every genome index back into its 18 bits, for all the pairs at once:
        #   np.array(missing)        (m, 2)      the two genome indices of each pair
        #   [:, :, None]             (m, 2, 1)   room for a third axis
        #   >> SHIFTS                (m, 2, 18)  index shifted right by 17, 16, ..., 0
        #   & 1                      (m, 2, 18)  keep only the last bit of each shift
        # Shifting right by k drops the last k bits, so "(x >> k) & 1" is the bit of x
        # with weight 2^k. Example with 3 bits, x = 5 = 101: 5>>2 = 1 -> 1, 5>>1 = 2 = 10
        # -> 0, 5>>0 = 5 = 101 -> 1, so we get back [1, 0, 1] (same order as genome_index).
        bits = (np.array(missing)[:, :, None] >> SHIFTS) & 1
        # Expected matches for all the m missing pairs
        f1, f2 = expected_matches(bits[:, 0], bits[:, 1], rounds, p_noise)
        for (u, v), x, y in zip(missing, f1, f2):  # one match gives both directions
            cache[(u, v)], cache[(v, u)] = float(x), float(y)

    # M[a, b] = payoff of genome uniq[a] against genome uniq[b]
    M = np.array([[cache[(u, v)] for v in uniq] for u in uniq])
    counts = Counter(keys)
    n_copies = np.array([counts[u] for u in uniq])  # how many individuals have each genome
    pos = {u: a for a, u in enumerate(uniq)}
    a = np.array([pos[k] for k in keys])  # row of M of each individual
    # M[a] @ n_copies = payoff of each individual against the whole population (each
    # genome weighted by its number of copies). That includes one game against itself,
    # M[a, a], which is removed.
    total = M[a] @ n_copies - M[a, a]
    return total / (len(pop) - 1)  # average over the n - 1 opponents


# ---------------------------------------------------------------- genetic algorithm
def run_ga(seed, p_noise=0.0, rounds=ROUNDS, n_pop=N_POP, n_gen=N_GEN, cxpb=CXPB,
           mut_indpb=MUT_INDPB, tourn_size=TOURN_SIZE, elitism=ELITISM):
    """Evolve one population. Returns one row per generation."""
    random.seed(seed)  # DEAP uses Python's random: fixes initialisation and operators
    cache = {}         # payoffs of pairs of genomes, reused across generations

    tb = base.Toolbox()
    tb.register("bit", random.randint, 0, 1)
    tb.register("individual", tools.initRepeat, creator.Individual, tb.bit, n=N_BITS)
    tb.register("population", tools.initRepeat, list, tb.individual)
    tb.register("mate", tools.cxUniform, indpb=0.5)  # indpb: prob. of swapping each bit
    tb.register("mutate", tools.mutFlipBit, indpb=mut_indpb)
    tb.register("select", tools.selTournament, tournsize=tourn_size)

    def evaluate_pop(pop):
        if len(cache) > MAX_CACHE:  # keep memory bounded in long runs
            cache.clear()
        # coevolution: fitness depends on the population, so everyone is re-evaluated
        for ind, f in zip(pop, evaluate(pop, cache, rounds, p_noise)):
            ind.fitness.values = (f,)

    def record(gen, pop):
        """Statistics of one generation (one row of the CSV)."""
        named = Counter(classify(ind) for ind in pop)
        genomes = Counter("".join(map(str, ind)) for ind in pop)
        top, top_count = genomes.most_common(1)[0]  # most frequent genome
        row = {"seed": seed, "gen": gen,
               "mean_payoff": float(np.mean([ind.fitness.values[0] for ind in pop]))}
        row.update({name: named[name] / len(pop) for name in COLUMNS})  # frequencies
        row.update({"n_distinct": len(genomes), "top_genome": "g" + top,
                    "top_freq": top_count / len(pop)})
        return row

    pop = tb.population(n=n_pop)
    evaluate_pop(pop)
    history = [record(0, pop)]
    for gen in range(1, n_gen + 1):
        elite = tb.clone(tools.selBest(pop, elitism))  # best of the previous generation
        # tournament selection, then uniform crossover with prob. cxpb per pair;
        # mutpb=1.0: every child goes through mutFlipBit, and mut_indpb decides each bit
        off = algorithms.varAnd(tb.select(pop, len(pop)), tb, cxpb=cxpb, mutpb=1.0)
        pop = elite + off[elitism:]  # the elite replaces the first children
        evaluate_pop(pop)
        history.append(record(gen, pop))
    return history


def save_csv(rows, path):
    """Write a list of dicts (all with the same keys) as a CSV file."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    os.makedirs(RESULTS_DIR, exist_ok=True)
    for k, p_noise in enumerate(NOISE_LEVELS):
        rows = []
        for run in range(N_RUNS):
            seed = SEED_OFFSET * k + run
            rows += [{"run": run, **r} for r in run_ga(seed, p_noise)]
        save_csv(rows, os.path.join(RESULTS_DIR, f"history_noise_{p_noise}.csv"))
        # summary of the last generation over all runs
        finals = [r for r in rows if r["gen"] == N_GEN]
        print(f"p_noise={p_noise}: median final mean payoff "
              f"{np.median([r['mean_payoff'] for r in finals]):.3f} over {N_RUNS} runs | "
              + ", ".join(f"{c} {np.mean([r[c] for r in finals]):.0%}" for c in COLUMNS))
