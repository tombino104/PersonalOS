<script>
  import { navigate } from '../lib/router.svelte.js';

  let { href, children, ...rest } = $props();

  function go(event) {
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(href);
  }
</script>

<a {href} onclick={go} {...rest}>{@render children?.()}</a>
