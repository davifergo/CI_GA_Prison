// One concrete noisy match, simulated with a seeded PRNG (for the courtroom).
// The expected payoff of the same pair is payoff.expectedMatch; this is one sample of it.

import { bit, PAYOFF_OWN, type Action, type Genome } from './game';

/** mulberry32: small, fast, seedable 32-bit PRNG. Returns floats in [0, 1). */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface Round {
  /** 0-based round number. */
  t: number;
  /** Rule (genome bit) each player used: 0 = first move, 1..4 = after CC, CD, DC, DD (own view). */
  rule: [number, number];
  intended: [Action, Action];
  played: [Action, Action];
  /** The clerk flipped the slip (noise). */
  error: [boolean, boolean];
  pay: [number, number];
  total: [number, number];
  /** Each player had cooperated and been defected against in the previous round. */
  betrayed: [boolean, boolean];
}

export interface Match {
  s1: Genome;
  s2: Genome;
  pNoise: number;
  seed: number;
  rounds: Round[];
  memory?: 1 | 2;
}

export function simulateMatch(s1: Genome, s2: Genome, nRounds: number, pNoise: number, seed: number): Match {
  const rng = mulberry32(seed);
  const rounds: Round[] = [];
  let t1 = 0, t2 = 0;
  let prev: [Action, Action] | null = null;
  for (let t = 0; t < nRounds; t++) {
    // each player reads the previous outcome with its own action first
    const rule: [number, number] = prev ? [1 + 2 * prev[0] + prev[1], 1 + 2 * prev[1] + prev[0]] : [0, 0];
    const intended: [Action, Action] = [bit(s1, rule[0]), bit(s2, rule[1])];
    const u1 = rng(), u2 = rng(); // always two draws per round, so the stream does not depend on p
    const error: [boolean, boolean] = [u1 < pNoise, u2 < pNoise];
    const played: [Action, Action] = [
      (error[0] ? 1 - intended[0] : intended[0]) as Action,
      (error[1] ? 1 - intended[1] : intended[1]) as Action,
    ];
    const pay: [number, number] = [PAYOFF_OWN[2 * played[0] + played[1]], PAYOFF_OWN[2 * played[1] + played[0]]];
    t1 += pay[0];
    t2 += pay[1];
    const betrayed: [boolean, boolean] = prev ? [prev[0] === 0 && prev[1] === 1, prev[1] === 0 && prev[0] === 1] : [false, false];
    rounds.push({ t, rule, intended, played, error, pay, total: [t1, t2], betrayed });
    prev = played;
  }
  return { s1, s2, pNoise, seed, rounds, memory: 1 };
}
