// Text and analysis built on top of the model: plain-language rules, invasion criterion,
// and the judge's verdict on a simulated match.

import { actionChar, ALL_GENOMES, bit, label, type Genome } from './game';
import type { PayoffMatrix } from './payoff';
import type { Match } from './match';
import { label2 } from './memory2';

/** Display name of a defendant of either memory. */
export const matchName = (m: Match, g: number): string => (m.memory === 2 ? label2(g) : label(g));

/** The five clauses of a case file, in genome order. */
export const RULE_SITUATIONS = [
  'Opening move',
  'After both cooperated',
  'After being betrayed', // own C, opponent D (CD)
  'After betraying',      // own D, opponent C (DC)
  'After both defected',
] as const;
export const RULE_CODES = ['—', 'CC', 'CD', 'DC', 'DD'] as const;

export function ruleText(g: Genome, i: number): string {
  const a = bit(g, i);
  return a === 0 ? 'cooperate' : 'defect';
}

// ------------------------------------------------------------------ invasion
export interface InvasionCheck {
  piYX: number; // mutant against resident
  piXX: number; // resident against itself
  piYY: number;
  piXY: number;
  /** strict advantage, or tie broken by the second condition */
  invades: boolean;
  /** pi(Y,X) == pi(X,X) up to rounding: the mutant can spread by drift */
  neutral: boolean;
}

const EPS = 1e-9;

/** The criterion of the report: Y invades X if pi(Y,X) > pi(X,X), or = and pi(Y,Y) > pi(X,Y). */
export function invasionCheck(M: PayoffMatrix, X: Genome, Y: Genome): InvasionCheck {
  return invasionFromPayoffs(M[Y][X], M[X][X], M[Y][Y], M[X][Y]);
}

export function invasionFromPayoffs(piYX: number, piXX: number, piYY: number, piXY: number): InvasionCheck {
  const tie = Math.abs(piYX - piXX) < EPS;
  return { piYX, piXX, piYY, piXY, invades: piYX > piXX + EPS || (tie && piYY > piXY + EPS), neutral: tie };
}

/** Genomes (other than X) that obtain at least pi(X,X) against X. Empty: X is not invadable. */
export function challengers(M: PayoffMatrix, X: Genome): Genome[] {
  return ALL_GENOMES.filter((Y) => Y !== X && M[Y][X] >= M[X][X] - EPS);
}

// ------------------------------------------------------------------ verdict
export interface Verdict {
  heading: string;
  paragraphs: string[];
}

const plural = (n: number, one: string, many = one + 's') => `${n} ${n === 1 ? one : many}`;
const pct = (x: number) => `${Math.round(100 * x)}%`;

interface Incident { start: number; end: number; byError: boolean; restored: boolean; retaliations: number }

/**
 * Builds the verdict from what actually happened in the match. `upTo` limits it to the
 * rounds played so far.
 */
