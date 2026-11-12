// Memory-2 strategies: port of main_memory2.py.
//
// Genome (18 bits, 0 = C, 1 = D), stored as the integer whose binary digits are the bits:
//   bit 0        action in round 1
//   bit 1        action in round 2 (unconditional)
//   bits 2..17   action after the last two outcomes: bit 2 + 4*o_prev + o_cur,
//                with an outcome o = 2*own + opponent (0 CC, 1 CD, 2 DC, 3 DD)
// The state of a match is the pair of the last two outcomes: a 16-state Markov chain.

import { fma } from './fma';
import { breed, npMean, Origin, randomPopulation, type GAParams } from './ga';
import { PAYOFF_OWN, ROUNDS, type Action } from './game';
import { mulberry32, type Match, type Round } from './match';
import { PyRandom } from './pyrandom';

export type Genome2 = number; // 0 .. 2^18 - 1
export const N_BITS2 = 18;
export const N_GENOMES2 = 2 ** N_BITS2;

export const bit2 = (g: Genome2, i: number): Action => ((g >>> (N_BITS2 - 1 - i)) & 1) as Action;
export const bits2 = (g: Genome2): Action[] => Array.from({ length: N_BITS2 }, (_, i) => bit2(g, i));
export const fromBits2 = (b: ReadonlyArray<number>): Genome2 => b.reduce<number>((a, x) => a * 2 + (x ? 1 : 0), 0);
/** Parses "ab | CC CD DC DD" or a plain 18-bit string. */
export const parse2 = (s: string): Genome2 => fromBits2([...s].filter((c) => c === '0' || c === '1').map(Number));
/** The report's notation: "ab | 0110 1111 1111 0110". */
export const format2 = (g: Genome2): string => {
  const b = bits2(g).join('');
  return `${b.slice(0, 2)} | ${b.slice(2, 6)} ${b.slice(6, 10)} ${b.slice(10, 14)} ${b.slice(14, 18)}`;
};

// The same outcome seen by the other player: CC and DD stay, CD <-> DC.
const SWAP = [0, 2, 1, 3];
/** STATE_SWAP[s]: state s = 4*o_prev + o_cur as seen by player 2. */
export const STATE_SWAP = Array.from({ length: 16 }, (_, s) => 4 * SWAP[s >> 2] + SWAP[s & 3]);

// ------------------------------------------------------------------ named strategies
/** Memory-1 strategies (first move, after CC, CD, DC, DD), as in main_memory2.MEMORY1. */
const MEMORY1: [string, number[]][] = [
  ['ALLC', [0, 0, 0, 0, 0]],
  ['ALLD', [1, 1, 1, 1, 1]],
  ['TFT', [0, 0, 1, 0, 1]],
  ['PAVLOV', [0, 0, 1, 1, 0]],
  ['GRIM', [0, 0, 1, 1, 1]],
  ['STFT', [1, 0, 1, 0, 1]],
];
/** Tit-for-two-tats: defects only if the opponent defected in both of the last two rounds. */
export const TF2T: Genome2 = fromBits2([0, 0, ...Array.from({ length: 16 }, (_, s) => +((s >> 2) % 2 === 1 && (s & 3) % 2 === 1))]);
export const COLUMNS2 = [...MEMORY1.map(([n]) => n), 'TF2T', 'OTHER'] as const;

/** Name of the strategy the genome behaves like (main_memory2.classify), or "OTHER". */
export function classify2(g: Genome2): string {
  if (g === TF2T) return 'TF2T';
  for (const [name, m1] of MEMORY1) {
    if (bit2(g, 0) !== m1[0]) continue;
    let ok = true;
    for (let s = 0; s < 16 && ok; s++) ok = bit2(g, 2 + s) === m1[1 + (s & 3)];
    if (ok) return name;
  }
  return 'OTHER';
}

/** A memory-1 strategy written as a memory-2 genome (its round-2 move is set equal to round 1). */
export const embed1 = (m1: number[]): Genome2 => fromBits2([m1[0], m1[0], ...Array.from({ length: 16 }, (_, s) => m1[1 + (s & 3)])]);

/**
 * Strategies offered by name. The last three are the most frequent final genomes of the
 * report's memory-2 runs; the names are ours, not the report's.
 */
