<script lang="ts">
  // The printer's pointing hand (☞), drawn as a small engraving.
  let { flip = false }: { flip?: boolean } = $props();
</script>

<svg viewBox="0 0 34 18" width="100%" height="100%" class:flip aria-hidden="true">
  <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
    <!-- cuff -->
    <path d="M1.5 4.2 L6.2 4.2 L6.2 14.6 L1.5 14.6 Z" stroke-width="1.1" />
    <path d="M2.6 5.6 L2.6 13.2 M4 5.6 L4 13.2" stroke-width="0.5" />
    <!-- back of the hand and the pointing finger -->
    <path d="M6.2 5.4 C9 4.4 11 3.6 13.6 4.3 L31.2 4.6 C32.6 4.7 32.8 6.9 31.2 7 L17.6 7.1" stroke-width="1.1" />
    <!-- curled fingers -->
    <path d="M17.6 7.1 C19.3 7.2 19.6 9.5 17.7 9.6 L15.4 9.6 C17.2 9.8 17.3 11.9 15.4 12 L14 12 C15.6 12.2 15.5 14.2 13.8 14.3 L10.6 14.4 C9 14.6 7.6 14.4 6.2 13.6" stroke-width="1.1" />
    <!-- thumb -->
    <path d="M13.6 4.3 C12.6 5.6 12.8 7 14.6 7.1 L17.6 7.1" stroke-width="0.9" />
    <!-- shading -->
    <path d="M8 12.6 L10 9.4 M9.6 12.9 L11.4 10.1 M11.2 13.2 L12.6 11" stroke-width="0.45" />
  </g>
</svg>

<style>
  svg { display: block; }
  .flip { transform: scaleX(-1); }
</style>
