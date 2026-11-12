// Exact expected payoff of a match: port of main.expected_match.
//
// The outcome of a round is a 4-state Markov chain (CC, CD, DC, DD as seen by player 1).
// We propagate its probability distribution for `rounds` rounds and add the expected payoff
// of every round. The arithmetic follows the order of the NumPy code, so the matrix is the
// same to the last bit (checked in model.test.ts against main.py).

import { bit, N_GENOMES, PAYOFF_OWN, ROUNDS, type Genome } from './game';
import { fma } from './fma';

const PAY1 = [PAYOFF_OWN[0], PAYOFF_OWN[1], PAYOFF_OWN[2], PAYOFF_OWN[3]]; // R S T P
const PAY2 = [PAYOFF_OWN[0], PAYOFF_OWN[2], PAYOFF_OWN[1], PAYOFF_OWN[3]]; // R T S P

/** Distribution [P(C), P(D)] of the action actually played. */
const played = (intended: number, p: number): [number, number] => (intended === 0 ? [1 - p, p] : [p, 1 - p]);

const outer = (a: [number, number], b: [number, number]) => [a[0] * b[0], a[0] * b[1], a[1] * b[0], a[1] * b[1]];

export interface ExpectedMatch {
  /** Mean payoff per round of player 1 and player 2. */
  pay1: number;
  pay2: number;
}

/** Transition matrix: trans[s][t] = P(next outcome t | current outcome s), player 1's view. */
export function transitionMatrix(s1: Genome, s2: Genome, p: number): number[][] {
  const trans: number[][] = [];
  for (let a1 = 0; a1 < 2; a1++)
    for (let a2 = 0; a2 < 2; a2++) {
      // player 2 sees the outcome with its own action first: index 2*a2 + a1
      const nxt1 = bit(s1, 1 + 2 * a1 + a2);
      const nxt2 = bit(s2, 1 + 2 * a2 + a1);
      trans[2 * a1 + a2] = outer(played(nxt1, p), played(nxt2, p));
    }
  return trans;
}

export function expectedMatch(s1: Genome, s2: Genome, rounds = ROUNDS, p = 0): ExpectedMatch {
  const trans = transitionMatrix(s1, s2, p);
  let dist = outer(played(bit(s1, 0), p), played(bit(s2, 0), p));
  let total1 = 0, total2 = 0;
  for (let r = 0; r < rounds; r++) {
    total1 += dot4(dist, PAY1);
    total2 += dot4(dist, PAY2);
    dist = vecMat4(dist, trans);
  }
  return { pay1: total1 / rounds, pay2: total2 / rounds };
}

/** Expected per-round distribution of the outcome, round by round (for the "precedent" chart). */
export function expectedCumulative(s1: Genome, s2: Genome, rounds = ROUNDS, p = 0): { c1: number[]; c2: number[] } {
  const trans = transitionMatrix(s1, s2, p);
  let dist = outer(played(bit(s1, 0), p), played(bit(s2, 0), p));
  let t1 = 0, t2 = 0;
  const c1: number[] = [], c2: number[] = [];
  for (let r = 0; r < rounds; r++) {
    t1 += dot4(dist, PAY1);
    t2 += dot4(dist, PAY2);
    c1.push(t1);
    c2.push(t2);
    dist = vecMat4(dist, trans);
  }
  return { c1, c2 };
}

function dot4(a: number[], b: number[]): number {
  let s = 0;
  for (let i = 0; i < 4; i++) s += a[i] * b[i];
  return s;
}

// dist @ trans, rounded as OpenBLAS's dgemv kernel does it (two FMA accumulators over the
// even and odd terms, then their sum). Plain sequential sums give the same value to ~1e-16.
function vecMat4(v: number[], m: number[][]): number[] {
  const out = [0, 0, 0, 0];
  for (let i = 0; i < 4; i++)
    out[i] = fma(v[2], m[2][i], v[0] * m[0][i]) + fma(v[3], m[3][i], v[1] * m[1][i]);
  return out;
}

export type PayoffMatrix = Float64Array[]; // M[i][j] = payoff of genome i against genome j

/** M[i][j] = expected payoff per round of genome i against genome j (main.payoff_matrix). */
export function payoffMatrix(p: number, rounds = ROUNDS): PayoffMatrix {
  const M = Array.from({ length: N_GENOMES }, () => new Float64Array(N_GENOMES));
  for (let i = 0; i < N_GENOMES; i++)
    for (let j = i; j < N_GENOMES; j++) {
      const { pay1, pay2 } = expectedMatch(i, j, rounds, p);
      M[i][j] = pay1;
      M[j][i] = pay2;
    }
  return M;
}