export const NAMED2: { name: string; g: Genome2; blurb: string }[] = [
  ...MEMORY1.map(([name, m1]) => ({ name, g: embed1(m1), blurb: `memory-1 ${name}; second move = first move` })),
  { name: 'TF2T', g: TF2T, blurb: 'defects only after two defections in a row' },
  { name: 'PAV2', g: parse2('10|0110 1111 1111 0110'), blurb: 'PAVLOV after an agreement, D after a disagreement (most frequent at p = 0.01)' },
  { name: 'PAV2D', g: parse2('11|0111 1111 1111 0110'), blurb: 'like PAV2, harsher after CC→DD (most frequent at p = 0.05)' },
  { name: 'GRIM1', g: parse2('11|0111 0111 0111 0000'), blurb: 'cooperates only after CC, always after DD (invadable; 6 runs at p = 0.05)' },
];
const NAME2 = new Map(NAMED2.map((x) => [x.g, x.name]));
/** Our display name, else the memory-1 class (main_memory2.classify), else the bits. */
export const label2 = (g: Genome2): string => {
  const n = NAME2.get(g);
  if (n) return n;
  const c = classify2(g);
  return c === 'OTHER' ? format2(g) : `${c}-like`;
};
export const shortLabel2 = (g: Genome2): string => NAME2.get(g) ?? (classify2(g) !== 'OTHER' ? classify2(g) : 'g' + g.toString(36));

// ------------------------------------------------------------------ exact expected payoff
const PAY1 = [PAYOFF_OWN[0], PAYOFF_OWN[1], PAYOFF_OWN[2], PAYOFF_OWN[3]]; // R S T P
const PAY2 = [PAYOFF_OWN[0], PAYOFF_OWN[2], PAYOFF_OWN[1], PAYOFF_OWN[3]]; // R T S P

/** (B,4) @ (4,) as NumPy/OpenBLAS rounds it: (v0 p0 + v2 p2) + (v1 p1 + v3 p3). */
const dotH = (v: ArrayLike<number>, p: number[]) => (v[0] * p[0] + v[2] * p[2]) + (v[1] * p[1] + v[3] * p[3]);

function outcomeDist(q1: number, q2: number, out: Float64Array, o: number): void {
  // q = probability of playing D; same expression as outcome_dist in main_memory2.py
  out[o] = (1 - q1) * (1 - q2);
  out[o + 1] = (1 - q1) * q2;
  out[o + 2] = q1 * (1 - q2);
  out[o + 3] = q1 * q2;
}

export interface Transitions2 { d1: Float64Array; d2: Float64Array; nxt: Float64Array }

export function transitions2(g1: Genome2, g2: Genome2, p: number): Transitions2 {
  const pd = (a: number) => (a === 1 ? 1 - p : p);
  const d1 = new Float64Array(4), d2 = new Float64Array(4), nxt = new Float64Array(64);
  outcomeDist(pd(bit2(g1, 0)), pd(bit2(g2, 0)), d1, 0);
  outcomeDist(pd(bit2(g1, 1)), pd(bit2(g2, 1)), d2, 0);
  for (let s = 0; s < 16; s++) outcomeDist(pd(bit2(g1, 2 + s)), pd(bit2(g2, 2 + STATE_SWAP[s])), nxt, 4 * s);
  return { d1, d2, nxt };
}

/**
 * Exact expected payoff per round of a memory-2 pair (main_memory2.expected_matches for one
 * pair). With `cumulative`, also the expected running totals after every round.
 */
export function expectedMatch2(g1: Genome2, g2: Genome2, rounds = ROUNDS, p = 0, cumulative = false) {
  const { d1, d2, nxt } = transitions2(g1, g2, p);
  let total1 = dotH(d1, PAY1), total2 = dotH(d1, PAY2);
  const c1 = cumulative ? [total1] : [], c2 = cumulative ? [total2] : [];
  let dist = new Float64Array(16), next = new Float64Array(16);
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) dist[4 * i + j] = d1[i] * d2[j];
  const cur = new Float64Array(4);
  for (let r = 0; r < rounds - 1; r++) {
    for (let j = 0; j < 4; j++) cur[j] = ((dist[j] + dist[4 + j]) + dist[8 + j]) + dist[12 + j];
    total1 += dotH(cur, PAY1);
    total2 += dotH(cur, PAY2);
    if (cumulative) { c1.push(total1); c2.push(total2); }
    for (let c = 0; c < 4; c++)
      for (let o = 0; o < 4; o++)
        next[4 * c + o] = ((dist[c] * nxt[4 * c + o] + dist[4 + c] * nxt[4 * (4 + c) + o]) +
          dist[8 + c] * nxt[4 * (8 + c) + o]) + dist[12 + c] * nxt[4 * (12 + c) + o];
    [dist, next] = [next, dist];
  }
  return { pay1: total1 / rounds, pay2: total2 / rounds, c1, c2 };
}

