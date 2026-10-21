<script>
  import Link from '../components/Link.svelte';
  import ResetForm from '../components/ResetForm.svelte';
  import { t } from '../lib/i18n.svelte.js';
</script>

<main class="page bare">
  <div class="content narrow reset stagger">
    <header>
      <div class="eyebrow">Personal OS</div>
      <h1 class="title">{t('reset.title')}</h1>
      <p class="lede">{t('reset.lede')}</p>
    </header>

    <ResetForm onreset={() => location.assign('/')} />

    <Link class="back" href="/">
      <svg class="icon small" viewBox="0 0 24 24" aria-hidden="true"><path d="m14.5 6-6 6 6 6" /></svg>{t('reset.back')}
    </Link>
  </div>
</main>

<style>
  .reset {
    justify-content: center;
  }
</style>
