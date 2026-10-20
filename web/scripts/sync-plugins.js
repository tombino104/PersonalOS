import { cpSync, existsSync, mkdirSync, readdirSync, rmSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

const source = resolve(process.env.PLUGINS_SOURCE ?? '../plugins');
const target = resolve('src/plugin-ui');

rmSync(target, { recursive: true, force: true });
mkdirSync(target, { recursive: true });

if (existsSync(source)) {
  for (const name of readdirSync(source)) {
    const ui = join(source, name, 'ui');
    const hidden = name.startsWith('_') || name.startsWith('.');
    if (!hidden && existsSync(ui) && statSync(ui).isDirectory()) {
      cpSync(ui, join(target, name), { recursive: true });
    }
  }
}
