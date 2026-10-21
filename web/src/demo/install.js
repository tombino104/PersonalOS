import { createDemoServer } from './server.js';

const API = '/api/v1';
const FLAG = 'personal-os-demo-empty';
const REPO = 'https://github.com/tombino104/PersonalOS';

function readFlag() {
  try {
    return sessionStorage.getItem(FLAG) === '1';
  } catch {
    return false;
  }
}

function writeFlag(on) {
  try {
    if (on) sessionStorage.setItem(FLAG, '1');
    else sessionStorage.removeItem(FLAG);
  } catch {
  }
}

const COPY = {
  en: { text: 'Live demo with made-up data. Nothing leaves your browser, and a reload starts over.', link: 'Get Personal OS', close: 'Close' },
  it: { text: 'Demo con dati inventati. Niente lascia il tuo browser e, se ricarichi, si riparte da zero.', link: 'Scarica Personal OS', close: 'Chiudi' },
};

function banner() {
  const copy = (navigator.language ?? 'en').toLowerCase().startsWith('it') ? COPY.it : COPY.en;
  const bar = document.createElement('div');
  bar.setAttribute('role', 'note');
  bar.style.cssText =
    'display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;padding:8px 16px;' +
    'background:var(--paper-2);color:var(--ink-2);border-bottom:1px solid var(--line);' +
    'font:400 13px/1.4 var(--sans);text-align:center;';
  const text = document.createElement('span');
  text.textContent = copy.text;
  const link = document.createElement('a');
  link.href = REPO;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  link.textContent = copy.link;
  link.style.cssText = 'color:var(--ink);font-weight:500;';
  const close = document.createElement('button');
  close.type = 'button';
  close.textContent = '×';
  close.setAttribute('aria-label', copy.close);
  close.style.cssText = 'border:0;background:none;color:inherit;font:inherit;font-size:18px;cursor:pointer;padding:0 4px;';
  close.addEventListener('click', () => bar.remove());
  bar.append(text, link, close);
  document.body.prepend(bar);
}

export function installDemo({ version = 'demo' } = {}) {
  const server = createDemoServer({ version, empty: readFlag() });
  const realFetch = window.fetch.bind(window);

  window.fetch = async (input, init = {}) => {
    const url = new URL(typeof input === 'string' ? input : input.url, location.origin);
    const isApi = url.pathname.startsWith(API);
    if (!isApi && url.pathname !== '/health') return realFetch(input, init);
    const method = (init.method ?? 'GET').toUpperCase();
    let result;
    if (!isApi) {
      result = { status: 200, data: { status: 'ok', version } };
    } else {
      let body;
      if (typeof init.body === 'string') {
        try {
          body = JSON.parse(init.body);
        } catch {
          body = undefined;
        }
      }
      result = server.handle(method, url.pathname.slice(API.length), url.searchParams, body);
      if (result.status < 400) {
        const path = url.pathname.slice(API.length);
        if (path === '/auth/reset') writeFlag(true);
        if (path === '/auth/setup') writeFlag(false);
      }
    }
    return new Response(JSON.stringify(result.data), {
      status: result.status,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  banner();
}