// ------------------------------------------------------------------ fitness and GA
/** Row-times-counts dot product in the order of OpenBLAS's dgemv_t kernel (4 FMA lanes). */
function gemvRow(row: Float64Array, c: Float64Array, U: number): number {
  if (U < 4) {
    let s = row[0] * c[0];
    for (let j = 1; j < U; j++) s = fma(row[j], c[j], s);
    return s;
  }
  const m = U - (U % 4);
  const l = [row[0] * c[0], row[1] * c[1], row[2] * c[2], row[3] * c[3]];
  for (let j = 4; j < m; j++) l[j & 3] = fma(row[j], c[j], l[j & 3]);
  let s = (l[0] + l[2]) + (l[1] + l[3]);
  const t = U - m;
  if (t === 1) s = fma(row[m], c[m], s);
  else if (t === 2) s = s + (row[m] * c[m] + row[m + 1] * c[m + 1]);
  else if (t === 3) s = s + fma(row[m + 2], c[m + 2], row[m] * c[m] + row[m + 1] * c[m + 1]);
  return s;
}

export type Cache2 = Map<number, number>;
const key = (u: number, v: number) => u * N_GENOMES2 + v;
const MAX_CACHE = 600_000;

/** main_memory2.evaluate: round robin without self-play, pair payoffs cached per run. */
export function evaluate2(pop: ArrayLike<number>, cache: Cache2, rounds: number, p: number): Float64Array {
  if (cache.size > MAX_CACHE) cache.clear(); // memory bound; values are recomputed identically
  const n = pop.length;
  const uniq = [...new Set(Array.from(pop))].sort((a, b) => a - b);
  const U = uniq.length;
  for (let a = 0; a < U; a++)
    for (let b = a; b < U; b++) {
      const u = uniq[a], v = uniq[b];
      if (cache.has(key(u, v))) continue;
      const { pay1, pay2 } = expectedMatch2(u, v, rounds, p);
      cache.set(key(u, v), pay1);
      cache.set(key(v, u), pay2);
    }
  const pos = new Map(uniq.map((u, a) => [u, a]));
  const copies = new Float64Array(U);
  for (let i = 0; i < n; i++) copies[pos.get(pop[i])!]++;
  const fitOf = new Float64Array(U);
  const row = new Float64Array(U);
  for (let a = 0; a < U; a++) {
    for (let b = 0; b < U; b++) row[b] = cache.get(key(uniq[a], uniq[b]))!;
    fitOf[a] = (gemvRow(row, copies, U) - row[a]) / (n - 1);
  }
  const fit = new Float64Array(n);
  for (let i = 0; i < n; i++) fit[i] = fitOf[pos.get(pop[i])!];
  return fit;
}

export interface Generation2 {
  gen: number;
  pop: Uint32Array;
  fitness: Float64Array;
  origin: Uint8Array;
  meanPayoff: number;
  freq: Record<string, number>;
  nDistinct: number;
  /** genomes by number of copies, most frequent first (ties: first seen in the population) */
  top: { g: Genome2; n: number }[];
}

function record2(gen: number, pop: Uint32Array, fitness: Float64Array, origin: Uint8Array): Generation2 {
  const counts = new Map<number, number>(); // insertion order = first appearance, as Counter
  for (const g of pop) counts.set(g, (counts.get(g) ?? 0) + 1);
  const top = [...counts].map(([g, n]) => ({ g, n })).sort((a, b) => b.n - a.n); // stable
  const freq: Record<string, number> = Object.fromEntries(COLUMNS2.map((c) => [c, 0]));
  for (const { g, n } of top) freq[classify2(g)] += n / pop.length;
  return { gen, pop: pop.slice(), fitness: fitness.slice(), origin: origin.slice(), meanPayoff: npMean(fitness), freq, nDistinct: counts.size, top: top.slice(0, 8) };
}

