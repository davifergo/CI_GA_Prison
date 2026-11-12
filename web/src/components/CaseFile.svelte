<script lang="ts">
  import { bit, bitString, isNamed, label, type Genome } from '../lib/model/game';
  import { RULE_CODES, RULE_SITUATIONS } from '../lib/model/analysis';
  import { STYLE } from '../lib/strategies';
  import Manicule from './Manicule.svelte';

  let { genome, side, active = -1, letter }: { genome: Genome; side: 'left' | 'right'; active?: number; letter: string } =
    $props();
  const NUMERALS = ['I', 'II', 'III', 'IV', 'V'];
  const name = $derived(label(genome));
  const blurb = $derived(isNamed(genome) ? STYLE[name as keyof typeof STYLE]?.blurb : 'an unnamed memory-one strategy');
</script>

<article class="file {side}" aria-label="Case file of defendant {letter}">
  <header>
    <span class="tab kicker">Case file · Defendant {letter}</span>
    <h3>{name}</h3>
    <p class="genome"><span class="mono">{bitString(genome)}</span> <span class="blurb">— {blurb}</span></p>
  </header>
  <ol>
    {#each RULE_SITUATIONS as sit, i}
      {@const a = bit(genome, i)}
      <li class:active={active === i}>
        <span class="hand" aria-hidden="true">{#if active === i}<Manicule />{/if}</span>
        <span class="n">{NUMERALS[i]}.</span>
        <span class="sit">{sit}{#if i > 0}<span class="code mono">{RULE_CODES[i]}</span>{/if}</span>
        <span class="act" class:d={a === 1}>{a ? 'defects' : 'cooperates'}</span>
        {#if active === i}<span class="visually-hidden">(rule applied this round)</span>{/if}
      </li>
    {/each}
  </ol>
</article>

<style>
  .file {
    position: relative;
    background: var(--paper-2);
    border: 1px solid var(--rule-strong);
    padding: 0.7rem 0.8rem 0.55rem;
    /* a slightly uneven sheet: one dog-eared corner */
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
  header { border-bottom: 1px solid var(--rule); padding-bottom: 0.35rem; margin-bottom: 0.3rem; }
  .tab { display: block; font-size: 0.8rem; }
  h3 { font-size: 1.55rem; margin: 0.05rem 0 0.1rem; }
  .genome { margin: 0; font-size: 0.82rem; color: var(--ink-2); line-height: 1.3; }
  .genome .mono { color: var(--ink); font-size: 0.86rem; letter-spacing: 0.08em; }
  ol { list-style: none; margin: 0; padding: 0; }
  li {
    display: grid;
    grid-template-columns: 1.3rem 1.5rem 1fr auto;
    align-items: baseline;
    gap: 0.25rem;
    padding: 0.18rem 0.2rem 0.18rem 0;
    font-size: 0.86rem;
    line-height: 1.25;
    border-bottom: 1px dotted var(--rule);
    transition: background-color 180ms var(--ease-ink);
  }
  li:last-child { border-bottom: 0; }
  li.active { background: var(--brass-tint); }
  .hand { width: 1.35rem; height: 0.9rem; align-self: center; color: var(--ink); }
  .n { font-family: var(--font-display); color: var(--ink-3); }
  .code { font-size: 0.7rem; color: var(--ink-3); margin-left: 0.35em; white-space: nowrap; }
  .act { font-style: italic; color: var(--coop); text-align: right; }
  .act.d { color: var(--defect); }
  li.active .sit { font-weight: 600; }
</style>
