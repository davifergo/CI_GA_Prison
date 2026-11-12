// Genetic algorithm: port of main.run_ga (DEAP eaSimple-style loop with elitism).
//
// The random number stream is Python's (PyRandom) and every operator consumes it in the
// same order as DEAP 1.4 (initRepeat, selTournament, varAnd, cxUniform, mutFlipBit), so a run
// with seed s reproduces run_ga(M, s) of main.py generation by generation.

import { classify, COLUMNS, N_BITS, N_GENOMES, type Genome } from './game';
import { payoffMatrix, type PayoffMatrix } from './payoff';
import { PyRandom } from './pyrandom';
import { fma } from './fma';

export interface GAParams {
  nPop: number;       // N_POP = 100
  cxpb: number;       // CXPB = 0.7 (uniform crossover, 0.5 swap probability per bit)
  mutIndpb: number;   // MUT_INDPB = 0.01 per bit
  tournSize: number;  // TOURN_SIZE = 3
  elitism: number;    // ELITISM = 2
  pNoise: number;
  rounds: number;     // ROUNDS = 150
  seed: number;
}

export const DEFAULT_PARAMS: GAParams = {
  nPop: 100, cxpb: 0.7, mutIndpb: 0.01, tournSize: 3, elitism: 2, pNoise: 0, rounds: 150, seed: 0,
};

/** Where an individual of the current generation comes from. */
export const Origin = {
  Initial: 0, // generation 0
  Elite: 1,   // copy of one of the best of the previous generation
  Copy: 2,    // tournament winner, no crossover change and no mutation
  Crossed: 3, // changed by crossover (and not mutated)
  Mutant: 4,  // at least one bit flipped by mutation
} as const;
export type Origin = (typeof Origin)[keyof typeof Origin];

export interface Generation {
  gen: number;
  pop: Uint8Array;          // genome of each individual, in population order
  fitness: Float64Array;
  origin: Uint8Array;       // Origin of each individual
  meanPayoff: number;
  counts: Uint16Array;      // individuals per genome (32)
  freq: Record<string, number>; // frequency of each column of COLUMNS
}

/** Fitness of every individual: main.evaluate (round robin without self-play). */
export function evaluate(pop: ArrayLike<number>, M: PayoffMatrix): Float64Array {
  const n = pop.length;
  const counts = new Float64Array(N_GENOMES);
  for (let i = 0; i < n; i++) counts[pop[i]]++;
  const fit = new Float64Array(n);
  const cache = new Float64Array(N_GENOMES).fill(NaN);
  for (let i = 0; i < n; i++) {
    const g = pop[i];
    if (Number.isNaN(cache[g])) {
      const row = M[g];
      // M[idx] @ counts in the order of OpenBLAS's dgemv: 4 FMA lanes (j mod 4), then
      // (lane0 + lane2) + (lane1 + lane3)
      const l = [row[0] * counts[0], row[1] * counts[1], row[2] * counts[2], row[3] * counts[3]];
      for (let j = 4; j < N_GENOMES; j++) l[j & 3] = fma(row[j], counts[j], l[j & 3]);
      const s = (l[0] + l[2]) + (l[1] + l[3]);
      cache[g] = (s - row[g]) / (n - 1);
    }
    fit[i] = cache[g];
  }
  return fit;
}

/** np.mean of a 1-D float array: NumPy's pairwise sum (blocks of 8), divided by n. */
export function npMean(a: ArrayLike<number>): number {
  if (a.length === 0) return NaN;
  return pairwiseSum(a, 0, a.length) / a.length;
}

