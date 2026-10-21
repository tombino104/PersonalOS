import { api } from './api.js';
import { session } from './session.svelte.js';

export const profile = $state({
  loaded: false,
  display_name: null,
  about: null,
  birth_year: null,
  has_photo: false,
  version: null,
});

function apply(data) {
  Object.assign(profile, data, { loaded: true });
}

export async function loadProfile() {
  try {
    apply(await api.profile());
  } catch {
    profile.loaded = true;
  }
}

export async function saveProfile(details) {
  apply(await api.updateProfile(details));
}

export async function savePhoto(blob) {
  apply(await api.uploadPhoto(blob));
}

export async function deletePhoto() {
  apply(await api.removePhoto());
}

export const displayName = () => profile.display_name || session.name;
export const photoSrc = () => (profile.has_photo ? api.photoUrl(profile.version) : null);
