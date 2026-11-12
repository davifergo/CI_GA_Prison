<script lang="ts">
  // A memory-2 genome as the report writes it: the two opening moves, then a 4×4 table of
  // replies (rows: the outcome before last; columns: the last outcome). Own action first.
  import { bit2, type Genome2 } from '../lib/model/memory2';

  let {
    genome, active = -1, onflip, compact = false, label = 'Genome',
  }: { genome: Genome2; active?: number; onflip?: (i: number) => void; compact?: boolean; label?: string } = $props();
  const O = ['CC', 'CD', 'DC', 'DD'];
  const editable = $derived(!!onflip);
</script>

<div class="g2" class:compact class:editable role="group" aria-label={label}>
  <div class="opening">
    {#each [0, 1] as i}
      {@const a = bit2(genome, i)}
      <span class="lab">Round {i + 1}</span>
      {#if editable}
        <button type="button" class="cell" class:d={a === 1} class:on={active === i} onclick={() => onflip?.(i)}
          aria-label="Round {i + 1}: {a ? 'defect' : 'cooperate'} (click to flip)">{a ? 'D' : 'C'}</button>
      {:else}
        <span class="cell" class:d={a === 1} class:on={active === i}>{a ? 'D' : 'C'}</span>
      {/if}
    {/each}
  </div>
  <table>
    <thead>
      <tr><th class="corner"><span>before last</span><span>last →</span></th>{#each O as c}<th scope="col">{c}</th>{/each}</tr>
    </thead>
    <tbody>
      {#each O as r, pr}
        <tr>
          <th scope="row">{r}</th>
          {#each O as c, cu}
            {@const i = 2 + 4 * pr + cu}
            {@const a = bit2(genome, i)}
            <td>
              {#if editable}
                <button type="button" class="cell" class:d={a === 1} class:on={active === i} onclick={() => onflip?.(i)}
                  aria-label="After {r} then {c}: {a ? 'defect' : 'cooperate'} (click to flip)">{a ? 'D' : 'C'}</button>
              {:else}
                <span class="cell" class:d={a === 1} class:on={active === i} aria-label="After {r} then {c}: {a ? 'defect' : 'cooperate'}{active === i ? ' (rule applied this round)' : ''}">{a ? 'D' : 'C'}</span>
              {/if}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .g2 { --c: 1.75rem; display: grid; gap: 0.35rem; font-family: var(--font-mono); }
  .compact { --c: 1.35rem; }
  .opening { display: grid; grid-template-columns: auto var(--c) auto var(--c); gap: 0.3rem 0.45rem; align-items: center; justify-content: start; }
  .lab { font-family: var(--font-body); font-variant-caps: all-small-caps; letter-spacing: 0.06em; color: var(--ink-2); font-size: 0.85rem; }
  table { border-collapse: separate; border-spacing: 2px; }
  th { font-weight: 400; font-size: 0.68rem; color: var(--ink-3); padding: 0 0.2rem; }
  thead th { text-align: center; }
  tbody th { text-align: right; }
  .corner { display: grid; text-align: left; font-family: var(--font-body); font-style: italic; font-size: 0.66rem; line-height: 1.05; padding: 0 0.25rem 0 0; }
  .compact .corner span:first-child { display: none; }
  td { padding: 0; }
  .cell {
    display: grid;
    place-items: center;
    width: var(--c);
    height: var(--c);
    padding: 0;
    font: inherit;
    font-weight: 600;
    font-size: 0.8rem;
    background: var(--coop-tint);
    color: var(--coop);
    border: 1px solid color-mix(in srgb, var(--coop) 50%, transparent);
    border-radius: 1px;
    transition: background-color 160ms var(--ease-ink), outline-color 160ms var(--ease-ink);
  }
  .compact .cell { font-size: 0.7rem; }
  .cell.d { background: var(--defect); color: var(--paper); border-color: var(--defect); }
  .cell.on { outline: 2.5px solid var(--brass); outline-offset: 1px; }
  button.cell { cursor: pointer; }
  button.cell:hover { outline: 1px solid var(--ink); outline-offset: 1px; }
</style>