function pairwiseSum(a: ArrayLike<number>, off: number, n: number): number {
  if (n < 8) {
    let res = 0;
    for (let i = 0; i < n; i++) res += a[off + i];
    return res;
  }
  if (n <= 128) {
    const r = [0, 1, 2, 3, 4, 5, 6, 7].map((j) => a[off + j]);
    let i = 8;
    for (; i < n - (n % 8); i += 8) for (let j = 0; j < 8; j++) r[j] += a[off + i + j];
    let res = (r[0] + r[1] + (r[2] + r[3])) + (r[4] + r[5] + (r[6] + r[7]));
    for (; i < n; i++) res += a[off + i];
    return res;
  }
  let n2 = Math.floor(n / 2);
  n2 -= n2 % 8;
  return pairwiseSum(a, off, n2) + pairwiseSum(a, off + n2, n - n2);
}

function record(gen: number, pop: Uint8Array, fitness: Float64Array, origin: Uint8Array): Generation {
  const counts = new Uint16Array(N_GENOMES);
  for (const g of pop) counts[g]++;
  const freq: Record<string, number> = Object.fromEntries(COLUMNS.map((c) => [c, 0]));
  for (let g = 0; g < N_GENOMES; g++) if (counts[g]) freq[classify(g)] += counts[g] / pop.length;
  return { gen, pop: pop.slice(), fitness: fitness.slice(), origin: origin.slice(), meanPayoff: npMean(fitness), counts, freq };
}

export class GA {
  readonly rng: PyRandom;
  params: GAParams;
  M: PayoffMatrix;
  pop: Uint8Array;
  fitness: Float64Array;
  gen = 0;
  current: Generation;

  /**
   * @param initial optional starting population (genomes); if absent it is drawn at random
   *                exactly as tb.population(n=n_pop) in main.py.
   * @param M       optional precomputed payoff matrix for (params.pNoise, params.rounds).
   */
  constructor(params: GAParams, initial?: ArrayLike<number>, M?: PayoffMatrix) {
    this.params = { ...params };
    this.rng = new PyRandom(params.seed);
    this.M = M ?? payoffMatrix(params.pNoise, params.rounds);
    if (initial) {
      this.pop = Uint8Array.from(initial);
    } else {
      this.pop = Uint8Array.from(randomPopulation(this.rng, params.nPop, N_BITS));
    }
    this.fitness = evaluate(this.pop, this.M);
    this.current = record(0, this.pop, this.fitness, new Uint8Array(this.pop.length));
  }

  /** Change parameters between generations (a new noise level or match length recomputes M). */
  setParams(p: Partial<GAParams>, M?: PayoffMatrix): void {
    const old = this.params;
    this.params = { ...old, ...p };
    if (M) this.M = M;
    else if (this.params.pNoise !== old.pNoise || this.params.rounds !== old.rounds)
      this.M = payoffMatrix(this.params.pNoise, this.params.rounds);
  }

  /** One generation of main.run_ga. */
  step(): Generation {
    const { off, origin } = breed(this.rng, this.pop, this.fitness, this.params, N_BITS);
    const next = Uint8Array.from(off);
    this.pop = next;
    this.fitness = evaluate(next, this.M);
    this.gen++;
    this.current = record(this.gen, this.pop, this.fitness, origin);
    return this.current;
  }

  run(nGen: number): Generation[] {
    const out = [this.current];
    for (let g = 0; g < nGen; g++) out.push(this.step());
    return out;
  }
}

/** Draws a random population exactly as tb.population(n) with tb.bit = randint(0, 1). */
export function randomPopulation(rng: PyRandom, n: number, nBits: number): number[] {
  const pop: number[] = [];
  for (let i = 0; i < n; i++) {
    let g = 0;
    for (let b = 0; b < nBits; b++) g = g * 2 + rng.randint(0, 1);
    pop.push(g);
  }
  return pop;
}

/**
 * The variation step of run_ga, shared by memory 1 and memory 2: selBest for the elite,
 * selTournament, varAnd (cxUniform with 0.5 per bit, mutFlipBit for every child) and
 * pop = elite + off[elitism:]. Genomes are integers whose binary digits are the bits.
 */
