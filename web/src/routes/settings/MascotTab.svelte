<script>
  import { untrack } from 'svelte';
  import Avatar from '../../components/Avatar.svelte';
  import { ApiError } from '../../lib/api.js';
  import { resizePhoto } from '../../lib/image.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { deletePhoto, profile, savePhoto, saveProfile } from '../../lib/profile.svelte.js';
  import { session } from '../../lib/session.svelte.js';

  let name = $state(untrack(() => profile.display_name ?? ''));
  let about = $state(untrack(() => profile.about ?? ''));
  let birthYear = $state(untrack(() => profile.birth_year ?? ''));
  let busy = $state(false);
  let message = $state('');
  let error = $state('');
  let fileInput;

  $effect(() => {
    if (profile.loaded) {
      untrack(() => {
        name = profile.display_name ?? '';
        about = profile.about ?? '';
        birthYear = profile.birth_year ?? '';
      });
    }
  });

  async function run(action, success) {
    busy = true;
    message = '';
    error = '';
    try {
      await action();
      message = success;
    } catch (failure) {
      error = failure instanceof ApiError && failure.status === 422 ? t('mascot.invalid') : t('error.generic');
    } finally {
      busy = false;
    }
  }

  function saveDetails(event) {
    event.preventDefault();
    return run(
      () =>
        saveProfile({
          display_name: name.trim() || null,
          about: about.trim() || null,
          birth_year: birthYear === '' ? null : Number(birthYear),
        }),
      t('mascot.saved'),
    );
  }

  async function choosePhoto(event) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = '';
    if (!file) return;
    await run(async () => savePhoto(await resizePhoto(file)), t('mascot.photoSaved'));
  }
</script>

<section class="card panel" aria-label={t('settings.mascot')}>
  <h2>{t('settings.mascot')}</h2>
  <p class="desc">{t('mascot.lede')}</p>

  <div class="photo">
    <Avatar size={96} />
    <div class="photo-actions">
      <button class="btn" type="button" disabled={busy} onclick={() => fileInput.click()}>
        {profile.has_photo ? t('mascot.changePhoto') : t('mascot.addPhoto')}
      </button>
      {#if profile.has_photo}
        <button class="btn" type="button" disabled={busy} onclick={() => run(deletePhoto, t('mascot.photoRemoved'))}>
          {t('mascot.removePhoto')}
        </button>
      {/if}
      <input
        bind:this={fileInput}
        class="hidden"
        type="file"
        accept="image/*"
        aria-label={t('mascot.addPhoto')}
        onchange={choosePhoto}
      />
    </div>
  </div>

  <form onsubmit={saveDetails}>
    <div>
      <label class="label" for="mascot-name">{t('mascot.name')}</label>
      <input id="mascot-name" class="field" type="text" maxlength="60" placeholder={session.name} bind:value={name} />
      <p class="muted help">{t('mascot.nameHelp')}</p>
    </div>
    <div>
      <label class="label" for="mascot-about">{t('mascot.about')}</label>
      <textarea id="mascot-about" class="field" rows="4" maxlength="500" bind:value={about}></textarea>
    </div>
    <div class="year">
      <label class="label" for="mascot-year">{t('mascot.birthYear')}</label>
      <input id="mascot-year" class="field" type="number" min="1900" max="2100" inputmode="numeric" bind:value={birthYear} />
    </div>
    {#if error}
      <p class="error" role="alert">{error}</p>
    {:else if message}
      <p class="muted" role="status">{message}</p>
    {/if}
    <div>
      <button class="btn solid" type="submit" disabled={busy}>{t('common.save')}</button>
    </div>
  </form>
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
    margin: 8px 0 20px;
    font: 400 14px/1.5 var(--sans);
    color: var(--ink-2);
  }

  .photo {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 20px;
    margin-bottom: 24px;
  }

  .photo-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .hidden {
    display: none;
  }

  form {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .help {
    margin: 8px 0 0;
    font: 400 13px/1.5 var(--sans);
  }

  .year {
    max-width: 160px;
  }
</style>
