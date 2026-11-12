<script lang="ts">
  // Payoff matrix of a list of genomes: the row player's exact expected payoff per round.
  let {
    ids, pay, name, full, named, compact = false,
  }: {
    ids: number[];
    /** pay(i, j): payoff of ids[i] against ids[j] */
    pay: (i: number, j: number) => number;
    /** short label for the axes */
    name: (g: number) => string;
    /** full description for the tooltip */
    full: (g: number) => string;
    /** marked in brass on a compact matrix */
    named?: (g: number) => boolean;
    compact?: boolean;
  } = $props();
  const n = $derived(ids.length);
  const C = $derived(compact ? 17 : n > 7 ? 50 : 58);
  const LBL = $derived(compact ? 46 : 62);
  const W = $derived(LBL + n * C + (compact ? 34 : 74));
  const H = $derived(LBL + n * C + 4);
  // ink density: 0 → paper, 5 → full ink
  const shade = (v: number) => Math.max(0, Math.min(1, v / 5));
  const rowMean = $derived(ids.map((_, i) => ids.reduce((s, _g, j) => s + pay(i, j), 0) / n));
  let hover: { i: number; j: number } | null = $state(null);
</script>

<div class="wrap">
  <div class="scroll">
    <svg viewBox="0 0 {W} {H}" width={compact ? W : undefined} height={compact ? H : undefined}
      style={compact ? '' : `width:100%;max-width:${W}px;height:auto`} role="img" aria-label="Payoff matrix" onpointerleave={() => (hover = null)}>
      {#each ids as g, c}
        <text x={LBL + c * C + C / 2} y={LBL - 6} class="lab" class:hl={hover?.j === c} class:named={compact && !!named?.(g)}
          transform={compact || n > 7 ? `rotate(-50 ${LBL + c * C + C / 2} ${LBL - 6})` : ''} text-anchor={compact || n > 7 ? 'start' : 'middle'}>{name(g)}</text>
        <text x={LBL - 5} y={LBL + c * C + C / 2 + 3} class="lab" class:hl={hover?.i === c} class:named={compact && !!named?.(g)} text-anchor="end">{name(g)}</text>
      {/each}
      {#each ids as _r, r}
        {#each ids as _c, c}
          {@const v = pay(r, c)}
          <rect x={LBL + c * C} y={LBL + r * C} width={C} height={C} class="cell" style="fill-opacity:{shade(v)}"
            onpointerenter={() => (hover = { i: r, j: c })} role="presentation" />
          {#if !compact}
            <text x={LBL + c * C + C / 2} y={LBL + r * C + C / 2 + 4} class="val" class:inv={shade(v) > 0.5}>{v.toFixed(2)}</text>
          {/if}
        {/each}
        {#if !compact}
          <text x={LBL + n * C + 10} y={LBL + r * C + C / 2 + 4} class="mean">{rowMean[r].toFixed(2)}</text>
        {/if}
      {/each}
      {#if !compact}<text x={LBL + n * C + 10} y={LBL - 6} class="lab">row mean</text>{/if}
      {#if hover}
        <rect x={LBL + hover.j * C} y={LBL + hover.i * C} width={C} height={C} class="hover" />
      {/if}
    </svg>
  </div>
  <p class="caption tip" aria-live="polite">
    {#if hover}
      {full(ids[hover.i])} against {full(ids[hover.j])}:
      <span class="mono">{pay(hover.i, hover.j).toFixed(3)}</span> per round; the column player gets
      <span class="mono">{pay(hover.j, hover.i).toFixed(3)}</span>.
    {:else}
      Point at a cell for both payoffs of the pair.{#if compact && named} Named strategies are marked in brass.{/if}
    {/if}
  </p>
</div>

<style>
  .scroll { overflow-x: auto; max-width: 100%; padding-bottom: 0.3rem; }
  svg { display: block; max-width: none; }
  .cell { fill: var(--ink); stroke: var(--paper); stroke-width: 1; }
  .hover { fill: none; stroke: var(--brass); stroke-width: 2.4; pointer-events: none; }
  .lab { font-family: var(--font-mono); font-size: 10px; fill: var(--ink-2); }
  .lab.hl { fill: var(--ink); font-weight: 700; }
  .lab.named { fill: var(--brass-text); font-weight: 700; }
  .val { font-family: var(--font-mono); font-size: 12px; text-anchor: middle; fill: var(--ink); pointer-events: none; }
  .val.inv { fill: var(--paper); }
  .mean { font-family: var(--font-mono); font-size: 12px; fill: var(--ink); }
  .tip { min-height: 2.8em; }
</style>
