<script lang="ts">
  import { bit, bitString, label, NAMED, type Genome } from '../lib/model/game';
  import { RULE_CODES } from '../lib/model/analysis';

  let { value = $bindable(), legend, id }: { value: Genome; legend: string; id: string } = $props();

  const named = $derived(NAMED.find(([, g]) => g === value)?.[0] ?? 'custom');
  const BIT_LABELS = ['1st', ...RULE_CODES.slice(1)];

  function choose(e: Event) {
    const v = (e.currentTarget as HTMLSelectElement).value;
    const g = NAMED.find(([n]) => n === v)?.[1];
    if (g !== undefined) value = g;
  }
  const flip = (i: number) => (value = value ^ (1 << (4 - i)));
</script>

<fieldset class="picker">
  <legend class="kicker">{legend}</legend>
  <div class="row">
    <label class="visually-hidden" for={id}>{legend}: named strategy</label>
    <select {id} value={named} onchange={choose}>
      {#each NAMED as [n, g]}
        <option value={n}>{n} · {bitString(g)}</option>
      {/each}
      <option value="custom" disabled>Custom · {bitString(value)}</option>
    </select>
    <div class="bits" role="group" aria-label="{legend}: genome bits (click to flip)">
      {#each BIT_LABELS as b, i}
        {@const a = bit(value, i)}
        <button
          type="button"
          class="bit"
          class:d={a === 1}
          onclick={() => flip(i)}
          aria-label="{b === '1st' ? 'first move' : 'after ' + b}: {a ? 'defect' : 'cooperate'}"
          title="{b === '1st' ? 'First move' : 'After ' + b}: {a ? 'D' : 'C'} (click to flip)"
        >
          <span class="v">{a}</span>
          <span class="k">{b}</span>
        </button>
      {/each}
    </div>
  </div>
  <span class="visually-hidden" aria-live="polite">{label(value)}</span>
</fieldset>

<style>
  .picker { border: 0; padding: 0; margin: 0; min-width: 0; }
  legend { padding: 0; margin-bottom: 0.1rem; }
  .row { display: flex; flex-wrap: wrap; align-items: end; gap: 0.5rem 0.9rem; }
  select { min-width: 9.5rem; font-family: var(--font-mono); font-size: 0.9rem; }
  .bits { display: flex; gap: 3px; }
  .bit {
    display: grid;
    justify-items: center;
    width: 2.15rem;
    padding: 0.1rem 0 0.15rem;
    background: var(--coop-tint);
    color: var(--coop);
    border: 1px solid var(--coop);
    border-radius: 1px;
    cursor: pointer;
    line-height: 1.1;
  }
  .bit.d { background: var(--defect); color: var(--paper); border-color: var(--defect); }
  .bit .v { font-family: var(--font-mono); font-weight: 600; font-size: 0.95rem; }
  .bit .k { font-family: var(--font-mono); font-size: 0.62rem; opacity: 0.85; }
  .bit:hover { outline: 1px solid var(--ink); outline-offset: 1px; }
</style>
