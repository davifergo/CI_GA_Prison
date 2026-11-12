<script lang="ts">
  import { format2, label2, NAMED2, type Genome2 } from '../lib/model/memory2';
  import Genome2Grid from './Genome2Grid.svelte';

  let { value = $bindable(), legend, id }: { value: Genome2; legend: string; id: string } = $props();
  const named = $derived(NAMED2.find((x) => x.g === value)?.name ?? 'custom');
  let editing = $state(false);

  function choose(e: Event) {
    const g = NAMED2.find((x) => x.name === (e.currentTarget as HTMLSelectElement).value)?.g;
    if (g !== undefined) value = g;
  }
  const flip = (i: number) => (value = value ^ (1 << (17 - i)));
</script>

<fieldset class="picker">
  <legend class="kicker">{legend}</legend>
  <div class="row">
    <label class="visually-hidden" for={id}>{legend}: strategy</label>
    <select {id} value={named} onchange={choose}>
      {#each NAMED2 as x}<option value={x.name}>{x.name}</option>{/each}
      <option value="custom" disabled>Custom</option>
    </select>
    <button type="button" class="toggle" aria-expanded={editing} onclick={() => (editing = !editing)}>
      {editing ? 'Hide the 18 bits' : 'Edit the 18 bits'}
    </button>
  </div>
  <p class="bits mono" title={label2(value)}>{format2(value)}</p>
  {#if editing}
    <div class="editor"><Genome2Grid genome={value} onflip={flip} compact label="{legend}: genome (click a cell to flip it)" /></div>
  {/if}
</fieldset>

<style>
  .picker { border: 0; padding: 0; margin: 0; min-width: 0; }
  legend { padding: 0; margin-bottom: 0.1rem; }
  .row { display: flex; flex-wrap: wrap; align-items: end; gap: 0.4rem 0.9rem; }
  select { min-width: 8rem; font-family: var(--font-mono); font-size: 0.9rem; }
  .toggle { background: none; border: 0; padding: 0.2rem 0; min-height: 32px; cursor: pointer; font-style: italic; color: var(--ink-2);
    text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 3px; text-decoration-color: var(--brass); }
  .bits { margin: 0.25rem 0 0; font-size: 0.82rem; letter-spacing: 0.04em; color: var(--ink); white-space: nowrap; }
  .editor { margin-top: 0.4rem; }
</style>
