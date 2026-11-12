<script lang="ts">
  import { bit2, format2, label2, NAMED2, ruleSituation2, type Genome2 } from '../lib/model/memory2';
  import Genome2Grid from './Genome2Grid.svelte';
  import Manicule from './Manicule.svelte';

  let { genome, active = -1, letter }: { genome: Genome2; side: 'left' | 'right'; active?: number; letter: string } = $props();
  const named = $derived(NAMED2.find((x) => x.g === genome));
  const name = $derived(named?.name ?? (label2(genome).endsWith('-like') ? label2(genome) : 'Unnamed'));
</script>

<article class="file" aria-label="Case file of defendant {letter}">
  <header>
    <span class="tab kicker">Case file · Defendant {letter} · memory two</span>
    <h3>{name}</h3>
    <p class="genome"><span class="mono">{format2(genome)}</span></p>
    {#if named}<p class="blurb">{named.blurb}</p>{/if}
  </header>
  <Genome2Grid {genome} {active} label="Rules of defendant {letter}" />
  <p class="now" aria-live="off">
    {#if active >= 0}
      <span class="hand" aria-hidden="true"><Manicule /></span>
      <span>{ruleSituation2(active)}: <em class:d={bit2(genome, active) === 1}>{bit2(genome, active) ? 'defects' : 'cooperates'}</em></span>
    {:else}
      <span class="caption">Rows: the round before last. Columns: the last round. Own move first.</span>
    {/if}
  </p>
</article>

<style>
  .file {
    position: relative;
    background: var(--paper-2);
    border: 1px solid var(--rule-strong);
    padding: 0.7rem 0.8rem 0.55rem;
    clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%);
  }
  .file::after {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 14px;
    height: 14px;
    background: linear-gradient(225deg, var(--paper) 50%, var(--paper-3) 50%);
    border-left: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
  }
  header { border-bottom: 1px solid var(--rule); padding-bottom: 0.35rem; margin-bottom: 0.45rem; }
  .tab { display: block; font-size: 0.78rem; }
  h3 { font-size: 1.55rem; margin: 0.05rem 0 0.1rem; }
  .genome { margin: 0; font-size: 0.8rem; white-space: nowrap; }
  .blurb { margin: 0.15rem 0 0; font-size: 0.8rem; color: var(--ink-2); line-height: 1.3; }
  .now { display: flex; align-items: center; gap: 0.35rem; min-height: 2.6em; margin: 0.45rem 0 0; font-size: 0.86rem; line-height: 1.25; }
  .hand { width: 1.35rem; height: 0.9rem; flex: none; }
  em { color: var(--coop); }
  em.d { color: var(--defect); }
</style>
