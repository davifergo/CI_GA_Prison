import { describe, expect, it } from 'vitest';
import fx from './__fixtures__/python_m2.json';
import { DEFAULT_PARAMS } from './ga';
import { classify2, expectedMatch2, format2, GA2, NAMED2, parse2, simulateMatch2, TF2T } from './memory2';

const named = (n: string) => NAMED2.find((x) => x.name === n)!.g;
const pi = (p: number, a: string, b: string) => expectedMatch2(named(a), named(b), 150, p).pay1;

describe('memory 2: encoding', () => {
  it('reads and writes the report notation', () => {
    expect(format2(parse2('10|0110 1111 1111 0110'))).toBe('10 | 0110 1111 1111 0110');
  });
  it('classifies like main_memory2.classify', () => {
    for (const [bits, name] of fx.classify) expect(classify2(parseInt(bits, 2))).toBe(name);
    expect(classify2(TF2T)).toBe('TF2T');
  });
});

describe('memory 2: values quoted in the report', () => {
  const cases: [number, string, string, number][] = [
    [0.01, 'PAV2', 'PAV2', 2.9],    // "2.90 against itself"
    [0.01, 'ALLD', 'PAV2', 2.33],   // "ALLD obtains 2.33 against it"
    [0.05, 'PAV2D', 'PAV2D', 2.6],  // "2.60 against itself"
    [0.05, 'GRIM1', 'GRIM1', 2.65], // "what it obtains against itself (2.65)"
  ];
  for (const [p, a, b, want] of cases)
    it(`p=${p}: ${a} vs ${b} = ${want}`, () => expect(pi(p, a, b)).toBeCloseTo(want, 2));
  it('p=0.05: the one-bit mutant of GRIM1 earns 0.13 more against it, and 1.97 against itself', () => {
    const mut = parse2('11|0111 0111 0111 0001');
    expect(expectedMatch2(mut, named('GRIM1'), 150, 0.05).pay1 - pi(0.05, 'GRIM1', 'GRIM1')).toBeCloseTo(0.13, 2);
    expect(expectedMatch2(mut, mut, 150, 0.05).pay1).toBeCloseTo(1.97, 2);
  });
});

describe('memory 2: agreement with main_memory2.py', () => {
  for (const P of fx.pairs)
    it(`expected payoff of ${P.g1.length} pairs, p=${P.p}`, () => {
      let maxDiff = 0;
      P.g1.forEach((a, i) => {
        const r = expectedMatch2(parseInt(a, 2), parseInt(P.g2[i], 2), 150, P.p);
        maxDiff = Math.max(maxDiff, Math.abs(r.pay1 - P.f1[i]), Math.abs(r.pay2 - P.f2[i]));
      });
      expect(maxDiff).toBeLessThan(1e-12);
    });

  // With noise the trajectory is reproducible (the report says so across machines too).
  // Without noise exact fitness ties make it depend on the last bit of floating point
  // (see Limitations in the report), so only the first generations are compared.
  for (const run of fx.runs) {
    const gens = run.p_noise === 0 ? 30 : run.mean_payoff.length - 1;
    it(`GA seed ${run.seed}, p=${run.p_noise}: ${gens} generations`, () => {
      const ga = new GA2({ ...DEFAULT_PARAMS, seed: run.seed, pNoise: run.p_noise });
      const hist = ga.run(gens);
      hist.forEach((h, i) => {
        expect(h.meanPayoff, `gen ${i}`).toBeCloseTo(run.mean_payoff[i], 12);
        expect(h.nDistinct, `gen ${i}`).toBe(run.n_distinct[i]);
        expect('g' + h.top[0].g.toString(2).padStart(18, '0'), `gen ${i}`).toBe(run.top_genome[i]);
      });
    }, 60_000);
  }
});

describe('memory 2: simulated match', () => {
  it('uses round-1 and round-2 bits, then the last two outcomes', () => {
    // PAV2 = 10|0110 1111 1111 0110 against ALLD: D, C (unconditional), then by state
    // DD,CD -> bit 15 (D); CD,DD -> bit 9 (D); DD,DD -> bit 17 (C); DD,CD -> bit 15 (D)
    const m = simulateMatch2(named('PAV2'), named('ALLD'), 6, 0, 1);
    expect(m.rounds.map((r) => r.rule[0])).toEqual([0, 1, 2 + 4 * 3 + 1, 2 + 4 * 1 + 3, 2 + 4 * 3 + 3, 2 + 4 * 3 + 1]);
    expect(m.rounds.map((r) => r.played[0])).toEqual([1, 0, 1, 1, 0, 1]);
  });
  it('without noise matches the exact payoff', () => {
    for (const a of NAMED2) for (const b of NAMED2) {
      const m = simulateMatch2(a.g, b.g, 150, 0, 3);
      expect(m.rounds[149].total[0] / 150).toBeCloseTo(expectedMatch2(a.g, b.g, 150, 0).pay1, 12);
    }
  });
});