/** main_memory2.run_ga, one generation at a time. */
export class GA2 {
  readonly rng: PyRandom;
  params: GAParams;
  cache: Cache2 = new Map();
  pop: Uint32Array;
  fitness: Float64Array;
  gen = 0;
  current: Generation2;

  constructor(params: GAParams, initial?: ArrayLike<number>) {
    this.params = { ...params };
    this.rng = new PyRandom(params.seed);
    this.pop = Uint32Array.from(initial ?? randomPopulation(this.rng, params.nPop, N_BITS2));
    this.fitness = evaluate2(this.pop, this.cache, params.rounds, params.pNoise);
    this.current = record2(0, this.pop, this.fitness, new Uint8Array(this.pop.length).fill(Origin.Initial));
  }

  setParams(p: Partial<GAParams>): void {
    const old = this.params;
    this.params = { ...old, ...p };
    if (this.params.pNoise !== old.pNoise || this.params.rounds !== old.rounds) this.cache.clear();
  }

  step(): Generation2 {
    const { off, origin } = breed(this.rng, this.pop, this.fitness, this.params, N_BITS2);
    this.pop = Uint32Array.from(off);
    this.fitness = evaluate2(this.pop, this.cache, this.params.rounds, this.params.pNoise);
    this.gen++;
    this.current = record2(this.gen, this.pop, this.fitness, origin);
    return this.current;
  }

  run(nGen: number): Generation2[] {
    const out = [this.current];
    for (let g = 0; g < nGen; g++) out.push(this.step());
    return out;
  }
}

// ------------------------------------------------------------------ one simulated match
/**
 * One noisy match between memory-2 strategies (for the courtroom). Same conventions as
 * match.simulateMatch: two PRNG draws per round; `rule` is the genome bit used.
 */
export function simulateMatch2(s1: Genome2, s2: Genome2, nRounds: number, pNoise: number, seed: number): Match {
  const rng = mulberry32(seed);
  const rounds: Round[] = [];
  let t1 = 0, t2 = 0;
  const hist: [Action, Action][] = [];
  for (let t = 0; t < nRounds; t++) {
    let rule: [number, number];
    if (t < 2) rule = [t, t];
    else {
      const [p0, p1] = [hist[t - 2], hist[t - 1]];
      const o = (a: [Action, Action], k: 0 | 1) => 2 * a[k] + a[1 - k];
      rule = [2 + 4 * o(p0, 0) + o(p1, 0), 2 + 4 * o(p0, 1) + o(p1, 1)];
    }
    const intended: [Action, Action] = [bit2(s1, rule[0]), bit2(s2, rule[1])];
    const u1 = rng(), u2 = rng();
    const error: [boolean, boolean] = [u1 < pNoise, u2 < pNoise];
    const played: [Action, Action] = [
      (error[0] ? 1 - intended[0] : intended[0]) as Action,
      (error[1] ? 1 - intended[1] : intended[1]) as Action,
    ];
    const pay: [number, number] = [PAYOFF_OWN[2 * played[0] + played[1]], PAYOFF_OWN[2 * played[1] + played[0]]];
    t1 += pay[0];
    t2 += pay[1];
    rounds.push({ t, rule, intended, played, error, pay, total: [t1, t2], betrayed: t > 0 ? [hist[t - 1][0] === 0 && hist[t - 1][1] === 1, hist[t - 1][1] === 0 && hist[t - 1][0] === 1] : [false, false] });
    hist.push(played);
  }
  return { s1, s2, pNoise, seed, rounds, memory: 2 };
}

/** Plain-language reading of rule i of a memory-2 genome. */
export const OUTCOME_NAMES = ['CC', 'CD', 'DC', 'DD'] as const;
export function ruleSituation2(i: number): string {
  if (i === 0) return 'Round 1';
  if (i === 1) return 'Round 2';
  const s = i - 2;
  return `After ${OUTCOME_NAMES[s >> 2]} then ${OUTCOME_NAMES[s & 3]}`;
}
