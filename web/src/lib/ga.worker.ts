/// <reference lib="webworker" />
// Runs the GA off the main thread. One worker per view; requests are answered in order.

import { GA, type GAParams, type Generation } from './model/ga';
import { COLUMNS, type Genome } from './model/game';
import { payoffMatrix, type PayoffMatrix } from './model/payoff';
import { expectedMatch2, GA2, N_GENOMES2, type Generation2 } from './model/memory2';

export type WorkerRequest =
  | { type: 'init'; params: GAParams; initial?: number[]; memory?: 1 | 2 }
  | { type: 'step'; n: number }
  | { type: 'set'; params: Partial<GAParams> }
  | { type: 'sweep'; ps: number[]; runs: number; gens: number; params: GAParams; memory?: 1 | 2 }
  | { type: 'invasion'; resident: Genome; mutant: Genome; k: number; runs: number; gens: number; params: GAParams; memory?: 1 | 2 }
  | { type: 'challengers2'; resident: number; p: number; rounds: number };

export interface SweepPoint {
  p: number;
  /** response variable of the report: mean payoff over the last 100 generations, per run */
  payoffs: number[];
  /** strategy with the highest mean frequency over the last 100 generations, per run */
  dominant: string[];
  /** mean frequency of each column over the last 100 generations and all runs */
  freq: Record<string, number>;
  /** memory two: share of the most frequent genome at the end of each run */
  topShare?: number[];
}

export type WorkerResponse =
  | { type: 'gens'; gens: (Generation | Generation2)[] }
  | { type: 'challengers2'; count: number; better: number; best: { g: number; pay: number } | null; self: number }
  | { type: 'progress'; done: number; total: number }
  | { type: 'sweep'; points: SweepPoint[] }
  | { type: 'invasion'; traces: number[][]; invaded: number; grew: number };

let ga: GA | GA2 | null = null;
const post = (m: WorkerResponse) => (self as unknown as Worker).postMessage(m);

self.onmessage = (ev: MessageEvent<WorkerRequest>) => {
  const msg = ev.data;
  switch (msg.type) {
    case 'init':
      ga = msg.memory === 2 ? new GA2(msg.params, msg.initial) : new GA(msg.params, msg.initial);
      post({ type: 'gens', gens: [ga.current] });
      break;
    case 'step': {
      if (!ga) return;
      const gens: (Generation | Generation2)[] = [];
      for (let i = 0; i < msg.n; i++) gens.push(ga.step());
      post({ type: 'gens', gens });
      break;
    }
    case 'set':
      ga?.setParams(msg.params);
      break;
    case 'sweep':
      post({ type: 'sweep', points: sweep(msg) });
      break;
    case 'invasion':
      post({ type: 'invasion', ...invasion(msg) });
      break;
    case 'challengers2':
      post(challengers2(msg));
      break;
  }
};

function sweep(msg: Extract<WorkerRequest, { type: 'sweep' }>): SweepPoint[] {
  const total = msg.ps.length * msg.runs;
  const tail = Math.min(100, msg.gens);
  const points: SweepPoint[] = [];
  let done = 0;
  msg.ps.forEach((p, k) => {
    const M = msg.memory === 2 ? undefined : payoffMatrix(p, msg.params.rounds);
    const pt: SweepPoint = { p, payoffs: [], dominant: [], freq: Object.fromEntries(COLUMNS.map((c) => [c, 0])) };
    for (let r = 0; r < msg.runs; r++) {
      // independent seeds per level, as in the report: level k uses 100k, 100k+1, ...
      const prm = { ...msg.params, pNoise: p, seed: msg.params.seed + 100 * k + r };
      const g = msg.memory === 2 ? new GA2(prm) : new GA(prm, undefined, M);
      let pay = 0;
      const f: Record<string, number> = Object.fromEntries(COLUMNS.map((c) => [c, 0]));
      for (let gen = 1; gen <= msg.gens; gen++) {
        const h = g.step();
        if (gen > msg.gens - tail) {
          pay += h.meanPayoff;
          for (const c of COLUMNS) f[c] += h.freq[c];
        }
      }
      pt.payoffs.push(pay / tail);
      for (const c of COLUMNS) {
        f[c] /= tail;
        pt.freq[c] += f[c] / msg.runs;
      }
      if (g instanceof GA2) {
        // memory two: the named classes are almost never present; describe the final most
        // frequent genome by what it earns against itself
        const top = g.current.top[0];
        const self = expectedMatch2(top.g, top.g, msg.params.rounds, p).pay1;
        pt.dominant.push(self >= 2.5 ? 'fam:coop' : self < 1.5 ? 'fam:defect' : 'fam:brass');
        (pt.topShare ??= []).push(top.n / g.pop.length);
      } else pt.dominant.push(COLUMNS.reduce((a, b) => (f[b] > f[a] ? b : a)));
      post({ type: 'progress', done: ++done, total });
    }
    points.push(pt);
  });
  return points;
}

function invasion(msg: Extract<WorkerRequest, { type: 'invasion' }>) {
  const M: PayoffMatrix | undefined = msg.memory === 2 ? undefined : payoffMatrix(msg.params.pNoise, msg.params.rounds);
  const n = msg.params.nPop;
  const initial = Array.from({ length: n }, (_, i) => (i < msg.k ? msg.mutant : msg.resident));
  const traces: number[][] = [];
  let invaded = 0, grew = 0;
  for (let r = 0; r < msg.runs; r++) {
    const prm = { ...msg.params, seed: msg.params.seed + r };
    const g = msg.memory === 2 ? new GA2(prm, initial) : new GA(prm, initial, M);
    const tr = [msg.k / n];
    for (let gen = 0; gen < msg.gens; gen++) {
      const h = g.step();
      let c = 0;
      for (const x of h.pop) if (x === msg.mutant) c++;
      tr.push(c / n);
    }
    traces.push(tr);
    if (tr[tr.length - 1] > 0.5) invaded++;
    if (tr.slice(1, 11).some((f) => f > tr[0])) grew++;
  }
  return { traces, invaded, grew };
}


/**
 * Memory 2: every one of the 262,144 genomes against the resident X. Counts the genomes Y != X
 * with pi(Y, X) >= pi(X, X) (they can invade or drift in), as in the report's check.
 */
function challengers2(msg: Extract<WorkerRequest, { type: 'challengers2' }>) {
  const X = msg.resident;
  const self = expectedMatch2(X, X, msg.rounds, msg.p).pay1;
  let count = 0, better = 0;
  let best: { g: number; pay: number } | null = null;
  const EPS = 1e-12;
  for (let Y = 0; Y < N_GENOMES2; Y++) {
    if (Y === X) continue;
    const pay = expectedMatch2(Y, X, msg.rounds, msg.p).pay1;
    if (pay >= self - EPS) {
      count++;
      if (pay > self + EPS) better++;
      if (!best || pay > best.pay) best = { g: Y, pay };
    }
    if ((Y & 4095) === 4095) post({ type: 'progress', done: Y + 1, total: N_GENOMES2 });
  }
  return { type: 'challengers2' as const, count, better, best, self };
}
