<script lang="ts">
  // Cumulative score of both defendants, against the exact expectation ("precedent").
  import type { Round } from '../lib/model/match';

  let {
    rounds, t, expected, names,
  }: { rounds: Round[]; t: number; expected: { c1: number[]; c2: number[] }; names: [string, string] } = $props();

  const W = 300, H = 200, L = 30, Rm = 62, Tm = 8, B = 28;
  const n = $derived(rounds.length);
  const yMax = $derived(Math.max(5, Math.ceil(Math.max(rounds[n - 1].total[0], rounds[n - 1].total[1], expected.c1[n - 1], expected.c2[n - 1]) / 50) * 50));
  const x = (i: number) => L + ((i + 1) / n) * (W - L - Rm);
  const y = (v: number) => Tm + (1 - v / yMax) * (H - Tm - B);
  const line = (vals: number[], upto: number) =>
    'M' + x(-1) + ' ' + y(0) + vals.slice(0, upto + 1).map((v, i) => `L${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join('');
  const shown = $derived(Math.max(-1, t));
  const yTicks = $derived(Array.from({ length: 6 }, (_, i) => (i * yMax) / 5));
  const last = $derived(shown >= 0 ? rounds[shown].total : [0, 0]);
  // end labels: keep them apart when the lines finish close together
  const labelY = $derived.by(() => {
    let a = y(last[0]), b = y(last[1]);
    if (Math.abs(a - b) < 13) { const m = (a + b) / 2; const s = a <= b ? -6.5 : 6.5; a = m + s; b = m - s; }
    return [a, b];
  });
</script>

<figure class="chart">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Cumulative score: {names[0]} {last[0]}, {names[1]} {last[1]} after {shown + 1} rounds">
    {#each yTicks as v}
      <line x1={L} x2={W - Rm} y1={y(v)} y2={y(v)} class="grid" />
      <text x={L - 5} y={y(v) + 3} class="ax" text-anchor="end">{v}</text>
    {/each}
    {#each [0, Math.floor(n / 2), n - 1] as i}
      <text x={x(i)} y={H - B + 14} class="ax" text-anchor="middle">{i + 1}</text>
    {/each}
    <text x={(L + W - Rm) / 2} y={H - 2} class="ax" text-anchor="middle">round</text>

    <!-- precedent: expected cumulative score over all possible errors -->
    <path d={line(expected.c1, n - 1)} class="exp a" />
    <path d={line(expected.c2, n - 1)} class="exp b" />

    {#if shown >= 0}
      <path d={line(rounds.map((r) => r.total[0]), shown)} class="obs a" />
      <path d={line(rounds.map((r) => r.total[1]), shown)} class="obs b" />
      <circle cx={x(shown)} cy={y(last[0])} r="2.6" class="dot a" />
      <circle cx={x(shown)} cy={y(last[1])} r="2.6" class="dot b" />
      <text x={W - Rm + 6} y={labelY[0] + 4} class="end a">{names[0]} {last[0]}</text>
      <text x={W - Rm + 6} y={labelY[1] + 4} class="end b">{names[1]} {last[1]}</text>
    {/if}
  </svg>
  <figcaption class="caption">
    Solid: points so far (left defendant in ink, right in brass). Dotted: precedent, the expected total
    averaged over every possible sequence of clerk’s errors.
  </figcaption>
</figure>

<style>
  .chart { margin: 0; }
  svg { width: 100%; height: auto; display: block; overflow: visible; }
  .grid { stroke: var(--rule); stroke-width: 0.6; }
  .ax { font-family: var(--font-mono); font-size: 10px; fill: var(--ink-3); }
  .exp { fill: none; stroke-width: 1.1; stroke-dasharray: 1.5 2.6; stroke-linecap: round; }
  .obs { fill: none; stroke-width: 1.8; stroke-linejoin: round; }
  .a { stroke: var(--ink); }
  .b { stroke: var(--brass); }
  .obs.b { stroke-width: 2.4; }
  .dot.a { fill: var(--ink); stroke: none; }
  .dot.b { fill: var(--brass); stroke: none; }
  .end { font-family: var(--font-mono); font-size: 10.5px; stroke: none; font-weight: 600; }
  .end.a { fill: var(--ink); }
  .end.b { fill: var(--brass-text); }
  figcaption { margin-top: 0.3rem; }
</style>
