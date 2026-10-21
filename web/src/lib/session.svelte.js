import { api, setUnauthorizedHandler } from './api.js';

export const session = $state({ status: 'loading', name: '', codeRequired: true });

async function signedOut() {
  session.name = '';
  try {
    const result = await api.authStatus();
    session.codeRequired = result.setup_code_required !== false;
    session.status = result.setup_required ? 'setup' : 'anonymous';
  } catch {
    session.status = 'anonymous';
  }
}

setUnauthorizedHandler(signedOut);

export async function bootstrap() {
  try {
    const me = await api.me();
    session.name = me.name;
    session.status = 'authenticated';
  } catch {
    await signedOut();
  }
}

export async function login(name, password) {
  const result = await api.login(name, password);
  session.name = result.name;
  session.status = 'authenticated';
}

export async function setup(code, name, password) {
  const result = await api.setup(code, name, password);
  session.name = result.name;
  session.status = 'authenticated';
}

export async function reset(code, name, password) {
  const result = await api.reset(code, name, password);
  session.name = result.name;
  session.status = 'authenticated';
}

export async function logout() {
  try {
    await api.logout();
  } catch {
  }
  await signedOut();
}
