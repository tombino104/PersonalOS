<script>
  import { onMount, untrack } from 'svelte';
  import { ApiError, pluginRequest } from '$core/lib/api.js';
  import { formatDate } from '$core/lib/dates.js';
  import { locale, t } from '$core/lib/i18n.svelte.js';
  import { parseBirthday, toBirthday } from './people.js';

  let { person = null, onsaved, onclose } = $props();

  const start = untrack(() => parseBirthday(person?.birthday));
  let dialog;
  let name = $state(untrack(() => person?.name ?? ''));
  let day = $state(start?.day ?? '');
  let month = $state(start?.month ?? '');
  let year = $state(start?.year ?? '');
  let error = $state('');
  let busy = $state(false);
  let confirmDelete = $state(false);

  const months = Array.from({ length: 12 }, (_, index) => ({
    value: index + 1,
    label: formatDate(`2000-${String(index + 1).padStart(2, '0')}-01`, locale(), { month: 'long' }),
  }));

  onMount(() => {
    dialog.showModal();
  });

  async function save(event) {
    event.preventDefault();
    const birthday = toBirthday({ day, month, year });
    if (birthday === undefined) {
      error = t('plugin.people.invalid');
      return;
    }
    busy = true;
    error = '';
    const payload = { name: name.trim(), birthday };
    try {
      if (person) await pluginRequest('people', 'PUT', `/people/${person.id}`, payload);
      else await pluginRequest('people', 'POST', '/people', payload);
      onsaved();
    } catch (failure) {
      error = failure instanceof ApiError && failure.status === 422 ? t('plugin.people.invalid') : t('error.generic');
      busy = false;
    }
  }

  async function remove() {
    if (!confirmDelete) {
      confirmDelete = true;
      return;
    }
    busy = true;
    error = '';
    try {
      await pluginRequest('people', 'DELETE', `/people/${person.id}`);
      onsaved();
    } catch {
      error = t('error.generic');
      busy = false;
    }
  }
</script>

<dialog bind:this={dialog} class="card" aria-labelledby="person-dialog-title" {onclose}>
  <form onsubmit={save}>
    <h2 id="person-dialog-title">{person ? t('plugin.people.edit') : t('plugin.people.add')}</h2>

    <div>
      <label class="label" for="person-name">{t('plugin.people.name')}</label>
      <input id="person-name" class="field" type="text" maxlength="100" required bind:value={name} />
    </div>

    <div>
      <span class="label" id="person-birthday-label">{t('plugin.people.birthday')}</span>
      <div class="birthday" role="group" aria-labelledby="person-birthday-label">
        <input class="field day" type="number" min="1" max="31" inputmode="numeric" placeholder={t('plugin.people.day')} aria-label={t('plugin.people.day')} bind:value={day} />
        <select class="field month" aria-label={t('plugin.people.month')} bind:value={month}>
          <option value="">{t('plugin.people.month')}</option>
          {#each months as item (item.value)}
            <option value={item.value}>{item.label}</option>
          {/each}
        </select>
        <input class="field year" type="number" min="1900" max="2100" inputmode="numeric" placeholder={t('plugin.people.year')} aria-label={t('plugin.people.year')} bind:value={year} />
      </div>
      <p class="muted help">{t('plugin.people.birthdayHint')}</p>
    </div>

    {#if error}
      <p class="error" role="alert">{error}</p>
    {/if}

    <div class="actions">
      <button class="btn solid" type="submit" disabled={busy}>{t('common.save')}</button>
      <button class="btn" type="button" onclick={() => dialog.close()}>{t('common.cancel')}</button>
      {#if person}
        <button class="btn remove" type="button" disabled={busy} onclick={remove}>
          {confirmDelete ? t('plugin.people.deleteSure') : t('plugin.people.delete')}
        </button>
      {/if}
    </div>
  </form>
</dialog>

<style>
  dialog {
    width: min(440px, calc(100vw - 32px));
    padding: 24px;
    color: var(--ink);
    box-shadow: var(--shadow);
  }

  dialog::backdrop {
    background: rgba(28, 26, 23, 0.45);
  }

  form {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  h2 {
    margin: 0;
    font: 400 26px/1.2 var(--serif);
  }

  .birthday {
    display: flex;
    gap: 8px;
  }

  .day {
    flex: 0 0 76px;
  }

  .month {
    flex: 1 1 auto;
    appearance: auto;
  }

  .year {
    flex: 0 0 96px;
  }

  .help {
    margin: 8px 0 0;
    font: 400 13px/1.5 var(--sans);
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .remove {
    margin-left: auto;
    color: var(--danger);
  }
</style>
