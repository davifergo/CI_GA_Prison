import { describe, expect, it } from 'vitest';
import { bitString, genomeOfName, NAMED } from './game';
import { expectedMatch, payoffMatrix } from './payoff';
import { PyRandom } from './pyrandom';
import { GA, DEFAULT_PARAMS } from './ga';
import { mulberry32, simulateMatch } from './match';
import { fma } from './fma';
import fx from './__fixtures__/python.json';

const g = (name: string) => {
  const v = genomeOfName(name);
  if (v === undefined) throw new Error(name);
  return v;
};
const pi = (p: number, a: string, b: string) => expectedMatch(g(a), g(b), 150, p).pay1;

describe('encoding', () => {
  it('named genomes have the bits of the report', () => {
    expect(Object.fromEntries(NAMED.map(([n, x]) => [n, bitString(x)]))).toEqual({
      ALLC: '00000', ALLD: '11111', TFT: '00101', PAVLOV: '00110', GRIM: '00111', STFT: '10101',
    });
  });
});

describe('exact expected payoff (values given in the brief, row vs column)', () => {
  const cases: [number, string, string, number, number][] = [
    [0, 'TFT', 'ALLD', 0.993, 3],
    [0.01, 'TFT', 'TFT', 2.521, 3],
    [0.01, 'GRIM', 'GRIM', 1.658, 3],
    [0.01, 'ALLC', 'TFT', 2.961, 3],
    [0.01, 'ALLD', 'PAVLOV', 2.992, 3],
    [0.01, 'PAVLOV', 'PAVLOV', 2.951, 3],
    [0.05, 'TFT', 'TFT', 2.3, 2],
    [0.05, 'GRIM', 'GRIM', 1.31, 2],
    [0.05, 'ALLD', 'GRIM', 1.18, 2],
  ];
  for (const [p, a, b, want, digits] of cases)
    it(`p=${p}: ${a} vs ${b} = ${want}`, () => expect(pi(p, a, b)).toBeCloseTo(want, digits));
});

describe('bit-for-bit agreement with main.py', () => {
  for (const [p, M] of Object.entries(fx.matrices)) {
    it(`32x32 payoff matrix, p=${p}`, () => {
      const mine = payoffMatrix(Number(p));
      let maxDiff = 0, exact = 0;
      for (let i = 0; i < 32; i++)
        for (let j = 0; j < 32; j++) {
          const d = Math.abs(mine[i][j] - M[i][j]);
          maxDiff = Math.max(maxDiff, d);
          if (d === 0) exact++;
        }
      expect(maxDiff).toBeLessThan(1e-12);
      expect(exact).toBe(1024);
    });
  }

  it('emulated fused multiply-add equals math.fma (3000 cases, many near rounding ties)', () => {
    const bad = fx.fma.filter(([a, b, c, want]) => !Object.is(fma(a, b, c), want));
    expect(bad).toEqual([]);
  });

  it("Python's random stream (MT19937, randint, randrange)", () => {
    const r = new PyRandom(fx.rng.seed);
    expect(fx.rng.random.map(() => r.random())).toEqual(fx.rng.random);
    expect(fx.rng.randint01.map(() => r.randint(0, 1))).toEqual(fx.rng.randint01);
    expect(fx.rng.choice100.map(() => r.randbelow(100))).toEqual(fx.rng.choice100);
    expect(fx.rng.choice37.map(() => r.randbelow(37))).toEqual(fx.rng.choice37);
  });

  for (const run of fx.runs) {
    const label = `GA seed ${run.seed}, p=${run.p_noise}` + ('n_pop' in run ? ' (non-default parameters)' : '');
    it(`${label}: same mean payoff in every generation and same final population`, () => {
      const r = run as typeof run & Partial<{ n_pop: number; cxpb: number; mut_indpb: number; tourn_size: number; elitism: number }>;
      const ga = new GA({
        ...DEFAULT_PARAMS, seed: r.seed, pNoise: r.p_noise,
        nPop: r.n_pop ?? 100, cxpb: r.cxpb ?? 0.7, mutIndpb: r.mut_indpb ?? 0.01,
        tournSize: r.tourn_size ?? 3, elitism: r.elitism ?? 2,
      });
      const hist = ga.run(r.mean_payoff.length - 1);
      const n = hist[0].pop.length;
      hist.forEach((h, i) => expect(h.meanPayoff, `generation ${i}`).toBe(r.mean_payoff[i]));
      const last = hist[hist.length - 1];
      expect(Array.from(last.counts, (c) => c / n)).toEqual(r.final_genomes);
    });
  }
});

describe('simulated match', () => {
  it('is reproducible with the same seed', () => {
    expect(simulateMatch(g('TFT'), g('GRIM'), 150, 0.05, 42)).toEqual(simulateMatch(g('TFT'), g('GRIM'), 150, 0.05, 42));
  });
  it('without noise matches the exact payoff', () => {
    for (const [, a] of NAMED)
      for (const [, b] of NAMED) {
        const m = simulateMatch(a, b, 150, 0, 1);
        expect(m.rounds[149].total[0] / 150).toBeCloseTo(expectedMatch(a, b, 150, 0).pay1, 12);
      }
  });
  it('with noise, the mean of many matches approaches the exact payoff', () => {
    const rng = mulberry32(9);
    let s = 0;
    const N = 4000;
    for (let k = 0; k < N; k++) s += simulateMatch(g('TFT'), g('TFT'), 150, 0.01, Math.floor(rng() * 2 ** 32)).rounds[149].total[0] / 150;
    expect(Math.abs(s / N - pi(0.01, 'TFT', 'TFT'))).toBeLessThan(0.02);
  });
});
