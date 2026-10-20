import { createServer } from 'node:http';
import { accessSync, constants, readFileSync } from 'node:fs';

const PORT = Number(process.env.PORT ?? 3000);
const DATA_DIR = process.env.DATA_DIR ?? './data';
const { version } = JSON.parse(
  readFileSync(new URL('../package.json', import.meta.url), 'utf8'),
);

function cartellaDatiScrivibile() {
  try {
    accessSync(DATA_DIR, constants.R_OK | constants.W_OK);
    return true;
  } catch {
    return false;
  }
}

const server = createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    const datiOk = cartellaDatiScrivibile();
    res.writeHead(datiOk ? 200 : 503, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ stato: datiOk ? 'ok' : 'errore', versione: version, dati: datiOk }));
    return;
  }
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ errore: 'non trovato' }));
});

server.listen(PORT, () => {
  console.log(`Personal OS v${version} in ascolto sulla porta ${PORT}`);
});

for (const segnale of ['SIGTERM', 'SIGINT']) {
  process.on(segnale, () => server.close(() => process.exit(0)));
}
