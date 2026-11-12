<!--
  Shared SVG definitions: one hatching pattern per strategy, the pen-line roughening filter,
  and the paper grain. Rendered once (hidden) by App; any inline SVG can use url(#id).
-->
<script lang="ts"></script>

<svg class="defs" aria-hidden="true" width="0" height="0" focusable="false">
  <defs>
    <!-- ALLC: sparse single hatching on pale verdigris -->
    <pattern id="pat-allc" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect width="6" height="6" class="p-coop-tint" />
      <line x1="0" y1="0" x2="0" y2="6" class="p-coop-line" stroke-width="1.1" />
    </pattern>
    <!-- TFT: solid verdigris -->
    <pattern id="pat-tft" width="6" height="6" patternUnits="userSpaceOnUse">
      <rect width="6" height="6" class="p-coop" />
    </pattern>
    <!-- PAVLOV: cross-hatched verdigris -->
    <pattern id="pat-pavlov" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect width="5" height="5" class="p-coop-tint" />
      <line x1="0" y1="0" x2="0" y2="5" class="p-coop-line" stroke-width="1.6" />
      <line x1="0" y1="0" x2="5" y2="0" class="p-coop-line" stroke-width="1.6" />
    </pattern>
    <!-- GRIM: cross-hatched oxblood -->
    <pattern id="pat-grim" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect width="5" height="5" class="p-defect-tint" />
      <line x1="0" y1="0" x2="0" y2="5" class="p-defect-line" stroke-width="1.6" />
      <line x1="0" y1="0" x2="5" y2="0" class="p-defect-line" stroke-width="1.6" />
    </pattern>
    <!-- STFT: brass with horizontal rules -->
    <pattern id="pat-stft" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="4" class="p-brass-tint" />
      <line x1="0" y1="1" x2="4" y2="1" class="p-brass-line" stroke-width="1.4" />
    </pattern>
    <!-- ALLD: solid oxblood -->
    <pattern id="pat-alld" width="6" height="6" patternUnits="userSpaceOnUse">
      <rect width="6" height="6" class="p-defect" />
    </pattern>
    <!-- OTHER: ink stipple on paper -->
    <pattern id="pat-other" width="5" height="5" patternUnits="userSpaceOnUse">
      <rect width="5" height="5" class="p-paper" />
      <circle cx="1.2" cy="1.2" r="0.65" class="p-ink" />
      <circle cx="3.7" cy="3.7" r="0.65" class="p-ink" />
    </pattern>

    <!-- memory two: the most frequent genomes get a hatching each (slot 0..5), in the colour
         of their family (how much they earn against themselves: coop / brass / defect) -->
    {#each ['coop', 'brass', 'defect'] as fam}
      <pattern id="pat-s0-{fam}" width="6" height="6" patternUnits="userSpaceOnUse">
        <rect width="6" height="6" class="p-{fam}" />
      </pattern>
      <pattern id="pat-s1-{fam}" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="5" height="5" class="p-{fam}-tint" /><line x1="0" y1="0" x2="0" y2="5" class="p-{fam}-line" stroke-width="1.8" />
      </pattern>
      <pattern id="pat-s2-{fam}" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="5" height="5" class="p-{fam}-tint" /><line x1="0" y1="0" x2="0" y2="5" class="p-{fam}-line" stroke-width="1.5" /><line x1="0" y1="0" x2="5" y2="0" class="p-{fam}-line" stroke-width="1.5" />
      </pattern>
      <pattern id="pat-s3-{fam}" width="4" height="4" patternUnits="userSpaceOnUse">
        <rect width="4" height="4" class="p-{fam}-tint" /><line x1="0" y1="1" x2="4" y2="1" class="p-{fam}-line" stroke-width="1.5" />
      </pattern>
      <pattern id="pat-s4-{fam}" width="4" height="4" patternUnits="userSpaceOnUse">
        <rect width="4" height="4" class="p-{fam}-tint" /><circle cx="2" cy="2" r="1.1" class="p-{fam}-dot" />
      </pattern>
      <pattern id="pat-s5-{fam}" width="4" height="4" patternUnits="userSpaceOnUse">
        <rect width="4" height="4" class="p-{fam}-tint" /><line x1="1" y1="0" x2="1" y2="4" class="p-{fam}-line" stroke-width="1.5" />
      </pattern>
    {/each}

    <!-- shading for the illustration: fine single and cross hatching in ink -->
    <pattern id="hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(-50)">
      <line x1="0" y1="0" x2="0" y2="4" class="p-ink-line" stroke-width="0.7" />
    </pattern>
    <pattern id="hatch-wide" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(-50)">
      <line x1="0" y1="0" x2="0" y2="7" class="p-ink-line" stroke-width="0.6" />
    </pattern>
    <pattern id="xhatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(40)">
      <line x1="0" y1="0" x2="0" y2="4" class="p-ink-line" stroke-width="0.8" />
      <line x1="0" y1="0" x2="4" y2="0" class="p-ink-line" stroke-width="0.8" />
    </pattern>
    <pattern id="xhatch-dense" width="3" height="3" patternUnits="userSpaceOnUse" patternTransform="rotate(40)">
      <line x1="0" y1="0" x2="0" y2="3" class="p-ink-line" stroke-width="1.1" />
      <line x1="0" y1="0" x2="3" y2="0" class="p-ink-line" stroke-width="1.1" />
    </pattern>
    <pattern id="vgrain" width="9" height="40" patternUnits="userSpaceOnUse">
      <path d="M2 0 C2.6 10 1.4 22 2.2 40 M6 0 C5.4 14 6.7 26 5.8 40" class="p-ink-line" stroke-width="0.45" fill="none" />
    </pattern>

    <!-- slight wobble of pen strokes -->
    <filter id="pen" x="-5%" y="-5%" width="110%" height="110%">
      <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="n" />
      <feDisplacementMap in="SourceGraphic" in2="n" scale="2.2" xChannelSelector="R" yChannelSelector="G" />
    </filter>
    <filter id="pen-strong" x="-5%" y="-5%" width="110%" height="110%">
      <feTurbulence type="fractalNoise" baseFrequency="0.06" numOctaves="2" seed="3" result="n" />
      <feDisplacementMap in="SourceGraphic" in2="n" scale="3" xChannelSelector="R" yChannelSelector="G" />
    </filter>
  </defs>
</svg>

<style>
  .defs { position: absolute; width: 0; height: 0; overflow: hidden; }
  .defs :global(.p-coop) { fill: var(--coop); }
  .defs :global(.p-coop-tint) { fill: var(--coop-tint); }
  .defs :global(.p-coop-line) { stroke: var(--coop); }
  .defs :global(.p-defect) { fill: var(--defect); }
  .defs :global(.p-defect-tint) { fill: var(--defect-tint); }
  .defs :global(.p-defect-line) { stroke: var(--defect); }
  .defs :global(.p-brass-tint) { fill: var(--brass-tint); }
  .defs :global(.p-brass-line) { stroke: var(--brass); }
  .defs :global(.p-brass) { fill: var(--brass); }
  .defs :global(.p-coop-dot) { fill: var(--coop); }
  .defs :global(.p-defect-dot) { fill: var(--defect); }
  .defs :global(.p-brass-dot) { fill: var(--brass); }
  .defs :global(.p-paper) { fill: var(--paper); }
  .defs :global(.p-ink) { fill: var(--ink); }
  .defs :global(.p-ink-line) { stroke: var(--ink); }
</style>
