<script>
  import { displayName, photoSrc } from '../lib/profile.svelte.js';

  let { size = 56 } = $props();

  const src = $derived(photoSrc());
  const initial = $derived(displayName().charAt(0).toUpperCase());
</script>

<span class="avatar" style:--size="{size}px" aria-hidden="true">
  {#if src}
    <img {src} alt="" />
  {:else}
    {initial}
  {/if}
</span>

<style>
  .avatar {
    display: inline-grid;
    flex: none;
    place-items: center;
    width: var(--size);
    height: var(--size);
    overflow: hidden;
    border-radius: 50%;
    background: var(--ink);
    color: var(--paper);
    font: 500 calc(var(--size) / 2) / 1 var(--serif);
  }

  img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
</style>
