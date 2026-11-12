<script lang="ts">
  import { STYLE, type Column } from '../lib/strategies';
  let { col, size = 14 }: { col: Column; size?: number } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 14 14" aria-hidden="true">
  <rect x="0.5" y="0.5" width="13" height="13" style="fill:{STYLE[col].fill}" />
</svg>

<style>
  svg { flex: none; display: inline-block; vertical-align: -2px; }
  rect { stroke: var(--ink); stroke-width: 1; }
</style>
