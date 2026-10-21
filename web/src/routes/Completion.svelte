<script>
  import { onMount } from 'svelte';
  import Link from '../components/Link.svelte';
  import { api } from '../lib/api.js';
  import { formatDate, parseDay } from '../lib/dates.js';
  import { locale, t } from '../lib/i18n.svelte.js';
  import { router } from '../lib/router.svelte.js';
  import { displayName } from '../lib/profile.svelte.js';

  let today = $state('');
  const day = $derived(router.query.get('day') ?? today);

  onMount(async () => {
    try {
      today = (await api.today()).day;
    } catch {
      today = '';
    }
  });

  const number = $derived(day ? parseDay(day).getUTCDate() : '');
  const monthYear = $derived(day ? formatDate(day, locale(), { month: 'long', year: 'numeric' }) : '');
  const until = $derived(day === today ? t('completion.untilTomorrow') : t('completion.untilTonight'));
</script>

<div class="content narrow done">
  <div class="stamp-wrap">
    <span class="halo"></span>
    <svg
      class="stamp"
      viewBox="0 0 236 236"
      role="img"
      aria-label={t('completion.stampLabel', { date: `${number} ${monthYear}` })}
    >
      <defs>
        <filter id="rough" x="-5%" y="-5%" width="110%" height="110%">
          <feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="4" result="noise" />
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="2.6" />
        </filter>
        <path id="ring" d="M118 118 m-84 0 a84 84 0 1 1 168 0 a84 84 0 1 1 -168 0" />
      </defs>
      <g filter="url(#rough)" fill="none" stroke="currentColor">
        <circle cx="118" cy="118" r="112" stroke-width="3" />
        <circle cx="118" cy="118" r="104" stroke-width="1" />
        <circle cx="118" cy="118" r="66" stroke-width="1" />
        <text fill="currentColor" stroke="none" class="ring-text">
          <textPath href="#ring" startOffset="0">{t('completion.ring')}</textPath>
        </text>
        <text x="118" y="128" text-anchor="middle" fill="currentColor" stroke="none" class="stamp-number">{number}</text>
        <text x="118" y="154" text-anchor="middle" fill="currentColor" stroke="none" class="stamp-month">{monthYear}</text>
        <path d="M96 84h44" stroke-width="1" />
      </g>
    </svg>
  </div>

  <div class="message">
    <h1>{t('completion.titleStart')} <em>{t('completion.titleEmphasis')}</em>{t('completion.titleEnd')}</h1>
    <p>{t('completion.body', { name: displayName(), until })}</p>
  </div>

  <Link class="home-link message" href="/">{t('completion.home')}</Link>
</div>

<style>
  .done {
    align-items: center;
    justify-content: center;
    gap: 40px;
    padding-bottom: 80px;
    text-align: center;
  }

  .stamp-wrap {
    position: relative;
    width: 236px;
    height: 236px;
  }

  .stamp {
    width: 236px;
    height: 236px;
    color: var(--stamp);
    transform: rotate(-8deg);
    opacity: 0.94;
  }

  .halo {
    position: absolute;
    inset: 6px;
    border: 1.5px solid var(--stamp);
    border-radius: 50%;
    opacity: 0;
  }

  .ring-text {
    font: 600 14.5px 'DM Sans', system-ui, sans-serif;
    letter-spacing: 0.34em;
  }

  .stamp-number {
    font: 500 62px 'Newsreader', Georgia, serif;
  }

  .stamp-month {
    font: italic 400 17px 'Newsreader', Georgia, serif;
    letter-spacing: 0.04em;
  }

  h1 {
    margin: 0;
    font: 400 34px/1.15 var(--serif);
    letter-spacing: -0.01em;
  }

  p {
    margin: 12px 0 0;
    font: 400 16px/1.5 var(--sans);
    color: var(--ink-2);
  }

  .done :global(.home-link) {
    min-height: 52px;
    padding: 0 28px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface);
    font: 500 15px/1 var(--sans);
    display: flex;
    align-items: center;
    justify-content: center;
    text-decoration: none;
  }

  @media (prefers-reduced-motion: no-preference) {
    .stamp {
      transform-origin: 50% 50%;
      animation: stamp-in 0.75s cubic-bezier(0.2, 1.2, 0.3, 1) 0.2s 1 both;
    }

    .halo {
      animation: ink 1.4s ease-out 0.55s 1 both;
    }

    .message {
      animation: message-in 0.8s ease-out 0.8s 1 both;
    }
  }

  @keyframes stamp-in {
    0% { transform: rotate(-16deg) scale(1.7); opacity: 0; }
    55% { opacity: 1; }
    72% { transform: rotate(-8deg) scale(0.95); }
    100% { transform: rotate(-8deg) scale(1); opacity: 0.94; }
  }

  @keyframes ink {
    0% { transform: scale(1); opacity: 0.5; }
    100% { transform: scale(1.35); opacity: 0; }
  }

  @keyframes message-in {
    0% { transform: translateY(10px); opacity: 0; }
    100% { transform: translateY(0); opacity: 1; }
  }
</style>
