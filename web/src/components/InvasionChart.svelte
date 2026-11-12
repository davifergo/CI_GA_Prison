<script lang="ts">
  let { traces, invaded, grew, mutant, k0 }: { traces: number[][]; invaded: number; grew: number; mutant: string; k0: number } = $props();
  let cw = $state(520);
  const W = $derived(Math.max(280, Math.min(640, cw)));
  const H = 200, L = 34, R = 12, T = 10, B = 26;
  const gens = $derived(traces[0]?.length ? traces[0].length - 1 : 1);
  const x = (g: number) => L + (g / gens) * (W - L - R);
  const y = (f: number) => T + (1 - f) * (H - T - B);
  const path = (tr: number[]) => 'M' + tr.map((f, g) => `${x(g).toFixed(1)} ${y(f).toFixed(1)}`).join('L');
  const median = $derived.by(() => {
    if (!traces.length) return [];
    return traces[0].map((_, g) => {
      const v = traces.map((t) => t[g]).sort((a, b) => a - b);
      return v[Math.floor(v.length / 2)];
    });
  });
</script>

<figure bind:clientWidth={cw}>
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Share of {mutant} per generation in {traces.length} runs; {invaded} ended above one half">
    {#each [0, 0.5, 1] as f}
      <line x1={L} x2={W - R} y1={y(f)} y2={y(f)} class={f === 0.5 ? 'half' : 'grid'} />
      <text x={L - 5} y={y(f) + 3} class="ax" text-anchor="end">{f * 100}%</text>
    {/each}
    <line x1={L} x2={W - R} y1={y(k0)} y2={y(k0)} class="start" />
    {#each traces as tr}<path d={path(tr)} class="tr" />{/each}
    {#if median.length}<path d={path(median)} class="med" />{/if}
    <text x={x(0)} y={H - 8} class="ax">0</text>
    <text x={x(gens)} y={H - 8} class="ax" text-anchor="end">{gens} generations</text>
  </svg>
  <figcaption class="caption">
    Share of {mutant} in {traces.length} runs (thin lines; thick: the median run). The dashed line is the starting share.
    {mutant} grew from its starting share within 10 generations in <strong>{grew} of {traces.length}</strong> runs and holds over half
    the gallery at the end in <strong>{invaded}</strong>. Invading means growing while rare; a mutant that does badly against
    itself can invade and still never take over.
  </figcaption>
</figure>

<style>
  figure { margin: 0.6rem 0 0; max-width: 640px; }
  svg { width: 100%; height: auto; display: block; }
  .grid { stroke: var(--rule); stroke-width: 0.6; }
  .half { stroke: var(--ink-3); stroke-width: 0.7; }
  .start { stroke: var(--brass); stroke-width: 1; stroke-dasharray: 4 3; }
  .ax { font-family: var(--font-mono); font-size: 10px; fill: var(--ink-3); }
  .tr { fill: none; stroke: var(--defect); stroke-width: 0.8; opacity: 0.4; }
  .med { fill: none; stroke: var(--ink); stroke-width: 2; }
</style>
