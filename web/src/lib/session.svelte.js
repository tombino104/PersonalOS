import { api, setUnauthorizedHandler } from './api.js';

export const session = $state({ status: 'loading', name: '' });

function signedOut() {
  session.status = 'anonymous';
  session.name = '';
}

setUnauthorizedHandler(signedOut);

export async function bootstrap() {
  try {
    const me = await api.me();
    session.name = me.name;
    session.status = 'authenticated';
  } catch {
    signedOut();
  }
}

export async function login(name, password) {
  const result = await api.login(name, password);
  session.name = result.name;
  session.status = 'authenticated';
}

export async function logout() {
  try {
    await api.logout();
  } catch {
  }
  signedOut();
}
