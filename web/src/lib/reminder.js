import { api } from './api.js';
import { t } from './i18n.svelte.js';

const CACHE = 'personal-os-shell-v1';
const TEXT_FILE = 'reminder-text.json';

export function supported() {
  return (
    typeof window !== 'undefined' &&
    window.isSecureContext &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  );
}

export function blocker() {
  if (typeof window === 'undefined') return null;
  if (!window.isSecureContext) return 'insecure';
  if (supported()) return null;
  const apple = /iPhone|iPad|iPod/.test(navigator.userAgent);
  return apple && !navigator.standalone ? 'install' : 'unsupported';
}

export function keyBytes(value) {
  const padded = value + '='.repeat((4 - (value.length % 4)) % 4);
  const raw = atob(padded.replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(raw, (char) => char.charCodeAt(0));
}

async function registration() {
  return navigator.serviceWorker.ready;
}

export async function currentSubscription() {
  if (!supported()) return null;
  return (await registration()).pushManager.getSubscription();
}

export async function syncText() {
  if (!supported()) return;
  try {
    const scope = (await registration()).scope;
    const cache = await caches.open(CACHE);
    const body = JSON.stringify({ title: t('reminder.notificationTitle'), body: t('reminder.notificationBody') });
    await cache.put(new URL(TEXT_FILE, scope).href, new Response(body, { headers: { 'Content-Type': 'application/json' } }));
  } catch {
  }
}

export async function enableDevice() {
  if ((await Notification.requestPermission()) !== 'granted') return 'denied';
  const worker = await registration();
  let subscription = await worker.pushManager.getSubscription();
  if (!subscription) {
    const { public_key } = await api.pushStatus();
    subscription = await worker.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: keyBytes(public_key),
    });
  }
  await api.pushSubscribe(subscription.endpoint);
  await api.updateSettings({ reminder_enabled: true });
  await syncText();
  return 'granted';
}

export async function disableDevice() {
  const subscription = await currentSubscription();
  if (!subscription) return;
  const { endpoint } = subscription;
  await subscription.unsubscribe();
  const { devices } = await api.pushUnsubscribe(endpoint);
  if (devices === 0) await api.updateSettings({ reminder_enabled: false });
}