export function verdict(m: Match, exp: { pay1: number; pay2: number }, upTo = m.rounds.length): Verdict {
  const rs = m.rounds.slice(0, upTo);
  const n = rs.length;
  const A = matchName(m, m.s1), B = matchName(m, m.s2);
  const same = m.s1 === m.s2;
  const nameA = same ? `${A} (left)` : A, nameB = same ? `${B} (right)` : B;
  const [t1, t2] = rs[n - 1].total;

  const cc = rs.filter((r) => r.played[0] === 0 && r.played[1] === 0).length;
  const dd = rs.filter((r) => r.played[0] === 1 && r.played[1] === 1).length;
  const errs = rs.filter((r) => r.error[0] || r.error[1]);
  const errCount = rs.reduce((s, r) => s + (r.error[0] ? 1 : 0) + (r.error[1] ? 1 : 0), 0);

  // longest stretch of mutual cooperation
  let best = 0, run = 0, bestEnd = -1;
  rs.forEach((r, i) => {
    run = r.played[0] === 0 && r.played[1] === 0 ? run + 1 : 0;
    if (run > best) { best = run; bestEnd = i; }
  });

  // incidents: from the first defection after a cooperative round (or from the start) until
  // mutual cooperation returns
  const incidents: Incident[] = [];
  let open: Incident | null = null;
  rs.forEach((r, i) => {
    const anyD = r.played[0] === 1 || r.played[1] === 1;
    if (!open && anyD) open = { start: i, end: i, byError: r.error[0] || r.error[1], restored: false, retaliations: 0 };
    if (open) {
      // a retaliation: a player intends D because it was betrayed in the previous round
      open.retaliations += (r.betrayed[0] && r.intended[0] === 1 ? 1 : 0) + (r.betrayed[1] && r.intended[1] === 1 ? 1 : 0);
      if (!anyD) { open.end = i - 1; open.restored = true; incidents.push(open); open = null; }
      else open.end = i;
    }
  });
  if (open) incidents.push(open);
  const chains = incidents.filter((x) => x.retaliations >= 2);
  const longestChain = chains.reduce<Incident | null>((a, x) => (!a || x.retaliations > a.retaliations ? x : a), null);

  // a party that "never forgave": intended D in every round from some point well before the end
  const grudge = (k: 0 | 1): number | null => {
    let i = n - 1;
    while (i >= 0 && rs[i].intended[k] === 1) i--;
    const from = i + 1;
    return from > 0 && n - from >= 10 && rs.slice(0, from).some((r) => r.played[k] === 0) ? from : null;
  };

  const paras: string[] = [];
  const diff = Math.abs(t1 - t2);
  let heading: string;
  if (diff === 0) heading = `No party prevails: ${t1} points each.`;
  else {
    const [w, l, tw, tl] = t1 > t2 ? [nameA, nameB, t1, t2] : [nameB, nameA, t2, t1];
    heading = `The court finds for ${w}, ${tw} points to ${tl}.`;
    paras.push(`${w} takes ${tw} points against ${tl} for ${l}, a margin of ${plural(diff, 'point')} (${(diff / n).toFixed(2)} per round).`);
  }

  if (cc === n) paras.push(`Both parties cooperated in all ${n} rounds. The clerk recorded every slip correctly.`);
  else {
    const coop = cc === 0
      ? `The parties never cooperated together in ${plural(n, 'round')}`
      : `Both parties cooperated in ${cc} of ${n} rounds (${pct(cc / n)})` +
        (best >= 3 ? `, the longest truce running ${best} rounds (to round ${bestEnd + 1})` : '');
    paras.push(coop + (dd ? `; both defected in ${plural(dd, 'round')}.` : '.'));
  }

  if (errCount === 0) {
    if (m.pNoise > 0) paras.push(`The clerk made no errors in ${plural(n, 'round')}.`);
  } else {
    const first = errs[0];
    const who = first.error[0] && first.error[1] ? 'both slips' : first.error[0] ? `${nameA}'s slip` : `${nameB}'s slip`;
    let s = `The clerk erred ${errCount === 1 ? 'once' : `${errCount} times`}; the first error, in round ${first.t + 1}, falsified ${who}.`;
    const triggered = incidents.find((x) => x.start === first.t);
    if (triggered) {
      if (triggered.restored) {
        const len = triggered.end - triggered.start + 1;
        s += len === 1 ? ' Cooperation resumed the next round.' : ` It took ${plural(len, 'round')} for mutual cooperation to return.`;
      } else s += ' Mutual cooperation never returned.';
    }
    paras.push(s);
  }

  if (chains.length) {
    const c = longestChain!;
    paras.push(
      `The record shows ${plural(chains.length, 'chain')} of retaliation` +
      ` (a party defecting because it had just been betrayed); the longest, from round ${c.start + 1} to ${c.end + 1}, held ${c.retaliations} retaliations` +
      (c.byError ? ' and was set off by a clerk’s error.' : '.'),
    );
  }

  for (const k of [0, 1] as const) {
    const g = grudge(k);
    if (g !== null) paras.push(`From round ${g + 1} to the end, ${k === 0 ? nameA : nameB} chose to defect in every round.`);
  }

  const e1 = exp.pay1, e2 = exp.pay2;
  if (n === m.rounds.length) {
    const d1 = t1 / n - e1;
    paras.push(
      `Precedent: averaged over every possible run of errors, ${nameA} earns ${e1.toFixed(3)} per round and ${nameB} ${e2.toFixed(3)}. ` +
      (Math.abs(d1) < 0.005 ? `This match followed precedent.` :
        `In this match ${nameA} earned ${(t1 / n).toFixed(3)}, ${d1 > 0 ? 'above' : 'below'} precedent by ${Math.abs(d1).toFixed(3)}.`),
    );
  }
  return { heading, paragraphs: paras };
}

/** A one-line account of a single round, for the caption under the bench. */
export function roundCaption(m: Match, t: number): string {
  const r = m.rounds[t];
  const A = matchName(m, m.s1), B = matchName(m, m.s2);
  const parts = [0, 1].map((k) => {
    const name = k === 0 ? A : B;
    const i = actionChar(r.intended[k]), p = actionChar(r.played[k]);
    return r.error[k] ? `${name} wrote ${i}; the clerk entered ${p}` : `${name} plays ${p}`;
  });
  return `Round ${t + 1}. ${parts.join(', ')}. Points ${r.pay[0]}–${r.pay[1]}.`;
}