export function breed(
  rng: PyRandom, pop: ArrayLike<number>, fit: ArrayLike<number>,
  params: Pick<GAParams, 'cxpb' | 'mutIndpb' | 'tournSize' | 'elitism'>, nBits: number,
): { off: number[]; origin: Uint8Array } {
  const { cxpb, mutIndpb, tournSize, elitism } = params;
  const n = pop.length;

  // elite = selBest(pop, elitism): stable sort by fitness, descending
  const order = Array.from({ length: n }, (_, i) => i).sort((a, b) => fit[b] - fit[a] || a - b);
  const elite = order.slice(0, elitism).map((i) => pop[i]);

  // selTournament(pop, n, tournsize): max() keeps the first of equal aspirants
  const off: number[] = new Array(n);
  for (let k = 0; k < n; k++) {
    let best = rng.randbelow(n);
    for (let t = 1; t < tournSize; t++) {
      const c = rng.randbelow(n);
      if (fit[c] > fit[best]) best = c;
    }
    off[k] = pop[best];
  }

  // varAnd: uniform crossover of consecutive pairs, then mutation of every child
  const origin = new Uint8Array(n).fill(Origin.Copy);
  for (let i = 1; i < n; i += 2) {
    if (rng.random() < cxpb) {
      let a = off[i - 1], b = off[i];
      const a0 = a, b0 = b;
      for (let bitIx = 0; bitIx < nBits; bitIx++) {
        if (rng.random() < 0.5) {
          const m = 2 ** (nBits - 1 - bitIx);
          const ba = Math.floor(a / m) % 2, bb = Math.floor(b / m) % 2;
          if (ba !== bb) { a += (bb - ba) * m; b += (ba - bb) * m; }
        }
      }
      off[i - 1] = a; off[i] = b;
      if (a !== a0) origin[i - 1] = Origin.Crossed;
      if (b !== b0) origin[i] = Origin.Crossed;
    }
  }
  for (let i = 0; i < n; i++) {
    rng.random(); // `if random.random() < mutpb` with mutpb = 1.0: always true, still drawn
    let g = off[i];
    for (let bitIx = 0; bitIx < nBits; bitIx++)
      if (rng.random() < mutIndpb) g ^= 1 << (nBits - 1 - bitIx);
    if (g !== off[i]) origin[i] = Origin.Mutant;
    off[i] = g;
  }

  // pop = elite + off[elitism:]
  for (let e = 0; e < elitism && e < n; e++) { off[e] = elite[e]; origin[e] = Origin.Elite; }
  return { off, origin };
}

/**
 * Regime as in the report: a period of at least `minLen` generations in which the same
 * strategy holds more than 50 % of the population. Returns the regime that holds at the end
 * of `history` (or null), with its length.
 */
export function currentRegime(history: Pick<Generation, 'freq'>[], minLen = 10): { name: string; since: number; length: number } | null {
  if (history.length === 0) return null;
  const last = history[history.length - 1];
  const name = majority(last.freq);
  if (!name) return null;
  let len = 0;
  for (let i = history.length - 1; i >= 0 && majority(history[i].freq) === name; i--) len++;
  return len >= minLen ? { name, since: history.length - len, length: len } : null;
}

export function majority(freq: Record<string, number>): string | null {
  for (const [k, v] of Object.entries(freq)) if (v > 0.5) return k;
  return null;
}

/**
 * Sequence of regimes in a history, as analysis.py counts them: a regime starts when the same
 * column has held > 50 % for 10 consecutive generations; consecutive repeats are merged.
 */
export function regimes(history: Pick<Generation, 'freq' | 'gen'>[], minLen = 10): { name: string; start: number }[] {
  const out: { name: string; start: number }[] = [];
  let cur: string | null = null, len = 0;
  for (const h of history) {
    const d = majority(h.freq);
    if (d === cur) len++;
    else { cur = d; len = 1; }
    if (len === minLen && d && (!out.length || out[out.length - 1].name !== d)) out.push({ name: d, start: h.gen - minLen + 1 });
  }
  return out;
}
