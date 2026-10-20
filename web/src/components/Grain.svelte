<svg class="grain" aria-hidden="true">
  <filter id="grain">
    <feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" stitchTiles="stitch" />
    <feColorMatrix values="0 0 0 0 .45  0 0 0 0 .38  0 0 0 0 .28  0 0 0 .55 0" />
  </filter>
  <rect width="100%" height="100%" filter="url(#grain)" />
</svg>

<style>
  .grain {
    position: fixed;
    inset: 0;
    z-index: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    opacity: var(--grain);
  }
</style>
