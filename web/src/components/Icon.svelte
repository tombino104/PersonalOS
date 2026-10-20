<script>
  import { icons } from '../lib/icons.js';

  let { name, small = false } = $props();
</script>

<svg class="icon" class:small viewBox="0 0 24 24" aria-hidden="true">
  {#each icons[name] as shape}
    <svelte:element this={shape.tag} {...shape.attrs} />
  {/each}
</svg>
