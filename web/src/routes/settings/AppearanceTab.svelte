<script>
  import { i18n, setLanguage, t } from '../../lib/i18n.svelte.js';
  import { setTheme, theme } from '../../lib/theme.svelte.js';

  const themes = [
    ['light', 'settings.themeLight'],
    ['dark', 'settings.themeDark'],
    ['auto', 'settings.themeAuto'],
  ];
  const languages = [
    ['en', 'settings.languageEn'],
    ['it', 'settings.languageIt'],
    ['auto', 'settings.languageAuto'],
  ];
</script>

<section class="card panel" aria-label={t('settings.appearance')}>
  <h2>{t('settings.appearance')}</h2>
  <p class="desc">{t('settings.appearanceLede')}</p>
  <span class="label" id="theme-label">{t('settings.theme')}</span>
  <div class="segmented fit" role="group" aria-labelledby="theme-label">
    {#each themes as [mode, label]}
      <button class="seg" class:on={theme.mode === mode} aria-pressed={theme.mode === mode} onclick={() => setTheme(mode)}>{t(label)}</button>
    {/each}
  </div>
  <span class="label spaced" id="language-label">{t('settings.language')}</span>
  <div class="segmented fit" role="group" aria-labelledby="language-label">
    {#each languages as [value, label]}
      <button class="seg" class:on={i18n.preference === value} aria-pressed={i18n.preference === value} onclick={() => setLanguage(value)}>{t(label)}</button>
    {/each}
  </div>
</section>

<style>
  .panel {
    padding: 24px;
  }

  h2 {
    margin: 0;
    font: 400 26px/1.2 var(--serif);
  }

  .desc {
    margin: 8px 0 16px;
    font: 400 14px/1.5 var(--sans);
    color: var(--ink-2);
  }

  .fit {
    width: fit-content;
  }

  .spaced {
    margin-top: 20px;
  }
</style>
